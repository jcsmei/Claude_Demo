"""Turn the saved evaluation runs into a readable report.

Run with `python -m evals.report` from the project folder.  It reads
every model run in `evals/runs/` and every retrieval measurement in
`evals/retrieval_runs/`, and writes `evals/REPORT.md`: the latest of
each in full, and a log of all runs.  It makes no model calls.

The numbers and answers come from the run files.  The findings,
decision and limitations are written by a person and stored in the run
file, because judging what a result means is not something to
automate.
"""

import json
from pathlib import Path

from evals.compare_models import build_cases

RUNS_FOLDER = Path(__file__).parent / "runs"
RETRIEVAL_RUNS_FOLDER = Path(__file__).parent / "retrieval_runs"
REPORT_FILE = Path(__file__).parent / "REPORT.md"


def load_runs(folder=RUNS_FOLDER):
    """Return every saved run, oldest first."""
    return [json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(folder.glob("*.json"))]


def cell(text):
    """Return `text` made safe to sit inside a Markdown table cell."""
    return " ".join(str(text).split()).replace("|", "\\|")


def short(model):
    """Return a model's name without its publisher prefix."""
    return model.split("/")[-1]


def mark(row):
    return "pass" if row["pass"] else "**FAIL**"


def diverging_cases(run):
    """Return the names of cases the models did not all agree on."""
    models = list(run["results"])
    names = [row["case"] for row in run["results"][models[0]]]
    outcomes = {
        name: {run["results"][model][index]["pass"] for model in models}
        for index, name in enumerate(names)
    }
    return [name for name in names if len(outcomes[name]) > 1]


def percent(part, whole):
    return f"{100 * part / whole:.0f}%" if whole else "n/a"


def render_retrieval(retrieval_runs):
    """Return the report's section on retrieval quality, as lines."""
    if not retrieval_runs:
        return []
    run = retrieval_runs[-1]
    total = run["questions"]
    lines = [
        "## Retrieval quality",
        "",
        f"Measured on {run['run_date']} with the retrieval benchmark: "
        f"{total} real questions,",
        f"each paired with the passage that answers it, searched across "
        f"{run['chunks']} chunks.",
        "This uses the real embedding model and no language model, so "
        "it costs no tokens.",
        "",
        "| The right passage is within the... | Questions | Share |",
        "|---|---|---|",
    ]
    for k, hits in run["recall"].items():
        lines.append(f"| Top {k} | {hits} of {total} | "
                     f"{percent(hits, total)} |")
    lines += [
        "",
        f"**Mean reciprocal rank: {run['mean_reciprocal_rank']:.2f}.** "
        "This is the average of 1 / position",
        "of the right passage, so 1.00 would mean it is always ranked "
        "first.",
        "",
        f"The assistant retrieves {run['retrieved_per_question']} "
        "passages per question, so what matters in practice is the",
        f"top-{run['retrieved_per_question']} row.",
        "",
        "**What this does and does not measure.** This is context "
        "recall: whether retrieval finds",
        "the passage that holds the answer. It does not measure context "
        "precision, which is",
        "whether the other retrieved passages were relevant, or "
        "faithfulness, which is whether",
        "an answer stays within the passages. Those are not yet "
        "measured.",
        "",
    ]
    slow = [item for item in run.get("not_ranked_first", [])
            if item["rank"] is None or item["rank"] > 3]
    if slow:
        lines += ["Questions whose passage ranked below third:", ""]
        for item in slow:
            place = item["rank"] if item["rank"] else "not found"
            lines.append(f"- \"{cell(item['question'])}\": position "
                         f"{place}")
        lines.append("")
    lines += [
        "| Date | Questions | Chunks | Top 1 | Top 3 | Top 5 | MRR |",
        "|---|---|---|---|---|---|---|",
    ]
    for past in retrieval_runs:
        count = past["questions"]
        recall = past["recall"]
        lines.append(
            f"| {past['run_date']} | {count} | {past['chunks']} | "
            f"{percent(recall['1'], count)} | "
            f"{percent(recall['3'], count)} | "
            f"{percent(recall['5'], count)} | "
            f"{past['mean_reciprocal_rank']:.2f} |"
        )
    lines.append("")
    return lines


def render(runs, cases, retrieval_runs=()):
    """Return the report as Markdown, for the latest of `runs`.

    `cases` are the evaluation's cases, used for each question and
    what was expected of the answer.  `retrieval_runs` are the saved
    retrieval measurements, oldest first.
    """
    run = runs[-1]
    models = list(run["results"])
    by_name = {case["name"]: case for case in cases}
    rows = {model: {row["case"]: row for row in run["results"][model]}
            for model in models}
    names = [row["case"] for row in run["results"][models[0]]]
    lines = [
        "# Model evaluation report",
        "",
        "This report is generated by `python -m evals.report` from the",
        "runs saved in `evals/runs/`. Do not edit it by hand.",
        "",
        f"**Latest run:** {run['run_date']}",
        "",
        "## What was compared",
        "",
        "| Model | Role in the project |",
        "|---|---|",
    ]
    for model in models:
        role = run.get("roles", {}).get(model, "")
        lines.append(f"| `{model}` | {cell(role)} |")
    lines += ["", "## Method", ""]
    lines += [f"- {item}" for item in run.get("method", [])]
    lines += [
        "",
        "## Result",
        "",
        "| Model | Cases passed | Model calls | Tokens |",
        "|---|---|---|---|",
    ]
    for model in models:
        summary = run["summary"][model]
        lines.append(
            f"| `{short(model)}` | {summary['passed']} of "
            f"{summary['cases']} | {summary['model_calls']} | "
            f"{summary['tokens']:,} |"
        )
    if run.get("decision"):
        lines += ["", f"**Decision:** {run['decision']}"]

    lines += ["", "## Where the models diverged", ""]
    diverged = diverging_cases(run)
    if not diverged:
        lines.append("The models agreed on every case.")
    for name in diverged:
        case = by_name.get(name, {})
        lines += [
            f"### {name}",
            "",
            f"- **Question:** {cell(case.get('question', ''))}",
            f"- **Expected:** {cell(case.get('expect', ''))}",
        ]
        for model in models:
            row = rows[model][name]
            lines.append(
                f"- **`{short(model)}`:** {mark(row)}, status "
                f"`{row['status']}`. Answer: \"{cell(row['answer'])}\""
            )
        lines.append("")

    lines += ["## Findings", ""]
    for finding in run.get("findings", []):
        lines += [f"**{finding['title']}** {finding['detail']}", ""]

    lines += ["## Every case", ""]
    header = "| Case | Question | Expected |"
    divider = "|---|---|---|"
    for model in models:
        header += f" `{short(model)}` |"
        divider += "---|"
    lines += [header, divider]
    for name in names:
        case = by_name.get(name, {})
        line = (f"| {cell(name)} | {cell(case.get('question', ''))} | "
                f"{cell(case.get('expect', ''))} |")
        for model in models:
            line += f" {mark(rows[model][name])} |"
        lines.append(line)

    lines += ["", "## Answers given", ""]
    for name in names:
        lines.append(f"**{name}**")
        lines.append("")
        for model in models:
            row = rows[model][name]
            lines.append(f"- `{short(model)}` ({row['seconds']}s): "
                         f"\"{cell(row['answer'])}\"")
        lines.append("")

    for title, key in [("Limits of this evaluation", "limitations"),
                       ("Corrections made to the raw results", "notes"),
                       ("Earlier informal comparison", "background")]:
        if run.get(key):
            lines += [f"## {title}", ""]
            lines += [f"- {item}" for item in run[key]]
            lines.append("")

    lines += render_retrieval(list(retrieval_runs))
    lines += [
        "## Model run log",
        "",
        "| Date | Models | Result |",
        "|---|---|---|",
    ]
    for past in runs:
        result = "; ".join(
            f"{short(model)} {summary['passed']}/{summary['cases']}"
            for model, summary in past["summary"].items()
        )
        compared = ", ".join(short(model) for model in past["results"])
        lines.append(f"| {past['run_date']} | {compared} | {result} |")
    lines += [
        "",
        "## Running it again",
        "",
        "```",
        "python -m evals.compare_models     # models: real model calls",
        "python -m evals.retrieval_metrics  # retrieval: no model calls",
        "python -m evals.report             # rebuild this report",
        "```",
        "",
        "A new run is saved beside the earlier ones, so results can be",
        "compared over time.",
    ]
    return "\n".join(lines) + "\n"


def main():
    """Write the report for the saved runs."""
    runs = load_runs()
    if not runs:
        raise SystemExit("No runs found in evals/runs/.")
    cases = build_cases(total_drivers=0, expiring_2027=0)
    retrieval_runs = load_runs(RETRIEVAL_RUNS_FOLDER)
    REPORT_FILE.write_text(render(runs, cases, retrieval_runs),
                           encoding="utf-8", newline="\n")
    print(f"Wrote {REPORT_FILE.name} from {len(runs)} model run(s) and "
          f"{len(retrieval_runs)} retrieval run(s).")


if __name__ == "__main__":
    main()
