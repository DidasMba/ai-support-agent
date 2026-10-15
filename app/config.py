"""Settings you are likely to change, in one place."""

import os

from dotenv import load_dotenv

load_dotenv()

# Gemini models
CHAT_MODEL = "gemini-3.6-flash"
EMBEDDING_MODEL = "models/gemini-embedding-001"

# Retrieval
TOP_K = 3  # how many FAQ sections to give Gemini per question
MIN_SCORE = 0.3  # loose relevance floor; below this the question is handed off

# Seconds to wait for Gemini before giving the customer the "busy" reply
GEMINI_TIMEOUT = 20

KB_PATH = os.path.join(os.path.dirname(__file__), "knowledge", "business_faq.md")


def gemini_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Copy .env.example to .env and add your key."
        )
    return key
