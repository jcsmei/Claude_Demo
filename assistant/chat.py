"""Route each message to the tool that fits it, then answer with it.

The orchestration is a LangGraph graph: a router node picks a tool,
and the graph routes to the node for that tool.  A tool that follows
the interface in `tools/base.py` is added by listing it in `TOOLS`.
"""

import re
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime

from assistant import guard
from assistant import rag
from assistant.llm import ask
from assistant.tools.base import GraphTool, ToolContext
from assistant.tools.documents import DOCUMENTS
from assistant.tools.github import GITHUB
from assistant.tools.nyc_data import NYC_DATA

# Tools that follow the interface in tools/base.py.  The others move
# onto it one at a time.
TOOLS = (DOCUMENTS, GITHUB, NYC_DATA)

# The tools the model may choose from, and when to choose each.  The
# first one is the fallback when the model's choice cannot be read.
TOOL_GUIDE = {tool.name: tool.description for tool in TOOLS}
DEFAULT_TOOL = TOOLS[0].name

# Longer messages are refused: nobody needs this much room to ask a
# question, and long text is costly and a common carrier of attacks.
MAX_QUESTION_CHARS = 1000
TOO_LONG_MESSAGE = (
    f"Please keep your question under {MAX_QUESTION_CHARS:,} characters."
)
BLOCKED_MESSAGE = (
    "This message looks like an attempt to change the assistant's "
    "instructions, so it was not processed. Please ask a question "
    "about the project instead."
)

# A message that is only small talk gets a fixed reply from code, so
# no model is called for it.  The lists are deliberately short: any
# other wording goes to the model as before.
THANKS = frozenset({
    "thanks", "thank you", "thanks a lot", "thanks so much",
    "thanks very much", "thank you so much", "thank you very much",
    "many thanks", "much appreciated", "thx", "ty", "cheers",
})
GREETINGS = frozenset({
    "hi", "hello", "hey", "hi there", "hello there", "hey there",
    "good morning", "good afternoon", "good evening", "greetings",
})
GOODBYES = frozenset({
    "bye", "goodbye", "good bye", "bye bye", "see you", "see you later",
    "good night", "take care", "have a good day", "have a nice day",
})
# Words that may come before small talk, as in "ok thanks".
SMALL_TALK_FILLERS = ("ok", "okay", "alright", "great", "awesome",
                    "perfect", "cool", "nice", "got it")
SMALL_TALK_REPLIES = (
    (THANKS, "You're welcome! Ask me anything else about the project."),
    (GREETINGS, f"Hello! {rag.UNCLEAR_MESSAGE}"),
    (GOODBYES, "Goodbye, and thanks for trying the demo!"),
)

def small_talk_reply(text):
    """Return the fixed reply to a message that is only small talk.

    Return None for any other message.  The whole message must be a
    small talk: "thanks, and what is a chunk?" is still a question.
    Capitals, punctuation and emoji are ignored.
    """
    phrase = " ".join(re.sub(r"[^a-z ]", " ", text.lower()).split())
    candidates = {phrase}
    for filler in SMALL_TALK_FILLERS:
        if phrase.startswith(f"{filler} "):
            candidates.add(phrase[len(filler) + 1:])
    for phrases, reply in SMALL_TALK_REPLIES:
        if candidates & phrases:
            return reply
    return None


def route(question, history=None, client=None):
    """Return the tool for `question` and the question made standalone.

    One model call does both jobs: it picks a tool from `TOOL_GUIDE`
    and rewrites a follow-up so it can be understood without the
    conversation.  If the reply cannot be read, the result falls back
    to the documents tool and the question as it was asked.
    """
    guide = "\n".join(f"- {name}: {use}"
                      for name, use in TOOL_GUIDE.items())
    instructions = (
        "You route messages for a chat bot about a software demo "
        "project. Choose the tool for the latest message, and rewrite "
        "the message so that it can be understood without the "
        "conversation. Replace words such as 'it', 'he' or 'that' "
        "with what they refer to. If the user did not understand, ask "
        "for a simpler explanation of the topic being discussed. If "
        "the message is already complete, or is only a greeting or "
        "thanks, keep it unchanged.\n\n"
        f"Tools:\n{guide}\n\n"
        "Reply with exactly two lines:\n"
        "TOOL: <tool name>\n"
        "QUESTION: <the message, rewritten if needed>"
    )
    prompt = (
        f"Conversation:\n{rag.format_history(history) or '(none)'}\n\n"
        f"Latest message: {question}"
    )
    tool, standalone = DEFAULT_TOOL, question
    reply = ask(prompt, client=client, system=instructions)
    for line in reply.splitlines():
        label, _, value = line.partition(":")
        value = " ".join(value.split())
        if label.strip().upper() == "TOOL":
            if value.lower() in TOOL_GUIDE:
                tool = value.lower()
        elif label.strip().upper() == "QUESTION":
            # With no conversation there is nothing to resolve, so
            # the question is searched exactly as it was asked.
            if history and value and len(value) <= rag.MAX_QUERY_CHARS:
                standalone = value
    return tool, standalone


class ChatState(TypedDict, total=False):
    """What the graph's nodes read and write while answering."""

    question: str
    history: list
    tool: str
    search_query: str
    # Written by the NYC data tool's own steps.
    sql: str
    sql_error: str | None
    sql_attempts: int
    query: dict
    result: dict


class ChatContext(TypedDict):
    """What the nodes need but do not change."""

    collection: Any
    client: Any


def blocked(question, message):
    """Return the result for a message that is refused unanswered."""
    return {"answer": message, "status": "blocked", "answered": False,
            "tool": "guard", "sources": [], "passages": [],
            "search_query": question}


def small_talk(question, reply):
    """Return the result for small talk answered with a fixed reply."""
    return {"answer": reply, "status": "small_talk", "answered": False,
            "tool": "small_talk", "sources": [], "passages": [],
            "search_query": question}


def small_talk_node(state, runtime: Runtime[ChatContext]):
    """Reply to small talk such as "thanks" with its fixed reply.

    It runs first and calls no model.  It only matches short, fixed
    phrases, so a long or hostile message always goes on to the input
    guardrail.
    """
    reply = small_talk_reply(state["question"])
    if reply:
        return {"result": small_talk(state["question"], reply)}
    return {}


def input_guardrail_node(state, runtime: Runtime[ChatContext]):
    """Refuse a message that is too long or looks like an injection.

    The length check costs nothing; the injection check calls the
    classifier model.
    """
    question = state["question"]
    if len(question) > MAX_QUESTION_CHARS:
        return {"result": blocked(question, TOO_LONG_MESSAGE)}
    if guard.looks_like_injection(question,
                                  client=runtime.context["client"]):
        return {"result": blocked(question, BLOCKED_MESSAGE)}
    return {}


def router_node(state, runtime: Runtime[ChatContext]):
    """Pick the tool and make the question standalone."""
    tool, standalone = route(
        state["question"], state["history"],
        client=runtime.context["client"],
    )
    return {"tool": tool, "search_query": standalone}


def as_graph_node(tool):
    """Return a graph node that answers the message with `tool`."""
    def node(state, runtime: Runtime[ChatContext]):
        context = ToolContext(
            question=state["question"],
            search_query=state["search_query"],
            history=state["history"],
            client=runtime.context["client"],
        )
        return {"result": tool.run({}, context)}
    node.__name__ = f"{tool.name}_node"
    return node


def build_graph():
    """Return the compiled graph: small talk, input guardrail, router,
    then the tools' nodes."""
    graph = StateGraph(ChatState, context_schema=ChatContext)
    graph.add_node("small_talk", small_talk_node)
    graph.add_node("input_guardrail", input_guardrail_node)
    graph.add_node("router", router_node)
    # Each tool's first node, which the router sends the message to.
    entries = {}
    for tool in TOOLS:
        if isinstance(tool, GraphTool):
            entries[tool.name] = tool.add_to_graph(graph, END)
        else:
            graph.add_node(tool.name, as_graph_node(tool))
            graph.add_edge(tool.name, END)
            entries[tool.name] = tool.name
    graph.add_edge(START, "small_talk")
    # Small talk has its reply and goes no further.
    graph.add_conditional_edges(
        "small_talk",
        lambda state: "replied" if state.get("result") else "continue",
        {"replied": END, "continue": "input_guardrail"},
    )
    # A message that was refused goes no further.
    graph.add_conditional_edges(
        "input_guardrail",
        lambda state: "refuse" if state.get("result") else "continue",
        {"refuse": END, "continue": "router"},
    )
    graph.add_conditional_edges(
        "router", lambda state: state["tool"],
        entries,
    )
    return graph.compile()


GRAPH = build_graph()


def flow_diagram():
    """Return the graph in Graphviz DOT format, for display.

    It is generated from the compiled graph, so the picture cannot
    drift from the code.  Dashed arrows are choices made by the model.
    """
    drawing = GRAPH.get_graph()
    names = {"__start__": "message", "__end__": "answer"}
    lines = ["digraph {", "  rankdir=LR;", "  node [shape=box];"]
    for edge in drawing.edges:
        source = names.get(edge.source, edge.source)
        target = names.get(edge.target, edge.target)
        style = " [style=dashed]" if edge.conditional else ""
        lines.append(f'  "{source}" -> "{target}"{style};')
    lines.append("}")
    return "\n".join(lines)


def respond(question, collection, history=None, client=None):
    """Answer `question` with whichever tool fits it.

    Return the same dict as `rag.answer`, plus `tool`: the name of the
    tool that produced the answer.  A message that is only small talk
    has the status "small_talk".  A github answer also has
    `evidence`, the commits the answer was drawn from, an nyc_data
    answer has `evidence` with the SQL that ran and its result, and a web
    answer has `evidence` with the web results.  A tool that fails raises
    `tools.ToolFailure`, except the web search, whose failure is added
    to the documents' refusal.
    """
    final = GRAPH.invoke(
        {"question": question, "history": history or []},
        context={"collection": collection, "client": client},
    )
    return final["result"]
