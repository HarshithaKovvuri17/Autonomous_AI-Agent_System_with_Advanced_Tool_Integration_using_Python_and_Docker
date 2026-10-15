"""Unit tests for ReAct Output Parser."""
import pytest
from src.agent.parser import OutputParser, ParsingError


def test_parser_standard_json():
    raw = '{"thought": "Need to calculate", "action": "calculator", "action_input": {"expression": "2+2"}}'
    step = OutputParser.parse(raw)
    assert step.thought == "Need to calculate"
    assert step.tool_name == "calculator"
    assert step.tool_arguments == {"expression": "2+2"}
    assert step.is_final is False


def test_parser_markdown_fenced_json():
    raw = """
```json
{
  "thought": "I should read the file.",
  "tool_name": "file_system",
  "tool_arguments": {
    "action": "read",
    "file_path": "report.txt"
  }
}
```
"""
    step = OutputParser.parse(raw)
    assert step.thought == "I should read the file."
    assert step.tool_name == "file_system"
    assert step.tool_arguments["action"] == "read"
    assert step.is_final is False


def test_parser_final_answer_detection():
    raw = '{"thought": "All steps done", "action": "Final Answer", "action_input": "The sum is 420."}'
    step = OutputParser.parse(raw)
    assert step.is_final is True
    assert step.tool_name == "Final Answer"
    assert step.tool_arguments == "The sum is 420."


def test_parser_text_fallback():
    raw = """Thought: Need to look up info
Action: web_search
Action Input: {"query": "python latest release"}"""
    step = OutputParser.parse(raw)
    assert step.thought == "Need to look up info"
    assert step.tool_name == "web_search"
    assert step.tool_arguments == {"query": "python latest release"}


def test_parser_malformed_json_raises_parsing_error():
    with pytest.raises(ParsingError):
        OutputParser.parse("This is just random chatter without any thought or action.")

    with pytest.raises(ParsingError):
        OutputParser.parse("")
