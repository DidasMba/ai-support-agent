# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A RAG customer-support chat agent for a local pharmacy (example data: a fictional Kigali pharmacy), built with FastAPI and the Gemini API (`google-generativeai`). v1 is a web chat widget. The README roadmap lists planned extensions: WhatsApp channel, real human handoff, ADK agent with tools, a managed vector DB, and document ingestion.

## Commands

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements-dev.txt   # runtime deps + pytest, httpx, ruff
uvicorn app.main:app --reload          # http://localhost:8000
```

`GEMINI_API_KEY` must be set, either exported or in `.env` (loaded by `python-dotenv`; `.env` is gitignored). The server fails at startup without it (`create_agent()` runs in the FastAPI lifespan), but modules import fine, so tests don't need it.

Deploy (Cloud Run, Dockerfile serves on port 8080). `.dockerignore` keeps `.env` and `venv/` out of the image; keep it that way:
```bash
gcloud run deploy ai-support-agent --source . --region us-central1 --allow-unauthenticated --set-env-vars GEMINI_API_KEY=...
```

There is no build step. `python -m pytest` runs `tests/`, which need no API key: `test_agent.py` drives `SupportAgent` with fake store/model objects, `test_rag.py` drives `InMemoryStore` with a fake embedder, `test_api.py` hits the HTTP layer with `TestClient` and a fake agent on `app.state.agent` (no `with` block, so the lifespan never runs), `test_basics.py` covers chunking, handoff phrases and prompt building. CI (`.github/workflows/ci.yml`) runs `ruff check .` (rules in `pyproject.toml`) and pytest on every push and PR. To verify behavior, run the server and `POST /chat` with `{"message": "...", "history": [...]}`.

## Architecture

Code is split one file per job under `app/`:
- `config.py`: model names, `TOP_K`, `MIN_SCORE`, `GEMINI_TIMEOUT`, `KB_PATH`, `BUSINESS_NAME`, `SUGGESTED_QUESTIONS`, message/history limits; loads `.env`. Every value can be overridden by an env var of the same name. Change defaults here, not in the modules.
- `schemas.py`: pydantic `ChatRequest` (message + optional `history` of `Turn`s), `ChatResponse`, `WidgetInfo`. `answer()` returns a `ChatResponse`.
- `main.py`: the web server only. The lifespan calls `create_agent()` once and stores it on `app.state.agent`; `POST /chat` calls its `answer()`. Also `GET /info` (widget config), `GET /health`, a request-logging middleware that sets `X-Request-ID`, and the widget at `/`.
- `agent.py`: `SupportAgent(store, model).answer(question, history)` is the pipeline (retrieve, call Gemini, decide handoff). Dependencies are injected so tests can pass fakes; `create_agent()` does the real Gemini setup. Future channels (WhatsApp) should call `answer()` rather than duplicating logic.
- `prompts.py`: `SYSTEM_PROMPT`, `NO_MATCH_REPLY`, `BUSY_REPLY`, and `build_prompt()`.
- `handoff.py`: `HANDOFF_PHRASES` and `needs_human()`.
- `rag.py`: chunking and the vector store. `InMemoryStore(chunks, embed=..., min_score=...)` takes an embedder function so tests can pass a fake; the real one is `gemini_embed`, which embeds the whole KB in one batched call.

Request flow for `POST /chat`:
0. The server is stateless: the widget sends the recent conversation as `history`; `answer()` keeps the last `MAX_HISTORY_TURNS`. The previous customer message is prepended to the search text so follow-ups ("and on Sunday?") retrieve the right section, and the transcript goes into the prompt.
1. `store.query()` (`rag.py`) embeds the question with `gemini-embedding-001` and runs cosine similarity against in-memory vectors. It returns the top `TOP_K` (3) chunks with a similarity above **`MIN_SCORE` (0.3)**.
2. **No matches → immediate handoff.** (If Gemini errors in search or generation, `BUSY_REPLY` is returned as a handoff instead of a 500; retries are off so failures return fast.) A canned "team will follow up" reply is returned and the LLM is never called.
3. Otherwise the prompt is built as `SYSTEM_PROMPT + retrieved context + conversation so far + question` (a single string, not a chat/system-instruction API), and one `generate_content` call is made to `CHAT_MODEL` (`gemini-3.6-flash`).
4. `handed_off` is a **substring heuristic** (`handoff.py`) over the reply (`"not sure"`, `"pharmacist"`, `"speak with"`, …). If you change the wording in `SYSTEM_PROMPT` or the fallback, update this phrase list to match, or handoff detection silently breaks.

Knowledge base: `app/knowledge/business_faq.md` is split into chunks on `### ` headings. Each chunk's heading becomes its `title`, which is returned as `sources`. Content above the first `###` (the `#` title and the example-data note) is dropped. New FAQ entries must use `### ` headings to be retrievable. Everything is embedded once at startup, so restart after editing the file.

Safety guardrail: `SYSTEM_PROMPT` has a hard rule to never give medical, dosage, or drug-interaction advice and to redirect to the on-duty pharmacist instead. This rule overrides the retrieved context. Keep it in place when editing prompts.

Frontend: `static/index.html` is one self-contained file (inline CSS/JS, no build) served at `/`. It loads `/info` for the business name and suggestion chips, calls `/chat` via `fetch` with recent history, renders replies with a tiny escape-first markdown subset (paragraphs, `- ` lists, `**bold**`), shows source chips and a handoff notice, and keeps the conversation in `sessionStorage`. Colors are CSS custom properties on `:root` / `:root[data-theme="dark"]`. Dark mode uses `data-theme` on `<html>`, follows the OS preference, and is persisted to `localStorage` only after the user toggles it explicitly.

`InMemoryStore` is intentionally the swap point for a real vector DB. Keep its `query(question, top_k) -> list[{title, text, score}]` interface stable.
