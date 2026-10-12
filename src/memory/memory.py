"""
Memory and State Management for the Autonomous AI Agent System.
Manages conversation history, message roles, sliding window pruning, and context preservation.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Message:
    """Represents a single message in the agent conversation memory."""
    role: str  # "system", "user", "assistant", "observation" / "tool"
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, str]:
        """Convert to standard format accepted by LLM chat APIs."""
        # Map internal observation role to user or tool for OpenAI API compatibility
        api_role = "user" if self.role == "observation" else self.role
        return {"role": api_role, "content": self.content}


class Memory:
    """
    Maintains the state and dialogue history for the ReAct reasoning loop.
    Implements sliding window truncation to avoid context window exhaustion.
    """

    def __init__(self, max_messages: int = 30, max_chars_per_message: int = 4000):
        self.max_messages = max_messages
        self.max_chars_per_message = max_chars_per_message
        self.messages: List[Message] = []

    def set_system_message(self, content: str) -> None:
        """Set or replace the system message (always kept at index 0)."""
        msg = Message(role="system", content=content)
        if self.messages and self.messages[0].role == "system":
            self.messages[0] = msg
        else:
            self.messages.insert(0, msg)

    def add_user_message(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add user goal or prompt to history."""
        sanitized = self._sanitize_content(content)
        self.messages.append(Message(role="user", content=sanitized, metadata=metadata or {}))
        self._prune_if_needed()

    def add_assistant_message(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add model thought and action response to history."""
        sanitized = self._sanitize_content(content)
        self.messages.append(Message(role="assistant", content=sanitized, metadata=metadata or {}))
        self._prune_if_needed()

    def add_observation(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add tool execution observation to history."""
        sanitized = self._sanitize_content(content)
        self.messages.append(Message(role="observation", content=sanitized, metadata=metadata or {}))
        self._prune_if_needed()

    def _sanitize_content(self, text: str) -> str:
        """Sanitize and limit character length to avoid context blowout."""
        if len(text) > self.max_chars_per_message:
            return text[:self.max_chars_per_message] + "\n...[Observation truncated by Memory store]"
        return text

    def _prune_if_needed(self) -> None:
        """
        Sliding window context preservation:
        Keep system prompt (index 0) and original user goal (index 1),
        while sliding older intermediate steps to prevent token overflow.
        """
        if len(self.messages) <= self.max_messages:
            return

        # Ensure we keep system and initial user goal
        pinned = []
        start_idx = 0
        if len(self.messages) > 0 and self.messages[0].role == "system":
            pinned.append(self.messages[0])
            start_idx += 1
        if len(self.messages) > start_idx and self.messages[start_idx].role == "user":
            pinned.append(self.messages[start_idx])
            start_idx += 1

        # Keep the most recent messages
        remaining_slots = self.max_messages - len(pinned)
        recent = self.messages[-remaining_slots:]
        self.messages = pinned + recent

    def get_messages(self) -> List[Dict[str, str]]:
        """Return standard message dictionaries for LLM chat completions."""
        return [msg.to_dict() for msg in self.messages]

    def get_history_as_text(self) -> str:
        """Return formatted textual history for single-prompt ReAct execution."""
        lines = []
        for msg in self.messages:
            if msg.role == "system":
                continue
            role_label = {
                "user": "Question / Goal",
                "assistant": "Agent",
                "observation": "Observation"
            }.get(msg.role, msg.role.capitalize())
            lines.append(f"{role_label}: {msg.content}")
        return "\n\n".join(lines)

    def clear(self) -> None:
        """Reset conversation memory."""
        self.messages.clear()

    def __len__(self) -> int:
        return len(self.messages)

