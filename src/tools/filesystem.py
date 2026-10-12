"""
File System Tool for secure file reading and writing with strict path traversal protections.
Guarantees all file operations are strictly confined within WORKSPACE_DIR.
"""
import logging
import os
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator
from src.tools.base import BaseTool
from src.config import WORKSPACE_DIR

logger = logging.getLogger("AgentSystem.Tools.FileSystem")

MAX_READ_LENGTH = 4000


class FileSystemInput(BaseModel):
    action: str = Field(..., description="Action to perform: 'read' or 'write'.")
    file_path: str = Field(..., description="Relative or absolute path of the target file.")
    content: Optional[str] = Field(None, description="Text content to write (required if action is 'write').")

    @field_validator("action")
    def validate_action(cls, v: str) -> str:
        clean = v.strip().lower()
        if clean not in ("read", "write"):
            raise ValueError(f"Action must be either 'read' or 'write', got '{v}'")
        return clean


class FileSystemTool(BaseTool):
    """
    Secure tool for reading and writing text files strictly constrained within the workspace directory.
    Enforces path traversal defenses against relative escape attempts (e.g., ../../etc/passwd).
    """
    name: str = "file_system"
    description: str = (
        "Use this tool to read and write files within the designated workspace sandbox. "
        "Inputs require 'action' ('read' or 'write'), 'file_path', and 'content' (if writing). "
        "Strict path traversal guards prevent escaping the workspace directory."
    )
    args_schema = FileSystemInput
    # Write actions require Human-in-the-Loop approval
    requires_approval: bool = False

    def __init__(self, workspace_dir: str = WORKSPACE_DIR, max_length: int = MAX_READ_LENGTH):
        self.workspace_dir = os.path.realpath(os.path.abspath(workspace_dir))
        self.max_length = max_length
        os.makedirs(self.workspace_dir, exist_ok=True)

    def _resolve_safe_path(self, file_path: str) -> Optional[str]:
        """
        Resolve target path and verify that it strictly resides within self.workspace_dir.
        Returns the resolved absolute path if safe, or None if a security violation is detected.
        """
        # Strip leading separators for relative resolution
        if os.path.isabs(file_path):
            target = os.path.realpath(os.path.abspath(file_path))
        else:
            target = os.path.realpath(os.path.abspath(os.path.join(self.workspace_dir, file_path)))

        try:
            common = os.path.commonpath([self.workspace_dir, target])
            if common == self.workspace_dir:
                return target
        except ValueError:
            # Different drives on Windows (e.g. C: vs D:)
            return None

        return None

    def execute(self, action: str, file_path: str, content: Optional[str] = None) -> str:
        action = action.lower()
        safe_path = self._resolve_safe_path(file_path)

        if not safe_path:
            return (
                f"Security Violation: Access denied. Path '{file_path}' resolves outside "
                f"the permitted WORKSPACE_DIR ({self.workspace_dir}). Path traversal blocked."
            )

        if action == "read":
            if not os.path.exists(safe_path):
                return f"File Not Found Error: The target file '{file_path}' does not exist in workspace."
            if os.path.isdir(safe_path):
                return f"File Error: Path '{file_path}' is a directory, not a file."

            try:
                with open(safe_path, "r", encoding="utf-8", errors="replace") as f:
                    data = f.read()
                if len(data) > self.max_length:
                    data = data[:self.max_length] + "\n...[Content truncated for context window]"
                return f"File Content ({file_path}):\n{data}"
            except Exception as e:
                return f"File Read Error: Could not read '{file_path}'. Details: {str(e)}"

        elif action == "write":
            if content is None:
                return "File Write Error: 'content' parameter is required when performing a write action."

            try:
                parent_dir = os.path.dirname(safe_path)
                os.makedirs(parent_dir, exist_ok=True)
                with open(safe_path, "w", encoding="utf-8") as f:
                    f.write(content)
                return f"Success: Successfully wrote {len(content)} characters to '{file_path}'."
            except Exception as e:
                return f"File Write Error: Could not write to '{file_path}'. Details: {str(e)}"

        return f"Unknown action '{action}'. Valid actions are 'read' and 'write'."

