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

import rag
import store
from fakes import FakeEmbedding

APP_FILE = str(Path(__file__).parent.parent / "app.py")
PASSAGES = [{"text": "Mars is called the red planet.",
             "source": "space.txt", "distance": 0.4321}]


def fake_answer(question, collection):
    return {"answer": "Mars.", "answered": True,
            "sources": ["space.txt"], "passages": PASSAGES}


def fake_refusal(question, collection):
    return {"answer": rag.NOT_COVERED_MESSAGE, "answered": False,
            "sources": [], "passages": PASSAGES}


def fake_collection():
    return chromadb.EphemeralClient().get_or_create_collection(
        f"test-{uuid.uuid4().hex}", embedding_function=FakeEmbedding()
    )


@pytest.fixture
def app(monkeypatch):
    """Return the app with a known password and fake backends."""
    monkeypatch.setenv("APP_PASSWORD", "open-sesame")
    monkeypatch.setenv("MAX_QUESTIONS", "2")
    monkeypatch.setattr(rag, "answer", fake_answer)
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
    monkeypatch.setattr(rag, "answer", fake_refusal)

    ask(log_in(app), "Who won the World Cup?")

    assert not app.exception
    reply = app.chat_message[1]
    assert reply.markdown[0].value.startswith(rag.NOT_COVERED_MESSAGE)
    assert "sidebar" in reply.markdown[0].value
    assert reply.expander[0].label == (
        "Closest passages, none with the answer (1)"
    )
    assert len(reply.error) == 0


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
    def broken(question, collection):
        raise error
    monkeypatch.setattr(rag, "answer", broken)


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


def test_secrets_are_removed_from_error_details(app, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test_secret")
    fail_with(monkeypatch, RuntimeError("bad key gsk_test_secret used"))

    ask(log_in(app), "Which is the red planet?")

    detail = app.chat_message[1].code[0].value
    assert detail == "RuntimeError: bad key [redacted] used"
