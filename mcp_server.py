"""MCP server that exposes the RAG demo as tools for AI assistants.

Run with `python mcp_server.py`.  The server talks to its client over
standard input and output, so nothing in this project may print to
standard output while it runs: that would corrupt the protocol.
"""

import functools
import logging
import time
from pathlib import Path
from typing import TypedDict

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from rag import DATA_FOLDER, answer
from store import add_documents, get_collection, search

server = MCPServer(
    "rag-demo",
    instructions=(
        "Search and answer questions about the demo project's "
        "documents on RAG, MCP and the project itself."
    ),
)

LOG_FILE = Path(__file__).parent / "logs" / "mcp_server.log"
logger = logging.getLogger("rag_demo.mcp_server")

_collection_cache = None


def configure_logging():
    """Send this server's log records to `LOG_FILE`.

    A file is used because standard output is reserved for the
    protocol and clients often hide the error stream.
    """
    LOG_FILE.parent.mkdir(exist_ok=True)
    handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def logged(tool):
    """Wrap a tool so every call, result and failure is logged.

    Failures are re-raised after logging, so the assistant is still
    told that the call failed.
    """
    @functools.wraps(tool)
    def wrapper(*args, **kwargs):
        name = tool.__name__
        logger.info("%s called with %s", name, kwargs or args)
        started = time.perf_counter()
        try:
            result = tool(*args, **kwargs)
        except ToolError as error:
            # Expected: the assistant sent input the tool rejects.
            logger.warning("%s rejected its input: %s", name, error)
            raise
        except Exception:
            # Unexpected: record the full traceback for debugging.
            logger.exception("%s failed", name)
            raise
        elapsed = time.perf_counter() - started
        logger.info("%s succeeded in %.2fs", name, elapsed)
        return result
    return wrapper


class Passage(TypedDict):
    """The fields of each passage returned by search_documents."""

    text: str
    source: str
    distance: float


class Answer(TypedDict):
    """The fields returned by ask_documents.

    Declaring them lets the server tell assistants the exact shape of
    the result.
    """

    answer: str
    sources: list[str]


def _collection():
    """Return the collection, loading the documents on first use."""
    global _collection_cache
    if _collection_cache is None:
        _collection_cache = get_collection()
        add_documents(_collection_cache, DATA_FOLDER)
    return _collection_cache


@server.tool()
@logged
def search_documents(query: str, k: int = 3) -> list[Passage]:
    """Return the document passages most relevant to a query.

    Each passage has its `text`, the `source` file it came from and
    its `distance` from the query (0 is identical in meaning, values
    near 2 are unrelated).  `k` is the maximum number of passages to
    return (1 to 10).
    """
    # ToolError messages are passed on to the assistant, so it can
    # correct its input; other exceptions are reported only as a crash.
    if not query.strip():
        raise ToolError("query must not be empty")
    if not 1 <= k <= 10:
        raise ToolError("k must be between 1 and 10")
    return search(_collection(), query, k=k)


@server.tool()
@logged
def ask_documents(question: str) -> Answer:
    """Answer a question using only the project's documents.

    Return the `answer` and the `sources` (file names) it drew on.
    When the documents do not contain the answer, the answer says so
    and `sources` is empty.
    """
    if not question.strip():
        raise ToolError("question must not be empty")
    result = answer(question, _collection())
    return {"answer": result["answer"], "sources": result["sources"]}


if __name__ == "__main__":
    configure_logging()
    logger.info("server starting")
    server.run()
