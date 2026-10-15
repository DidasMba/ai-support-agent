"""The agent's steps: search the knowledge base, ask Gemini, decide on handoff.

Every channel (web widget today, WhatsApp later) calls `SupportAgent.answer()`.
"""

import logging

import google.generativeai as genai

from app import config
from app.handoff import needs_human
from app.prompts import BUSY_REPLY, NO_MATCH_REPLY, build_prompt
from app.rag import build_store

logger = logging.getLogger(__name__)


class SupportAgent:
    def __init__(self, store, model):
        # `store` needs .query(question, top_k); `model` needs .generate_content().
        self.store = store
        self.model = model

    def answer(self, question: str) -> dict:
        """Return {reply, handed_off, sources} for a customer question."""
        try:
            matches = self.store.query(question, top_k=config.TOP_K)
        except Exception:
            # Embedding the question is also a Gemini API call.
            logger.exception("Knowledge base search failed")
            return {"reply": BUSY_REPLY, "handed_off": True, "sources": []}

        if not matches:
            return {"reply": NO_MATCH_REPLY, "handed_off": True, "sources": []}

        sources = [m["title"] for m in matches]
        try:
            response = self.model.generate_content(
                build_prompt(question, matches),
                # Fail fast instead of retrying for a minute while rate-limited.
                request_options={"timeout": config.GEMINI_TIMEOUT, "retry": None},
            )
            reply = response.text
        except Exception:
            # Rate limit, outage, or a blocked reply (response.text raises ValueError).
            logger.exception("Gemini call failed")
            return {"reply": BUSY_REPLY, "handed_off": True, "sources": sources}

        return {"reply": reply, "handed_off": needs_human(reply), "sources": sources}


def create_agent() -> SupportAgent:
    """Connect to Gemini and embed the knowledge base. Called once at startup."""
    genai.configure(api_key=config.gemini_api_key())
    store = build_store(config.KB_PATH)
    model = genai.GenerativeModel(config.CHAT_MODEL)
    return SupportAgent(store, model)
