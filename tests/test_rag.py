"""Tests for rag, with fakes in place of Groq and the embedding model."""

import uuid

import chromadb

from fakes import FakeClient, FakeEmbedding
from rag import answer, build_prompt
from store import add_documents, get_collection


def test_build_prompt_includes_context_sources_and_question():
    chunks = [{"text": "Mars is red.", "source": "space.txt"}]
    prompt = build_prompt("What colour is Mars?", chunks)
    assert "[space.txt]\nMars is red." in prompt
    assert prompt.endswith("Question: What colour is Mars?")


def test_build_prompt_without_chunks_says_so():
    assert "(no documents found)" in build_prompt("Anything?", [])


def test_answer_sends_retrieved_text_and_returns_sources(tmp_path):
    (tmp_path / "space.txt").write_text(
        "Mars is called the red planet.", encoding="utf-8"
    )
    collection = get_collection(
        client=chromadb.EphemeralClient(),
        name=f"test-{uuid.uuid4().hex}",
        embedding_function=FakeEmbedding(),
    )
    add_documents(collection, tmp_path)
    client = FakeClient("Mars.")

    result = answer("Which is the red planet?", collection, client=client)

    assert result == {"answer": "Mars.", "sources": ["space.txt"]}
    sent = client.received["messages"][0]["content"]
    assert "Mars is called the red planet." in sent
