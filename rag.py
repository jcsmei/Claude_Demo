"""Answer questions from stored documents (retrieval-augmented generation)."""

from pathlib import Path

from llm import ask
from store import add_documents, get_collection, search

DATA_FOLDER = Path(__file__).parent / "data"

# The model is told to reply with this marker when the context lacks
# the answer, so the code can detect a refusal reliably.
NOT_COVERED_MARKER = "NOT_IN_DOCUMENTS"
NOT_COVERED_MESSAGE = (
    "The documents do not contain an answer to this question."
)


def build_prompt(question, chunks):
    """Return a prompt that asks the model to answer from `chunks` only."""
    context = "\n\n".join(
        f"[{chunk['source']}]\n{chunk['text']}" for chunk in chunks
    )
    return (
        "Answer the question using only the context below. Answer in "
        "complete sentences, as if explaining to a curious reader, "
        "and do not mention the context itself. If the context does "
        "not contain the answer, reply with only the word "
        f"{NOT_COVERED_MARKER}.\n\n"
        f"Context:\n{context or '(no documents found)'}\n\n"
        f"Question: {question}"
    )


def answer(question, collection, client=None, k=5):
    """Retrieve relevant chunks, then ask the model to answer from them.

    Return a dict with:
    - `answer`: the model's answer, or `NOT_COVERED_MESSAGE`;
    - `answered`: False when the passages did not contain the answer;
    - `sources`: the file names the answer drew on (empty when not
      answered);
    - `passages`: the retrieved chunks, each with its `text`,
      `source` and `distance`, kept even when not answered so the
      caller can show what the search found.
    """
    chunks = search(collection, question, k=k)
    reply = ask(build_prompt(question, chunks), client=client)
    answered = NOT_COVERED_MARKER not in reply
    if answered:
        sources = sorted({chunk["source"] for chunk in chunks})
    else:
        reply, sources = NOT_COVERED_MESSAGE, []
    return {"answer": reply, "answered": answered, "sources": sources,
            "passages": chunks}


if __name__ == "__main__":
    collection = get_collection()
    count = add_documents(collection, DATA_FOLDER)
    print(f"Stored {count} chunks from '{DATA_FOLDER.name}'.\n")

    question = "What is this project's codename and when is the review?"
    result = answer(question, collection)
    print(f"Q: {question}")
    print(f"A: {result['answer']}")
    print(f"Sources: {', '.join(result['sources'])}")
