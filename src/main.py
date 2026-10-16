"""
CLI Entrypoint for the Autonomous AI Agent System.
Usage:
    python src/main.py --goal "[text]" [--auto-eval]
"""
import argparse
import sys
import os

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.config import MAX_ITERATIONS, AUTO_EVAL, MOCK_LLM
from src.tools.registry import ToolRegistry
from src.tools.search import WebSearchTool
from src.tools.calculator import CalculatorTool
from src.tools.api import ApiTool
from src.tools.filesystem import FileSystemTool
from src.tools.code_exec import CodeExecutionTool
from src.agent.react import ReActAgent
from src.agent.llm_client import LLMClient
from src.memory.memory import Memory


def create_agent(auto_eval: bool = False, max_iterations: int = MAX_ITERATIONS, mock_llm: bool = False) -> ReActAgent:
    """Initialize ToolRegistry with all 5 core tools and instantiate ReActAgent."""
    registry = ToolRegistry()
    registry.register(WebSearchTool())
    registry.register(CalculatorTool())
    registry.register(ApiTool())
    registry.register(FileSystemTool())
    registry.register(CodeExecutionTool())

    llm_client = LLMClient(mock_mode=mock_llm)
    memory = Memory()

    return ReActAgent(
        registry=registry,
        memory=memory,
        llm_client=llm_client,
        max_iterations=max_iterations,
        auto_eval=auto_eval
    )


def main():
    parser = argparse.ArgumentParser(
        description="Autonomous AI Agent System with Advanced Tool Integration and Docker Sandboxing"
    )
    parser.add_argument(
        "--goal",
        type=str,
        required=True,
        help="The natural language goal or problem statement for the agent to resolve."
    )
    parser.add_argument(
        "--auto-eval",
        action="store_true",
        default=AUTO_EVAL,
        help="Bypass human-in-the-loop prompts and default to auto-approval for automated testing/benchmarks."
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=MAX_ITERATIONS,
        help=f"Maximum ReAct iterations before timeout termination (default: {MAX_ITERATIONS})."
    )
    parser.add_argument(
        "--mock-llm",
        action="store_true",
        default=MOCK_LLM,
        help="Use deterministic offline ReAct engine instead of calling live LLM API."
    )

    args = parser.parse_args()

    agent = create_agent(
        auto_eval=args.auto_eval,
        max_iterations=args.max_iterations,
        mock_llm=args.mock_llm
    )

    result = agent.run(args.goal)
    print(f"\nFinal Result: {result}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
