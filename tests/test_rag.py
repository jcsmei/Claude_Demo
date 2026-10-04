"""Tests for rag, with fakes in place of Groq and the embedding model."""

import uuid

import chromadb
import pytest

from fakes import FakeClient, FakeEmbedding
from rag import (NOT_COVERED_MARKER, NOT_COVERED_MESSAGE, UNCLEAR_MARKER,
                 UNCLEAR_MESSAGE, answer, build_prompt, format_history,
                 standalone_question)
from store import add_documents, get_collection


def test_build_prompt_includes_context_sources_and_question():
    chunks = [{"text": "Mars is red.", "source": "space.txt"}]
    prompt = build_prompt("What colour is Mars?", chunks)
    assert "[space.txt]\nMars is red." in prompt
    assert prompt.endswith("Question: What colour is Mars?")


def test_build_prompt_without_chunks_says_so():
    assert "(no documents found)" in build_prompt("Anything?", [])


def test_build_prompt_asks_for_the_marker_when_not_covered():
    assert NOT_COVERED_MARKER in build_prompt("Anything?", [])


@pytest.fixture
def collection(tmp_path):
    """Return an in-memory collection holding one document."""
    (tmp_path / "space.txt").write_text(
        "Mars is called the red planet.", encoding="utf-8"
    )
    collection = get_collection(
        client=chromadb.EphemeralClient(),
        name=f"test-{uuid.uuid4().hex}",
        embedding_function=FakeEmbedding(),
    )
    add_documents(collection, tmp_path)
    return collection


def test_answer_sends_retrieved_text_and_returns_sources(collection):
    client = FakeClient("Mars.")

    result = answer("Which is the red planet?", collection, client=client)

    assert result["answer"] == "Mars."
    assert result["answered"] is True
    assert result["sources"] == ["space.txt"]
    (passage,) = result["passages"]
    assert passage["text"] == "Mars is called the red planet."
    assert passage["distance"] >= 0
    sent = client.received["messages"][0]["content"]
    assert "Mars is called the red planet." in sent


HISTORY = [
    {"role": "user", "content": "Which is the red planet?"},
    {"role": "assistant", "content": "Mars is the red planet."},
]


def test_build_prompt_includes_the_conversation():
    prompt = build_prompt("I don't understand", [], history=HISTORY)
    assert ("Conversation so far:\n"
            "User: Which is the red planet?\n"
            "Assistant: Mars is the red planet.") in prompt
    assert prompt.endswith("Question: I don't understand")


def test_build_prompt_without_history_says_so():
    assert "Conversation so far:\n(none)" in build_prompt("Hi", [])


def test_format_history_keeps_only_recent_shortened_messages():
    history = [{"role": "user", "content": f"question {n} " + "x" * 600}
               for n in range(6)]
    lines = format_history(history).split("\n")
    assert len(lines) == 4
    assert lines[0].startswith("User: question 2 ")
    assert all(len(line) <= len("User: ") + 400 for line in lines)


def test_standalone_question_without_history_skips_the_model():
    client = FakeClient("unused")
    assert standalone_question("What is RAG?", client=client) == (
        "What is RAG?"
    )
    assert client.calls == []


def test_standalone_question_asks_the_model_to_rewrite_a_follow_up():
    client = FakeClient("  Why is Mars\ncalled the red planet? ")

    rewritten = standalone_question("why is that?", HISTORY, client=client)

    assert rewritten == "Why is Mars called the red planet?"
    sent = client.received["messages"][0]["content"]
    assert "User: Which is the red planet?" in sent
    assert sent.endswith("Latest message: why is that?")


@pytest.mark.parametrize("bad_rewrite", ["", "   ", "x" * 301])
def test_standalone_question_falls_back_on_a_bad_rewrite(bad_rewrite):
    client = FakeClient(bad_rewrite)
    assert standalone_question("why?", HISTORY, client=client) == "why?"


def test_answer_searches_with_the_rewritten_follow_up(tmp_path):
    (tmp_path / "space.txt").write_text(
        "Mars is called the red planet.", encoding="utf-8"
    )
    (tmp_path / "pets.txt").write_text(
        "Dogs enjoy long walks.", encoding="utf-8"
    )
    collection = get_collection(
        client=chromadb.EphemeralClient(),
        name=f"test-{uuid.uuid4().hex}",
        embedding_function=FakeEmbedding(),
    )
    add_documents(collection, tmp_path)
    # First reply: the rewrite.  Second reply: the answer.
    client = FakeClient(["Which planet is the red planet?", "Mars."])

    result = answer("which one is it?", collection, client=client, k=1,
                    history=HISTORY)

    assert result["search_query"] == "Which planet is the red planet?"
    assert [chunk["source"] for chunk in result["passages"]] == [
        "space.txt"
    ]
    assert result["answer"] == "Mars."
    # The model answers the user's own words, not the rewrite.
    final_prompt = client.calls[1]["messages"][0]["content"]
    assert final_prompt.endswith("Question: which one is it?")


def test_answer_reports_an_unclear_message(collection):
    client = FakeClient(UNCLEAR_MARKER)

    result = answer("hi", collection, client=client)

    assert result["answer"] == UNCLEAR_MESSAGE
    assert result["status"] == "unclear"
    assert result["answered"] is False
    assert result["sources"] == []


def test_answer_reports_when_the_documents_lack_the_answer(collection):
    client = FakeClient(f" {NOT_COVERED_MARKER}\n")

    result = answer("Who won the World Cup?", collection, client=client)

    assert result["answer"] == NOT_COVERED_MESSAGE
    assert result["answered"] is False
    assert result["sources"] == []
    assert len(result["passages"]) == 1
