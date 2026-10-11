"""Unit tests for Memory and State Management."""
from src.memory.memory import Memory, Message


def test_memory_add_messages():
    mem = Memory()
    mem.set_system_message("You are an AI assistant.")
    mem.add_user_message("What is 5 + 5?")
    mem.add_assistant_message("I will compute this.")
    mem.add_observation("10")

    msgs = mem.get_messages()
    assert len(msgs) == 4
    assert msgs[0]["role"] == "system"
    assert msgs[1]["role"] == "user"
    assert msgs[2]["role"] == "assistant"
    # Observation mapped to user for chat API compatibility
    assert msgs[3]["role"] == "user"
    assert msgs[3]["content"] == "10"


def test_memory_sliding_window_pruning():
    # Set small max_messages to test sliding window
    mem = Memory(max_messages=5)
    mem.set_system_message("System Prompt")
    mem.add_user_message("Initial Goal")

    # Add several intermediate steps
    for i in range(10):
        mem.add_assistant_message(f"Assistant step {i}")
        mem.add_observation(f"Observation {i}")

    msgs = mem.get_messages()
    assert len(msgs) <= 5
    # Crucial: First two messages must remain System Prompt and Initial Goal
    assert msgs[0]["content"] == "System Prompt"
    assert msgs[1]["content"] == "Initial Goal"
    # The last message is the most recent observation
    assert "Observation 9" in msgs[-1]["content"]


def test_memory_truncation_on_large_observation():
    mem = Memory(max_chars_per_message=100)
    huge_text = "A" * 500
    mem.add_observation(huge_text)
    stored = mem.messages[-1].content
    assert len(stored) < 200
    assert "truncated" in stored
