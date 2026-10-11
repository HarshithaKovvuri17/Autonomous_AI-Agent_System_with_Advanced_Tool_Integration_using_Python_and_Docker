"""
Structured logging and execution trace logging for the Autonomous AI Agent System.
Maintains execution_trace.jsonl format as specified in contract requirements.
"""
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from src.config import EXECUTION_TRACE_FILE, LOG_LEVEL


class ExecutionTracer:
    """Manages appending trace events to execution_trace.jsonl."""

    def __init__(self, trace_file: str = EXECUTION_TRACE_FILE):
        self.trace_file = trace_file

    def record_step(
        self,
        iteration: int,
        thought: str,
        action_selected: str,
        action_arguments: Any,
        observation: str,
        timestamp: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Record a single iteration step into execution_trace.jsonl.
        Format matches: timestamp, iteration number, thought, action_selected,
        action_arguments, and the resulting observation.
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc).isoformat()

        entry = {
            "timestamp": timestamp,
            "iteration": iteration,
            "thought": thought,
            "action_selected": action_selected,
            "action_arguments": action_arguments,
            "observation": observation
        }

        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(self.trace_file)), exist_ok=True)

        with open(self.trace_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        return entry

    def clear(self) -> None:
        """Clear trace file if needed before a fresh test/run."""
        if os.path.exists(self.trace_file):
            with open(self.trace_file, "w", encoding="utf-8") as f:
                f.truncate(0)


def setup_logger(name: str = "AgentSystem") -> logging.Logger:
    """Configure structured console logging."""
    logger = logging.getLogger(name)
    level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(level)
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


logger = setup_logger()
tracer = ExecutionTracer()
