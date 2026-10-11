"""Configuration settings for the Autonomous AI Agent System."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent

# Workspace Directory for safe file system sandboxing
_workspace_env = os.getenv("WORKSPACE_DIR", "./workspace")
if os.path.isabs(_workspace_env):
    WORKSPACE_DIR = os.path.abspath(_workspace_env)
else:
    WORKSPACE_DIR = os.path.abspath(os.path.join(BASE_DIR, _workspace_env))

os.makedirs(WORKSPACE_DIR, exist_ok=True)

# Execution Trace File
_trace_env = os.getenv("EXECUTION_TRACE_FILE", "execution_trace.jsonl")
if os.path.isabs(_trace_env):
    EXECUTION_TRACE_FILE = os.path.abspath(_trace_env)
else:
    EXECUTION_TRACE_FILE = os.path.abspath(os.path.join(BASE_DIR, _trace_env))

# LLM API configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

# Execution parameters
MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "15"))
CONTAINER_TIMEOUT_SECONDS = int(os.getenv("CONTAINER_TIMEOUT_SECONDS", "15"))
CONTAINER_MEMORY_LIMIT = os.getenv("CONTAINER_MEMORY_LIMIT", "128m")
SANDBOX_IMAGE = os.getenv("SANDBOX_IMAGE", "python:3.10-slim")

# Operational & Logging flags
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
AUTO_EVAL = os.getenv("AUTO_EVAL", "false").lower() in ("true", "1", "yes")

# Mock LLM mode: if true, or if no API key is provided and MOCK_LLM is not explicitly set to false
_mock_raw = os.getenv("MOCK_LLM")
if _mock_raw is not None:
    MOCK_LLM = _mock_raw.lower() in ("true", "1", "yes")
else:
    # Auto-enable mock LLM if no OpenAI API key is set
    MOCK_LLM = not bool(OPENAI_API_KEY.strip())
