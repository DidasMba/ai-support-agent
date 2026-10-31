"""Settings you are likely to change, in one place.

Every value has a sensible default and can be overridden with an environment
variable of the same name (or a line in `.env`), so a deployment can be tuned
without code changes.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _env_str(name: str, default: str) -> str:
    return os.environ.get(name, default)


def _env_int(name: str, default: int) -> int:
    return int(os.environ.get(name, default))


def _env_float(name: str, default: float) -> float:
    return float(os.environ.get(name, default))


# Paths
APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR.parent / "static"
KB_PATH = Path(_env_str("KB_PATH", str(APP_DIR / "knowledge" / "business_faq.md")))

# Business shown in the chat widget
BUSINESS_NAME = _env_str("BUSINESS_NAME", "Kigali Central Pharmacy")

# Where Gemini runs.
# With GOOGLE_CLOUD_PROJECT set, the app uses Gemini Enterprise Agent Platform
# (formerly Vertex AI) and authenticates with Application Default Credentials:
# no API key to store or leak. Without it, it falls back to the Gemini
# Developer API with GEMINI_API_KEY, which is enough for a first local run.
GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT") or None
GOOGLE_CLOUD_LOCATION = _env_str("GOOGLE_CLOUD_LOCATION", "global")
# Set this if your embedding model is served from a different location than
# the chat model (for example, "us-central1").
EMBEDDING_LOCATION = _env_str("EMBEDDING_LOCATION", GOOGLE_CLOUD_LOCATION)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or None

# Gemini models
CHAT_MODEL = _env_str("CHAT_MODEL", "gemini-3.6-flash")
EMBEDDING_MODEL = _env_str("EMBEDDING_MODEL", "gemini-embedding-001")

# Retrieval
TOP_K = _env_int("TOP_K", 3)  # how many FAQ sections to give Gemini per question
MIN_SCORE = _env_float("MIN_SCORE", 0.3)  # relevance floor; below it we hand off

# Seconds to wait for Gemini before giving the customer the "busy" reply
GEMINI_TIMEOUT = _env_float("GEMINI_TIMEOUT", 20)

# How long Gemini "thinks" before answering: minimal, low, medium or high.
# Answering from a short FAQ needs little reasoning, and the default (high on
# recent models) can take longer than GEMINI_TIMEOUT. Empty = model default.
THINKING_LEVEL = _env_str("THINKING_LEVEL", "low")

# Conversation limits (protect the prompt size and the API bill)
MAX_MESSAGE_CHARS = _env_int("MAX_MESSAGE_CHARS", 1000)
MAX_HISTORY_TURNS = _env_int("MAX_HISTORY_TURNS", 6)  # earlier turns sent to Gemini

LOG_LEVEL = _env_str("LOG_LEVEL", "INFO")

# Quick-start questions shown as chips in the chat widget
SUGGESTED_QUESTIONS = [
    "What time do you open?",
    "Do you deliver?",
    "Which payment methods do you accept?",
    "Do you accept insurance?",
]
