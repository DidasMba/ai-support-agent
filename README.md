# AI Support Agent

A RAG-powered customer support chat agent for small businesses, built on the Gemini API. Give it your FAQs, hours, prices and policies, and it answers customer questions grounded only in that knowledge — with a clear handoff to a human when it doesn't know.

Built for pharmacies and other local businesses in Rwanda, and usable by any small business.

## What it does

- Loads a business's FAQ/knowledge from `app/knowledge/business_faq.md`
- Embeds it with Gemini's embedding model, retrieves relevant chunks per question
- Answers customer questions grounded ONLY in that knowledge (no hallucinated policies)
- Falls back to "a human will follow up" when it doesn't know — critical for trust
- Ships with a simple web chat widget so you can demo it today, before wiring up WhatsApp

## Quickstart (5 minutes)

```bash
git clone https://github.com/DidasMba/ai-support-agent.git
cd ai-support-agent
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # add your free key from aistudio.google.com/apikey
uvicorn app.main:app --reload
```

Open http://localhost:8000 and try: "What time do you open?" It answers using the included fictional pharmacy example.

## Use it for your own business

Replace the placeholder content in `app/knowledge/business_faq.md` with your own business's real hours, prices and policies. This is the single highest-leverage thing you can do — the whole quality of the agent depends on this file.

Keep real business data out of version control: if you fork this repo for a real deployment, put your knowledge file somewhere git-ignored (or in a private repo) rather than committing it here.

## Deploy to Cloud Run

```bash
gcloud run deploy ai-support-agent \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=your-key-here
```

For production, store the key in Secret Manager and reference it with `--set-secrets` instead of `--set-env-vars`.

## Roadmap

1. **v1 (this repo):** web widget + RAG + Gemini + handoff heuristic — get one real business using it
2. **WhatsApp integration:** swap the web widget for the WhatsApp Business Cloud API (Meta) as the customer-facing channel — same `/chat` backend
3. **Real handoff:** instead of a text heuristic, notify a human via email/Slack/WhatsApp when the agent can't answer, and let them reply through the same thread
4. **Agent framework (ADK):** turn the single Gemini call into a proper agent with tools — e.g., "check order status," "log a complaint," "escalate to human" as callable tools instead of prompt tricks
5. **Vector DB upgrade:** once you support multiple businesses or large catalogs, move from in-memory vectors to Vertex AI Vector Search or AlloyDB + pgvector
6. **Document ingestion:** add Document AI / Gemini multimodal to handle receipts, price lists, or catalogs as PDFs/photos instead of manually written markdown

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) and the issues labeled `good first issue`.

## License

Apache 2.0. See [LICENSE](LICENSE).
