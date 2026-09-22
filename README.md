# AI Support Agent — MVP

A RAG-powered customer support chat agent for a local business, built on
the Gemini API. This is the flagship-project starting point for the
GDE Cloud AI path: v1 proves the core loop (knowledge base → RAG →
Gemini → human handoff), deployed publicly. Everything after this is
extension, not rebuild.

## What this does

- Loads a business's FAQ/knowledge from `app/knowledge/business_faq.md`
- Embeds it with Gemini's embedding model, retrieves relevant chunks per question
- Answers customer questions grounded ONLY in that knowledge (no hallucinated policies)
- Falls back to "a human will follow up" when it doesn't know — critical for trust
- Ships with a simple web chat widget so you can demo it today, before
  wiring up WhatsApp

## 1. Local setup

```bash
cd ai-support-agent
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Get a Gemini API key at https://aistudio.google.com/apikey (free tier is
enough for development), then:

```bash
export GEMINI_API_KEY="your-key-here"   # Windows: set GEMINI_API_KEY=your-key-here
uvicorn app.main:app --reload
```

Open http://localhost:8000 — you'll see the demo chat widget.

## 2. Make it real

Before you demo it to anyone, replace the placeholder content in
`app/knowledge/business_faq.md` with your pilot business's actual hours,
prices, policies, etc. This is the single highest-leverage thing you can
do — the whole quality of the agent depends on this file.

## 3. Deploy to Cloud Run

```bash
gcloud run deploy ai-support-agent \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=your-key-here
```

(Better long-term: store the key in Secret Manager and reference it with
`--set-secrets` instead of `--set-env-vars`.)

## Roadmap (in build order)

1. **v1 (this repo):** web widget + RAG + Gemini + handoff heuristic — get
   one real business using it
2. **WhatsApp integration:** swap the web widget for the WhatsApp Business
   Cloud API (Meta) as the customer-facing channel — same `/chat` backend
3. **Real handoff:** instead of a text heuristic, notify a human via
   email/Slack/WhatsApp when the agent can't answer, and let them reply
   through the same thread
4. **Agent framework (ADK):** turn the single Gemini call into a proper
   agent with tools — e.g., "check order status," "log a complaint,"
   "escalate to human" as callable tools instead of prompt tricks
5. **Vector DB upgrade:** once you support multiple businesses or large
   catalogs, move from in-memory vectors to Vertex AI Vector Search or
   AlloyDB + pgvector
6. **Document ingestion:** add Document AI / Gemini multimodal to handle
   receipts, price lists, or catalogs as PDFs/photos instead of manually
   written markdown

## Content this naturally produces

- "I built an AI support agent for a local business using Gemini + RAG" (article 1)
- "How I handled the human-handoff problem in an AI support agent" (article 2)
- "From web widget to WhatsApp: adding a real channel" (article 3)
- "Turning a single Gemini call into an agent with ADK" (article 4)
- A live demo you can show at a GDG meetup or on your GDE portfolio
