"""InMemoryStore retrieval, with a fake embedder instead of Gemini."""

import pytest

from app.config import KB_PATH
from app.rag import InMemoryStore, load_chunks

CHUNKS = [
    {"title": "Hours", "text": "### Hours\nopen"},
    {"title": "Delivery", "text": "### Delivery\ndeliver"},
    {"title": "Payment", "text": "### Payment\npay"},
]
# Each keyword points along its own axis, so similarity is easy to predict.
AXES = {"open": [1, 0, 0], "deliver": [0, 1, 0], "pay": [0, 0, 1]}


def fake_embed(texts, task_type):
    return [next(v for k, v in AXES.items() if k in t) for t in texts]


def test_returns_best_match_above_min_score():
    store = InMemoryStore(CHUNKS, embed=fake_embed, min_score=0.3)
    matches = store.query("do you deliver?", top_k=3)
    assert [m["title"] for m in matches] == ["Delivery"]
    assert matches[0]["score"] == pytest.approx(1.0)


def test_empty_knowledge_base_is_rejected():
    with pytest.raises(ValueError):
        InMemoryStore([], embed=fake_embed)


def test_every_faq_section_becomes_a_chunk():
    chunks = load_chunks(KB_PATH)
    assert len(chunks) == KB_PATH.read_text(encoding="utf-8").count("\n### ")
    assert chunks[-1]["title"] == "Contact for Pharmacist / Human Help"
