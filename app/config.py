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

# Gemini models
CHAT_MODEL = _env_str("CHAT_MODEL", "gemini-3.6-flash")
EMBEDDING_MODEL = _env_str("EMBEDDING_MODEL", "models/gemini-embedding-001")

# Retrieval
TOP_K = _env_int("TOP_K", 3)  # how many FAQ sections to give Gemini per question
MIN_SCORE = _env_float("MIN_SCORE", 0.3)  # relevance floor; below it we hand off

# Seconds to wait for Gemini before giving the customer the "busy" reply
GEMINI_TIMEOUT = _env_float("GEMINI_TIMEOUT", 20)

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


def gemini_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Copy .env.example to .env and add your key."
        )
    return key
