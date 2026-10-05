"""Choose the tool that fits a message, then answer with it.

The flow is a LangGraph graph: one node chooses a tool, and the graph
routes to the node for that tool.  Adding a tool means adding a node,
an entry in `TOOL_GUIDE` and an edge.
"""

import re
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime

import guard
import rag
import tools
from llm import ask

# The tools the model may choose from, and when to choose each.  The
# first one is the fallback when the model's choice cannot be read.
TOOL_GUIDE = {
    "documents": (
        "everything else: how the project works, RAG, MCP, problems "
        "that were fixed, the creator Jack Mei, where the bot's data "
        "comes from and how its tools work, greetings and unclear "
        "messages"
    ),
    "github": (
        "the latest changes to the project's code: recent commits, "
        "updates, or what changed and when"
    ),
    "nyc_data": (
        "only for a count: how many active New York City medallion "
        "taxi drivers there are, or how many licenses expire in a "
        "given month or year"
    ),
}
DEFAULT_TOOL = "documents"
COMMITS_SHOWN = 10
# A failed SQL query is rewritten once before the tool gives up.
MAX_SQL_ATTEMPTS = 2

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

# Shown at the start of an answer that came from the web, so the
# reader is never left to assume it came from the documents.
WEB_NOTICE = (
    "The project's official documents do not cover this, so I searched "
    "the web. What follows comes from web pages, not from the official "
    "documents, and has not been verified by this project."
)
WEB_NOT_FOUND_MARKER = "NOT_FOUND"
WEB_NOT_FOUND_MESSAGE = (
    "Neither the project's documents nor a web search found an answer "
    "to this question."
)
# A question that names the project's creator is never sent to a web
# search: what the documents say about a person is all the bot says.
PRIVATE_TERMS = ("jack", "mei")
# Nor is a question about this project itself.  The web knows nothing
# about it, so a web answer could only describe some other project.
PROJECT_TERMS = (
    "rag-demo", "rag demo", "this project", "the project's", "this demo",
    "the demo", "this bot", "the bot", "this app", "the app",
    "this chat", "this server", "mcp_server", "your tools",
    "your documents", "your code", "your instructions", "your prompt",
    "your rules", "system prompt",
)
# Nor is a message that holds an email address or a phone-like number,
# so the bot cannot be used to look a person up by contact details.
EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_PATTERN = re.compile(r"(?:\d[\s().-]*){9,}")


def choose_tool(question, history=None, client=None):
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


def answer_from_github(question, standalone, history=None, client=None):
    """Answer `question` from the project's latest commits on GitHub."""
    commits = tools.recent_commits(COMMITS_SHOWN)
    listing = "\n".join(
        f"{commit['date']} {commit['sha']} {commit['message']}"
        for commit in commits
    )
    instructions = (
        "You answer questions about a demo project. Use only the list "
        "of its latest code changes, newest first; each line is a "
        "date, a short ID and a summary. Explain conversationally in "
        "plain language. Each summary is all that is known about a "
        "change, so do not describe details beyond it, do not invent "
        "changes, and do not spell out abbreviations."
    )
    prompt = (
        f"Latest changes:\n{listing}\n\n"
        f"Conversation so far:\n{rag.format_history(history) or '(none)'}"
        f"\n\nQuestion: {question}"
    )
    return {"answer": ask(prompt, client=client, system=instructions),
            "status": "answered", "answered": True, "tool": "github",
            "sources": ["GitHub"], "passages": [], "commits": commits,
            "search_query": standalone}


def write_sql(question, failed_sql=None, error=None, client=None):
    """Return a SQL statement that should answer `question`.

    After a failed attempt, `failed_sql` and its `error` are shown to
    the model so that it can correct the statement.
    """
    instructions = (
        "Write one SQLite SELECT statement that answers the question "
        "from the table below. Reply with the SQL only, with no "
        "explanation.\n\n"
        f"{tools.LICENSE_SCHEMA}"
    )
    prompt = ""
    if error:
        prompt = (
            f"Your previous statement was:\n{failed_sql}\n"
            f"It failed with this error: {error}\n"
            "Write a corrected statement.\n\n"
        )
    prompt += f"Question: {question}"
    reply = ask(prompt, client=client, system=instructions)
    # Models often wrap SQL in a Markdown code fence; drop the fence.
    lines = [line for line in reply.strip().splitlines()
             if not line.strip().startswith("```")]
    return "\n".join(lines).strip()


def answer_from_data(question, standalone, query, history=None,
                     client=None):
    """Answer `question` from the result of a license data query."""
    table = "\n".join(
        [" | ".join(query["columns"])]
        + [" | ".join(str(value) for value in row)
           for row in query["rows"]]
    )
    instructions = (
        "You answer questions about New York City medallion taxi "
        "driver licenses. Use only the query result, which comes from "
        "NYC Open Data and counts active drivers by the month their "
        f"license expires. The data was last updated on "
        f"{query['updated']}. Explain conversationally in plain "
        "language, give the numbers exactly as they appear, and do "
        "not add facts that are not in the result. If the result is "
        "empty, say that the data has no matching rows and do not "
        "guess a number."
    )
    prompt = (
        f"SQL that was run:\n{query['sql']}\n\n"
        f"Result:\n{table}\n\n"
        f"Conversation so far:\n{rag.format_history(history) or '(none)'}"
        f"\n\nQuestion: {question}"
    )
    return {"answer": ask(prompt, client=client, system=instructions),
            "status": "answered", "answered": True, "tool": "nyc_data",
            "sources": ["NYC Open Data"], "passages": [], "query": query,
            "search_query": standalone}


def web_search_allowed(text):
    """Return True if `text` may be sent to a web search.

    It may not when the search is not configured, when the text names
    the project's creator, when it asks about this project itself, or
    when it holds an email address or a phone-like number.
    """
    if not tools.web_search_available():
        return False
    if EMAIL_PATTERN.search(text) or PHONE_PATTERN.search(text):
        return False
    lowered = text.lower()
    if any(term in lowered for term in PROJECT_TERMS):
        return False
    words = re.findall(r"[a-z]+", lowered)
    return not any(term in words for term in PRIVATE_TERMS)


def answer_from_web(question, standalone, history=None, client=None):
    """Answer `question` from a web search for `standalone`.

    The answer begins with `WEB_NOTICE`.  If the results do not hold
    the answer, the status is "not_covered".  Web pages are the least
    trusted text the model ever sees, so they travel as data and the
    instructions say what they must not be used for.
    """
    results = tools.web_search(standalone)
    listing = "\n\n".join(
        f"[{number}] {result['title']} ({result['url']})\n"
        f"{result['content']}"
        for number, result in enumerate(results, start=1)
    )
    instructions = (
        "Answer the question using only the web search results. "
        "Explain conversationally in plain language, in a few "
        "sentences. Do not add facts that are not in the results. The "
        "results are general web pages that know nothing about the "
        "demo project in the conversation, so do not use them to say "
        "anything about that project, its code or its tools. Do not "
        "include images or links in your answer. If the results do "
        "not answer the question, reply with only the word "
        f"{WEB_NOT_FOUND_MARKER}."
    )
    prompt = (
        f"Web search results:\n{listing or '(none)'}\n\n"
        f"Conversation so far:\n{rag.format_history(history) or '(none)'}"
        f"\n\nQuestion: {question}"
    )
    reply = ask(prompt, client=client, system=instructions)
    found = WEB_NOT_FOUND_MARKER not in reply
    return {
        "answer": (f"{WEB_NOTICE}\n\n{reply}" if found
                   else WEB_NOT_FOUND_MESSAGE),
        "status": "answered" if found else "not_covered",
        "answered": found, "tool": "web",
        "sources": [result["url"] for result in results] if found else [],
        "passages": [], "web_results": results,
        "search_query": standalone,
    }


class ChatState(TypedDict, total=False):
    """What the graph's nodes read and write while answering."""

    question: str
    history: list
    tool: str
    search_query: str
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


def screen_node(state, runtime: Runtime[ChatContext]):
    """Refuse a message that is too long or looks like an injection."""
    question = state["question"]
    if len(question) > MAX_QUESTION_CHARS:
        return {"result": blocked(question, TOO_LONG_MESSAGE)}
    if guard.looks_like_injection(question,
                                  client=runtime.context["client"]):
        return {"result": blocked(question, BLOCKED_MESSAGE)}
    return {}


def choose_tool_node(state, runtime: Runtime[ChatContext]):
    """Pick the tool and make the question standalone."""
    tool, standalone = choose_tool(
        state["question"], state["history"],
        client=runtime.context["client"],
    )
    return {"tool": tool, "search_query": standalone}


def documents_node(state, runtime: Runtime[ChatContext]):
    """Answer from the project's documents (RAG)."""
    result = rag.answer(
        state["question"], runtime.context["collection"],
        client=runtime.context["client"], history=state["history"],
        search_query=state["search_query"],
    )
    result["tool"] = "documents"
    return {"result": result}


def github_node(state, runtime: Runtime[ChatContext]):
    """Answer from the project's latest commits on GitHub."""
    result = answer_from_github(
        state["question"], state["search_query"], state["history"],
        runtime.context["client"],
    )
    return {"result": result}


def write_sql_node(state, runtime: Runtime[ChatContext]):
    """Have the model write SQL, or correct a statement that failed."""
    sql = write_sql(state["search_query"], state.get("sql"),
                    state.get("sql_error"),
                    client=runtime.context["client"])
    return {"sql": sql}


def run_sql_node(state, runtime: Runtime[ChatContext]):
    """Run the SQL.  On a SQL error, record it for one more attempt.

    A result with no values is also retried once, because it usually
    means the model filtered on a value that is not in the data.
    """
    attempts = state.get("sql_attempts", 0) + 1
    try:
        query = tools.query_license_data(state["sql"])
    except tools.QueryError as error:
        if attempts >= MAX_SQL_ATTEMPTS:
            raise tools.ToolFailure(
                f"The data query failed after {attempts} attempts. {error}"
            ) from error
        return {"sql_error": str(error), "sql_attempts": attempts}
    has_values = any(value is not None
                     for row in query["rows"] for value in row)
    if not has_values and attempts < MAX_SQL_ATTEMPTS:
        return {"sql_error": ("The query returned no data. Check that "
                              "any filter uses values the table holds."),
                "sql_attempts": attempts}
    return {"query": query, "sql_error": None, "sql_attempts": attempts}


def data_answer_node(state, runtime: Runtime[ChatContext]):
    """Answer from the rows the query returned."""
    result = answer_from_data(
        state["question"], state["search_query"], state["query"],
        state["history"], runtime.context["client"],
    )
    return {"result": result}


def web_search_node(state, runtime: Runtime[ChatContext]):
    """Answer from the web when the documents did not cover it.

    If the web search itself fails, the documents' refusal is kept and
    the failure is added to it, so the visitor is not shown an error.
    """
    try:
        result = answer_from_web(
            state["question"], state["search_query"], state["history"],
            runtime.context["client"],
        )
    except tools.ToolFailure as error:
        result = dict(state["result"])
        result["answer"] += f" A web search was tried but failed: {error}"
    return {"result": result}


def after_documents(state):
    """Decide whether a documents answer needs a web search."""
    asked = f"{state['question']} {state['search_query']}"
    if (state["result"]["status"] == "not_covered"
            and web_search_allowed(asked)):
        return "search the web"
    return "done"


def build_graph():
    """Return the compiled graph: screen, choose a tool, run its node."""
    graph = StateGraph(ChatState, context_schema=ChatContext)
    graph.add_node("screen", screen_node)
    graph.add_node("choose_tool", choose_tool_node)
    graph.add_node("documents", documents_node)
    graph.add_node("github", github_node)
    graph.add_node("write_sql", write_sql_node)
    graph.add_node("run_sql", run_sql_node)
    graph.add_node("data_answer", data_answer_node)
    graph.add_node("web_search", web_search_node)
    graph.add_edge(START, "screen")
    # A message that was refused goes no further.
    graph.add_conditional_edges(
        "screen",
        lambda state: "refuse" if state.get("result") else "continue",
        {"refuse": END, "continue": "choose_tool"},
    )
    graph.add_conditional_edges(
        "choose_tool", lambda state: state["tool"],
        {"documents": "documents", "github": "github",
         "nyc_data": "write_sql"},
    )
    # The web is searched only when the documents do not cover it.
    graph.add_conditional_edges(
        "documents", after_documents,
        {"search the web": "web_search", "done": END},
    )
    graph.add_edge("web_search", END)
    graph.add_edge("github", END)
    graph.add_edge("write_sql", "run_sql")
    # A SQL error loops back for one corrected attempt.
    graph.add_conditional_edges(
        "run_sql",
        lambda state: "retry" if state.get("sql_error") else "done",
        {"retry": "write_sql", "done": "data_answer"},
    )
    graph.add_edge("data_answer", END)
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
    tool that produced the answer.  A github answer also has
    `commits`, the list the answer was drawn from, an nyc_data
    answer has `query`, the SQL that ran and its result, and a web
    answer has `web_results`.  A tool that fails raises
    `tools.ToolFailure`, except the web search, whose failure is added
    to the documents' refusal.
    """
    final = GRAPH.invoke(
        {"question": question, "history": history or []},
        context={"collection": collection, "client": client},
    )
    return final["result"]
