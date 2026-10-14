"""Unit tests for Docker Sandboxed Code Execution Tool."""
from unittest.mock import patch, MagicMock
import pytest
import requests
from src.tools.code_exec import CodeExecutionTool
from src.sandbox.docker_runner import DockerSandboxRunner
from src.tools.base import ToolValidationError


def test_code_exec_successful_execution(mock_docker_client):
    client, container = mock_docker_client
    runner = DockerSandboxRunner(client=client, timeout=15)
    tool = CodeExecutionTool(runner=runner)

    assert tool.requires_approval is True

    result = tool.execute("print('Hello from isolated Docker sandbox!')")

    # Assert Docker run was called with mandatory security constraints
    client.containers.run.assert_called_once()
    call_kwargs = client.containers.run.call_args[1]
    assert call_kwargs["network_disabled"] is True
    assert call_kwargs["mem_limit"] == "128m"
    assert call_kwargs["detach"] is True

    # Assert volume is mounted as read-only
    volumes = call_kwargs["volumes"]
    mounted_mode = list(volumes.values())[0]["mode"]
    assert mounted_mode == "ro"

    # Assert container cleanup was triggered
    container.remove.assert_called_once_with(force=True)

    assert "Hello from isolated Docker sandbox!" in result


def test_code_exec_timeout_enforcement(mock_docker_client):
    client, container = mock_docker_client
    # Simulate timeout during wait
    container.wait.side_effect = requests.exceptions.ReadTimeout("Container execution timed out")

    runner = DockerSandboxRunner(client=client, timeout=5)
    tool = CodeExecutionTool(runner=runner)

    result = tool.execute("while True: pass")

    # Assert container was forcefully killed
    container.kill.assert_called_once()
    # Assert container was removed
    container.remove.assert_called_once_with(force=True)
    # Assert Contract Specification observation
    assert "Execution timed out" in result


def test_code_exec_docker_unavailable():
    from docker.errors import DockerException
    with patch("docker.from_env", side_effect=DockerException("Docker daemon not running")):
        runner = DockerSandboxRunner(timeout=10)
        tool = CodeExecutionTool(runner=runner)
        result = tool.execute("print('test')")
        assert "Docker Sandbox Error" in result or "Docker daemon" in result


def test_code_exec_empty_code():
    tool = CodeExecutionTool()
    res = tool.execute("   ")
    assert "cannot be empty" in res


def test_code_exec_schema_validation():
    tool = CodeExecutionTool()
    with pytest.raises(ToolValidationError):
        tool.run({})
