"""The agent's steps: search the knowledge base, ask Gemini, decide on handoff.

Every channel (web widget today, WhatsApp later) calls `SupportAgent.answer()`.
"""

import logging
from collections.abc import Sequence
from typing import Protocol

import google.generativeai as genai

from app import config
from app.handoff import needs_human
from app.prompts import BUSY_REPLY, NO_MATCH_REPLY, build_prompt
from app.rag import build_store
from app.schemas import ChatResponse, Turn

logger = logging.getLogger(__name__)


class Store(Protocol):
    def query(self, question: str, top_k: int) -> list[dict]: ...


class Model(Protocol):
    def generate_content(self, prompt: str, **kwargs): ...


class SupportAgent:
    def __init__(self, store: Store, model: Model):
        self.store = store
        self.model = model

    def answer(self, question: str, history: Sequence[Turn] = ()) -> ChatResponse:
        """Answer a customer question, optionally in the light of earlier turns."""
        question = question.strip()
        history = list(history)[-config.MAX_HISTORY_TURNS:]

        try:
            matches = self.store.query(_search_text(question, history), top_k=config.TOP_K)
        except Exception:
            # Embedding the question is also a Gemini API call.
            logger.exception("Knowledge base search failed")
            return _handoff(BUSY_REPLY)

        if not matches:
            logger.info("No knowledge base match; handing off")
            return _handoff(NO_MATCH_REPLY)

        sources = [m["title"] for m in matches]
        try:
            response = self.model.generate_content(
                build_prompt(question, matches, history),
                # Fail fast instead of retrying for a minute while rate-limited.
                request_options={"timeout": config.GEMINI_TIMEOUT, "retry": None},
            )
            reply = response.text.strip()
        except Exception:
            # Rate limit, outage, or a blocked reply (response.text raises ValueError).
            logger.exception("Gemini call failed")
            return _handoff(BUSY_REPLY, sources)

        return ChatResponse(reply=reply, handed_off=needs_human(reply), sources=sources)


def _search_text(question: str, history: Sequence[Turn]) -> str:
    """Include the previous customer message so follow-ups ("and on Sunday?") match."""
    previous = next((t.content for t in reversed(history) if t.role == "user"), None)
    return f"{previous}\n{question}" if previous else question


def _handoff(reply: str, sources: list[str] | None = None) -> ChatResponse:
    return ChatResponse(reply=reply, handed_off=True, sources=sources or [])


def create_agent() -> SupportAgent:
    """Connect to Gemini and embed the knowledge base. Called once at startup."""
    genai.configure(api_key=config.gemini_api_key())
    store = build_store(config.KB_PATH)
    model = genai.GenerativeModel(config.CHAT_MODEL)
    return SupportAgent(store, model)
