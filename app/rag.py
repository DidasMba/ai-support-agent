"""
Minimal RAG layer for the support agent.

For a pilot with a small knowledge base (one business's FAQ), an in-memory
vector store is enough — no need for a managed vector DB yet. When the
business's docs grow (multiple locations, big catalogs, PDFs), swap
`InMemoryStore` for Vertex AI Vector Search or AlloyDB + pgvector without
changing the rest of the app: keep `query(question, top_k)` returning
a list of `Match` dicts.
"""

import logging
import re
from collections.abc import Callable
from pathlib import Path
from typing import TypedDict

import google.generativeai as genai
import numpy as np

from app import config

logger = logging.getLogger(__name__)

# (texts, task_type) -> one vector per text
Embedder = Callable[[list[str], str], list[list[float]]]


class Chunk(TypedDict):
    title: str
    text: str


class Match(Chunk):
    score: float


_HEADING = re.compile(r"^### (.+)$", re.MULTILINE)


def load_chunks(md_path: str | Path) -> list[Chunk]:
    """Split a markdown knowledge file into one chunk per '### ' section.

    Anything above the first '### ' heading (page title, notes) is dropped.
    """
    text = Path(md_path).read_text(encoding="utf-8")
    headings = list(_HEADING.finditer(text))
    chunks: list[Chunk] = []
    for heading, following in zip(headings, [*headings[1:], None], strict=True):
        end = following.start() if following else len(text)
        body = text[heading.start():end].strip()
        chunks.append({"title": heading.group(1).strip(), "text": body})
    return chunks


def gemini_embed(texts: list[str], task_type: str) -> list[list[float]]:
    """Embed texts with Gemini (the SDK batches long lists for us)."""
    # Startup indexing may retry; a live customer question must fail fast.
    options = {"timeout": config.GEMINI_TIMEOUT}
    if task_type == "retrieval_query":
        options["retry"] = None
    result = genai.embed_content(
        model=config.EMBEDDING_MODEL,
        content=texts,
        task_type=task_type,
        request_options=options,
    )
    return result["embedding"]


def _normalize(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=-1, keepdims=True)
    return vectors / np.maximum(norms, 1e-8)


class InMemoryStore:
    """Embeds chunks once at startup and does cosine-similarity retrieval."""

    def __init__(
        self,
        chunks: list[Chunk],
        embed: Embedder = gemini_embed,
        min_score: float = config.MIN_SCORE,
    ):
        if not chunks:
            raise ValueError("The knowledge base has no '### ' sections to index.")
        self.chunks = chunks
        self.embed = embed
        self.min_score = min_score
        # Normalized once, so a query is a single matrix-vector product.
        vectors = embed([c["text"] for c in chunks], "retrieval_document")
        self.vectors = _normalize(np.asarray(vectors, dtype=np.float32))

    def query(self, question: str, top_k: int = config.TOP_K) -> list[Match]:
        q_vec = _normalize(
            np.asarray(self.embed([question], "retrieval_query")[0], dtype=np.float32)
        )
        scores = self.vectors @ q_vec
        best = np.argsort(scores)[::-1][:top_k]
        return [
            {**self.chunks[i], "score": float(scores[i])}
            for i in best
            if scores[i] > self.min_score
        ]


def build_store(kb_path: str | Path) -> InMemoryStore:
    chunks = load_chunks(kb_path)
    logger.info("Indexing %d knowledge base sections from %s", len(chunks), kb_path)
    return InMemoryStore(chunks)
