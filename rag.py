"""Answer questions from stored documents (retrieval-augmented generation)."""

from pathlib import Path

from llm import ask
from store import add_documents, get_collection, search

DATA_FOLDER = Path(__file__).parent / "data"

# The model is told to reply with one of these markers instead of an
# answer, so the code can detect each case reliably.
NOT_COVERED_MARKER = "NOT_IN_DOCUMENTS"
UNCLEAR_MARKER = "MESSAGE_UNCLEAR"
NOT_COVERED_MESSAGE = (
    "The documents do not contain an answer to this question."
)
UNCLEAR_MESSAGE = (
    "I can answer questions about how RAG works, the MCP server and "
    "its tools, how this project was built, the problems found along "
    "the way, and Jack Mei's background. What would you like to know?"
)

# How much of the conversation the model is shown.
HISTORY_MESSAGES = 4
HISTORY_CHARS = 400
# A rewritten question longer than this is treated as a failed rewrite.
MAX_QUERY_CHARS = 300


def format_history(history):
    """Return the most recent messages as "User:" / "Assistant:" lines.

    Each message is shortened to `HISTORY_CHARS` so that the
    conversation cannot crowd the passages out of the prompt.
    """
    lines = []
    for message in (history or [])[-HISTORY_MESSAGES:]:
        speaker = "User" if message["role"] == "user" else "Assistant"
        content = " ".join(message["content"].split())[:HISTORY_CHARS]
        lines.append(f"{speaker}: {content}")
    return "\n".join(lines)


def build_prompt(question, chunks, history=None):
    """Return a prompt that asks the model to answer from `chunks` only.

    `history` is the earlier conversation, a list of messages with a
    `role` ("user" or "assistant") and `content`.  It lets the model
    work out what a follow-up message refers to.
    """
    context = "\n\n".join(
        f"[{chunk['source']}]\n{chunk['text']}" for chunk in chunks
    )
    return (
        "You answer questions about a demo project. Use only the "
        "facts in the context below. Explain them conversationally in "
        "plain language, as if talking to a curious reader, and do "
        "not mention the context itself. Do not add facts, and do not "
        "spell out abbreviations unless the context does. Use the "
        "conversation so far to work out what the question refers to. "
        "If the user did not understand an earlier answer, explain "
        "the same facts again more simply. If the question is only a "
        "greeting or thanks, "
        "or is too unclear to answer even with the conversation, "
        f"reply with only the word {UNCLEAR_MARKER}. If the context "
        "does not contain the facts needed to answer, reply with only "
        f"the word {NOT_COVERED_MARKER}.\n\n"
        f"Context:\n{context or '(no documents found)'}\n\n"
        f"Conversation so far:\n{format_history(history) or '(none)'}\n\n"
        f"Question: {question}"
    )


def standalone_question(question, history=None, client=None):
    """Return `question` rewritten so it can be searched for alone.

    A follow-up such as "What tools does it have?" means nothing to
    the search without the conversation, so the model is asked to
    rewrite it, for example as "What tools does the MCP server have?".
    With no earlier conversation the question is returned unchanged
    and the model is not called.
    """
    if not history:
        return question
    prompt = (
        "Rewrite the latest message as one question that can be "
        "understood without the conversation. Replace words such as "
        "'it', 'he' or 'that' with what they refer to. If the user "
        "did not understand, ask for a simpler explanation of the "
        "topic being discussed. If the latest message is already "
        "complete, or is only a greeting or thanks, return it "
        "unchanged. Reply with the rewritten message only.\n\n"
        f"Conversation:\n{format_history(history)}\n\n"
        f"Latest message: {question}"
    )
    rewritten = " ".join(ask(prompt, client=client).split())
    if not rewritten or len(rewritten) > MAX_QUERY_CHARS:
        return question
    return rewritten


def answer(question, collection, client=None, k=5, history=None,
           search_query=None):
    """Retrieve relevant chunks, then ask the model to answer from them.

    With a `history`, the search uses a standalone rewrite of the
    question, while the model still sees the original question and the
    conversation.  A caller that has already made that rewrite passes
    it as `search_query`, which saves a model call.

    Return a dict with:
    - `search_query`: the text that was searched for;
    - `answer`: the model's answer, `NOT_COVERED_MESSAGE` or
      `UNCLEAR_MESSAGE`;
    - `status`: "answered", "not_covered" when the passages did not
      contain the answer, or "unclear" when the message was a greeting
      or could not be understood;
    - `answered`: True when `status` is "answered";
    - `sources`: the file names the answer drew on (empty unless
      answered);
    - `passages`: the retrieved chunks, each with its `text`,
      `source` and `distance`, kept in every case so the caller can
      show what the search found.
    """
    if search_query is None:
        search_query = standalone_question(question, history,
                                           client=client)
    chunks = search(collection, search_query, k=k)
    prompt = build_prompt(question, chunks, history=history)
    reply = ask(prompt, client=client)
    sources = []
    if UNCLEAR_MARKER in reply:
        status, reply = "unclear", UNCLEAR_MESSAGE
    elif NOT_COVERED_MARKER in reply:
        status, reply = "not_covered", NOT_COVERED_MESSAGE
    else:
        status = "answered"
        sources = sorted({chunk["source"] for chunk in chunks})
    return {"answer": reply, "status": status,
            "answered": status == "answered", "sources": sources,
            "passages": chunks, "search_query": search_query}


if __name__ == "__main__":
    collection = get_collection()
    count = add_documents(collection, DATA_FOLDER)
    print(f"Stored {count} chunks from '{DATA_FOLDER.name}'.\n")

    question = "What is this project's codename and when is the review?"
    result = answer(question, collection)
    print(f"Q: {question}")
    print(f"A: {result['answer']}")
    print(f"Sources: {', '.join(result['sources'])}")
