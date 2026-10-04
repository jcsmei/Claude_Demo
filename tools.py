"""Tools that fetch live information from outside the project."""

import os
import sqlite3
import time

import httpx

GITHUB_REPO = "jcsmei/Claude_Demo"
GITHUB_URL = f"https://api.github.com/repos/{GITHUB_REPO}/commits"
# GitHub limits calls made without a login per network address, and a
# hosting service shares addresses between apps, so results are reused
# for a while instead of fetched on every question.
CACHE_SECONDS = 600
MAX_COMMITS = 20
TIMEOUT_SECONDS = 15

_cache = {}


class ToolFailure(Exception):
    """A tool could not finish.  Its message is safe to show a user."""


def clear_cache():
    """Forget every cached result, so the next call fetches again."""
    _cache.clear()


def recent_commits(limit=5, http_get=httpx.get):
    """Return the project's most recent commits on GitHub, newest first.

    Each commit is a dict with its short `sha`, its `date`, the first
    line of its `message` and its `url`.  Author names and email
    addresses are left out on purpose.  `http_get` exists so tests can
    pass in a fake instead of calling GitHub.
    """
    if not 1 <= limit <= MAX_COMMITS:
        raise ToolFailure(f"limit must be between 1 and {MAX_COMMITS}")
    cached = _cache.get("commits")
    if cached and time.monotonic() - cached[0] < CACHE_SECONDS:
        return cached[1][:limit]
    try:
        response = http_get(
            GITHUB_URL,
            params={"per_page": MAX_COMMITS},
            headers={"Accept": "application/vnd.github+json"},
            timeout=TIMEOUT_SECONDS,
        )
    except httpx.HTTPError as error:
        raise ToolFailure("GitHub could not be reached.") from error
    if response.status_code in (403, 429):
        raise ToolFailure(
            "GitHub's rate limit was reached. Try again in a few minutes."
        )
    if response.status_code != 200:
        raise ToolFailure(f"GitHub returned HTTP {response.status_code}.")
    commits = [
        {
            "sha": item["sha"][:7],
            "date": item["commit"]["author"]["date"],
            "message": item["commit"]["message"].splitlines()[0],
            "url": item["html_url"],
        }
        for item in response.json()
    ]
    _cache["commits"] = (time.monotonic(), commits)
    return commits[:limit]


NYC_DATA_URL = "https://data.cityofnewyork.us/resource/jb3k-j3gp.json"
# The city refreshes this dataset once a day.
NYC_DATA_CACHE_SECONDS = 6 * 3600
MAX_ROWS = 50
# A query is stopped after this many database steps, so that a badly
# written one cannot keep the app busy.
MAX_QUERY_STEPS = 1_000_000

LICENSE_SCHEMA = """\
Table driver_licenses: New York City medallion taxi drivers who hold an
active license, counted by the month in which the license expires.
- expiry_month TEXT: the month the licenses expire, as 'YYYY-MM'
- expiry_year INTEGER: the year the licenses expire
- drivers INTEGER: how many active drivers have a license that expires
  in that month
Every row is a medallion taxi driver license, so no filter on the type
of license is needed. The total number of active drivers is
SUM(drivers)."""
LICENSE_TABLE = "driver_licenses"


class QueryError(ToolFailure):
    """A SQL query was rejected or failed; a corrected one may work."""


def license_counts(http_get=httpx.get):
    """Return counts of active NYC medallion taxi driver licenses.

    The result is a dict with `rows`, each an (expiry_month,
    expiry_year, drivers) tuple, and `updated`, the date
    the city last refreshed the data.  Only counts are requested from
    NYC Open Data: the drivers' names and license numbers in the
    source dataset are never downloaded.
    """
    cached = _cache.get("licenses")
    if cached and time.monotonic() - cached[0] < NYC_DATA_CACHE_SECONDS:
        return cached[1]
    params = {
        "$select": ("date_trunc_ym(expiration_date) as month, "
                    "count(*) as drivers, "
                    "max(last_updated_date) as updated"),
        "$group": "month",
        "$order": "month",
        "$limit": 5000,
    }
    try:
        response = http_get(NYC_DATA_URL, params=params,
                            timeout=TIMEOUT_SECONDS)
    except httpx.HTTPError as error:
        raise ToolFailure("NYC Open Data could not be reached.") from error
    if response.status_code != 200:
        raise ToolFailure(
            f"NYC Open Data returned HTTP {response.status_code}."
        )
    items = [item for item in response.json() if item.get("month")]
    data = {
        "rows": [(item["month"][:7], int(item["month"][:4]),
                  int(item["drivers"]))
                 for item in items],
        "updated": max((item.get("updated", "")[:10] for item in items),
                       default=""),
    }
    _cache["licenses"] = (time.monotonic(), data)
    return data


def query_license_data(sql, http_get=httpx.get):
    """Run one read-only SQL query on the driver license counts.

    The table is described by `LICENSE_SCHEMA`.  Return a dict with
    the `sql` that ran, the result's `columns` and `rows` (at most
    `MAX_ROWS`), and `updated`, the date of the data.  Anything other
    than a single SELECT statement that reads the table, and any SQL
    error, raises `QueryError`.
    """
    statement = sql.strip().rstrip(";").strip()
    if ";" in statement:
        raise QueryError("Only one SQL statement is allowed.")
    if not statement.lower().startswith(("select", "with")):
        raise QueryError("Only SELECT statements are allowed.")
    # A query that reads no data could only return text the model made
    # up, such as SELECT 'some claim'.
    if LICENSE_TABLE not in statement.lower():
        raise QueryError(f"The query must read from {LICENSE_TABLE}.")
    data = license_counts(http_get)
    connection = sqlite3.connect(":memory:")
    try:
        connection.execute(
            "CREATE TABLE driver_licenses (expiry_month TEXT, "
            "expiry_year INTEGER, drivers INTEGER)"
        )
        connection.executemany(
            "INSERT INTO driver_licenses VALUES (?, ?, ?)", data["rows"]
        )
        # Belt and braces: the database itself refuses any change.
        connection.execute("PRAGMA query_only = ON")
        connection.set_progress_handler(lambda: 1, MAX_QUERY_STEPS)
        cursor = connection.execute(statement)
        columns = [column[0] for column in cursor.description]
        rows = [list(row) for row in cursor.fetchmany(MAX_ROWS)]
    except sqlite3.Error as error:
        raise QueryError(f"The SQL failed: {error}") from error
    finally:
        connection.close()
    return {"sql": statement, "columns": columns, "rows": rows,
            "updated": data["updated"]}


TAVILY_URL = "https://api.tavily.com/search"
WEB_RESULTS = 3
# Each result's text is cut to this length to limit the tokens used.
SNIPPET_CHARS = 500


def web_search_available():
    """Return True when a key for the web search service is set."""
    return bool(os.environ.get("TAVILY_API_KEY"))


def web_search(query, http_post=httpx.post):
    """Return up to `WEB_RESULTS` web results for `query`, from Tavily.

    Each result is a dict with its `title`, `url` and `content`, a
    short extract of the page.  The key is read from the
    TAVILY_API_KEY setting.
    """
    key = os.environ.get("TAVILY_API_KEY", "")
    if not key:
        raise ToolFailure("Web search is not configured.")
    try:
        response = http_post(
            TAVILY_URL,
            headers={"Authorization": f"Bearer {key}"},
            json={"query": query, "max_results": WEB_RESULTS},
            timeout=TIMEOUT_SECONDS,
        )
    except httpx.HTTPError as error:
        raise ToolFailure(
            "The web search service could not be reached."
        ) from error
    if response.status_code in (401, 403):
        raise ToolFailure("The web search key was rejected.")
    if response.status_code == 429:
        raise ToolFailure("The web search allowance is used up.")
    if response.status_code != 200:
        raise ToolFailure(
            f"The web search service returned HTTP {response.status_code}."
        )
    return [
        {
            "title": item.get("title", ""),
            "url": item["url"],
            "content": " ".join(item.get("content", "").split())
            [:SNIPPET_CHARS],
        }
        for item in response.json().get("results", [])[:WEB_RESULTS]
    ]
