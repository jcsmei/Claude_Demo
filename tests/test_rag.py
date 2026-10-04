"""Tests for rag, with fakes in place of Groq and the embedding model."""

import uuid

import chromadb
import pytest

from fakes import FakeClient, FakeEmbedding
from rag import (NOT_COVERED_MARKER, NOT_COVERED_MESSAGE, answer,
                 build_prompt)
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


def test_answer_reports_when_the_documents_lack_the_answer(collection):
    client = FakeClient(f" {NOT_COVERED_MARKER}\n")

    result = answer("Who won the World Cup?", collection, client=client)

    assert result["answer"] == NOT_COVERED_MESSAGE
    assert result["answered"] is False
    assert result["sources"] == []
    assert len(result["passages"]) == 1
