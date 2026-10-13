"""The agent's steps: search the knowledge base, ask Gemini, decide on handoff.

Every channel (web widget today, WhatsApp later) calls `answer()`.
"""

import logging
import os

import google.generativeai as genai
from dotenv import load_dotenv

from app.handoff import needs_human
from app.prompts import BUSY_REPLY, NO_MATCH_REPLY, build_prompt
from app.rag import build_store

load_dotenv()
logger = logging.getLogger(__name__)

# Built once at startup — embeddings for a small FAQ are cheap and fast.
store = build_store()
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-3.6-flash")


def answer(question: str) -> dict:
    """Return {reply, handed_off, sources} for a customer question."""
    matches = store.query(question, top_k=3)

    if not matches:
        return {"reply": NO_MATCH_REPLY, "handed_off": True, "sources": []}

    try:
        response = model.generate_content(
            build_prompt(question, matches),
            # Fail fast instead of retrying for a minute while rate-limited.
            request_options={"timeout": 20, "retry": None},
        )
        reply = response.text
    except Exception:
        # Rate limit, outage, or a blocked reply (response.text raises ValueError).
        logger.exception("Gemini call failed")
        return {
            "reply": BUSY_REPLY,
            "handed_off": True,
            "sources": [m["title"] for m in matches],
        }

    return {
        "reply": reply,
        "handed_off": needs_human(reply),
        "sources": [m["title"] for m in matches],
    }
