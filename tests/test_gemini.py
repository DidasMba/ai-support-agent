"""The google-genai wiring, with a fake client (no credentials, no network)."""

from types import SimpleNamespace

import pytest

from app import config, gemini


class FakeModels:
    def __init__(self, reply="We open at 7:30 AM."):
        self.reply = reply
        self.embed_calls = []
        self.generate_calls = []

    def embed_content(self, *, model, contents, config):
        self.embed_calls.append((model, contents, config))
        vector = [float(len(contents)), 1.0]
        return SimpleNamespace(embeddings=[SimpleNamespace(values=vector)])

    def generate_content(self, *, model, contents, config):
        self.generate_calls.append((model, contents, config))
        return SimpleNamespace(text=self.reply)


def fake_client(reply="We open at 7:30 AM."):
    return SimpleNamespace(models=FakeModels(reply))


@pytest.fixture
def record_clients(monkeypatch):
    """Capture the arguments genai.Client is built with."""
    calls = []
    monkeypatch.setattr(gemini.genai, "Client", lambda **kwargs: calls.append(kwargs))
    return calls


def test_project_selects_agent_platform(monkeypatch, record_clients):
    monkeypatch.setattr(config, "GOOGLE_CLOUD_PROJECT", "pharmacy-pilot")
    monkeypatch.setattr(config, "GOOGLE_CLOUD_LOCATION", "global")
    monkeypatch.setattr(config, "GEMINI_API_KEY", "ignored-when-a-project-is-set")
    gemini.make_client()
    gemini.make_client("us-central1")
    assert record_clients == [
        {"enterprise": True, "project": "pharmacy-pilot", "location": "global"},
        {"enterprise": True, "project": "pharmacy-pilot", "location": "us-central1"},
    ]
    assert "Agent Platform" in gemini.backend_name()


def test_api_key_selects_developer_api(monkeypatch, record_clients):
    monkeypatch.setattr(config, "GOOGLE_CLOUD_PROJECT", None)
    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-key")
    gemini.make_client()
    assert record_clients == [{"enterprise": False, "api_key": "test-key"}]
    assert gemini.backend_name() == "Gemini Developer API"


def test_missing_configuration_explains_both_options(monkeypatch, record_clients):
    monkeypatch.setattr(config, "GOOGLE_CLOUD_PROJECT", None)
    monkeypatch.setattr(config, "GEMINI_API_KEY", None)
    with pytest.raises(RuntimeError, match="GOOGLE_CLOUD_PROJECT.*GEMINI_API_KEY"):
        gemini.make_client()
    assert record_clients == []


def test_embedder_sends_one_text_per_request():
    client = fake_client()
    embed = gemini.GeminiEmbedder(client, model="gemini-embedding-001")
    vectors = embed(["### Hours", "### Delivery options"], "retrieval_document")
    assert vectors == [[9.0, 1.0], [20.0, 1.0]]
    calls = client.models.embed_calls
    assert [contents for _, contents, _ in calls] == ["### Hours", "### Delivery options"]
    model, _, embed_config = calls[0]
    assert model == "gemini-embedding-001"
    assert embed_config.task_type == "RETRIEVAL_DOCUMENT"
    assert embed_config.http_options.retry_options.attempts == gemini.STARTUP_RETRIES


def test_query_embedding_fails_fast(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_TIMEOUT", 20)
    client = fake_client()
    gemini.GeminiEmbedder(client)(["When do you open?"], "retrieval_query")
    _, _, embed_config = client.models.embed_calls[0]
    assert embed_config.task_type == "RETRIEVAL_QUERY"
    assert embed_config.http_options.retry_options.attempts == gemini.NO_RETRY
    assert embed_config.http_options.timeout == 20_000  # milliseconds


def test_chat_sends_prompt_without_retries():
    client = fake_client()
    response = gemini.GeminiChat(client, model="gemini-3.6-flash").generate_content("Hi")
    assert response.text == "We open at 7:30 AM."
    model, contents, chat_config = client.models.generate_calls[0]
    assert (model, contents) == ("gemini-3.6-flash", "Hi")
    assert chat_config.http_options.retry_options.attempts == gemini.NO_RETRY
    assert chat_config.thinking_config.thinking_level == "LOW"


def test_thinking_level_can_be_turned_off(monkeypatch):
    monkeypatch.setattr(config, "THINKING_LEVEL", "")
    assert gemini.thinking_config() is None


def test_blocked_or_empty_reply_raises():
    with pytest.raises(ValueError):
        gemini.GeminiChat(fake_client(reply=None)).generate_content("Hi")
