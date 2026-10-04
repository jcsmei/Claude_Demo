"""Tests for store, using an in-memory database and a fake embedding."""

import uuid

import chromadb
import pytest

from fakes import FakeEmbedding
from store import add_documents, chunk_text, get_collection, search


@pytest.fixture
def collection():
    """Return an empty in-memory collection with a unique name."""
    return get_collection(
        client=chromadb.EphemeralClient(),
        name=f"test-{uuid.uuid4().hex}",
        embedding_function=FakeEmbedding(),
    )


@pytest.fixture
def folder(tmp_path):
    """Return a folder holding two documents and one file to ignore."""
    (tmp_path / "pets.md").write_text(
        "Cats sleep most of the day.\n\nDogs enjoy long walks.",
        encoding="utf-8",
    )
    (tmp_path / "space.txt").write_text(
        "Mars is called the red planet.", encoding="utf-8"
    )
    (tmp_path / "ignored.csv").write_text("a,b,c", encoding="utf-8")
    return tmp_path


def test_chunk_text_packs_short_paragraphs_together():
    assert chunk_text("One.\n\nTwo.", max_chars=100) == ["One.\n\nTwo."]


def test_chunk_text_starts_a_new_chunk_at_the_limit():
    text = "a" * 30 + "\n\n" + "b" * 30
    assert chunk_text(text, max_chars=40) == ["a" * 30, "b" * 30]


def test_chunk_text_skips_blank_paragraphs():
    assert chunk_text("\n\n  \n\nOnly.\n\n\n\n") == ["Only."]
    assert chunk_text("") == []


def test_add_documents_stores_only_supported_files(collection, folder):
    assert add_documents(collection, folder) == 2
    assert collection.count() == 2


def test_add_documents_twice_does_not_duplicate(collection, folder):
    add_documents(collection, folder)
    add_documents(collection, folder)
    assert collection.count() == 2


def test_search_returns_the_most_relevant_chunk_first(collection, folder):
    add_documents(collection, folder)
    (result,) = search(collection, "Which planet is the red planet?", k=1)
    assert result["text"] == "Mars is called the red planet."
    assert result["source"] == "space.txt"


def test_search_orders_results_by_increasing_distance(collection, folder):
    add_documents(collection, folder)
    results = search(collection, "Which planet is the red planet?", k=2)
    distances = [result["distance"] for result in results]
    assert len(distances) == 2
    assert 0 <= distances[0] <= distances[1]


def test_search_on_an_empty_collection_returns_nothing(collection):
    assert search(collection, "anything") == []
