"""The web server: receives chat messages and serves the chat widget."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.agent import create_agent


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Built once at startup — embeddings for a small FAQ are cheap and fast.
    app.state.agent = create_agent()
    yield


app = FastAPI(title="AI Support Agent", lifespan=lifespan)


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    handed_off: bool
    sources: list[str]


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, request: Request):
    return ChatResponse(**request.app.state.agent.answer(req.message))


# Serve the demo chat widget at "/"
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def index():
    return FileResponse("static/index.html")
