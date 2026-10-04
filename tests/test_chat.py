"""Tests for chat: choosing a tool and answering with it."""

import uuid

import chromadb
import pytest

import chat
import tools
from fakes import FakeClient, FakeEmbedding
from store import add_documents, get_collection

COMMITS = [
    {"sha": "abc1234", "date": "2026-10-04T20:42:40Z",
     "message": "Add conversation memory",
     "url": "https://github.com/example/commit/abc1234"},
]
HISTORY = [
    {"role": "user", "content": "What is MCP?"},
    {"role": "assistant", "content": "A protocol for tools."},
]


@pytest.fixture(autouse=True)
def no_web_search(monkeypatch):
    """Keep tests off the network; tests of the web search turn it on."""
    monkeypatch.setattr(tools, "web_search_available", lambda: False)


@pytest.fixture
def collection(tmp_path):
    """Return an in-memory collection holding one document."""
    (tmp_path / "space.txt").write_text(
        "Mars is called the red planet.", encoding="utf-8"
    )
    collection = get_collection(
        client=chromadb.EphemeralClient(),
        name=f"test-{uuid.uuid4().hex}",
        embedding_function=FakeEmbedding(),
    )
    add_documents(collection, tmp_path)
    return collection


def test_choose_tool_reads_the_tool_and_the_rewritten_question():
    client = FakeClient(
        "TOOL: github\nQUESTION: What changed in the code recently?"
    )
    assert chat.choose_tool("what's new?", HISTORY, client=client) == (
        "github", "What changed in the code recently?"
    )


def test_choose_tool_keeps_a_first_message_as_it_was_asked():
    client = FakeClient(
        "TOOL: github\nQUESTION: What changed in the code recently?"
    )
    assert chat.choose_tool("what's new?", client=client) == (
        "github", "what's new?"
    )


def test_choose_tool_shows_the_model_the_tools_and_conversation():
    client = FakeClient("TOOL: documents\nQUESTION: What tools has MCP?")

    chat.choose_tool("what tools does it have?", HISTORY, client=client)

    sent = client.received["messages"][0]["content"]
    assert "- documents:" in sent and "- github:" in sent
    assert "User: What is MCP?" in sent
    assert sent.endswith("Latest message: what tools does it have?")


@pytest.mark.parametrize("reply", [
    "I think github would be best.",
    "TOOL: weather\nQUESTION:",
    "",
    "TOOL: web\nQUESTION: " + "x" * 301,
])
def test_choose_tool_falls_back_when_the_reply_cannot_be_used(reply):
    client = FakeClient(reply)
    assert chat.choose_tool("hello there", client=client) == (
        "documents", "hello there"
    )


def test_choose_tool_accepts_untidy_formatting():
    client = FakeClient("tool:  GitHub \nquestion:   What   changed? ")
    assert chat.choose_tool("what changed?", HISTORY, client=client) == (
        "github", "What changed?"
    )


def test_respond_answers_from_the_documents(collection):
    client = FakeClient(
        ["TOOL: documents\nQUESTION: Which planet is red?", "Mars."]
    )

    result = chat.respond("which one is red?", collection, client=client,
                          history=HISTORY)

    assert result["tool"] == "documents"
    assert result["answer"] == "Mars."
    assert result["search_query"] == "Which planet is red?"
    assert result["sources"] == ["space.txt"]
    # Two model calls: choosing the tool, then answering.
    assert len(client.calls) == 2


def test_respond_answers_from_github(collection, monkeypatch):
    monkeypatch.setattr(tools, "recent_commits", lambda limit: COMMITS)
    client = FakeClient(
        ["TOOL: github\nQUESTION: What changed recently?",
         "Conversation memory was added."]
    )

    result = chat.respond("what's new?", collection, client=client)

    assert result["tool"] == "github"
    assert result["answer"] == "Conversation memory was added."
    assert result["status"] == "answered"
    assert result["commits"] == COMMITS
    assert result["passages"] == []
    sent = client.calls[1]["messages"][0]["content"]
    assert "2026-10-04T20:42:40Z abc1234 Add conversation memory" in sent
    assert sent.endswith("Question: what's new?")


def test_respond_lets_a_tool_failure_through(collection, monkeypatch):
    def failing(limit):
        raise tools.ToolFailure("GitHub could not be reached.")
    monkeypatch.setattr(tools, "recent_commits", failing)
    client = FakeClient("TOOL: github\nQUESTION: What changed?")

    with pytest.raises(tools.ToolFailure, match="could not be reached"):
        chat.respond("what's new?", collection, client=client)


QUERY = {"sql": "SELECT SUM(drivers) AS total FROM driver_licenses",
         "columns": ["total"], "rows": [[180648]],
         "updated": "2026-10-04"}


def test_write_sql_removes_a_code_fence():
    client = FakeClient("```sql\nSELECT 1\n```")
    assert chat.write_sql("How many?", client=client) == "SELECT 1"
    sent = client.received["messages"][0]["content"]
    assert "Table driver_licenses" in sent
    assert sent.endswith("Question: How many?")


def test_write_sql_shows_the_model_its_failed_attempt():
    client = FakeClient("SELECT 1")
    chat.write_sql("How many?", "SELECT nope", "no such column: nope",
                   client=client)
    sent = client.received["messages"][0]["content"]
    assert "SELECT nope" in sent
    assert "no such column: nope" in sent


def test_respond_answers_from_the_license_data(collection, monkeypatch):
    ran = []

    def fake_query(sql):
        ran.append(sql)
        return QUERY
    monkeypatch.setattr(tools, "query_license_data", fake_query)
    client = FakeClient([
        "TOOL: nyc_data\nQUESTION: How many drivers?",
        "SELECT SUM(drivers) AS total FROM driver_licenses",
        "There are 180648 active drivers.",
    ])

    result = chat.respond("how many drivers?", collection, client=client)

    assert result["tool"] == "nyc_data"
    assert result["answer"] == "There are 180648 active drivers."
    assert result["query"] == QUERY
    assert ran == ["SELECT SUM(drivers) AS total FROM driver_licenses"]
    final_prompt = client.calls[2]["messages"][0]["content"]
    assert "total\n180648" in final_prompt
    assert "2026-10-04" in final_prompt


def test_respond_retries_once_when_the_sql_fails(collection, monkeypatch):
    ran = []

    def fake_query(sql):
        ran.append(sql)
        if "nope" in sql:
            raise tools.QueryError("The SQL failed: no such column: nope")
        return QUERY
    monkeypatch.setattr(tools, "query_license_data", fake_query)
    client = FakeClient([
        "TOOL: nyc_data\nQUESTION: How many drivers?",
        "SELECT nope FROM driver_licenses",
        "SELECT SUM(drivers) AS total FROM driver_licenses",
        "There are 180648 active drivers.",
    ])

    result = chat.respond("how many drivers?", collection, client=client)

    assert result["answer"] == "There are 180648 active drivers."
    assert ran == ["SELECT nope FROM driver_licenses",
                   "SELECT SUM(drivers) AS total FROM driver_licenses"]
    # The second SQL request shows the model what went wrong.
    retry_prompt = client.calls[2]["messages"][0]["content"]
    assert "no such column: nope" in retry_prompt


def test_respond_retries_once_when_the_result_is_empty(
        collection, monkeypatch):
    empty = {"sql": "SELECT ...", "columns": ["total"], "rows": [[None]],
             "updated": "2026-10-04"}
    results = [empty, QUERY]
    monkeypatch.setattr(tools, "query_license_data",
                        lambda sql: results.pop(0))
    client = FakeClient([
        "TOOL: nyc_data\nQUESTION: How many drivers?",
        "SELECT SUM(drivers) FROM driver_licenses WHERE expiry_year = 1",
        "SELECT SUM(drivers) AS total FROM driver_licenses",
        "There are 180648 active drivers.",
    ])

    result = chat.respond("how many drivers?", collection, client=client)

    assert result["query"] == QUERY
    retry_prompt = client.calls[2]["messages"][0]["content"]
    assert "returned no data" in retry_prompt


def test_respond_reports_an_empty_result_after_the_retry(
        collection, monkeypatch):
    empty = {"sql": "SELECT ...", "columns": ["total"], "rows": [],
             "updated": "2026-10-04"}
    monkeypatch.setattr(tools, "query_license_data", lambda sql: empty)
    client = FakeClient([
        "TOOL: nyc_data\nQUESTION: How many expire in 1999?",
        "SELECT ...", "SELECT ...", "The data has no matching rows.",
    ])

    result = chat.respond("how many in 1999?", collection, client=client)

    assert result["answer"] == "The data has no matching rows."
    assert result["query"] == empty


def test_respond_gives_up_after_two_failed_queries(collection, monkeypatch):
    def failing(sql):
        raise tools.QueryError("The SQL failed: no such column: nope")
    monkeypatch.setattr(tools, "query_license_data", failing)
    client = FakeClient([
        "TOOL: nyc_data\nQUESTION: How many drivers?",
        "SELECT nope FROM driver_licenses",
    ])

    with pytest.raises(tools.ToolFailure, match="after 2 attempts"):
        chat.respond("how many drivers?", collection, client=client)
    # Choosing the tool, then two attempts at the SQL.
    assert len(client.calls) == 3


WEB_RESULTS = [{"title": "Taxi medallion", "content": "A permit.",
                "url": "https://example.com/medallion"}]
NOT_COVERED_REPLIES = ["TOOL: documents\nQUESTION: unused",
                       "NOT_IN_DOCUMENTS"]


def enable_web_search(monkeypatch, search=None):
    """Turn the web search on, with a fake in place of Tavily."""
    searched = []

    def fake_search(query):
        searched.append(query)
        return WEB_RESULTS
    monkeypatch.setattr(tools, "web_search_available", lambda: True)
    monkeypatch.setattr(tools, "web_search", search or fake_search)
    return searched


def test_respond_searches_the_web_when_documents_do_not_cover_it(
        collection, monkeypatch):
    searched = enable_web_search(monkeypatch)
    client = FakeClient(NOT_COVERED_REPLIES + ["A medallion is a permit."])

    result = chat.respond("what are medallions?", collection, client=client)

    assert searched == ["what are medallions?"]
    assert result["tool"] == "web"
    assert result["status"] == "answered"
    assert result["answer"] == (
        f"{chat.WEB_NOTICE}\n\nA medallion is a permit."
    )
    assert result["web_results"] == WEB_RESULTS
    assert result["sources"] == ["https://example.com/medallion"]
    sent = client.calls[2]["messages"][0]["content"]
    assert "Taxi medallion (https://example.com/medallion)" in sent


def test_respond_does_not_search_the_web_when_documents_answer(
        collection, monkeypatch):
    searched = enable_web_search(monkeypatch)
    client = FakeClient(["TOOL: documents\nQUESTION: unused", "Mars."])

    result = chat.respond("which planet is red?", collection, client=client)

    assert result["tool"] == "documents"
    assert searched == []


@pytest.mark.parametrize("question", [
    "What is Jack's phone number?",
    "where does jack mei live",
    "who owns the email jane.doe@example.com?",
    "whose number is 774-555-0123?",
    "look up (212) 555 0199",
])
def test_respond_never_searches_the_web_for_personal_details(
        collection, monkeypatch, question):
    searched = enable_web_search(monkeypatch)
    client = FakeClient(NOT_COVERED_REPLIES)

    result = chat.respond(question, collection, client=client)

    assert searched == []
    assert result["tool"] == "documents"
    assert result["status"] == "not_covered"


def test_respond_stays_with_the_refusal_when_web_search_is_off(collection):
    client = FakeClient(NOT_COVERED_REPLIES)

    result = chat.respond("what are medallions?", collection, client=client)

    assert result["tool"] == "documents"
    assert result["status"] == "not_covered"
    assert len(client.calls) == 2


def test_respond_says_when_the_web_has_no_answer_either(
        collection, monkeypatch):
    enable_web_search(monkeypatch)
    client = FakeClient(NOT_COVERED_REPLIES + ["NOT_FOUND"])

    result = chat.respond("what are medallions?", collection, client=client)

    assert result["tool"] == "web"
    assert result["status"] == "not_covered"
    assert result["answer"] == chat.WEB_NOT_FOUND_MESSAGE
    assert result["sources"] == []


def test_respond_keeps_the_refusal_when_the_web_search_fails(
        collection, monkeypatch):
    def failing(query):
        raise tools.ToolFailure("The web search allowance is used up.")
    enable_web_search(monkeypatch, search=failing)
    client = FakeClient(NOT_COVERED_REPLIES)

    result = chat.respond("what are medallions?", collection, client=client)

    assert result["tool"] == "documents"
    assert result["status"] == "not_covered"
    assert result["answer"].endswith(
        "A web search was tried but failed: "
        "The web search allowance is used up."
    )


@pytest.mark.parametrize("question", [
    "what are medallions?",
    "how many licenses expire in 2027?",
    "what happened between 2019 and 2021?",
])
def test_ordinary_questions_may_be_searched_on_the_web(
        monkeypatch, question):
    monkeypatch.setattr(tools, "web_search_available", lambda: True)
    assert chat.web_search_allowed(question)


def test_web_notice_says_the_answer_is_not_from_the_documents():
    assert "not from the official documents" in chat.WEB_NOTICE
    assert "not been verified" in chat.WEB_NOTICE


def test_flow_diagram_shows_the_web_search_fallback():
    diagram = chat.flow_diagram()
    assert '"documents" -> "web_search" [style=dashed];' in diagram
    assert '"documents" -> "answer" [style=dashed];' in diagram
    assert '"web_search" -> "answer";' in diagram


def test_graph_routes_through_one_node_per_tool():
    nodes = set(chat.GRAPH.get_graph().nodes)
    assert {"choose_tool", "documents", "github", "write_sql",
            "run_sql", "data_answer"} <= nodes


def test_flow_diagram_shows_the_sql_retry_loop():
    diagram = chat.flow_diagram()
    assert '"choose_tool" -> "write_sql" [style=dashed];' in diagram
    assert '"run_sql" -> "write_sql" [style=dashed];' in diagram
    assert '"run_sql" -> "data_answer" [style=dashed];' in diagram


def test_flow_diagram_shows_the_choice_between_tools():
    diagram = chat.flow_diagram()
    assert '"message" -> "choose_tool";' in diagram
    assert '"choose_tool" -> "documents" [style=dashed];' in diagram
    assert '"choose_tool" -> "github" [style=dashed];' in diagram
    assert '"github" -> "answer";' in diagram
