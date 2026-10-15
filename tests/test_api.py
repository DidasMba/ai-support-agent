"""HTTP layer, with a fake agent (the lifespan, and so Gemini, never runs)."""

from fastapi.testclient import TestClient

from app import config
from app.main import app
from app.schemas import ChatResponse


class FakeAgent:
    def __init__(self):
        self.calls = []

    def answer(self, question, history=()):
        self.calls.append((question, list(history)))
        return ChatResponse(reply="We open at 7:30 AM.", handed_off=False, sources=["Hours"])


def client() -> tuple[TestClient, FakeAgent]:
    agent = FakeAgent()
    app.state.agent = agent
    return TestClient(app), agent


def test_chat_passes_message_and_history_to_agent():
    http, agent = client()
    res = http.post("/chat", json={
        "message": "  When do you open?  ",
        "history": [{"role": "user", "content": "Hi"}],
    })
    assert res.status_code == 200
    assert res.json() == {"reply": "We open at 7:30 AM.", "handed_off": False, "sources": ["Hours"]}
    question, history = agent.calls[0]
    assert question == "When do you open?"
    assert history[0].content == "Hi"
    assert res.headers["X-Request-ID"]


def test_chat_rejects_blank_and_oversized_messages():
    http, agent = client()
    assert http.post("/chat", json={"message": "   "}).status_code == 422
    too_long = "x" * (config.MAX_MESSAGE_CHARS + 1)
    assert http.post("/chat", json={"message": too_long}).status_code == 422
    assert agent.calls == []


def test_info_and_health():
    http, _ = client()
    assert http.get("/health").json() == {"status": "ok"}
    info = http.get("/info").json()
    assert info["business_name"] == config.BUSINESS_NAME
    assert info["suggestions"]


def test_widget_is_served():
    http, _ = client()
    res = http.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
