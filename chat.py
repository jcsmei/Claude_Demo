"""Choose the tool that fits a message, then answer with it."""

import rag
import tools
from llm import ask

# The tools the model may choose from, and when to choose each.  The
# first one is the fallback when the model's choice cannot be read.
TOOL_GUIDE = {
    "documents": (
        "everything else: how the project works, RAG, MCP, problems "
        "that were fixed, the creator Jack Mei, greetings and unclear "
        "messages"
    ),
    "github": (
        "the latest changes to the project's code: recent commits, "
        "updates, or what changed and when"
    ),
}
DEFAULT_TOOL = "documents"
COMMITS_SHOWN = 10


def choose_tool(question, history=None, client=None):
    """Return the tool for `question` and the question made standalone.

    One model call does both jobs: it picks a tool from `TOOL_GUIDE`
    and rewrites a follow-up so it can be understood without the
    conversation.  If the reply cannot be read, the result falls back
    to the documents tool and the question as it was asked.
    """
    guide = "\n".join(f"- {name}: {use}"
                      for name, use in TOOL_GUIDE.items())
    prompt = (
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
        "QUESTION: <the message, rewritten if needed>\n\n"
        f"Conversation:\n{rag.format_history(history) or '(none)'}\n\n"
        f"Latest message: {question}"
    )
    tool, standalone = DEFAULT_TOOL, question
    for line in ask(prompt, client=client).splitlines():
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
    prompt = (
        "You answer questions about a demo project. Use only the list "
        "of its latest code changes below, newest first; each line is "
        "a date, a short ID and a summary. Explain conversationally "
        "in plain language. Do not invent changes that are not "
        "listed, and do not spell out abbreviations.\n\n"
        f"Latest changes:\n{listing}\n\n"
        f"Conversation so far:\n{rag.format_history(history) or '(none)'}"
        f"\n\nQuestion: {question}"
    )
    return {"answer": ask(prompt, client=client), "status": "answered",
            "answered": True, "tool": "github", "sources": ["GitHub"],
            "passages": [], "commits": commits,
            "search_query": standalone}


def respond(question, collection, history=None, client=None):
    """Answer `question` with whichever tool fits it.

    Return the same dict as `rag.answer`, plus `tool`: the name of the
    tool that produced the answer.  A github answer also has
    `commits`, the list the answer was drawn from.  A tool that fails
    raises `tools.ToolFailure`.
    """
    tool, standalone = choose_tool(question, history, client=client)
    if tool == "github":
        return answer_from_github(question, standalone, history, client)
    result = rag.answer(question, collection, client=client,
                        history=history, search_query=standalone)
    result["tool"] = "documents"
    return result
