"""Base interface and abstraction for agent tools."""
from abc import ABC, abstractmethod
from typing import Any, Dict, Type
from pydantic import BaseModel, ValidationError


class ToolValidationError(Exception):
    """Raised when tool input validation against Pydantic schema fails."""
    pass


class BaseTool(ABC):
    """
    Abstract base class for all tools in the Autonomous AI Agent System.
    Mandates name, description, args_schema, and an execution interface.
    """
    name: str
    description: str
    args_schema: Type[BaseModel]
    requires_approval: bool = False

    @abstractmethod
    def execute(self, **kwargs) -> str:
        """
        Execute the tool with validated keyword arguments.
        Must return a string observation to be passed back to the agent memory.
        """
        pass

    def validate_args(self, args: Any) -> BaseModel:
        """
        Validate raw arguments against the Pydantic args_schema.
        Raises ToolValidationError on failure.
        """
        if isinstance(args, str):
            # If string was passed to a single-field schema or needs conversion
            fields = list(self.args_schema.model_fields.keys())
            if len(fields) == 1:
                args = {fields[0]: args}
            else:
                raise ToolValidationError(
                    f"Tool '{self.name}' expects a JSON dictionary with fields {fields}, but received string: {args}"
                )

        if not isinstance(args, dict):
            raise ToolValidationError(
                f"Tool '{self.name}' expects dictionary arguments, received {type(args).__name__}"
            )

        try:
            return self.args_schema(**args)
        except ValidationError as e:
            # Provide clear message for agent to re-plan
            error_details = []
            for err in e.errors():
                loc = ".".join(str(p) for p in err.get("loc", []))
                msg = err.get("msg", "invalid")
                error_details.append(f"Field '{loc}': {msg}")
            raise ToolValidationError(f"Invalid parameters for tool '{self.name}': {'; '.join(error_details)}")

    def run(self, args: Any) -> str:
        """
        Entry point to validate arguments and execute the tool safely.
        """
        validated = self.validate_args(args)
        # Compatible with Pydantic v2 model_dump or v1 dict
        dump_kwargs = getattr(validated, "model_dump", None)
        kwargs = dump_kwargs() if callable(dump_kwargs) else validated.dict()
        return self.execute(**kwargs)

    def get_schema(self) -> Dict[str, Any]:
        """
        Return the tool metadata and JSON Schema representation for LLM prompt injection.
        """
        schema_method = getattr(self.args_schema, "model_json_schema", None)
        parameters = schema_method() if callable(schema_method) else self.args_schema.schema()

        # Clean schema representation
        clean_parameters = {
            "type": "object",
            "properties": parameters.get("properties", {}),
            "required": parameters.get("required", [])
        }

        return {
            "name": self.name,
            "description": self.description,
            "parameters": clean_parameters,
            "requires_approval": self.requires_approval
        }
