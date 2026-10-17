"""
External API Interaction Tool for performing HTTP requests.
Handles GET and POST methods, JSON/text payloads, and connection timeouts gracefully.
"""
import json
import logging
from typing import Any, Dict, Optional, Union
import requests
from pydantic import BaseModel, Field, field_validator
from src.tools.base import BaseTool

logger = logging.getLogger("AgentSystem.Tools.API")

MAX_RESPONSE_LENGTH = 2000


class ApiInput(BaseModel):
    url: str = Field(..., description="The complete HTTP/HTTPS URL to query.")
    method: str = Field("GET", description="The HTTP method: 'GET' or 'POST'.")
    headers: Optional[Dict[str, str]] = Field(
        default=None,
        description="Optional HTTP request headers (e.g., {'Content-Type': 'application/json'})."
    )
    body: Optional[Union[Dict[str, Any], str]] = Field(
        default=None,
        description="Optional request payload for POST requests (dict or JSON string)."
    )

    @field_validator("method")
    def validate_method(cls, v: str) -> str:
        upper = v.strip().upper()
        if upper not in ("GET", "POST"):
            raise ValueError(f"HTTP method must be 'GET' or 'POST', received '{v}'")
        return upper


class ApiTool(BaseTool):
    """
    Tool for communicating with external REST APIs and microservices via HTTP.
    """
    name: str = "api_client"
    description: str = (
        "Use this tool to communicate with external web APIs and microservices. "
        "Supports 'GET' and 'POST' requests. Input must include a valid 'url' and 'method', "
        "with optional 'headers' and 'body'. Returns the HTTP status code and response body."
    )
    args_schema = ApiInput
    requires_approval: bool = False

    def __init__(self, timeout: int = 10, max_length: int = MAX_RESPONSE_LENGTH):
        self.timeout = timeout
        self.max_length = max_length

    def execute(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Union[Dict[str, Any], str]] = None
    ) -> str:
        method = method.upper()
        req_headers = headers or {}

        # Prepare request payload
        json_data = None
        data = None
        if body is not None:
            if isinstance(body, dict):
                json_data = body
            elif isinstance(body, str):
                try:
                    json_data = json.loads(body)
                except Exception:
                    data = body
            else:
                data = str(body)

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=req_headers,
                json=json_data,
                data=data,
                timeout=self.timeout
            )

            status_code = response.status_code
            content_type = response.headers.get("Content-Type", "")

            if "application/json" in content_type:
                try:
                    parsed_json = response.json()
                    formatted_body = json.dumps(parsed_json, indent=2)
                except Exception:
                    formatted_body = response.text
            else:
                formatted_body = response.text

            if len(formatted_body) > self.max_length:
                formatted_body = formatted_body[:self.max_length] + "\n...[Body truncated for context length]"

            return f"Status Code: {status_code}\nResponse Body:\n{formatted_body}"

        except requests.exceptions.Timeout:
            return f"Timeout Error: Request timed out after {self.timeout}s while connecting to {url}"
        except requests.exceptions.ConnectionError as e:
            return f"Connection Error: Unable to establish connection to {url}. Details: {str(e)}"
        except requests.exceptions.RequestException as e:
            return f"HTTP Request Error: Failed to execute request on {url}. Details: {str(e)}"
        except Exception as e:
            return f"Unexpected Error: {str(e)}"
