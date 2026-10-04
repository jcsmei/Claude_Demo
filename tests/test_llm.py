"""Tests for llm.ask. A fake client stands in for Groq: no network, no tokens."""

from types import SimpleNamespace

import pytest

from llm import ask


class FakeClient:
    """Mimics the part of the Groq client that ask() uses, and records the call."""

    def __init__(self, reply):
        self.reply = reply
        self.received = None
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.received = kwargs
        message = SimpleNamespace(content=self.reply)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def test_ask_returns_the_model_reply():
    client = FakeClient("RAG looks things up before answering.")
    assert ask("What is RAG?", client=client) == "RAG looks things up before answering."


def test_ask_sends_the_question_and_model():
    client = FakeClient("ok")
    ask("What is MCP?", client=client, model="test-model")
    assert client.received["model"] == "test-model"
    assert client.received["messages"] == [{"role": "user", "content": "What is MCP?"}]


@pytest.mark.parametrize("empty", ["", "   "])
def test_ask_rejects_an_empty_question(empty):
    with pytest.raises(ValueError):
        ask(empty, client=FakeClient("unused"))
