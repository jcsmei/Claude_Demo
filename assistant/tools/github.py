"""The GitHub tool: answers from the project's latest commits."""

from assistant import rag
from assistant import tools
from assistant.llm import ask
from assistant.tools.base import Evidence, ToolContext, ToolResult

COMMITS_SHOWN = 10
INSTRUCTIONS = (
    "You answer questions about a demo project. Use only the list "
    "of its latest code changes, newest first; each line is a "
    "date, a short ID and a summary. Explain conversationally in "
    "plain language. Each summary is all that is known about a "
    "change, so do not describe details beyond it, do not invent "
    "changes, and do not spell out abbreviations."
)


class GitHubTool:
    """Answer from the project's latest commits on GitHub."""

    name = "github"
    description = (
        "the latest changes to the project's code: recent commits, "
        "updates, or what changed and when"
    )
    args_schema = None  # the router passes no arguments
    source_label = "Source: GitHub, the project's live commit history"

    def run(self, args: dict, context: ToolContext) -> ToolResult:
        """Fetch the latest commits and answer from them only."""
        commits = tools.recent_commits(COMMITS_SHOWN)
        listing = "\n".join(
            f"{commit['date']} {commit['sha']} {commit['message']}"
            for commit in commits
        )
        history = rag.format_history(context.history) or "(none)"
        prompt = (
            f"Latest changes:\n{listing}\n\n"
            f"Conversation so far:\n{history}"
            f"\n\nQuestion: {context.question}"
        )
        return {
            "answer": ask(prompt, client=context.client,
                          system=INSTRUCTIONS),
            "status": "answered", "answered": True, "tool": self.name,
            "sources": ["GitHub"], "passages": [],
            "evidence": Evidence("commits", commits),
            "search_query": context.search_query,
        }


GITHUB = GitHubTool()
