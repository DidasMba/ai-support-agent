"""The only module that talks to Gemini, through the google-genai SDK.

The same code runs on two backends:

- Gemini Enterprise Agent Platform (formerly Vertex AI), when
  GOOGLE_CLOUD_PROJECT is set. Calls are authenticated with Application
  Default Credentials, so on Cloud Run the service account is the identity and
  no API key exists to leak.
- The Gemini Developer API, when only GEMINI_API_KEY is set. Handy for a first
  local run with a free key from aistudio.google.com.

Swapping backends never touches the agent or the RAG code: they only see
`GeminiEmbedder` (an `Embedder`) and `GeminiChat` (a `Model`).
"""

import logging

from google import genai
from google.genai import types

from app import config

logger = logging.getLogger(__name__)

# Indexing the knowledge base at startup can afford a few retries;
# a live customer question must fail fast and get the "busy" reply instead.
STARTUP_RETRIES = 3
NO_RETRY = 1


def uses_agent_platform() -> bool:
    return bool(config.GOOGLE_CLOUD_PROJECT)


def backend_name() -> str:
    if uses_agent_platform():
        return f"Gemini Enterprise Agent Platform ({config.GOOGLE_CLOUD_PROJECT})"
    return "Gemini Developer API"


def make_client(location: str | None = None) -> genai.Client:
    """Build a client for whichever backend the environment configures."""
    if uses_agent_platform():
        return genai.Client(
            enterprise=True,
            project=config.GOOGLE_CLOUD_PROJECT,
            location=location or config.GOOGLE_CLOUD_LOCATION,
        )
    if config.GEMINI_API_KEY:
        return genai.Client(enterprise=False, api_key=config.GEMINI_API_KEY)
    raise RuntimeError(
        "No Gemini backend configured. Set GOOGLE_CLOUD_PROJECT to use Gemini "
        "Enterprise Agent Platform (formerly Vertex AI), or GEMINI_API_KEY to use "
        "the Gemini Developer API. See .env.example."
    )


def http_options(attempts: int) -> types.HttpOptions:
    return types.HttpOptions(
        timeout=int(config.GEMINI_TIMEOUT * 1000),  # the SDK expects milliseconds
        retry_options=types.HttpRetryOptions(attempts=attempts),
    )


def thinking_config() -> types.ThinkingConfig | None:
    """Keep replies fast: FAQ answers need little reasoning (see THINKING_LEVEL)."""
    if not config.THINKING_LEVEL:
        return None
    return types.ThinkingConfig(thinking_level=config.THINKING_LEVEL.upper())


class GeminiEmbedder:
    """An `Embedder` for the RAG store: (texts, task_type) -> one vector per text."""

    def __init__(self, client: genai.Client, model: str | None = None):
        self.client = client
        self.model = model or config.EMBEDDING_MODEL

    def __call__(self, texts: list[str], task_type: str) -> list[list[float]]:
        is_query = task_type == "retrieval_query"
        embed_config = types.EmbedContentConfig(
            task_type=task_type.upper(),
            http_options=http_options(NO_RETRY if is_query else STARTUP_RETRIES),
        )
        # One text per request: some embedding models on Agent Platform accept
        # a single input per call, and a pilot FAQ has a few dozen sections at most.
        vectors = []
        for text in texts:
            result = self.client.models.embed_content(
                model=self.model, contents=text, config=embed_config
            )
            vectors.append(list(result.embeddings[0].values))
        return vectors


class GeminiChat:
    """A `Model` for the agent: turns a prompt into a reply."""

    def __init__(self, client: genai.Client, model: str | None = None):
        self.client = client
        self.model = model or config.CHAT_MODEL

    def generate_content(self, prompt: str) -> types.GenerateContentResponse:
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                http_options=http_options(NO_RETRY),
                thinking_config=thinking_config(),
            ),
        )
        if not response.text:
            # A blocked or empty reply: the agent turns this into the "busy" reply.
            raise ValueError("Gemini returned no text (the reply was blocked or empty)")
        return response
