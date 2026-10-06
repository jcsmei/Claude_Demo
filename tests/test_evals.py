"""Tests for the evaluation's scoring, which must not be wrong itself.

The evaluation calls real models and is run by hand.  These tests
cover only its checks, and need no network.
"""

import pytest

from evals.compare_models import (build_cases, contains, contains_any,
                                  contains_number, excludes, normalise,
                                  score)


def test_normalise_treats_special_spaces_as_ordinary_ones():
    # A narrow non-breaking space, as models sometimes write.
    assert normalise("Blue Heron") == "blue heron"
    assert normalise("  Blue \n Heron ") == "blue heron"


def test_contains_passes_despite_a_special_space():
    # This exact case was wrongly failed in the first evaluation run.
    check = contains("Blue Heron")
    assert check("The project’s codename is **Blue Heron**.")
    assert not check("The codename is Red Kite.")


def test_contains_needs_every_phrase_and_contains_any_needs_one():
    assert contains("alpha", "beta")("Alpha and Beta")
    assert not contains("alpha", "beta")("Alpha only")
    assert contains_any("9", "nine")("He has nine years")
    assert not contains_any("9", "nine")("He has ten years")


def test_excludes_fails_when_the_phrase_appears():
    assert excludes("Paris")("The documents do not cover this.")
    assert not excludes("Paris")("The capital is PARIS.")


@pytest.mark.parametrize("answer", [
    "There are 180521 drivers.",
    "There are **180,521** drivers.",
    "There are 180 521 drivers.",
])
def test_contains_number_ignores_separators(answer):
    assert contains_number(180521)(answer)


def test_contains_number_rejects_a_different_number():
    assert not contains_number(180521)("There are 180,520 drivers.")
    assert not contains_number(40860)("None")


def test_score_needs_the_right_tool_status_and_text():
    case = {"tool": "documents", "status": "answered",
            "check": contains("Blue Heron")}
    right = {"tool": "documents", "status": "answered",
             "answer": "It is Blue Heron."}
    assert score(case, right)
    assert not score(case, {**right, "tool": "web"})
    assert not score(case, {**right, "status": "not_covered"})
    assert not score(case, {**right, "answer": "It is Red Kite."})


def test_cases_cover_each_kind_of_behaviour():
    cases = build_cases(total_drivers=100, expiring_2027=10)
    assert {case["tool"] for case in cases} == {
        "documents", "github", "nyc_data"
    }
    assert {case["status"] for case in cases} == {
        "answered", "not_covered", "unclear"
    }
    assert any(case["history"] for case in cases)
    assert len({case["name"] for case in cases}) == len(cases)
