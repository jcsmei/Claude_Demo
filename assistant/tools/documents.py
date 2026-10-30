"""The documents tool: answers from the knowledge base (RAG).

It brings its own steps: it answers from the retrieved passages, and
hands the question to a web search only when the documents do not
cover it and the web search rules allow it.
"""

from langgraph.runtime import Runtime

from assistant import rag
from assistant.tools.web import web_search_allowed, web_search_node


def documents_node(state, runtime: Runtime):
    """Answer from the project's documents (RAG)."""
    result = rag.answer(
        state["question"], runtime.context["collection"],
        client=runtime.context["client"], history=state["history"],
        search_query=state["search_query"],
    )
    result["tool"] = DOCUMENTS.name
    return {"result": result}


def after_documents(state):
    """Decide whether a documents answer needs a web search."""
    asked = f"{state['question']} {state['search_query']}"
    if (state["result"]["status"] == "not_covered"
            and web_search_allowed(asked)):
        return "search the web"
    return "done"


class DocumentsTool:
    """Answer from the project's documents, with a web fallback."""

    name = "documents"
    description = (
        "everything else: how the project works, RAG, MCP, problems "
        "that were fixed, the creator Jack Mei, where the bot's data "
        "comes from and how its tools work, greetings and unclear "
        "messages"
    )
    args_schema = None  # the router passes no arguments
    source_label = "Source: the project's documents"

    def add_to_graph(self, graph, end):
        """Add this tool's steps to `graph`; return its first node."""
        graph.add_node("documents", documents_node)
        graph.add_node("web_search", web_search_node)
        # The web is searched only when the documents do not cover it.
        graph.add_conditional_edges(
            "documents", after_documents,
            {"search the web": "web_search", "done": end},
        )
        graph.add_edge("web_search", end)
        return "documents"


DOCUMENTS = DocumentsTool()
