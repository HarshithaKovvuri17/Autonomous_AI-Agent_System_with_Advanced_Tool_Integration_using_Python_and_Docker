"""
Shared fixtures and setup for unit and integration test suite.
Mocks Docker SDK, external APIs, and isolates temporary directories.
"""
import os
import shutil
import tempfile
from unittest.mock import MagicMock
import pytest

from src.tools.registry import ToolRegistry
from src.tools.search import WebSearchTool
from src.tools.calculator import CalculatorTool
from src.tools.api import ApiTool
from src.tools.filesystem import FileSystemTool
from src.tools.code_exec import CodeExecutionTool
from src.logger import tracer


@pytest.fixture
def temp_workspace():
    """Create an isolated temporary workspace directory for filesystem tests."""
    temp_dir = tempfile.mkdtemp(prefix="test_workspace_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def clean_trace_file(tmp_path):
    """Provide a clean isolated execution_trace.jsonl path."""
    trace_path = tmp_path / "execution_trace.jsonl"
    old_file = tracer.trace_file
    tracer.trace_file = str(trace_path)
    yield str(trace_path)
    tracer.trace_file = old_file


@pytest.fixture
def mock_docker_client():
    """Mock Docker SDK client for container orchestration tests."""
    client = MagicMock()
    container = MagicMock()
    container.wait.return_value = {"StatusCode": 0}
    container.logs.return_value = b"Hello from isolated Docker sandbox!\n"
    container.kill.return_value = None
    container.remove.return_value = None
    client.containers.run.return_value = container
    return client, container


@pytest.fixture
def standard_registry(temp_workspace, mock_docker_client):
    """Provide a fully populated ToolRegistry with all 5 core tools."""
    client, _ = mock_docker_client
    registry = ToolRegistry()
    registry.register(WebSearchTool())
    registry.register(CalculatorTool())
    registry.register(ApiTool())
    registry.register(FileSystemTool(workspace_dir=temp_workspace))
    registry.register(CodeExecutionTool(runner=MagicMock(run_code=MagicMock(return_value="Mocked code output"))))
    return registry
