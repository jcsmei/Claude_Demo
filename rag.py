"""Answer questions from stored documents (retrieval-augmented generation)."""

from pathlib import Path

from llm import ask
from store import add_documents, get_collection, search

DATA_FOLDER = Path(__file__).parent / "data"


def build_prompt(question, chunks):
    """Return a prompt that asks the model to answer from `chunks` only."""
    context = "\n\n".join(
        f"[{chunk['source']}]\n{chunk['text']}" for chunk in chunks
    )
    return (
        "Answer the question using only the context below. If the "
        "context does not contain the answer, say you do not know.\n\n"
        f"Context:\n{context or '(no documents found)'}\n\n"
        f"Question: {question}"
    )


def answer(question, collection, client=None, k=3):
    """Retrieve relevant chunks, then ask the model to answer from them.

    Return a dict with the model's `answer` and the list of `sources`
    (file names) the retrieved chunks came from.
    """
    chunks = search(collection, question, k=k)
    reply = ask(build_prompt(question, chunks), client=client)
    sources = sorted({chunk["source"] for chunk in chunks})
    return {"answer": reply, "sources": sources}


if __name__ == "__main__":
    collection = get_collection()
    count = add_documents(collection, DATA_FOLDER)
    print(f"Stored {count} chunks from '{DATA_FOLDER.name}'.\n")

    question = "What is this project's codename and when is the review?"
    result = answer(question, collection)
    print(f"Q: {question}")
    print(f"A: {result['answer']}")
    print(f"Sources: {', '.join(result['sources'])}")
