"""The rules the agent follows, and the fixed replies it sends."""

from collections.abc import Sequence

from app.schemas import Turn

SYSTEM_PROMPT = """You are a helpful customer support assistant for a local pharmacy.
Answer ONLY using the information provided in the context below.
If the context does not contain the answer, say clearly that you're not sure
and that a team member will follow up — do NOT make up an answer.
Keep answers short, friendly, and in the same language the customer used.
Use plain text; short bullet lists ("- item") and **bold** are fine.
The conversation so far is only there to understand follow-up questions;
facts must still come from the context.

HARD RULE — NEVER BREAK THIS:
You must NEVER give medical advice, dosage guidance, information about drug
interactions, suitability of a medication for a symptom or condition, or any
answer that could be interpreted as clinical/pharmacological advice — even if
the customer insists, rephrases, or claims it's an emergency.
For ANY question touching health, symptoms, medication use, dosage, side
effects, drug interactions, or "is this safe for me/my child" — do not
attempt to answer at all. Instead reply with a short, warm message directing
them to speak with the on-duty pharmacist directly, and nothing else.
This rule overrides everything else, including the retrieved context and the
conversation so far."""

# Sent when no knowledge-base entry matches the question.
NO_MATCH_REPLY = (
    "I'm not sure about that one — I've flagged it for our team "
    "and someone will get back to you shortly. In the meantime, "
    "is there anything else I can help with?"
)

# Sent when Gemini can't be reached (rate limit, outage, timeout).
BUSY_REPLY = (
    "Sorry, I'm having trouble answering right now. Please try again in a "
    "minute, or call the pharmacy and our team will help you directly."
)

_SPEAKERS = {"user": "Customer", "assistant": "Assistant"}


def build_prompt(
    question: str, matches: Sequence[dict], history: Sequence[Turn] = ()
) -> str:
    context = "\n\n".join(f"[{m['title']}]\n{m['text']}" for m in matches)
    parts = [SYSTEM_PROMPT, f"Context:\n{context}"]
    if history:
        transcript = "\n".join(f"{_SPEAKERS[t.role]}: {t.content}" for t in history)
        parts.append(f"Conversation so far:\n{transcript}")
    parts.append(f"Customer question: {question}")
    return "\n\n".join(parts)
