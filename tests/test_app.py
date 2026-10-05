"""Tests for the Streamlit app, run with Streamlit's own test tool.

The model and the embedding are replaced by fakes, so the tests need
no network.
"""

import uuid
from pathlib import Path

import chromadb
import groq
import httpx
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

import chat
import rag
import store
import tools
from fakes import FakeEmbedding

APP_FILE = str(Path(__file__).parent.parent / "app.py")
PASSAGES = [{"text": "Mars is called the red planet.",
             "source": "space.txt", "distance": 0.4321}]


def fake_answer(question, collection, history=None):
    return {"answer": "Mars.", "status": "answered", "answered": True,
            "sources": ["space.txt"], "passages": PASSAGES,
            "search_query": question, "tool": "documents"}


def fake_refusal(question, collection, history=None):
    return {"answer": rag.NOT_COVERED_MESSAGE, "status": "not_covered",
            "answered": False, "sources": [], "passages": PASSAGES,
            "search_query": question, "tool": "documents"}


def fake_unclear(question, collection, history=None):
    return {"answer": rag.UNCLEAR_MESSAGE, "status": "unclear",
            "answered": False, "sources": [], "passages": PASSAGES,
            "search_query": question, "tool": "documents"}


def fake_collection():
    return chromadb.EphemeralClient().get_or_create_collection(
        f"test-{uuid.uuid4().hex}", embedding_function=FakeEmbedding()
    )


@pytest.fixture
def app(monkeypatch):
    """Return the app with a known password and fake backends."""
    monkeypatch.setenv("APP_PASSWORD", "open-sesame")
    monkeypatch.setenv("MAX_QUESTIONS", "2")
    monkeypatch.setattr(chat, "respond", fake_answer)
    monkeypatch.setattr(store, "get_collection", fake_collection)
    st.cache_resource.clear()
    return AppTest.from_file(APP_FILE, default_timeout=30)


def log_in(app, password="open-sesame"):
    app.run()
    app.text_input[0].set_value(password)
    app.button[0].click().run()
    return app


def ask(app, question):
    app.chat_input[0].set_value(question).run()
    return app


def test_welcome_explains_the_demo_before_login(app):
    app.run()
    assert app.title[0].value == "Jack Mei: RAG, LangGraph and MCP Demo"
    welcome = app.markdown[0].value
    assert "built by" in welcome and "Jack Mei" in welcome
    assert "Built with Claude Code" in welcome
    for term in ("**RAG**", "**LangGraph:**", "**MCP**"):
        assert term in welcome


def test_page_is_locked_before_login(app):
    app.run()
    assert not app.exception
    assert len(app.text_input) == 1
    assert len(app.chat_input) == 0


def test_wrong_password_is_rejected(app):
    log_in(app, password="guess")
    assert app.error[0].value == "Incorrect password."
    assert len(app.chat_input) == 0


def test_app_stays_locked_when_no_password_is_configured(
        app, monkeypatch):
    # An empty value stops load_dotenv from filling it in from .env.
    monkeypatch.setenv("APP_PASSWORD", "")
    app.run()
    assert "APP_PASSWORD is not set" in app.error[0].value
    assert len(app.text_input) == 0
    assert len(app.chat_input) == 0


def test_correct_password_opens_the_chat(app):
    log_in(app)
    assert not app.exception
    assert len(app.chat_input) == 1


def test_question_shows_answer_and_retrieved_passages(app):
    ask(log_in(app), "Which is the red planet?")
    assert not app.exception
    user, assistant = app.chat_message
    assert user.markdown[0].value == "Which is the red planet?"
    assert assistant.markdown[0].value == "Mars."
    assert assistant.expander[0].label == "Retrieved passages (1)"
    assert assistant.markdown[1].value == (
        "**1. space.txt** · distance 0.43"
    )
    assert assistant.text[0].value == "Mars is called the red planet."


def test_unanswerable_question_is_explained(app, monkeypatch):
    monkeypatch.setattr(chat, "respond", fake_refusal)

    ask(log_in(app), "Who won the World Cup?")

    assert not app.exception
    reply = app.chat_message[1]
    assert reply.markdown[0].value.startswith(rag.NOT_COVERED_MESSAGE)
    assert "sidebar" in reply.markdown[0].value
    assert reply.expander[0].label == (
        "Closest passages, none with the answer (1)"
    )
    assert len(reply.error) == 0


def test_documents_answer_names_its_source(app):
    ask(log_in(app), "Which is the red planet?")
    captions = [caption.value for caption in app.chat_message[1].caption]
    assert "Source: the project's documents" in captions


def test_github_answer_shows_its_source_and_commits(app, monkeypatch):
    commits = [{"sha": "abc1234", "date": "2026-10-04T20:42:40Z",
                "message": "Add conversation memory",
                "url": "https://github.com/example/commit/abc1234"}]

    def github_answer(question, collection, history=None):
        return {"answer": "Memory was added.", "status": "answered",
                "answered": True, "tool": "github", "sources": ["GitHub"],
                "passages": [], "commits": commits,
                "search_query": question}
    monkeypatch.setattr(chat, "respond", github_answer)

    ask(log_in(app), "What changed recently?")

    assert not app.exception
    reply = app.chat_message[1]
    assert reply.markdown[0].value == "Memory was added."
    captions = [caption.value for caption in reply.caption]
    assert "Source: GitHub, the project's live commit history" in captions
    assert reply.expander[0].label == "Commits fetched from GitHub (1)"
    assert reply.markdown[1].value == (
        "- 2026-10-04 · "
        "[abc1234](https://github.com/example/commit/abc1234) · "
        "Add conversation memory"
    )


def test_data_answer_shows_its_source_sql_and_rows(app, monkeypatch):
    query = {"sql": "SELECT SUM(drivers) AS total FROM driver_licenses",
             "columns": ["total"], "rows": [[180648]],
             "updated": "2026-10-04"}

    def data_answer(question, collection, history=None):
        return {"answer": "There are 180648 drivers.", "status": "answered",
                "answered": True, "tool": "nyc_data",
                "sources": ["NYC Open Data"], "passages": [],
                "query": query, "search_query": question}
    monkeypatch.setattr(chat, "respond", data_answer)

    ask(log_in(app), "How many drivers are there?")

    assert not app.exception
    reply = app.chat_message[1]
    assert reply.markdown[0].value == "There are 180648 drivers."
    captions = " ".join(caption.value for caption in reply.caption)
    assert "Source: NYC Open Data" in captions
    assert "no driver names or license numbers" in captions
    assert reply.expander[0].label == (
        "Query run on NYC Open Data (1 rows returned)"
    )
    assert reply.code[0].value == query["sql"]
    assert reply.dataframe[0].value.to_dict("records") == [
        {"total": 180648}
    ]


def test_web_answer_shows_its_source_and_results(app, monkeypatch):
    results = [{"title": "Taxi medallion", "content": "A permit.",
                "url": "https://example.com/medallion"}]

    def web_answer(question, collection, history=None):
        return {"answer": f"{chat.WEB_NOTICE}\n\nA medallion is a permit.",
                "status": "answered", "answered": True, "tool": "web",
                "sources": ["https://example.com/medallion"],
                "passages": [], "web_results": results,
                "search_query": question}
    monkeypatch.setattr(chat, "respond", web_answer)

    ask(log_in(app), "what are medallions?")

    assert not app.exception
    reply = app.chat_message[1]
    # The notice is a highlighted box, and is not repeated in the answer.
    assert reply.warning[0].value == chat.WEB_NOTICE
    assert reply.markdown[0].value == "A medallion is a permit."
    captions = " ".join(caption.value for caption in reply.caption)
    assert ("Source: a web search through Tavily's MCP server, not the "
            "project's official documents") in captions
    assert "not the project's official documents" in captions
    assert reply.expander[0].label == "Web results (1)"
    assert reply.markdown[1].value == (
        "**1. [Taxi medallion](https://example.com/medallion)**"
    )
    assert reply.text[0].value == "A permit."


def test_sidebar_shows_the_decision_flow(app):
    log_in(app)
    headers = [header.value for header in app.sidebar.header]
    assert "How the bot decides" in headers


def test_tool_failure_is_explained(app, monkeypatch):
    fail_with(monkeypatch, tools.ToolFailure("GitHub could not be reached."))

    ask(log_in(app), "What changed recently?")

    assert not app.exception
    headline = app.chat_message[1].error[0].value
    assert headline == "A tool failed: GitHub could not be reached."


def test_unclear_message_gets_help_without_passages(app, monkeypatch):
    monkeypatch.setattr(chat, "respond", fake_unclear)

    ask(log_in(app), "hi")

    assert not app.exception
    reply = app.chat_message[1]
    assert reply.markdown[0].value == rag.UNCLEAR_MESSAGE
    assert len(reply.expander) == 0


def test_earlier_conversation_is_passed_with_each_question(
        app, monkeypatch):
    histories = []

    def recording_answer(question, collection, history=None):
        histories.append([(message["role"], message["content"])
                          for message in history])
        return fake_answer(question, collection)
    monkeypatch.setattr(chat, "respond", recording_answer)
    log_in(app)

    ask(app, "Which is the red planet?")
    ask(app, "I don't understand")

    assert histories == [
        [],
        [("user", "Which is the red planet?"), ("assistant", "Mars.")],
    ]


def test_rewritten_follow_up_is_shown_with_the_passages(
        app, monkeypatch):
    def rewriting_answer(question, collection, history=None):
        result = fake_answer(question, collection)
        result["search_query"] = "Which planet is the red planet?"
        return result
    monkeypatch.setattr(chat, "respond", rewriting_answer)

    ask(log_in(app), "which one is it?")

    captions = [caption.value for caption in app.chat_message[1].caption]
    assert any('"Which planet is the red planet?"' in caption
               for caption in captions)


def test_unchanged_question_shows_no_rewrite_note(app):
    ask(log_in(app), "Which is the red planet?")
    captions = [caption.value for caption in app.chat_message[1].caption]
    assert not any("rewritten" in caption for caption in captions)


def test_failed_answers_are_left_out_of_the_conversation(
        app, monkeypatch):
    fail_with(monkeypatch, RuntimeError("database file is missing"))
    log_in(app)
    ask(app, "First question?")

    histories = []

    def recording_answer(question, collection, history=None):
        histories.append([message["content"] for message in history])
        return fake_answer(question, collection)
    monkeypatch.setattr(chat, "respond", recording_answer)
    ask(app, "Second question?")

    assert histories == [["First question?"]]


def test_clicking_an_example_question_asks_it(app):
    log_in(app)
    example = app.button[0].label
    app.button[0].click().run()

    assert not app.exception
    assert app.chat_message[0].markdown[0].value == example
    assert app.chat_message[1].markdown[0].value == "Mars."
    # The examples are only offered before the first question.
    assert len(app.button) == 0


def test_sidebar_explains_the_key_terms(app):
    log_in(app)
    sidebar_text = " ".join(m.value for m in app.sidebar.markdown)
    for term in ("Chunk", "Embedding", "Distance"):
        assert f"**{term}:**" in sidebar_text


def test_history_keeps_earlier_questions(app):
    log_in(app)
    ask(app, "First question?")
    ask(app, "Second question?")
    asked = [m.markdown[0].value for m in app.chat_message[::2]]
    assert asked == ["First question?", "Second question?"]


def test_index_is_rebuilt_only_when_a_document_changes(
        app, monkeypatch, tmp_path):
    document = tmp_path / "notes.md"
    document.write_text("Old text.", encoding="utf-8")
    indexed = []
    monkeypatch.setattr(rag, "DATA_FOLDER", tmp_path)
    monkeypatch.setattr(
        store, "add_documents",
        lambda collection, folder: indexed.append(document.read_text()),
    )
    monkeypatch.setenv("MAX_QUESTIONS", "5")
    log_in(app)

    ask(app, "First question?")
    ask(app, "Second question?")
    assert indexed == ["Old text."]

    document.write_text("New text.", encoding="utf-8")
    ask(app, "Third question?")
    assert indexed == ["Old text.", "New text."]
    assert not app.exception


def test_chat_is_disabled_at_the_question_limit(app):
    log_in(app)
    ask(app, "First question?")
    assert not app.chat_input[0].disabled
    ask(app, "Second question?")
    assert app.chat_input[0].disabled
    assert "question limit" in app.info[0].value


def fail_with(monkeypatch, error):
    """Make every question fail with `error`."""
    def broken(question, collection, history=None):
        raise error
    monkeypatch.setattr(chat, "respond", broken)


def groq_status_error(error_class, status):
    """Build the error Groq raises for an HTTP `status` response."""
    request = httpx.Request("POST", "https://api.groq.com/test")
    response = httpx.Response(status, request=request)
    return error_class(f"Error code: {status}", response=response,
                       body=None)


def test_unexpected_failure_shows_details_and_keeps_page_working(
        app, monkeypatch):
    fail_with(monkeypatch, RuntimeError("database file is missing"))

    ask(log_in(app), "Which is the red planet?")

    assert not app.exception
    reply = app.chat_message[1]
    assert "failed before the model could answer" in reply.error[0].value
    assert reply.expander[0].label == "Technical details"
    assert reply.code[0].value == "RuntimeError: database file is missing"
    assert len(app.chat_input) == 1


@pytest.mark.parametrize("error, expected", [
    (groq_status_error(groq.RateLimitError, 429), "rate limit"),
    (groq_status_error(groq.AuthenticationError, 401), "API key"),
    (groq_status_error(groq.InternalServerError, 500), "HTTP 500"),
    (groq.APIConnectionError(
        request=httpx.Request("POST", "https://api.groq.com/test")),
     "could not be reached"),
])
def test_groq_failures_are_explained(app, monkeypatch, error, expected):
    fail_with(monkeypatch, error)

    ask(log_in(app), "Which is the red planet?")

    headline = app.chat_message[1].error[0].value
    assert headline.startswith("Generation failed")
    assert expected in headline


def test_daily_limit_is_explained_differently(app, monkeypatch):
    request = httpx.Request("POST", "https://api.groq.com/test")
    error = groq.RateLimitError(
        "Rate limit reached on tokens per day (TPD): Limit 200000",
        response=httpx.Response(429, request=request), body=None,
    )
    fail_with(monkeypatch, error)

    ask(log_in(app), "Which is the red planet?")

    headline = app.chat_message[1].error[0].value
    assert "daily allowance" in headline
    assert "Wait a minute" not in headline


def test_secrets_are_removed_from_error_details(app, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test_secret")
    fail_with(monkeypatch, RuntimeError("bad key gsk_test_secret used"))

    ask(log_in(app), "Which is the red planet?")

    detail = app.chat_message[1].code[0].value
    assert detail == "RuntimeError: bad key [redacted] used"
