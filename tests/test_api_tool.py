"""Unit tests for External API Interaction Tool."""
from unittest.mock import patch, MagicMock
import pytest
import requests
from src.tools.api import ApiTool
from src.tools.base import ToolValidationError


def test_api_tool_successful_get():
    tool = ApiTool()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"Content-Type": "application/json"}
    mock_resp.json.return_value = {"status": "ok", "count": 5}

    with patch("requests.request", return_value=mock_resp):
        res = tool.execute(url="https://api.example.com/data", method="GET")
        assert "Status Code: 200" in res
        assert '"status": "ok"' in res


def test_api_tool_successful_post():
    tool = ApiTool()
    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.headers = {"Content-Type": "application/json"}
    mock_resp.json.return_value = {"id": 101, "created": True}

    with patch("requests.request", return_value=mock_resp):
        res = tool.execute(
            url="https://api.example.com/items",
            method="POST",
            body={"name": "Widget", "price": 9.99}
        )
        assert "Status Code: 201" in res
        assert '"created": true' in res


def test_api_tool_timeout_handling():
    tool = ApiTool(timeout=5)

    with patch("requests.request", side_effect=requests.exceptions.Timeout("Operation timed out")):
        res = tool.execute(url="https://slow.example.com", method="GET")
        assert "Timeout Error" in res
        assert "timed out after 5s" in res


def test_api_tool_connection_error_handling():
    tool = ApiTool()

    with patch("requests.request", side_effect=requests.exceptions.ConnectionError("Failed to connect")):
        res = tool.execute(url="https://invalid.domain.xyz", method="GET")
        assert "Connection Error" in res
        assert "Unable to establish connection" in res


def test_api_tool_schema_validation():
    tool = ApiTool()

    # Valid schema run
    mock_resp = MagicMock(status_code=200, headers={}, text="OK")
    with patch("requests.request", return_value=mock_resp):
        res = tool.run({"url": "https://example.com", "method": "GET"})
        assert "Status Code: 200" in res

    # Invalid HTTP method (must be GET or POST)
    with pytest.raises(ToolValidationError):
        tool.run({"url": "https://example.com", "method": "DELETE"})

    # Missing URL
    with pytest.raises(ToolValidationError):
        tool.run({"method": "GET"})
