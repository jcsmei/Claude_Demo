"""Tests for tools, with a fake in place of the call to GitHub."""

import json
from types import SimpleNamespace

import httpx
import pytest

import tools


def github_item(number):
    """Build one commit in the shape GitHub's API returns."""
    return {
        "sha": f"{number:07x}" + "f" * 33,
        "html_url": f"https://github.com/example/commit/{number}",
        "commit": {
            "message": f"Change number {number}\n\nLonger description.",
            "author": {"name": "Someone", "email": "someone@example.com",
                       "date": f"2026-10-0{number}T12:00:00Z"},
        },
    }


class FakeGitHub:
    """Stand in for httpx.get and count how often it is called."""

    def __init__(self, status=200, error=None):
        self.status = status
        self.error = error
        self.calls = 0

    def __call__(self, url, **kwargs):
        self.calls += 1
        if self.error:
            raise self.error
        items = [github_item(number) for number in (3, 2, 1)]
        return SimpleNamespace(status_code=self.status, json=lambda: items)


@pytest.fixture(autouse=True)
def empty_cache():
    tools.clear_cache()


def test_recent_commits_returns_the_public_fields_only():
    commits = tools.recent_commits(2, http_get=FakeGitHub())
    assert commits == [
        {"sha": "0000003", "date": "2026-10-03T12:00:00Z",
         "message": "Change number 3",
         "url": "https://github.com/example/commit/3"},
        {"sha": "0000002", "date": "2026-10-02T12:00:00Z",
         "message": "Change number 2",
         "url": "https://github.com/example/commit/2"},
    ]


def test_recent_commits_reuses_a_recent_result():
    github = FakeGitHub()
    tools.recent_commits(1, http_get=github)
    assert len(tools.recent_commits(3, http_get=github)) == 3
    assert github.calls == 1


@pytest.mark.parametrize("limit", [0, 21])
def test_recent_commits_rejects_a_limit_out_of_range(limit):
    github = FakeGitHub()
    with pytest.raises(tools.ToolFailure, match="between 1 and 20"):
        tools.recent_commits(limit, http_get=github)
    assert github.calls == 0


@pytest.mark.parametrize("status, message", [
    (403, "rate limit"),
    (429, "rate limit"),
    (500, "HTTP 500"),
])
def test_recent_commits_explains_a_bad_response(status, message):
    with pytest.raises(tools.ToolFailure, match=message):
        tools.recent_commits(http_get=FakeGitHub(status=status))


def test_recent_commits_explains_a_network_failure():
    github = FakeGitHub(error=httpx.ConnectError("no route"))
    with pytest.raises(tools.ToolFailure, match="could not be reached"):
        tools.recent_commits(http_get=github)


def test_a_failure_is_not_cached():
    with pytest.raises(tools.ToolFailure):
        tools.recent_commits(http_get=FakeGitHub(status=500))
    assert len(tools.recent_commits(http_get=FakeGitHub())) == 3


def city_item(month, drivers):
    """Build one row in the shape NYC Open Data returns."""
    return {"type": "MEDALLION TAXI DRIVER",
            "month": f"{month}-01T00:00:00.000", "drivers": str(drivers),
            "updated": "2026-10-04T00:00:00.000"}


class FakeCity:
    """Stand in for httpx.get when it calls NYC Open Data."""

    def __init__(self, status=200, error=None):
        self.status = status
        self.error = error
        self.calls = 0
        self.params = None

    def __call__(self, url, **kwargs):
        self.calls += 1
        self.params = kwargs["params"]
        if self.error:
            raise self.error
        items = [city_item("2026-12", 100), city_item("2027-01", 250),
                 city_item("2027-02", 50)]
        return SimpleNamespace(status_code=self.status, json=lambda: items)


def test_license_counts_parses_months_years_and_counts():
    assert tools.license_counts(http_get=FakeCity()) == {
        "rows": [("2026-12", 2026, 100), ("2027-01", 2027, 250),
                 ("2027-02", 2027, 50)],
        "updated": "2026-10-04",
    }


def test_license_counts_requests_counts_and_no_personal_columns():
    city = FakeCity()
    tools.license_counts(http_get=city)
    selected = city.params["$select"]
    assert "count(*)" in selected
    assert "name" not in selected
    assert "license_number" not in selected


def test_license_counts_reuses_a_recent_result():
    city = FakeCity()
    tools.license_counts(http_get=city)
    tools.license_counts(http_get=city)
    assert city.calls == 1


def test_license_counts_explains_failures():
    with pytest.raises(tools.ToolFailure, match="HTTP 503"):
        tools.license_counts(http_get=FakeCity(status=503))
    with pytest.raises(tools.ToolFailure, match="could not be reached"):
        tools.license_counts(
            http_get=FakeCity(error=httpx.ConnectError("no route"))
        )


def test_query_license_data_runs_a_select():
    result = tools.query_license_data(
        "SELECT expiry_year, SUM(drivers) AS drivers "
        "FROM driver_licenses GROUP BY expiry_year ORDER BY expiry_year;",
        http_get=FakeCity(),
    )
    assert result["columns"] == ["expiry_year", "drivers"]
    assert result["rows"] == [[2026, 100], [2027, 300]]
    assert result["updated"] == "2026-10-04"
    assert not result["sql"].endswith(";")


@pytest.mark.parametrize("sql, message", [
    ("DELETE FROM driver_licenses", "Only SELECT"),
    ("DROP TABLE driver_licenses", "Only SELECT"),
    ("SELECT 1; SELECT 2", "Only one SQL statement"),
    ("SELECT 'The city' AS source", "must read from driver_licenses"),
    ("SELECT missing FROM driver_licenses", "no such column"),
    ("WITH RECURSIVE c(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM c) "
     "SELECT COUNT(*) FROM c, driver_licenses", "interrupted"),
])
def test_query_license_data_rejects_unsafe_or_broken_sql(sql, message):
    with pytest.raises(tools.QueryError, match=message):
        tools.query_license_data(sql, http_get=FakeCity())


def test_query_license_data_limits_the_rows_returned():
    sql = ("WITH RECURSIVE c(x) AS (SELECT 1 UNION ALL SELECT x + 1 "
           "FROM c WHERE x < 500) SELECT x FROM c "
           "WHERE (SELECT COUNT(*) FROM driver_licenses) > 0")
    result = tools.query_license_data(sql, http_get=FakeCity())
    assert len(result["rows"]) == tools.MAX_ROWS


def tavily_reply(count=5, is_error=False, structured=True):
    """Build a tool result in the shape Tavily's MCP server returns."""
    data = {"results": [
        {"title": f"Page {number}", "url": f"https://example.com/{number}",
         "content": "Some   text\n" + "x" * 600, "score": 0.9}
        for number in range(1, count + 1)
    ]}
    text = SimpleNamespace(text=json.dumps(data))
    return SimpleNamespace(is_error=is_error, content=[text],
                           structured_content=data if structured else None)


class FakeTavily:
    """Stand in for the call to Tavily's MCP server."""

    def __init__(self, reply=None, error=None):
        self.reply = reply or tavily_reply()
        self.error = error
        self.calls = []

    def __call__(self, query, key):
        self.calls.append((query, key))
        if self.error:
            raise self.error
        return self.reply


def test_web_search_returns_short_extracts(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")
    tavily = FakeTavily()

    results = tools.web_search("what is a medallion?", call_tool=tavily)

    assert len(results) == tools.WEB_RESULTS
    assert results[0]["title"] == "Page 1"
    assert results[0]["url"] == "https://example.com/1"
    assert results[0]["content"].startswith("Some text x")
    assert len(results[0]["content"]) == tools.SNIPPET_CHARS
    assert tavily.calls == [("what is a medallion?", "tvly-test")]


def test_web_search_reads_a_result_sent_only_as_text(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")
    tavily = FakeTavily(reply=tavily_reply(count=2, structured=False))
    results = tools.web_search("anything", call_tool=tavily)
    assert [result["title"] for result in results] == ["Page 1", "Page 2"]


def test_web_search_needs_a_key(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    tavily = FakeTavily()
    assert not tools.web_search_available()
    with pytest.raises(tools.ToolFailure, match="not configured"):
        tools.web_search("anything", call_tool=tavily)
    assert tavily.calls == []


def test_web_search_explains_a_tool_error(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")
    tavily = FakeTavily(reply=tavily_reply(is_error=True))
    with pytest.raises(tools.ToolFailure, match="reported an error"):
        tools.web_search("anything", call_tool=tavily)


@pytest.mark.parametrize("error", [
    httpx.ConnectError("no route"), TimeoutError(), RuntimeError("boom"),
])
def test_web_search_explains_a_connection_failure(monkeypatch, error):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")
    tavily = FakeTavily(error=error)
    with pytest.raises(tools.ToolFailure, match="could not be reached"):
        tools.web_search("anything", call_tool=tavily)


def test_web_search_uses_only_the_plain_search_tool():
    assert tools.TAVILY_TOOL == "tavily_search"
    assert tools.TAVILY_MCP_URL.startswith("https://mcp.tavily.com/")
