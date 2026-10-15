"""SupportAgent decisions, using fakes instead of Gemini (no API key needed)."""

from app.agent import SupportAgent
from app.prompts import BUSY_REPLY, NO_MATCH_REPLY

HOURS = {"title": "Business Hours", "text": "### Business Hours\nOpen 7:30 AM.", "score": 0.8}


class FakeStore:
    def __init__(self, matches=None, error=None):
        self.matches, self.error = matches or [], error

    def query(self, question, top_k):
        if self.error:
            raise self.error
        return self.matches


class FakeModel:
    def __init__(self, reply=None, error=None):
        self.reply, self.error = reply, error
        self.prompts = []

    def generate_content(self, prompt, **kwargs):
        self.prompts.append(prompt)
        if self.error:
            raise self.error
        return type("Response", (), {"text": self.reply})()


def test_answers_from_matching_faq():
    model = FakeModel(reply="We open at 7:30 AM.")
    result = SupportAgent(FakeStore([HOURS]), model).answer("When do you open?")
    assert result == {
        "reply": "We open at 7:30 AM.",
        "handed_off": False,
        "sources": ["Business Hours"],
    }
    assert "Open 7:30 AM." in model.prompts[0]


def test_no_match_hands_off_without_calling_gemini():
    model = FakeModel(reply="unused")
    result = SupportAgent(FakeStore([]), model).answer("Do you sell tyres?")
    assert result["reply"] == NO_MATCH_REPLY
    assert result["handed_off"] is True
    assert model.prompts == []


def test_pharmacist_redirect_is_flagged_as_handoff():
    model = FakeModel(reply="Please speak with our on-duty pharmacist.")
    result = SupportAgent(FakeStore([HOURS]), model).answer("I have a headache")
    assert result["handed_off"] is True


def test_gemini_failure_gives_busy_reply():
    model = FakeModel(error=RuntimeError("429 quota"))
    result = SupportAgent(FakeStore([HOURS]), model).answer("When do you open?")
    assert result["reply"] == BUSY_REPLY
    assert result["handed_off"] is True


def test_search_failure_gives_busy_reply():
    store = FakeStore(error=RuntimeError("503"))
    result = SupportAgent(store, FakeModel()).answer("When do you open?")
    assert result["reply"] == BUSY_REPLY
    assert result["sources"] == []
