# Claude_Demo: a small RAG + MCP learning demo

This project answers questions from a folder of documents and exposes
that ability to AI assistants as tools.

- **RAG (retrieval-augmented generation):** documents are split into
  chunks and stored in a Chroma vector database. A question retrieves
  the most relevant chunks, and a Groq-hosted model answers from them.
- **MCP (Model Context Protocol):** a server offers the retrieval and
  the full question-answering as two tools that any MCP client, such
  as Claude Code, can call.

## How it fits together

| File | Role |
|---|---|
| `llm.py` | Sends a question to a Groq model and returns the reply. |
| `store.py` | Chunks documents, stores them in Chroma, searches them. |
| `rag.py` | Retrieves chunks, then asks the model to answer from them. |
| `mcp_server.py` | Exposes `search_documents` and `ask_documents` as MCP tools, with logging. |
| `data/` | The sample documents that get indexed. |
| `tests/` | Automated tests. They use fakes, so they need no network or API key. |
| `.mcp.json` | Tells Claude Code how to start the MCP server. |

## Setup (Windows, PowerShell)

Requires Python 3.12 and a free API key from
[console.groq.com](https://console.groq.com).

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Then create a file named `.env` in the project folder containing your
key:

```
GROQ_API_KEY=your_key_here
```

`.env` is listed in `.gitignore`, so the key is never committed.

## Run

```powershell
python llm.py     # one question straight to the model
python rag.py     # index data/ and answer a question from it
```

The first `python rag.py` downloads Chroma's embedding model (about
80 MB, once). The database is written to `chroma_db/` and can be
deleted at any time; it is rebuilt from `data/`.

To use a different Groq model, add `GROQ_MODEL=<model id>` to `.env`.

## Test

```powershell
python -m pytest -q
```

Use this exact form: `python -m pytest` lets the tests find the
project's modules, where plain `pytest` does not.

## Use the MCP server from Claude Code

Open this folder in Claude Code and approve the `rag-demo` server when
asked. Two tools become available:

| Tool | What it does | Uses Groq |
|---|---|---|
| `search_documents(query, k=3)` | Returns the `k` most relevant passages and their source files. | No |
| `ask_documents(question)` | Returns an answer drawn from the documents, plus its sources. | Yes |

Every call, rejected input and failure is recorded in
`logs/mcp_server.log`.

## Add your own documents

Put `.md` or `.txt` files in `data/` and run `python rag.py`, or
restart the MCP server. Existing chunks are updated, not duplicated.
