"""Unit and integration tests for ReAct Agent loop."""
import json
import os
from unittest.mock import MagicMock
from src.agent.react import ReActAgent
from src.agent.llm_client import LLMClient
from src.tools.registry import ToolRegistry
from src.tools.calculator import CalculatorTool
from src.logger import tracer


def test_react_agent_successful_loop(clean_trace_file):
    # Setup registry with Calculator
    registry = ToolRegistry()
    registry.register(CalculatorTool())

    # Simulated LLM responses:
    # 1. Thought + Action (calculator)
    # 2. Final Answer
    mock_llm = MagicMock(spec=LLMClient)
    mock_llm.chat_completion.side_effect = [
        '{"thought": "Compute 25 * 4", "action": "calculator", "action_input": {"expression": "25 * 4"}}',
        '{"thought": "Result received", "action": "Final Answer", "action_input": "The answer is 100."}'
    ]

    agent = ReActAgent(
        registry=registry,
        llm_client=mock_llm,
        auto_eval=True
    )

    result = agent.run("Calculate 25 * 4")
    assert "The answer is 100." in result

    # Verify execution_trace.jsonl was populated
    assert os.path.exists(clean_trace_file)
    with open(clean_trace_file, "r", encoding="utf-8") as f:
        lines = [json.loads(line) for line in f if line.strip()]

    assert len(lines) == 2
    assert lines[0]["iteration"] == 1
    assert lines[0]["action_selected"] == "calculator"
    assert lines[0]["observation"] == "100"
    assert lines[1]["iteration"] == 2
    assert lines[1]["action_selected"] == "Final Answer"


def test_react_agent_replans_after_tool_error(clean_trace_file):
    registry = ToolRegistry()
    registry.register(CalculatorTool())

    mock_llm = MagicMock(spec=LLMClient)
    # Step 1 attempts invalid expression
    # Step 2 analyzes error and fixes expression
    # Step 3 delivers final answer
    mock_llm.chat_completion.side_effect = [
        '{"thought": "Try division", "action": "calculator", "action_input": {"expression": "10 / 0"}}',
        '{"thought": "Division by zero occurred. Let me compute 10 / 2 instead.", "action": "calculator", "action_input": {"expression": "10 / 2"}}',
        '{"thought": "Completed calculation.", "action": "Final Answer", "action_input": "The corrected answer is 5."}'
    ]

    agent = ReActAgent(
        registry=registry,
        llm_client=mock_llm,
        auto_eval=True
    )

    result = agent.run("Perform calculation with recovery")
    assert "The corrected answer is 5." in result

    with open(clean_trace_file, "r", encoding="utf-8") as f:
        lines = [json.loads(line) for line in f if line.strip()]

    assert len(lines) == 3
    assert "Division by zero" in lines[0]["observation"]
    assert lines[1]["observation"] == "5"


def test_react_agent_max_iterations_timeout(clean_trace_file):
    registry = ToolRegistry()
    registry.register(CalculatorTool())

    # Infinite loop simulation
    mock_llm = MagicMock(spec=LLMClient)
    mock_llm.chat_completion.return_value = (
        '{"thought": "Endless loop", "action": "calculator", "action_input": {"expression": "1 + 1"}}'
    )

    max_iter = 3
    agent = ReActAgent(
        registry=registry,
        llm_client=mock_llm,
        max_iterations=max_iter,
        auto_eval=True
    )

    result = agent.run("Loop forever")
    assert f"maximum iteration limit ({max_iter})" in result
