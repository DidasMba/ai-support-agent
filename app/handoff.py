"""Deciding when a conversation should go to a human."""

# Simple handoff heuristic — refine once you see real conversations.
# Keep these in sync with the wording in prompts.py.
HANDOFF_PHRASES = [
    "not sure", "don't know", "team will", "follow up",
    "pharmacist", "speak with", "speak to",
]


def needs_human(reply: str) -> bool:
    reply = reply.lower()
    return any(phrase in reply for phrase in HANDOFF_PHRASES)
