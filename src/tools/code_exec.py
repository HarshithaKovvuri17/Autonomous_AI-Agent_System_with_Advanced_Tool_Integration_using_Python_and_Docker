"""
Code Execution Tool.
Executes Python code in a secure, sandboxed Docker container with strict resource limits and timeouts.
Requires human-in-the-loop approval before invocation.
"""
import logging
from typing import Optional
from pydantic import BaseModel, Field
from src.tools.base import BaseTool
from src.sandbox.docker_runner import DockerSandboxRunner

logger = logging.getLogger("AgentSystem.Tools.CodeExec")


class CodeExecutionInput(BaseModel):
    code: str = Field(
        ...,
        description="The Python code snippet to execute inside the isolated Docker sandbox."
    )


class CodeExecutionTool(BaseTool):
    """
    Tool for safely executing arbitrary Python code inside an ephemeral, network-isolated Docker container.
    Guards host security, imposes a 15-second execution timeout, and requires explicit human approval.
    """
    name: str = "code_execution"
    description: str = (
        "Use this tool to execute Python code in an isolated Docker sandbox container. "
        "Useful for dynamic computations, data processing, algorithms, and simulation. "
        "Code has no network access and runs in a strictly limited environment. "
        "Input must be valid Python code as a string in the 'code' parameter."
    )
    args_schema = CodeExecutionInput
    # High-risk tool: requires Human-in-the-Loop approval
    requires_approval: bool = True

    def __init__(self, runner: Optional[DockerSandboxRunner] = None):
        self.runner = runner or DockerSandboxRunner()

    def execute(self, code: str) -> str:
        if not code.strip():
            return "Observation: Code string cannot be empty."

        result = self.runner.run_code(code)
        return result

