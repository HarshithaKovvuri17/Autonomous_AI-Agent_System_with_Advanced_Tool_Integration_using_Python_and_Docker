"""Unit tests for Web Search Tool."""
from unittest.mock import patch, MagicMock
import pytest
from src.tools.search import WebSearchTool
from src.tools.base import ToolValidationError


def test_web_search_duckduckgo_mocked():
    tool = WebSearchTool()
    fake_results = [
        {"title": "Python 3.12 Release", "body": "Python 3.12 brings substantial performance improvements."},
        {"title": "Python Docs", "body": "Official documentation for the Python programming language."}
    ]

    mock_ddgs = MagicMock()
    mock_ddgs.__enter__.return_value = mock_ddgs
    mock_ddgs.text.return_value = fake_results

    with patch("duckduckgo_search.DDGS", return_value=mock_ddgs):
        res = tool.execute("Python release")
        assert "Python 3.12 Release" in res
        assert "substantially performance" in res or "Python Docs" in res


def test_web_search_empty_query():
    tool = WebSearchTool()
    res = tool.execute("   ")
    assert "cannot be empty" in res


def test_web_search_truncation():
    tool = WebSearchTool(max_length=100)
    fake_results = [{"title": "Long Page", "body": "X" * 500}]

    mock_ddgs = MagicMock()
    mock_ddgs.__enter__.return_value = mock_ddgs
    mock_ddgs.text.return_value = fake_results

    with patch("duckduckgo_search.DDGS", return_value=mock_ddgs):
        res = tool.execute("Long query")
        assert len(res) <= 250
        assert "truncated" in res


def test_web_search_schema_validation():
    tool = WebSearchTool()
    with pytest.raises(ToolValidationError):
        tool.run({})
