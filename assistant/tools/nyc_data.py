"""The NYC data tool: answers counts from NYC Open Data with SQL.

It brings its own steps: the model writes SQL, code runs it, a failed
or empty query is retried once, and the model explains the rows.  The
steps are graph nodes, so they stay visible in the drawn graph.
"""

from langgraph.runtime import Runtime

from assistant import rag
from assistant import tools
from assistant.llm import ask
from assistant.tools.base import Evidence

# A failed SQL query is rewritten once before the tool gives up.
MAX_SQL_ATTEMPTS = 2


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
            "status": "answered", "answered": True, "tool": NYC_DATA.name,
            "sources": ["NYC Open Data"], "passages": [],
            "evidence": Evidence("query", [query]),
            "search_query": standalone}


def write_sql_node(state, runtime: Runtime):
    """Have the model write SQL, or correct a statement that failed."""
    sql = write_sql(state["search_query"], state.get("sql"),
                    state.get("sql_error"),
                    client=runtime.context["client"])
    return {"sql": sql}


def run_sql_node(state, runtime: Runtime):
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


def data_answer_node(state, runtime: Runtime):
    """Answer from the rows the query returned."""
    result = answer_from_data(
        state["question"], state["search_query"], state["query"],
        state["history"], runtime.context["client"],
    )
    return {"result": result}


class NYCDataTool:
    """Answer counts of NYC taxi driver licenses, through SQL."""

    name = "nyc_data"
    description = (
        "only for a count: how many active New York City medallion "
        "taxi drivers there are, or how many licenses expire in a "
        "given month or year"
    )
    args_schema = None  # the router passes no arguments
    source_label = ("Source: NYC Open Data, live counts of active "
                    "medallion taxi driver licenses")

    def add_to_graph(self, graph, end):
        """Add this tool's steps to `graph`; return its first node."""
        graph.add_node("write_sql", write_sql_node)
        graph.add_node("run_sql", run_sql_node)
        graph.add_node("data_answer", data_answer_node)
        graph.add_edge("write_sql", "run_sql")
        # A SQL error loops back for one corrected attempt.
        graph.add_conditional_edges(
            "run_sql",
            lambda state: "retry" if state.get("sql_error") else "done",
            {"retry": "write_sql", "done": "data_answer"},
        )
        graph.add_edge("data_answer", end)
        return "write_sql"


NYC_DATA = NYCDataTool()
