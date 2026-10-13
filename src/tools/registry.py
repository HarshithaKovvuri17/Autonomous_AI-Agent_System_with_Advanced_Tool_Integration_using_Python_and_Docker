"""
ToolRegistry for managing and orchestrating agent tools.
Enforces schemas and provides tool contracts for system prompts.
"""
import json
import logging
import traceback
from typing import Any, Dict, List, Optional
from src.tools.base import BaseTool, ToolValidationError

logger = logging.getLogger("AgentSystem.Registry")


class ToolNotFoundError(Exception):
    """Raised when the agent attempts to invoke an unregistered tool."""
    pass


class ToolRegistry:
    """
    Central repository for registering, retrieving, and inspecting available tools.
    """

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool instance in the registry."""
        if not isinstance(tool, BaseTool):
            raise TypeError(f"Tool must be an instance of BaseTool, got {type(tool).__name__}")
        self._tools[tool.name] = tool
        logger.debug(f"Registered tool: '{tool.name}' (Approval Required: {tool.requires_approval})")

    def get_tool(self, name: str) -> BaseTool:
        """Retrieve a registered tool by name. Raises ToolNotFoundError if not found."""
        tool = self._tools.get(name)
        if not tool:
            available = ", ".join(self._tools.keys())
            raise ToolNotFoundError(
                f"Tool '{name}' is not registered. Available tools: [{available}]"
            )
        return tool

    def has_tool(self, name: str) -> bool:
        """Check if a tool exists in the registry."""
        return name in self._tools

    def list_tools(self) -> List[str]:
        """Return list of registered tool names."""
        return list(self._tools.keys())

    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """
        Generate a consolidated list of all registered tools, their descriptions,
        and JSON Schemas for injection into the ReAct system prompt.
        """
        return [tool.get_schema() for tool in self._tools.values()]

    def get_tools_prompt_string(self) -> str:
        """Format the tools schema as an indented JSON string for the prompt."""
        return json.dumps(self.get_tools_schema(), indent=2)

    def execute_tool(self, name: str, args: Any) -> str:
        """
        Execute tool with robust exception handling.
        All exceptions are caught and formatted as observations for the ReAct loop
        to facilitate autonomous replanning and recovery.
        """
        try:
            tool = self.get_tool(name)
            return tool.run(args)
        except ToolNotFoundError as e:
            return f"Tool Error: {str(e)}"
        except ToolValidationError as e:
            return f"Validation Error: {str(e)}"
        except Exception as e:
            logger.error(f"Execution failure in tool '{name}': {e}\n{traceback.format_exc()}")
            return f"Execution Error in tool '{name}': {str(e)}"
