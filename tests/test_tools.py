"""Tests for tools, with a fake in place of the call to GitHub."""

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
