# Subiza AI

A RAG-powered customer support chat agent for small businesses, built on Gemini with the [Google Gen AI SDK](https://github.com/googleapis/python-genai) and running on Gemini Enterprise Agent Platform (formerly Vertex AI). Give it your FAQs, hours, prices and policies, and it answers customer questions grounded only in that knowledge — with a clear handoff to a human when it doesn't know.

Built for pharmacies and other local businesses in Rwanda, and usable by any small business.

## What it does

- Loads a business's FAQ/knowledge from `app/knowledge/business_faq.md`
- Embeds it with Gemini's embedding model, retrieves relevant chunks per question
- Answers customer questions grounded ONLY in that knowledge (no hallucinated policies)
- Falls back to "a human will follow up" when it doesn't know — critical for trust
- Understands follow-up questions ("and on Sunday?") using the recent conversation
- Ships with a polished, mobile-friendly chat widget (light/dark mode, suggested
  questions, source chips, clear handoff notices) so you can demo it today

## Quickstart (5 minutes)

```bash
git clone https://github.com/DidasMba/ai-support-agent.git
cd ai-support-agent
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Then pick a backend in `.env`:

- **Gemini Enterprise Agent Platform (recommended).** Set `GOOGLE_CLOUD_PROJECT` to a project with the Agent Platform API (`aiplatform.googleapis.com`) enabled, then run `gcloud auth application-default login` once. No API key is involved.
- **Gemini Developer API.** Leave `GOOGLE_CLOUD_PROJECT` unset and set `GEMINI_API_KEY` to a free key from [aistudio.google.com/apikey](https://aistudio.google.com/apikey).

```bash
uvicorn app.main:app --reload
```

The startup log says which backend is in use. Open http://localhost:8000 and try: "What time do you open?" It answers using the included fictional pharmacy example.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/chat` | `{"message": "...", "history": [{"role": "user", "content": "..."}]}` → `{"reply", "handed_off", "sources"}` |
| `GET` | `/info` | Business name and suggested questions for the widget |
| `GET` | `/health` | Liveness check |
| `GET` | `/docs` | Interactive OpenAPI docs |

The server is stateless: the widget sends recent turns as `history`, so it scales out on Cloud Run without a session store.

## Configuration

Every setting in `app/config.py` can be overridden with an environment variable (or a line in `.env`), e.g. `BUSINESS_NAME`, `CHAT_MODEL`, `TOP_K`, `MIN_SCORE`, `MAX_HISTORY_TURNS`. See `.env.example`.

On Agent Platform, `GOOGLE_CLOUD_LOCATION` defaults to `global`. If your embedding model isn't served there, set `EMBEDDING_LOCATION` (for example `us-central1`) and the app uses a second client for embeddings only.

All Gemini calls live in `app/gemini.py`. Startup indexing retries up to 3 times; a live customer question never retries and gets the "busy" reply after `GEMINI_TIMEOUT` seconds.

## Development

```bash
pip install -r requirements-dev.txt
ruff check .
python -m pytest        # no API key needed — Gemini is replaced with fakes
```

## Use it for your own business

Replace the placeholder content in `app/knowledge/business_faq.md` with your own business's real hours, prices and policies. This is the single highest-leverage thing you can do — the whole quality of the agent depends on this file.

Keep real business data out of version control: if you fork this repo for a real deployment, put your knowledge file somewhere git-ignored (or in a private repo) rather than committing it here.

## Deploy to Cloud Run

On Cloud Run the service's own identity calls Gemini, so there is no API key to store, rotate or leak. Give the service a dedicated service account that can call models and nothing else:

```bash
PROJECT_ID=your-gcp-project-id
gcloud services enable aiplatform.googleapis.com run.googleapis.com --project $PROJECT_ID

gcloud iam service-accounts create support-agent --project $PROJECT_ID
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member "serviceAccount:support-agent@$PROJECT_ID.iam.gserviceaccount.com" \
  --role roles/aiplatform.user

gcloud run deploy ai-support-agent \
  --source . \
  --project $PROJECT_ID \
  --region us-central1 \
  --allow-unauthenticated \
  --service-account support-agent@$PROJECT_ID.iam.gserviceaccount.com \
  --set-env-vars GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_CLOUD_LOCATION=global
```

If you deploy with the Gemini Developer API instead, store `GEMINI_API_KEY` in Secret Manager and pass it with `--set-secrets`, never `--set-env-vars`.

## Roadmap

1. **v1 (this repo):** web widget + RAG + Gemini + handoff heuristic — get one real business using it
2. **WhatsApp integration:** swap the web widget for the WhatsApp Business Cloud API (Meta) as the customer-facing channel — same `/chat` backend
3. **Real handoff:** instead of a text heuristic, notify a human via email/Slack/WhatsApp when the agent can't answer, and let them reply through the same thread
4. **Agent framework (ADK):** turn the single Gemini call into a proper agent with tools — e.g., "check order status," "log a complaint," "escalate to human" as callable tools instead of prompt tricks
5. **Vector DB upgrade:** once you support multiple businesses or large catalogs, move from in-memory vectors to Vector Search on Gemini Enterprise Agent Platform or AlloyDB + pgvector
6. **Document ingestion:** add Document AI / Gemini multimodal to handle receipts, price lists, or catalogs as PDFs/photos instead of manually written markdown

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) and the issues labeled `good first issue`.

## License

Apache 2.0. See [LICENSE](LICENSE).
