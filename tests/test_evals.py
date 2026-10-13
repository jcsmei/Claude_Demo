"""Tests for the evaluation's scoring, which must not be wrong itself.

The evaluation calls real models and is run by hand.  These tests
cover only its checks, and need no network.
"""

import pytest

from evals.compare_models import (build_cases, contains, contains_any,
                                  contains_number, excludes, normalise,
                                  score)
from evals.report import diverging_cases, load_runs, render
from evals.retrieval_metrics import rank_of, summarise


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


def test_every_case_says_in_words_what_is_expected():
    for case in build_cases(total_drivers=100, expiring_2027=10):
        assert case["expect"].endswith(".")


def sample_run():
    """Build a small run in the shape the evaluation saves."""
    def row(case, passed, answer):
        return {"case": case, "tool": "documents", "status": "answered",
                "pass": passed, "seconds": 1.0, "answer": answer}
    return {
        "run_date": "2026-01-01",
        "roles": {"maker/small": "Main model"},
        "method": ["Same questions for each model."],
        "decision": "Keep the small model.",
        "findings": [{"title": "A tie.", "detail": "Both were right."}],
        "limitations": ["Only two cases."],
        "summary": {
            "maker/small": {"passed": 2, "cases": 2, "model_calls": 4,
                            "tokens": 1200},
            "maker/large": {"passed": 1, "cases": 2, "model_calls": 4,
                            "tokens": 1300},
        },
        "results": {
            "maker/small": [row("greeting", True, "SENTINEL"),
                            row("fact: codename", True, "Blue Heron")],
            "maker/large": [row("greeting", False, "Hello | welcome"),
                            row("fact: codename", True, "Blue Heron")],
        },
    }


def test_diverging_cases_are_the_ones_models_disagree_on():
    assert diverging_cases(sample_run()) == ["greeting"]


def test_report_shows_result_divergence_findings_and_log():
    cases = build_cases(total_drivers=100, expiring_2027=10)
    report = render([sample_run()], cases)

    assert "| `small` | 2 of 2 | 4 | 1,200 |" in report
    assert "**Decision:** Keep the small model." in report
    assert "### greeting" in report
    assert "### fact: codename" not in report
    assert "**A tie.** Both were right." in report
    assert "- Only two cases." in report
    assert "| 2026-01-01 | small, large | small 2/2; large 1/2 |" in report
    # A pipe inside an answer must not break the table it sits in.
    assert "Hello \\| welcome" in report


def test_the_saved_runs_produce_a_report():
    runs = load_runs()
    assert runs, "no evaluation run is saved in evals/runs/"
    report = render(runs, build_cases(total_drivers=0, expiring_2027=0))
    assert report.startswith("# Model evaluation report")
    for run in runs:
        assert run["run_date"] in report


def test_rank_of_finds_the_passage_across_line_breaks():
    passages = ["About chunks.", "The codename is Blue\nHeron."]
    assert rank_of("Blue Heron", passages) == 2
    assert rank_of("Red Kite", passages) is None


def test_summarise_computes_recall_and_mean_reciprocal_rank():
    # Four questions: found first, first, second, and not found.
    summary = summarise([1, 1, 2, None])
    assert summary["questions"] == 4
    assert summary["recall"] == {"1": 2, "3": 3, "5": 3, "10": 3}
    # (1 + 1 + 1/2 + 0) / 4
    assert summary["mean_reciprocal_rank"] == 0.625


def test_summarise_handles_no_questions():
    assert summarise([])["mean_reciprocal_rank"] == 0.0


def test_report_includes_retrieval_quality_when_measured():
    retrieval = [{"run_date": "2026-01-02", "chunks": 40,
                  "retrieved_per_question": 5, "questions": 4,
                  "recall": {"1": 2, "3": 3, "5": 4, "10": 4},
                  "mean_reciprocal_rank": 0.708,
                  "not_ranked_first": [
                      {"question": "A slow one?", "rank": 5}]}]
    cases = build_cases(total_drivers=100, expiring_2027=10)

    report = render([sample_run()], cases, retrieval)

    assert "## Retrieval quality" in report
    assert "| Top 5 | 4 of 4 | 100% |" in report
    assert "**Mean reciprocal rank: 0.71.**" in report
    assert '- "A slow one?": position 5' in report
    assert "| 2026-01-02 | 4 | 40 | 50% | 75% | 100% | 0.71 |" in report


def test_report_omits_retrieval_when_not_measured():
    cases = build_cases(total_drivers=100, expiring_2027=10)
    assert "## Retrieval quality" not in render([sample_run()], cases)
