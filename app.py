"""Streamlit chat interface for the RAG demo.

Run locally with `streamlit run app.py`.  The page is locked behind
the password in the APP_PASSWORD setting, and each visitor session is
limited to MAX_QUESTIONS questions to protect the Groq quota.
"""

import hashlib
import hmac
import logging
import os

import groq
import streamlit as st
from dotenv import load_dotenv

from chat import flow_diagram, respond
from rag import DATA_FOLDER
from tools import ToolFailure
from store import DOCUMENT_SUFFIXES, add_documents, get_collection

load_dotenv()
logger = logging.getLogger("rag_demo.app")

DEFAULT_MAX_QUESTIONS = "20"
EXAMPLE_QUESTIONS = (
    "What is this chat bot, and how does it know about itself?",
    "What is a chunk, and why are documents split into chunks?",
    "What tools does the MCP server have?",
    "Which language model writes the answers, and why that one?",
    "Who built this demo, and what is his background?",
    "What changed in the code most recently?",
    "How many active medallion taxi drivers are there in New York?",
)
# Shown under each answer, so the viewer knows where it came from.
SOURCE_LABELS = {
    "documents": "Source: the project's documents",
    "github": "Source: GitHub, the project's live commit history",
    "nyc_data": ("Source: NYC Open Data, live counts of active "
                 "medallion taxi driver licenses"),
}
# Values that must never appear on the page, even inside an error.
SECRET_SETTINGS = ("GROQ_API_KEY", "APP_PASSWORD")


def get_setting(name, default=""):
    """Return a setting from the environment or Streamlit's secrets.

    Locally the value comes from `.env`; on Streamlit's hosting it
    comes from the app's secrets.
    """
    value = os.environ.get(name, "")
    if value:
        return value
    try:
        return str(st.secrets[name])
    except Exception:
        # No secrets file, or no such secret: fall back to the default.
        return default


def documents_fingerprint():
    """Return a hash that changes whenever a document changes."""
    digest = hashlib.sha256()
    for path in sorted(DATA_FOLDER.iterdir()):
        if path.suffix.lower() in DOCUMENT_SUFFIXES:
            digest.update(path.name.encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


@st.cache_resource(show_spinner="Indexing the documents...",
                   max_entries=1)
def load_collection(fingerprint):
    """Open the database and index the documents.

    The result is cached, so indexing happens once and not on every
    question.  `fingerprint` is part of the cache key: when a document
    changes, the fingerprint changes and the index is rebuilt.  Without
    it, a host that updates the files but keeps the process running
    would go on searching the old index.
    """
    collection = get_collection()
    add_documents(collection, DATA_FOLDER)
    return collection


def require_password():
    """Show a password form and stop the page until it is passed."""
    if st.session_state.get("authenticated"):
        return
    expected = get_setting("APP_PASSWORD")
    if not expected:
        # Fail closed: with no password configured, nobody gets in.
        st.error("The app is locked because APP_PASSWORD is not set.")
        st.stop()
    with st.form("login"):
        entered = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Enter")
    if submitted:
        # compare_digest takes the same time whether or not the
        # password is close, so timing reveals nothing about it.
        if hmac.compare_digest(entered.encode(), expected.encode()):
            st.session_state.authenticated = True
            st.rerun()
        logger.warning("incorrect password entered")
        st.error("Incorrect password.")
    st.stop()


def describe_error(error):
    """Return a headline and the technical detail for a failure.

    The headline says which stage failed and whether asking again
    will help.  The detail is the error's type and message, with
    secret values removed.
    """
    # Specific Groq errors come before APIStatusError, their parent.
    if isinstance(error, ToolFailure):
        headline = f"A tool failed: {error}"
    elif isinstance(error, groq.RateLimitError):
        # Groq has a limit per minute and a limit per day, and names
        # the one that was hit in its message.
        if "per day" in str(error):
            headline = ("Generation failed: this demo has used its "
                        "daily allowance of Groq tokens. The allowance "
                        "refills gradually over 24 hours, so please "
                        "try again later.")
        else:
            headline = ("Generation failed: Groq's rate limit was "
                        "reached. Wait a minute, then ask again.")
    elif isinstance(error, groq.AuthenticationError):
        headline = ("Generation failed: Groq rejected the app's API "
                    "key. Asking again will not help until the key "
                    "is replaced.")
    elif isinstance(error, groq.APIConnectionError):
        headline = ("Generation failed: Groq could not be reached. "
                    "Ask again in a moment.")
    elif isinstance(error, groq.APIStatusError):
        headline = ("Generation failed: Groq returned HTTP "
                    f"{error.status_code}.")
    else:
        headline = ("The app failed before the model could answer. "
                    "The technical details show where.")
    detail = f"{type(error).__name__}: {error}"
    for name in SECRET_SETTINGS:
        secret = get_setting(name)
        if secret:
            detail = detail.replace(secret, "[redacted]")
    return headline, detail


def answer_question(question, history):
    """Return the chat message that answers `question`.

    `history` is the earlier conversation, which lets the bot follow
    up on what was said before.  A failure is logged with its
    traceback and turned into an error message, so the page keeps
    working.
    """
    logger.info("question asked: %s", question)
    try:
        collection = load_collection(documents_fingerprint())
        result = respond(question, collection, history=history)
    except Exception as error:
        logger.exception("question failed: %s", question)
        headline, detail = describe_error(error)
        return {"role": "assistant", "content": headline,
                "detail": detail, "error": True}
    content = result["answer"]
    if result["status"] == "not_covered":
        content += (" Try a question about the documents listed in "
                    "the sidebar.")
    # Kept only when a follow-up was rewritten for the search.
    rewritten = result["search_query"]
    if rewritten == question:
        rewritten = None
    return {"role": "assistant", "content": content,
            "passages": result["passages"],
            "commits": result.get("commits"),
            "query": result.get("query"),
            "status": result["status"], "tool": result["tool"],
            "rewritten": rewritten}


def show_commits(commits):
    """List the commits a GitHub answer was drawn from."""
    with st.expander(f"Commits fetched from GitHub ({len(commits)})"):
        st.caption(
            "These are the project's most recent code changes, "
            "fetched live from GitHub's public API. The model was "
            "given this list and told to answer from it only."
        )
        for commit in commits:
            st.markdown(
                f"- {commit['date'][:10]} · "
                f"[{commit['sha']}]({commit['url']}) · "
                f"{commit['message']}"
            )


def show_query(query):
    """Show the SQL a data answer ran and the rows it returned."""
    with st.expander(f"Query run on NYC Open Data ({len(query['rows'])} "
                     "rows returned)"):
        st.caption(
            "The model wrote this SQL, and it ran on counts fetched "
            "live from NYC Open Data (dataset jb3k-j3gp, last updated "
            f"{query['updated']}). Only counts are fetched: no driver "
            "names or license numbers. The model was given the rows "
            "below and told to answer from them only."
        )
        st.code(query["sql"], language="sql")
        st.dataframe(
            [dict(zip(query["columns"], row)) for row in query["rows"]],
            hide_index=True,
        )


def show_message(message):
    """Draw one chat message, with its retrieved passages if any."""
    with st.chat_message(message["role"]):
        if message.get("error"):
            st.error(message["content"])
            with st.expander("Technical details"):
                st.code(message["detail"], language=None)
            return
        st.markdown(message["content"])
        # Only the bot's answers have a source; a visitor's own
        # message and the reply to an unclear one do not.
        if message.get("tool") and message["status"] != "unclear":
            st.caption(SOURCE_LABELS[message["tool"]])
        if message.get("commits"):
            show_commits(message["commits"])
            return
        if message.get("query"):
            show_query(message["query"])
            return
        passages = message.get("passages")
        # An unclear message has no answer to trace back to passages.
        if not passages or message["status"] == "unclear":
            return
        if message["status"] == "answered":
            label = f"Retrieved passages ({len(passages)})"
        else:
            label = ("Closest passages, none with the answer "
                     f"({len(passages)})")
        with st.expander(label):
            if message.get("rewritten"):
                st.caption(
                    "Your message was a follow-up, so it was rewritten "
                    f"for the search as: \"{message['rewritten']}\""
                )
            st.caption(
                "The search found these passages in the documents. "
                "The model was given them and told to answer from "
                "them only. Distance shows how close each passage is "
                "to the question: 0 is identical in meaning, and "
                "values near 2 are unrelated."
            )
            for number, passage in enumerate(passages, start=1):
                st.markdown(
                    f"**{number}. {passage['source']}** · "
                    f"distance {passage['distance']:.2f}"
                )
                st.text(passage["text"])


def pick_example():
    """Offer example questions and return the one clicked, if any."""
    st.markdown("**New here? Try one of these questions:**")
    for example in EXAMPLE_QUESTIONS:
        if st.button(example):
            return example
    return None


def show_sidebar(remaining):
    """Explain how the demo works and show what is left to ask."""
    with st.sidebar:
        st.header("How this works")
        st.markdown(
            "1. **Retrieve:** your question is compared with the "
            "stored document chunks, and the closest ones are "
            "fetched.\n"
            "2. **Augment:** those chunks are placed in the prompt.\n"
            "3. **Generate:** the model answers from them only."
        )
        st.header("Key terms")
        st.markdown(
            "- **Chunk:** a small piece of a document, a paragraph "
            "or two, like an index card holding one idea.\n"
            "- **Embedding:** a list of numbers that represents the "
            "meaning of a chunk or a question.\n"
            "- **Distance:** how far apart a chunk and the question "
            "are in meaning. Lower is closer: 0 is identical, and "
            "near 2 is unrelated."
        )
        st.header("How the bot decides")
        st.caption(
            "Each message goes through this LangGraph flow. Dashed "
            "arrows are choices: which tool fits, and whether a "
            "failed SQL query is retried."
        )
        st.graphviz_chart(flow_diagram())
        st.header("Documents")
        for path in sorted(DATA_FOLDER.iterdir()):
            if path.suffix.lower() in DOCUMENT_SUFFIXES:
                st.markdown(f"- {path.name}")
        st.metric("Questions left this session", remaining)


st.set_page_config(page_title="RAG demo")
st.title("Ask the documents")
st.caption(
    "A retrieval-augmented generation (RAG) demo: answers come from "
    "the project's documents and two live sources, GitHub and NYC "
    "Open Data, not from the model's memory."
)
require_password()

max_questions = int(get_setting("MAX_QUESTIONS", DEFAULT_MAX_QUESTIONS))
messages = st.session_state.setdefault("messages", [])
st.session_state.setdefault("asked", 0)
limit_reached = st.session_state.asked >= max_questions

question = st.chat_input(
    "Ask a question about the documents", disabled=limit_reached
)
if not messages and not question:
    question = pick_example()
if question and question.strip() and not limit_reached:
    st.session_state.asked += 1
    # Failed answers are left out: they say nothing about the topic.
    history = [message for message in messages
               if not message.get("error")]
    messages.append({"role": "user", "content": question})
    with st.spinner("Searching the documents..."):
        messages.append(answer_question(question, history))
    # Redraw from the top so the chat box and the counter reflect the
    # question just asked.
    st.rerun()

show_sidebar(max(max_questions - st.session_state.asked, 0))
for message in messages:
    show_message(message)
if st.session_state.asked >= max_questions:
    st.info("You have reached the question limit for this session.")
