"""The web server: receives chat messages and serves the chat widget."""

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import config
from app.agent import create_agent
from app.schemas import ChatRequest, ChatResponse, WidgetInfo

logging.basicConfig(
    level=config.LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Built once at startup — embeddings for a small FAQ are cheap and fast.
    app.state.agent = create_agent()
    logger.info("Support agent ready (model=%s)", config.CHAT_MODEL)
    yield


app = FastAPI(title="AI Support Agent", version="1.1.0", lifespan=lifespan)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Tag each request with an id and log how long it took."""
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
    started = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - started) * 1000
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "%s %s -> %d (%.0f ms) [%s]",
        request.method, request.url.path, response.status_code, elapsed_ms, request_id,
    )
    return response


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, request: Request) -> ChatResponse:
    return request.app.state.agent.answer(req.message, req.history)


@app.get("/info", response_model=WidgetInfo)
def info() -> WidgetInfo:
    """What the chat widget needs to render itself for this business."""
    return WidgetInfo(
        business_name=config.BUSINESS_NAME,
        suggestions=config.SUGGESTED_QUESTIONS,
        max_message_chars=config.MAX_MESSAGE_CHARS,
    )


@app.get("/health")
def health() -> dict:
    """Liveness check for Cloud Run and load balancers."""
    return {"status": "ok"}


# Serve the demo chat widget at "/"
app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(config.STATIC_DIR / "index.html")
