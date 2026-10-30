"""The interface every tool follows, and what a tool returns.

The fields match those of LangChain's `BaseTool` and of MCP's tool
definitions: a name, a description the model reads to choose the tool,
and a schema for its arguments.  A tool returns its evidence as plain
data and never draws it; the page decides how each kind is shown.

Most tools answer in one step, through `run()`.  A tool that needs
several steps brings them as graph nodes instead, through
`add_to_graph()`, so they stay visible in the drawn graph.
"""

from dataclasses import dataclass
from typing import Any, Protocol, TypedDict, runtime_checkable


@dataclass(frozen=True)
class Evidence:
    """What an answer was drawn from, as plain data.

    `kind` tells the page how to draw `items`: "commits", or "query"
    for SQL that ran, one item per query.  Passages and web results
    follow as their tools move onto this interface.
    """

    kind: str
    items: list


@dataclass(frozen=True)
class ToolContext:
    """What a tool may read while it runs, besides its arguments."""

    question: str
    search_query: str
    history: list
    client: Any = None


class ToolResult(TypedDict, total=False):
    """The result every tool returns."""

    answer: str
    status: str
    answered: bool
    tool: str
    sources: list
    passages: list
    evidence: Evidence
    search_query: str


@runtime_checkable
class ToolInfo(Protocol):
    """What every tool declares about itself."""

    name: str              # what the model calls it
    description: str       # the line the model reads to choose it
    args_schema: type | None  # its arguments; None if it takes none
    source_label: str      # shown under each answer


@runtime_checkable
class Tool(ToolInfo, Protocol):
    """A tool that answers in one step."""

    def run(self, args: dict, context: ToolContext) -> ToolResult:
        """Fetch what the question needs and answer from it."""


@runtime_checkable
class GraphTool(ToolInfo, Protocol):
    """A tool that brings its own steps, as graph nodes.

    Its nodes read and write the graph's state, and the last one puts
    the tool's result in `result`.
    """

    def add_to_graph(self, graph, end) -> str:
        """Add the tool's nodes and edges, ending at `end`.

        Return the name of the first node, which the router sends the
        message to.
        """
