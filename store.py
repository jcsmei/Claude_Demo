"""Store text chunks in Chroma and retrieve them by meaning."""

from pathlib import Path

import chromadb

# Anchored to this file so it works whatever folder the program is
# started from.
DB_PATH = str(Path(__file__).parent / "chroma_db")
COLLECTION_NAME = "demo_docs"
DOCUMENT_SUFFIXES = {".md", ".txt"}


def chunk_text(text, max_chars=500):
    """Split text into chunks made of whole paragraphs.

    Paragraphs (separated by blank lines) are packed together until
    adding another would exceed `max_chars`.  A single paragraph longer
    than `max_chars` is kept whole rather than cut mid-sentence.
    """
    chunks = []
    current = ""
    for paragraph in text.split("\n\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if current and len(current) + len(paragraph) + 2 > max_chars:
            chunks.append(current)
            current = paragraph
        elif current:
            current = f"{current}\n\n{paragraph}"
        else:
            current = paragraph
    if current:
        chunks.append(current)
    return chunks


def get_collection(client=None, name=COLLECTION_NAME,
                   embedding_function=None):
    """Return the Chroma collection, creating it if needed.

    By default the data is saved on disk in `DB_PATH` and Chroma's
    built-in embedding model is used.  Tests pass an in-memory `client`
    and a fake `embedding_function` instead.
    """
    client = client or chromadb.PersistentClient(path=DB_PATH)
    options = {}
    if embedding_function is not None:
        options["embedding_function"] = embedding_function
    return client.get_or_create_collection(name, **options)


def add_documents(collection, folder):
    """Chunk every document in `folder` and store the chunks.

    Return the number of chunks stored.  Each chunk's ID is built from
    its file name and position, so loading the same folder again
    updates the existing chunks instead of duplicating them.
    """
    ids, documents, metadatas = [], [], []
    for path in sorted(Path(folder).iterdir()):
        if path.suffix.lower() not in DOCUMENT_SUFFIXES:
            continue
        chunks = chunk_text(path.read_text(encoding="utf-8"))
        for position, chunk in enumerate(chunks):
            ids.append(f"{path.name}-{position}")
            documents.append(chunk)
            metadatas.append({"source": path.name})
    if ids:
        collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
    return len(ids)


def search(collection, query, k=3):
    """Return up to `k` chunks closest in meaning to `query`.

    Each result is a dict with the chunk's `text`, its `source` file
    name and its `distance` from the query, ordered from most to least
    relevant.  A distance of 0 means identical in meaning; values
    near 2 mean unrelated.
    """
    k = min(k, collection.count())
    if k == 0:
        return []
    results = collection.query(query_texts=[query], n_results=k)
    return [
        {"text": text, "source": metadata["source"], "distance": distance}
        for text, metadata, distance in zip(results["documents"][0],
                                            results["metadatas"][0],
                                            results["distances"][0])
    ]
