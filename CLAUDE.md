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

`GEMINI_API_KEY` must be set, either exported or in `.env` (loaded by `python-dotenv`; `.env` is gitignored). The server fails at startup without it (`create_agent()` runs in the FastAPI lifespan), but modules import fine, so tests don't need it.

Deploy (Cloud Run, Dockerfile serves on port 8080). `.dockerignore` keeps `.env` and `venv/` out of the image; keep it that way:
```bash
gcloud run deploy ai-support-agent --source . --region us-central1 --allow-unauthenticated --set-env-vars GEMINI_API_KEY=...
```

There is no build step. `python -m pytest` runs `tests/`, which need no API key: `test_agent.py` drives `SupportAgent` with fake store/model objects, `test_basics.py` covers chunking, handoff phrases and prompt building. CI (`.github/workflows/ci.yml`) runs `ruff check .` on every push and PR; run it locally with `pip install ruff && ruff check .`. To verify behavior, run the server and `POST /chat` with `{"message": "..."}`.

## Architecture

Code is split one file per job under `app/`:
- `config.py`: model names, `TOP_K`, `MIN_SCORE`, `GEMINI_TIMEOUT`, `KB_PATH`; loads `.env`. Change settings here, not in the modules.
- `main.py`: the web server only. The lifespan calls `create_agent()` once and stores it on `app.state.agent`; `POST /chat` calls its `answer()`. Serves the widget at `/`.
- `agent.py`: `SupportAgent(store, model).answer()` is the pipeline (retrieve, call Gemini, decide handoff). Dependencies are injected so tests can pass fakes; `create_agent()` does the real Gemini setup. Future channels (WhatsApp) should call `answer()` rather than duplicating logic.
- `prompts.py`: `SYSTEM_PROMPT`, `NO_MATCH_REPLY`, `BUSY_REPLY`, and `build_prompt()`.
- `handoff.py`: `HANDOFF_PHRASES` and `needs_human()`.
- `rag.py`: chunking and the vector store.

Request flow for `POST /chat`:
1. `store.query()` (`rag.py`) embeds the question with `gemini-embedding-001` and runs cosine similarity against in-memory vectors. It returns the top `TOP_K` (3) chunks with a similarity above **`MIN_SCORE` (0.3)**.
2. **No matches → immediate handoff.** (If Gemini errors in search or generation, `BUSY_REPLY` is returned as a handoff instead of a 500; retries are off so failures return fast.) A canned "team will follow up" reply is returned and the LLM is never called.
3. Otherwise the prompt is built as `SYSTEM_PROMPT + retrieved context + question` (a single string, not a chat/system-instruction API), and one `generate_content` call is made to `CHAT_MODEL` (`gemini-3.6-flash`).
4. `handed_off` is a **substring heuristic** (`handoff.py`) over the reply (`"not sure"`, `"pharmacist"`, `"speak with"`, …). If you change the wording in `SYSTEM_PROMPT` or the fallback, update this phrase list to match, or handoff detection silently breaks.

Knowledge base: `app/knowledge/business_faq.md` is split into chunks on `### ` headings. Each chunk's heading becomes its `title`, which is returned as `sources`. Content above the first `###` (the `#` title and the example-data note) is dropped. New FAQ entries must use `### ` headings to be retrievable. Everything is embedded once at startup, so restart after editing the file.

Safety guardrail: `SYSTEM_PROMPT` has a hard rule to never give medical, dosage, or drug-interaction advice and to redirect to the on-duty pharmacist instead. This rule overrides the retrieved context. Keep it in place when editing prompts.

Frontend: `static/index.html` is one self-contained file (inline CSS/JS, no build) served at `/`. It calls `/chat` via `fetch`. Dark mode uses `data-theme` on `<html>`, follows the OS preference, and is persisted to `localStorage` only after the user toggles it explicitly.

`InMemoryStore` is intentionally the swap point for a real vector DB. Keep its `query(question, top_k) -> list[{title, text, score}]` interface stable.
