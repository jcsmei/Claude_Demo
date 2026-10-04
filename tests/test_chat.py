"""Tests for chat: choosing a tool and answering with it."""

import uuid

import chromadb
import pytest

import chat
import tools
from fakes import FakeClient, FakeEmbedding
from store import add_documents, get_collection

COMMITS = [
    {"sha": "abc1234", "date": "2026-10-04T20:42:40Z",
     "message": "Add conversation memory",
     "url": "https://github.com/example/commit/abc1234"},
]
HISTORY = [
    {"role": "user", "content": "What is MCP?"},
    {"role": "assistant", "content": "A protocol for tools."},
]


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


def test_choose_tool_reads_the_tool_and_the_rewritten_question():
    client = FakeClient(
        "TOOL: github\nQUESTION: What changed in the code recently?"
    )
    assert chat.choose_tool("what's new?", HISTORY, client=client) == (
        "github", "What changed in the code recently?"
    )


def test_choose_tool_keeps_a_first_message_as_it_was_asked():
    client = FakeClient(
        "TOOL: github\nQUESTION: What changed in the code recently?"
    )
    assert chat.choose_tool("what's new?", client=client) == (
        "github", "what's new?"
    )


def test_choose_tool_shows_the_model_the_tools_and_conversation():
    client = FakeClient("TOOL: documents\nQUESTION: What tools has MCP?")

    chat.choose_tool("what tools does it have?", HISTORY, client=client)

    sent = client.received["messages"][0]["content"]
    assert "- documents:" in sent and "- github:" in sent
    assert "User: What is MCP?" in sent
    assert sent.endswith("Latest message: what tools does it have?")


@pytest.mark.parametrize("reply", [
    "I think github would be best.",
    "TOOL: weather\nQUESTION:",
    "",
    "TOOL: web\nQUESTION: " + "x" * 301,
])
def test_choose_tool_falls_back_when_the_reply_cannot_be_used(reply):
    client = FakeClient(reply)
    assert chat.choose_tool("hello there", client=client) == (
        "documents", "hello there"
    )


def test_choose_tool_accepts_untidy_formatting():
    client = FakeClient("tool:  GitHub \nquestion:   What   changed? ")
    assert chat.choose_tool("what changed?", HISTORY, client=client) == (
        "github", "What changed?"
    )


def test_respond_answers_from_the_documents(collection):
    client = FakeClient(
        ["TOOL: documents\nQUESTION: Which planet is red?", "Mars."]
    )

    result = chat.respond("which one is red?", collection, client=client,
                          history=HISTORY)

    assert result["tool"] == "documents"
    assert result["answer"] == "Mars."
    assert result["search_query"] == "Which planet is red?"
    assert result["sources"] == ["space.txt"]
    # Two model calls: choosing the tool, then answering.
    assert len(client.calls) == 2


def test_respond_answers_from_github(collection, monkeypatch):
    monkeypatch.setattr(tools, "recent_commits", lambda limit: COMMITS)
    client = FakeClient(
        ["TOOL: github\nQUESTION: What changed recently?",
         "Conversation memory was added."]
    )

    result = chat.respond("what's new?", collection, client=client)

    assert result["tool"] == "github"
    assert result["answer"] == "Conversation memory was added."
    assert result["status"] == "answered"
    assert result["commits"] == COMMITS
    assert result["passages"] == []
    sent = client.calls[1]["messages"][0]["content"]
    assert "2026-10-04T20:42:40Z abc1234 Add conversation memory" in sent
    assert sent.endswith("Question: what's new?")


def test_respond_lets_a_tool_failure_through(collection, monkeypatch):
    def failing(limit):
        raise tools.ToolFailure("GitHub could not be reached.")
    monkeypatch.setattr(tools, "recent_commits", failing)
    client = FakeClient("TOOL: github\nQUESTION: What changed?")

    with pytest.raises(tools.ToolFailure, match="could not be reached"):
        chat.respond("what's new?", collection, client=client)
