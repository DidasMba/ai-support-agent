# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A RAG customer-support chat agent for a local pharmacy (example data: a fictional Kigali pharmacy), built with FastAPI and the Gemini API (`google-generativeai`). v1 is a web chat widget. The README roadmap lists planned extensions: WhatsApp channel, real human handoff, ADK agent with tools, a managed vector DB, and document ingestion.

## Commands

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload          # http://localhost:8000
```

`GEMINI_API_KEY` must be set, either exported or in `.env` (loaded by `python-dotenv`; `.env` is gitignored). The app fails at import time without it, because the vector store is built and the key read at module load.

Deploy (Cloud Run, Dockerfile serves on port 8080):
```bash
gcloud run deploy ai-support-agent --source . --region us-central1 --allow-unauthenticated --set-env-vars GEMINI_API_KEY=...
```

There is no test suite or build step. CI (`.github/workflows/ci.yml`) runs `ruff check .` on every push and PR; run it locally with `pip install ruff && ruff check .`. To verify behavior, run the server and `POST /chat` with `{"message": "..."}`.

## Architecture

Request flow for `POST /chat` (`app/main.py`):
1. `store.query()` (`app/rag.py`) embeds the question with `gemini-embedding-001` and runs cosine similarity against in-memory vectors. It returns the top 3 chunks with a similarity above **0.3**.
2. **No matches → immediate handoff.** A canned "team will follow up" reply is returned and the LLM is never called.
3. Otherwise the prompt is built as `SYSTEM_PROMPT + retrieved context + question` (a single string, not a chat/system-instruction API), and one `generate_content` call is made to `gemini-3.6-flash`.
4. `handed_off` is a **substring heuristic** over the reply (`"not sure"`, `"pharmacist"`, `"speak with"`, …). If you change the wording in `SYSTEM_PROMPT` or the fallback, update this phrase list to match, or handoff detection silently breaks.

Knowledge base: `app/knowledge/business_faq.md` is split into chunks on `### ` headings. Each chunk's heading becomes its `title`, which is returned as `sources`. Content above the first `###` (the `#` title and the example-data note) is dropped. New FAQ entries must use `### ` headings to be retrievable. Everything is embedded once at startup, so restart after editing the file.

Safety guardrail: `SYSTEM_PROMPT` has a hard rule to never give medical, dosage, or drug-interaction advice and to redirect to the on-duty pharmacist instead. This rule overrides the retrieved context. Keep it in place when editing prompts.

Frontend: `static/index.html` is one self-contained file (inline CSS/JS, no build) served at `/`. It calls `/chat` via `fetch`. Dark mode uses `data-theme` on `<html>`, follows the OS preference, and is persisted to `localStorage` only after the user toggles it explicitly.

`InMemoryStore` is intentionally the swap point for a real vector DB. Keep its `query(question, top_k) -> list[{title, text, score}]` interface stable.
