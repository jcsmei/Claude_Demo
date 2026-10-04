"""Tools that fetch live information from outside the project."""

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
