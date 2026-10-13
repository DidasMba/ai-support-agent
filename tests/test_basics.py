"""Checks that run without a Gemini API key."""

import os

from app.handoff import needs_human
from app.prompts import build_prompt
from app.rag import load_chunks

KB_PATH = os.path.join(os.path.dirname(__file__), "..", "app", "knowledge", "business_faq.md")


def test_chunks_split_on_h3_headings():
    chunks = load_chunks(KB_PATH)
    titles = [c["title"] for c in chunks]
    assert "Business Hours" in titles
    assert "Payment Methods" in titles
    # The "# Pharmacy Knowledge Base" title and the example-data note are dropped.
    assert all(c["text"].startswith("### ") for c in chunks)


def test_handoff_detection():
    assert needs_human("Please speak with the on-duty pharmacist.")
    assert needs_human("I'm not sure — a team member will follow up.")
    assert not needs_human("We are open 7:30 AM to 9:30 PM.")


def test_prompt_keeps_safety_rule_and_context():
    prompt = build_prompt("When do you open?", [{"title": "Hours", "text": "7:30 AM"}])
    assert "NEVER give medical advice" in prompt
    assert "[Hours]\n7:30 AM" in prompt
    assert prompt.endswith("Customer question: When do you open?")
