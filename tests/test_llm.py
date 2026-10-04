"""Tests for llm.ask, using a fake client in place of Groq."""

from types import SimpleNamespace

import groq
import httpx
import pytest

import llm
from fakes import FakeClient
from llm import ask


def rate_limit_error():
    """Build the error Groq raises when a model's allowance is used up."""
    request = httpx.Request("POST", "https://api.groq.com/test")
    return groq.RateLimitError(
        "Rate limit reached on tokens per day (TPD)",
        response=httpx.Response(429, request=request), body=None,
    )


class LimitedClient:
    """A fake Groq client on which the named models are rate limited."""

    def __init__(self, limited):
        self.limited = set(limited)
        self.models_called = []
        completions = SimpleNamespace(create=self._create)
        self.chat = SimpleNamespace(completions=completions)

    def _create(self, model, **kwargs):
        self.models_called.append(model)
        if model in self.limited:
            raise rate_limit_error()
        message = SimpleNamespace(content=f"reply from {model}")
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


@pytest.fixture(autouse=True)
def fresh_fallback(monkeypatch):
    """Start each test with no model marked as rate limited."""
    llm.reset_fallback()
    monkeypatch.setattr(llm, "FALLBACK_MODEL", "backup-model")


def test_ask_returns_the_model_reply():
    client = FakeClient("RAG looks things up before answering.")
    reply = ask("What is RAG?", client=client)
    assert reply == "RAG looks things up before answering."


def test_ask_sends_the_question_and_model():
    client = FakeClient("ok")
    ask("What is MCP?", client=client, model="test-model")
    assert client.received["model"] == "test-model"
    assert client.received["temperature"] == 0
    assert client.received["messages"] == [
        {"role": "user", "content": "What is MCP?"}
    ]


@pytest.mark.parametrize("empty", ["", "   "])
def test_ask_rejects_an_empty_question(empty):
    with pytest.raises(ValueError):
        ask(empty, client=FakeClient("unused"))


def test_ask_uses_the_fallback_when_the_model_is_rate_limited():
    client = LimitedClient(limited=["main-model"])
    reply = ask("What is RAG?", client=client, model="main-model")
    assert reply == "reply from backup-model"
    assert client.models_called == ["main-model", "backup-model"]


def test_ask_skips_a_rate_limited_model_on_later_questions():
    client = LimitedClient(limited=["main-model"])
    ask("First?", client=client, model="main-model")
    ask("Second?", client=client, model="main-model")
    assert client.models_called == ["main-model", "backup-model",
                                    "backup-model"]


def test_ask_tries_the_model_again_after_the_skip_period(monkeypatch):
    client = LimitedClient(limited=["main-model"])
    ask("First?", client=client, model="main-model")
    client.limited.clear()
    monkeypatch.setattr(llm, "SKIP_SECONDS", 0)
    llm.reset_fallback()

    assert ask("Second?", client=client, model="main-model") == (
        "reply from main-model"
    )


def test_ask_raises_when_the_fallback_is_rate_limited_too():
    client = LimitedClient(limited=["main-model", "backup-model"])
    with pytest.raises(groq.RateLimitError):
        ask("What is RAG?", client=client, model="main-model")
    assert client.models_called == ["main-model", "backup-model"]


def test_ask_does_not_fall_back_when_none_is_configured(monkeypatch):
    monkeypatch.setattr(llm, "FALLBACK_MODEL", "")
    client = LimitedClient(limited=["main-model"])
    with pytest.raises(groq.RateLimitError):
        ask("What is RAG?", client=client, model="main-model")
    assert client.models_called == ["main-model"]


def test_ask_does_not_fall_back_to_the_same_model():
    client = LimitedClient(limited=["backup-model"])
    with pytest.raises(groq.RateLimitError):
        ask("What is RAG?", client=client, model="backup-model")
    assert client.models_called == ["backup-model"]


def test_ask_logs_the_switch_to_the_fallback(caplog):
    client = LimitedClient(limited=["main-model"])
    with caplog.at_level("WARNING", logger="rag_demo.llm"):
        ask("What is RAG?", client=client, model="main-model")
    assert "main-model is rate limited" in caplog.text
    assert "using backup-model instead" in caplog.text
