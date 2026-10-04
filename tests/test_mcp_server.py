"""Tests for the MCP server, called through a real in-process client.

The database is in memory and Groq is replaced by a fake, so the tests
need no network.
"""

import asyncio
import logging
import uuid

import chromadb
import pytest
from mcp import Client

import mcp_server
import rag
from fakes import FakeEmbedding
from store import add_documents, get_collection

LOGGER = "rag_demo.mcp_server"


@pytest.fixture(autouse=True)
def fake_backends(tmp_path, monkeypatch):
    """Point the server at a small test collection and a fake model."""
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
    monkeypatch.setattr(mcp_server, "_collection", lambda: collection)
    monkeypatch.setattr(rag, "ask", lambda prompt, client=None: "Mars.")


def call(tool, arguments):
    """Call one of the server's tools the way an assistant would."""
    async def run():
        async with Client(mcp_server.server) as client:
            return await client.call_tool(tool, arguments)
    return asyncio.run(run())


def test_server_lists_both_tools():
    async def run():
        async with Client(mcp_server.server) as client:
            return await client.list_tools()
    names = {tool.name for tool in asyncio.run(run()).tools}
    assert names == {"search_documents", "ask_documents"}


def test_search_documents_returns_the_best_passage():
    result = call("search_documents", {"query": "red planet", "k": 1})
    assert not result.is_error
    assert result.structured_content == {"result": [
        {"text": "Mars is called the red planet.", "source": "space.txt"}
    ]}


@pytest.mark.parametrize("arguments, message", [
    ({"query": "  "}, "query must not be empty"),
    ({"query": "mars", "k": 0}, "k must be between 1 and 10"),
    ({"query": "mars", "k": 11}, "k must be between 1 and 10"),
])
def test_search_documents_explains_bad_input(arguments, message):
    result = call("search_documents", arguments)
    assert result.is_error
    assert message in result.content[0].text


def test_ask_documents_returns_answer_and_sources():
    result = call("ask_documents", {"question": "Which is the red planet?"})
    assert not result.is_error
    assert result.structured_content == {
        "answer": "Mars.",
        "sources": ["pets.txt", "space.txt"],
    }


def test_successful_call_is_logged(caplog):
    caplog.set_level(logging.INFO, logger=LOGGER)
    call("search_documents", {"query": "red planet", "k": 1})
    messages = [record.getMessage() for record in caplog.records]
    assert any("search_documents called with" in m for m in messages)
    assert any("search_documents succeeded in" in m for m in messages)


def test_rejected_input_is_logged_as_a_warning(caplog):
    caplog.set_level(logging.INFO, logger=LOGGER)
    call("search_documents", {"query": "mars", "k": 0})
    warnings = [r for r in caplog.records if r.levelname == "WARNING"]
    assert "k must be between 1 and 10" in warnings[0].getMessage()


def test_unexpected_failure_is_logged_with_its_traceback(
        caplog, monkeypatch):
    def broken(prompt, client=None):
        raise RuntimeError("Groq is unreachable")
    monkeypatch.setattr(rag, "ask", broken)
    caplog.set_level(logging.INFO, logger=LOGGER)

    result = call("ask_documents", {"question": "Which is the red planet?"})

    assert result.is_error
    errors = [r for r in caplog.records if r.name == LOGGER
              and r.levelname == "ERROR"]
    assert errors[0].getMessage() == "ask_documents failed"
    assert "Groq is unreachable" in str(errors[0].exc_info[1])


def test_ask_documents_explains_an_empty_question():
    result = call("ask_documents", {"question": ""})
    assert result.is_error
    assert "question must not be empty" in result.content[0].text
