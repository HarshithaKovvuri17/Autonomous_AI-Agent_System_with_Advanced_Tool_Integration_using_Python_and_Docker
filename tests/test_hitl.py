"""Unit tests for Human-in-the-Loop safety gate."""
from unittest.mock import patch, MagicMock
from src.agent.react import ReActAgent
from src.agent.llm_client import LLMClient
from src.tools.registry import ToolRegistry
from src.tools.code_exec import CodeExecutionTool


def test_hitl_approval_granted():
    mock_runner = MagicMock()
    mock_runner.run_code.return_value = "Code executed with approval"

    registry = ToolRegistry()
    registry.register(CodeExecutionTool(runner=mock_runner))

    mock_llm = MagicMock(spec=LLMClient)
    mock_llm.chat_completion.side_effect = [
        '{"thought": "Execute script", "action": "code_execution", "action_input": {"code": "print(1)"}}',
        '{"thought": "Done", "action": "Final Answer", "action_input": "Finished"}'
    ]

    agent = ReActAgent(
        registry=registry,
        llm_client=mock_llm,
        auto_eval=False
    )

    # Simulate user typing 'y'
    with patch("builtins.input", return_value="y"):
        res = agent.run("Run code")
        assert res == "Finished"
        mock_runner.run_code.assert_called_once()


def test_hitl_denial_triggers_replan():
    mock_runner = MagicMock()

    registry = ToolRegistry()
    registry.register(CodeExecutionTool(runner=mock_runner))

    mock_llm = MagicMock(spec=LLMClient)
    # Step 1: LLM proposes high risk code execution
    # Step 2: Human denies ('n'), LLM receives denial observation and formulates alternative plan
    mock_llm.chat_completion.side_effect = [
        '{"thought": "Execute script", "action": "code_execution", "action_input": {"code": "import os; os.system(\'dangerous\')"}}',
        '{"thought": "The human declined. I will formulate a safe alternate response.", "action": "Final Answer", "action_input": "Execution was safely aborted upon human request."}'
    ]

    agent = ReActAgent(
        registry=registry,
        llm_client=mock_llm,
        auto_eval=False
    )

    # Simulate user typing 'n'
    with patch("builtins.input", return_value="n"):
        res = agent.run("Run dangerous command")
        assert "Execution was safely aborted upon human request." in res
        # Ensure the underlying tool was NEVER executed
        mock_runner.run_code.assert_not_called()


def test_hitl_bypassed_with_auto_eval():
    mock_runner = MagicMock()
    mock_runner.run_code.return_value = "Auto approved result"

    registry = ToolRegistry()
    registry.register(CodeExecutionTool(runner=mock_runner))

    mock_llm = MagicMock(spec=LLMClient)
    mock_llm.chat_completion.side_effect = [
        '{"thought": "Execute script in benchmark", "action": "code_execution", "action_input": {"code": "print(42)"}}',
        '{"thought": "Done", "action": "Final Answer", "action_input": "42"}'
    ]

    # auto_eval=True: should never prompt user input
    agent = ReActAgent(
        registry=registry,
        llm_client=mock_llm,
        auto_eval=True
    )

    with patch("builtins.input", side_effect=Exception("input() should not be called in auto-eval")):
        res = agent.run("Automated benchmark")
        assert res == "42"
        mock_runner.run_code.assert_called_once()
