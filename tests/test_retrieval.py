"""Check that real questions retrieve the passage holding their answer.

Unlike the other tests, this one uses the real embedding model and the
real documents in data/, because retrieval quality depends on both.
It needs no API key, but the first run downloads the embedding model
(about 80 MB).  Run it after every change to the documents: a new
passage can push an older one out of the results.
"""

import uuid

import chromadb
import pytest

from evals.retrieval_cases import CASES, TOP_K
from rag import DATA_FOLDER
from store import add_documents, get_collection, search


@pytest.fixture(scope="module")
def collection():
    """Index the real documents once, in memory, for all the cases."""
    collection = get_collection(
        client=chromadb.EphemeralClient(),
        name=f"retrieval-{uuid.uuid4().hex}",
    )
    add_documents(collection, DATA_FOLDER)
    return collection


@pytest.mark.parametrize("question, expected", CASES)
def test_question_retrieves_its_answer(collection, question, expected):
    # Documents are wrapped at 70 characters, so compare with the line
    # breaks turned into spaces.
    passages = [" ".join(result["text"].split())
                for result in search(collection, question, k=TOP_K)]
    assert any(expected in passage for passage in passages), (
        f"No top-{TOP_K} passage for {question!r} contains {expected!r}"
    )
