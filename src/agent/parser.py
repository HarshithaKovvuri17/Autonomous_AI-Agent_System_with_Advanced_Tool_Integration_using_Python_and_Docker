"""
Output Parser for ReAct Agent.
Extracts thought, tool action, and parameters from JSON or structured markdown blocks.
Handles errors gracefully to allow agent replanning.
"""
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional


class ParsingError(Exception):
    """Raised when the LLM response cannot be parsed into a valid ReAct action."""
    pass


@dataclass
class AgentStep:
    """Represents a parsed step from the agent's ReAct response."""
    thought: str
    tool_name: str
    tool_arguments: Any
    is_final: bool = False
    raw_response: str = ""


class OutputParser:
    """
    Parses LLM textual output into structured AgentStep objects.
    Robust against markdown code blocks, escaped characters, and varied key naming conventions.
    """

    @staticmethod
    def parse(response_text: str) -> AgentStep:
        raw = response_text.strip()
        if not raw:
            raise ParsingError("Empty response received from LLM.")

        json_dict = None

        # 1. Try stripping markdown code fences (e.g. ```json ... ``` or ``` ...)
        clean_text = raw
        if "```" in raw:
            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw, re.IGNORECASE)
            if match:
                clean_text = match.group(1).strip()

        # 2. Try direct JSON parsing
        try:
            parsed = json.loads(clean_text)
            if isinstance(parsed, dict) and any(k in parsed for k in ("action", "tool_name", "tool", "final_answer", "answer")):
                json_dict = parsed
        except json.JSONDecodeError:
            pass

        # 3. Try finding any JSON object {...} in text via regex if direct parse didn't find a step
        if json_dict is None:
            match = re.search(r"(\{[\s\S]*\})", raw)
            if match:
                try:
                    candidate = json.loads(match.group(1).strip())
                    if isinstance(candidate, dict) and any(k in candidate for k in ("action", "tool_name", "tool", "final_answer", "answer")):
                        json_dict = candidate
                except json.JSONDecodeError:
                    pass

        # 4. Fallback for traditional ReAct text format:
        # Thought: ...
        # Action: ...
        # Action Input: ...
        if not isinstance(json_dict, dict):
            thought_match = re.search(r"Thought:\s*(.*?)(?=\nAction:|$)", raw, re.DOTALL | re.IGNORECASE)
            action_match = re.search(r"Action:\s*(.*?)(?=\nAction Input:|$)", raw, re.DOTALL | re.IGNORECASE)
            input_match = re.search(r"Action Input:\s*(.*)", raw, re.DOTALL | re.IGNORECASE)

            if action_match:
                thought = thought_match.group(1).strip() if thought_match else "Reasoning step"
                action = action_match.group(1).strip()
                action_input_raw = input_match.group(1).strip() if input_match else "{}"
                try:
                    action_input = json.loads(action_input_raw)
                except Exception:
                    action_input = action_input_raw

                is_final = action.lower().replace("_", " ").strip() == "final answer"
                return AgentStep(
                    thought=thought,
                    tool_name=action,
                    tool_arguments=action_input,
                    is_final=is_final,
                    raw_response=raw
                )

            raise ParsingError(
                f"Failed to parse LLM response into valid JSON. Expected keys: 'thought', 'action' (or 'tool_name'), "
                f"'action_input' (or 'tool_arguments'). Raw content was: {raw[:300]}"
            )

        # Extract thought
        thought = str(json_dict.get("thought", "")).strip()
        if not thought:
            thought = str(json_dict.get("reasoning", "")).strip() or "Analyzing current step..."

        # Extract tool name / action
        tool_name = (
            json_dict.get("action")
            or json_dict.get("tool_name")
            or json_dict.get("tool")
        )
        if not tool_name:
            # Check if answer key is directly supplied
            if "final_answer" in json_dict or "answer" in json_dict:
                tool_name = "Final Answer"
            else:
                raise ParsingError(
                    f"Parsed JSON missing required 'action' or 'tool_name' field. Keys found: {list(json_dict.keys())}"
                )

        tool_name = str(tool_name).strip()

        # Extract arguments
        args = (
            json_dict.get("action_input")
            if "action_input" in json_dict
            else json_dict.get("tool_arguments")
            if "tool_arguments" in json_dict
            else json_dict.get("arguments")
            if "arguments" in json_dict
            else json_dict.get("parameters")
            if "parameters" in json_dict
            else json_dict.get("final_answer")
            if "final_answer" in json_dict
            else json_dict.get("answer")
            if "answer" in json_dict
            else {}
        )

        # If args is a JSON string, decode it into dict if possible
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except Exception:
                pass

        # Check if final answer
        normalized_action = tool_name.lower().replace("_", " ").strip()
        is_final = normalized_action in ("final answer", "finalanswer", "finish")

        return AgentStep(
            thought=thought,
            tool_name="Final Answer" if is_final else tool_name,
            tool_arguments=args,
            is_final=is_final,
            raw_response=raw
        )

