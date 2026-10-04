"""Tests for llm.ask, using a fake client in place of Groq."""

import pytest

from fakes import FakeClient
from llm import ask


def test_ask_returns_the_model_reply():
    client = FakeClient("RAG looks things up before answering.")
    reply = ask("What is RAG?", client=client)
    assert reply == "RAG looks things up before answering."


def test_ask_sends_the_question_and_model():
    client = FakeClient("ok")
    ask("What is MCP?", client=client, model="test-model")
    assert client.received["model"] == "test-model"
    assert client.received["messages"] == [
        {"role": "user", "content": "What is MCP?"}
    ]


@pytest.mark.parametrize("empty", ["", "   "])
def test_ask_rejects_an_empty_question(empty):
    with pytest.raises(ValueError):
        ask(empty, client=FakeClient("unused"))
