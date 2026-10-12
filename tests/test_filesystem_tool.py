"""Unit tests for File System Tool with path traversal defenses."""
import os
import pytest
from src.tools.filesystem import FileSystemTool
from src.tools.base import ToolValidationError


def test_filesystem_write_and_read(temp_workspace):
    fs = FileSystemTool(workspace_dir=temp_workspace)

    # Write file
    write_res = fs.execute(action="write", file_path="notes.txt", content="Hello, Sandboxed World!")
    assert "Successfully wrote" in write_res
    assert os.path.exists(os.path.join(temp_workspace, "notes.txt"))

    # Read file back
    read_res = fs.execute(action="read", file_path="notes.txt")
    assert "Hello, Sandboxed World!" in read_res


def test_filesystem_nested_directory(temp_workspace):
    fs = FileSystemTool(workspace_dir=temp_workspace)
    write_res = fs.execute(action="write", file_path="sub/dir/nested.txt", content="Nested data")
    assert "Successfully wrote" in write_res

    read_res = fs.execute(action="read", file_path="sub/dir/nested.txt")
    assert "Nested data" in read_res


def test_filesystem_blocks_relative_path_traversal(temp_workspace):
    fs = FileSystemTool(workspace_dir=temp_workspace)
    res = fs.execute(action="read", file_path="../../etc/passwd")
    assert "Security Violation" in res
    assert "Path traversal blocked" in res

    res_write = fs.execute(action="write", file_path="../../../root/.ssh/id_rsa", content="evil")
    assert "Security Violation" in res_write


def test_filesystem_blocks_absolute_escape(temp_workspace):
    fs = FileSystemTool(workspace_dir=temp_workspace)
    # Attempting to read outside absolute path
    res = fs.execute(action="read", file_path="C:/Windows/System32/drivers/etc/hosts")
    assert "Security Violation" in res or "File Not Found" in res or "Access denied" in res


def test_filesystem_file_not_found(temp_workspace):
    fs = FileSystemTool(workspace_dir=temp_workspace)
    res = fs.execute(action="read", file_path="nonexistent.txt")
    assert "File Not Found Error" in res


def test_filesystem_schema_validation(temp_workspace):
    fs = FileSystemTool(workspace_dir=temp_workspace)
    
    # Valid run
    res = fs.run({"action": "write", "file_path": "test.txt", "content": "Valid run"})
    assert "Successfully wrote" in res

    # Invalid action
    with pytest.raises(ToolValidationError):
        fs.run({"action": "delete", "file_path": "test.txt"})

    # Missing file_path
    with pytest.raises(ToolValidationError):
        fs.run({"action": "read"})
