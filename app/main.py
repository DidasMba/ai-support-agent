import os
from dotenv import load_dotenv

load_dotenv()
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import google.generativeai as genai

from app.rag import build_store

app = FastAPI(title="AI Support Agent")

# Built once at startup — embeddings for a small FAQ are cheap and fast.
store = build_store()
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-3.6-flash")

SYSTEM_PROMPT = """You are a helpful customer support assistant for a local business.
Answer ONLY using the information provided in the context below.
If the context does not contain the answer, say clearly that you're not sure
and that a team member will follow up — do NOT make up an answer.
Keep answers short, friendly, and in the same language the customer used."""


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    handed_off: bool
    sources: list[str]


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    matches = store.query(req.message, top_k=3)

    if not matches:
        return ChatResponse(
            reply=(
                "I'm not sure about that one — I've flagged it for our team "
                "and someone will get back to you shortly. In the meantime, "
                "is there anything else I can help with?"
            ),
            handed_off=True,
            sources=[],
        )

    context = "\n\n".join(f"[{m['title']}]\n{m['text']}" for m in matches)
    prompt = f"{SYSTEM_PROMPT}\n\nContext:\n{context}\n\nCustomer question: {req.message}"

    response = model.generate_content(prompt)
    reply_text = response.text

    # Simple handoff heuristic — refine once you see real conversations.
    handed_off = any(
        phrase in reply_text.lower()
        for phrase in ["not sure", "don't know", "team will", "follow up"]
    )

    return ChatResponse(
        reply=reply_text,
        handed_off=handed_off,
        sources=[m["title"] for m in matches],
    )


# Serve the demo chat widget at "/"
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def index():
    return FileResponse("static/index.html")
