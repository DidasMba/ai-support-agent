"""
Minimal RAG layer for the support agent.

For a pilot with a small knowledge base (one business's FAQ), an in-memory
vector store is enough — no need for a managed vector DB yet. When the
business's docs grow (multiple locations, big catalogs, PDFs), swap
`InMemoryStore` for Vertex AI Vector Search or AlloyDB + pgvector without
changing the rest of the app.
"""

import os
import re
import numpy as np
import google.generativeai as genai

EMBEDDING_MODEL = "models/gemini-embedding-001"


def load_chunks(md_path: str) -> list[dict]:
    """Split a markdown knowledge file into chunks on '### ' headings."""
    with open(md_path, "r", encoding="utf-8") as f:
        text = f.read()

    raw_chunks = re.split(r"\n(?=### )", text)
    chunks = []
    for raw in raw_chunks:
        raw = raw.strip()
        if not raw or raw.startswith("#") and not raw.startswith("###"):
            continue
        title_match = re.match(r"### (.+)", raw)
        title = title_match.group(1) if title_match else "General"
        chunks.append({"title": title, "text": raw})
    return chunks


class InMemoryStore:
    """Embeds chunks once at startup and does cosine-similarity retrieval."""

    def __init__(self, chunks: list[dict]):
        self.chunks = chunks
        self.vectors = self._embed_all([c["text"] for c in chunks])

    def _embed_all(self, texts: list[str]) -> np.ndarray:
        vectors = []
        for t in texts:
            result = genai.embed_content(
                model=EMBEDDING_MODEL,
                content=t,
                task_type="retrieval_document",
            )
            vectors.append(result["embedding"])
        return np.array(vectors)

    def query(self, question: str, top_k: int = 3) -> list[dict]:
        q_vec = genai.embed_content(
            model=EMBEDDING_MODEL,
            content=question,
            task_type="retrieval_query",
        )["embedding"]
        q_vec = np.array(q_vec)

        sims = self.vectors @ q_vec / (
            np.linalg.norm(self.vectors, axis=1) * np.linalg.norm(q_vec) + 1e-8
        )
        top_idx = np.argsort(sims)[::-1][:top_k]
        return [
            {**self.chunks[i], "score": float(sims[i])}
            for i in top_idx
            if sims[i] > 0.3  # loose relevance floor; tune per business
        ]


def build_store() -> InMemoryStore:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    kb_path = os.path.join(os.path.dirname(__file__), "knowledge", "business_faq.md")
    chunks = load_chunks(kb_path)
    return InMemoryStore(chunks)
