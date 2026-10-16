"""
ReAct Loop Orchestrator.
Coordinates the Reasoning and Acting cycle, tool execution, state management,
Human-in-the-Loop safety gates, and trace logging.
"""
import json
import logging
from typing import Any, Dict, Optional, Tuple
from src.agent.prompt import build_system_prompt
from src.agent.parser import OutputParser, ParsingError, AgentStep
from src.agent.llm_client import LLMClient
from src.tools.registry import ToolRegistry
from src.memory.memory import Memory
from src.logger import tracer, logger
from src.config import MAX_ITERATIONS

logger_orch = logging.getLogger("AgentSystem.ReAct")


class ReActAgent:
    """
    Autonomous ReAct Agent orchestrating Thought -> Action -> Observation cycles.
    """

    def __init__(
        self,
        registry: ToolRegistry,
        memory: Optional[Memory] = None,
        llm_client: Optional[LLMClient] = None,
        max_iterations: int = MAX_ITERATIONS,
        auto_eval: bool = False
    ):
        self.registry = registry
        self.memory = memory or Memory()
        self.llm_client = llm_client or LLMClient()
        self.max_iterations = max_iterations
        self.auto_eval = auto_eval

    def _is_high_risk_action(self, tool_name: str, tool_args: Any) -> bool:
        """
        Determine whether an action requires Human-in-the-Loop approval.
        High-risk actions:
        - Code execution (runs arbitrary code in container)
        - File system write operations
        - Any tool configured with requires_approval = True
        """
        if not self.registry.has_tool(tool_name):
            return False

        tool = self.registry.get_tool(tool_name)
        if getattr(tool, "requires_approval", False):
            return True

        if tool_name == "file_system":
            if isinstance(tool_args, dict) and tool_args.get("action", "").lower() == "write":
                return True

        return False

    def _request_human_approval(self, tool_name: str, tool_args: Any) -> bool:
        """
        Execute Human-in-the-Loop safety gate.
        Bypassed if --auto-eval flag is active.
        """
        if self.auto_eval:
            print(f"[HITL GATE]: Auto-eval mode enabled. Automatically approved execution for '{tool_name}'.")
            return True

        print("\n" + "=" * 60)
        print("[HUMAN-IN-THE-LOOP SAFETY GATE]")
        print(f"The agent wishes to execute [{tool_name}] with arguments: {json.dumps(tool_args, ensure_ascii=False)}")
        print("=" * 60)

        try:
            choice = input(f"The agent wishes to execute [{tool_name}] with arguments: [{tool_args}]. Do you approve? (y/n): ").strip().lower()
            return choice in ("y", "yes")
        except (EOFError, KeyboardInterrupt):
            print("\nInput interrupted. Defaulting to rejection.")
            return False

    def run(self, goal: str) -> str:
        """
        Execute the autonomous ReAct reasoning loop until a Final Answer is derived
        or the maximum iteration limit is reached.
        """
        print(f"\n[AGENT INITIALIZING] Goal: {goal}")
        print(f"[CONFIG] Max Iterations: {self.max_iterations} | Auto-eval: {self.auto_eval}")

        # Initialize Memory with System Prompt and User Goal
        tools_schema = self.registry.get_tools_schema()
        system_prompt = build_system_prompt(tools_schema)
        self.memory.clear()
        self.memory.set_system_message(system_prompt)
        self.memory.add_user_message(goal)

        iteration = 0
        final_answer = ""

        while iteration < self.max_iterations:
            iteration += 1
            print(f"\n--- [ITERATION {iteration}/{self.max_iterations}] ---")

            # 1. Query LLM
            messages = self.memory.get_messages()
            raw_response = self.llm_client.chat_completion(messages)

            # 2. Parse Step
            try:
                step: AgentStep = OutputParser.parse(raw_response)
            except ParsingError as parse_err:
                error_msg = f"Parsing Error: {str(parse_err)}. Please respond strictly with valid JSON."
                print(f"[PARSING ERROR]: {parse_err}")
                self.memory.add_assistant_message(raw_response)
                self.memory.add_observation(error_msg)
                tracer.record_step(
                    iteration=iteration,
                    thought="Output parsing failed.",
                    action_selected="None",
                    action_arguments={},
                    observation=error_msg
                )
                continue

            # 3. Log Thought
            print(f"[AGENT THOUGHT]: {step.thought}")

            # 4. Check for Final Answer
            if step.is_final:
                answer = step.tool_arguments
                if isinstance(answer, dict):
                    final_answer = answer.get("answer") or answer.get("final_answer") or json.dumps(answer)
                else:
                    final_answer = str(answer)

                print(f"\n[FINAL ANSWER]: {final_answer}\n")
                tracer.record_step(
                    iteration=iteration,
                    thought=step.thought,
                    action_selected="Final Answer",
                    action_arguments=step.tool_arguments,
                    observation=final_answer
                )
                self.memory.add_assistant_message(raw_response)
                return final_answer

            # 5. Process Tool Invocation
            tool_name = step.tool_name
            tool_args = step.tool_arguments
            print(f"[TOOL CALL]: {tool_name} with arguments: {tool_args}")

            # 6. Human-in-the-Loop Safety Gate Check
            is_high_risk = self._is_high_risk_action(tool_name, tool_args)
            approved = True

            if is_high_risk:
                approved = self._request_human_approval(tool_name, tool_args)

            if not approved:
                observation = "Action aborted by user. Human declined execution. Please formulate an alternative plan."
                print(f"[HITL NOTICE]: Execution denied by human operator.")
            else:
                # 7. Execute Tool via Registry
                observation = self.registry.execute_tool(tool_name, tool_args)

            print(f"[OBSERVATION]: {observation}")

            # 8. Record in persistent execution trace
            tracer.record_step(
                iteration=iteration,
                thought=step.thought,
                action_selected=tool_name,
                action_arguments=tool_args,
                observation=observation
            )

            # 9. Update Memory for next cycle
            self.memory.add_assistant_message(raw_response)
            self.memory.add_observation(f"Observation: {observation}")

        # Loop limit reached without final answer
        limit_msg = (
            f"Agent reached maximum iteration limit ({self.max_iterations}) without reaching Final Answer. "
            f"Terminating loop to prevent infinite execution."
        )
        print(f"\n[TIMEOUT WARNING]: {limit_msg}")
        tracer.record_step(
            iteration=iteration,
            thought="Maximum iterations exceeded.",
            action_selected="Timeout",
            action_arguments={},
            observation=limit_msg
        )
        return limit_msg

