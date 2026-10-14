"""
Docker Sandbox Runner.
Manages ephemeral, network-disabled, memory-capped Docker containers for executing untrusted code safely.
Enforces strict execution timeout and automatic container removal.
"""
import logging
import os
import shutil
import tempfile
import time
from typing import Optional
import docker
from docker.errors import DockerException, NotFound, APIError
import requests
from src.config import CONTAINER_TIMEOUT_SECONDS, CONTAINER_MEMORY_LIMIT, SANDBOX_IMAGE

logger = logging.getLogger("AgentSystem.Sandbox.Docker")


class DockerSandboxRunner:
    """
    Executes Python scripts inside ephemeral Docker containers with strict security constraints:
    - Kernel isolation
    - Network disabled (network_disabled=True)
    - Memory cap (e.g., 128m)
    - Read-only volume mounting of temporary script directory
    - Forceful timeout termination (killing container after timeout)
    - Guaranteed cleanup
    """

    def __init__(
        self,
        image: str = SANDBOX_IMAGE,
        timeout: int = CONTAINER_TIMEOUT_SECONDS,
        mem_limit: str = CONTAINER_MEMORY_LIMIT,
        client: Optional[docker.DockerClient] = None
    ):
        self.image = image
        self.timeout = timeout
        self.mem_limit = mem_limit
        self._client = client

    def get_client(self) -> docker.DockerClient:
        """Obtain or initialize the Docker client."""
        if self._client is not None:
            return self._client
        try:
            self._client = docker.from_env()
            return self._client
        except DockerException as e:
            logger.error(f"Failed to connect to Docker daemon: {e}")
            raise

    def run_code(self, code: str) -> str:
        """
        Execute the provided Python code string inside an isolated ephemeral Docker container.
        Returns the captured stdout/stderr, or 'Execution timed out' if execution exceeds timeout.
        """
        temp_dir = tempfile.mkdtemp(prefix="agent_sandbox_")
        container = None
        try:
            # Write code to temp script
            script_path = os.path.join(temp_dir, "script.py")
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(code)

            # Ensure Docker client is reachable
            try:
                client = self.get_client()
            except DockerException as e:
                return f"Docker Sandbox Error: Could not connect to Docker daemon ({str(e)}). Ensure Docker is running."

            # Mount temporary directory as read-only inside container
            volumes = {
                os.path.abspath(temp_dir): {
                    "bind": "/sandbox",
                    "mode": "ro"
                }
            }

            logger.info(f"Starting ephemeral sandbox container (Image: {self.image}, Timeout: {self.timeout}s, Mem: {self.mem_limit})")

            # Launch detached container with strict security settings
            container = client.containers.run(
                image=self.image,
                command=["python", "-u", "/sandbox/script.py"],
                volumes=volumes,
                network_disabled=True,
                mem_limit=self.mem_limit,
                detach=True,
                stdout=True,
                stderr=True
            )

            # Enforce execution timeout via polling or wait
            start_time = time.time()
            timed_out = False

            try:
                # Wait for container execution with timeout
                result = container.wait(timeout=self.timeout)
                exit_code = result.get("StatusCode", 0) if isinstance(result, dict) else result
            except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError):
                timed_out = True
            except Exception as e:
                if "timeout" in str(e).lower():
                    timed_out = True
                else:
                    raise

            # Double check elapsed time if container.wait did not raise
            if time.time() - start_time >= self.timeout:
                timed_out = True

            if timed_out:
                logger.warning(f"Container exceeded {self.timeout}s timeout. Terminating container forcefully.")
                try:
                    container.kill()
                except Exception as kill_err:
                    logger.debug(f"Error killing timed out container: {kill_err}")
                return "Execution timed out"

            # Capture logs from container
            logs = container.logs(stdout=True, stderr=True).decode("utf-8", errors="replace")

            if exit_code != 0:
                return f"Execution Error (Exit Code {exit_code}):\n{logs}"

            return logs if logs.strip() else "[Code executed successfully with no stdout]"

        except Exception as e:
            logger.error(f"Sandbox execution error: {e}")
            return f"Sandbox Execution Failure: {str(e)}"

        finally:
            # Ephemeral cleanup: forcefully remove container
            if container is not None:
                try:
                    container.remove(force=True)
                except Exception:
                    pass

            # Clean up host temporary directory
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass
