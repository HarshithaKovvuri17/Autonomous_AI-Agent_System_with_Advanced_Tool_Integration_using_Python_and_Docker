"""Unit tests for CLI main.py entrypoint."""
from unittest.mock import patch
import pytest
from src.main import main


def test_cli_execution_with_goal(clean_trace_file):
    test_args = ["main.py", "--goal", "Calculate 10 + 20", "--auto-eval", "--mock-llm"]
    with patch("sys.argv", test_args):
        exit_code = main()
        assert exit_code == 0


def test_cli_requires_goal_argument():
    test_args = ["main.py"]
    with patch("sys.argv", test_args):
        with pytest.raises(SystemExit):
            main()
