"""Web search: the documents tool's fallback, through Tavily's MCP server.

The router never chooses this directly.  The documents tool hands a
question over only when its documents do not cover it and the rules in
`web_search_allowed` permit it.
"""

import re

from langgraph.runtime import Runtime

from assistant import rag
from assistant import tools
from assistant.llm import ask
from assistant.tools.base import Evidence

NAME = "web"
SOURCE_LABEL = ("Source: a web search through Tavily's MCP server, not "
                "the project's official documents")

# Shown at the start of an answer that came from the web, so the
# reader is never left to assume it came from the documents.
WEB_NOTICE = (
    "The project's official documents do not cover this, so I searched "
    "the web. What follows comes from web pages, not from the official "
    "documents, and has not been verified by this project."
)
WEB_NOT_FOUND_SENTINEL = "NOT_FOUND"
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
        f"{WEB_NOT_FOUND_SENTINEL}."
    )
    prompt = (
        f"Web search results:\n{listing or '(none)'}\n\n"
        f"Conversation so far:\n{rag.format_history(history) or '(none)'}"
        f"\n\nQuestion: {question}"
    )
    reply = ask(prompt, client=client, system=instructions)
    found = WEB_NOT_FOUND_SENTINEL not in reply
    return {
        "answer": (f"{WEB_NOTICE}\n\n{reply}" if found
                   else WEB_NOT_FOUND_MESSAGE),
        "status": "answered" if found else "not_covered",
        "answered": found, "tool": NAME,
        "sources": [result["url"] for result in results] if found else [],
        "passages": [], "evidence": Evidence("web_results", results),
        "search_query": standalone,
    }


def web_search_node(state, runtime: Runtime):
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
