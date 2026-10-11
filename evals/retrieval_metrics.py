"""Measure how well retrieval finds the passage that answers a question.

Run with `python -m evals.retrieval_metrics` from the project folder.

It uses the benchmark in `evals/retrieval_cases.py`: real questions,
each paired with text that only the right passage contains.  For
every question it finds the position of that passage in the search
results, then reports two standard measures:

- recall at k: the share of questions whose right passage is within
  the first k results;
- mean reciprocal rank: the average of 1 / position, so 1.0 means the
  right passage is always first.

It uses the real embedding model and makes no language model calls, so
it costs no tokens.  Each run is saved as a dated file in
`evals/retrieval_runs/`.
"""

import json
import os
import sys
import uuid
from datetime import date
from pathlib import Path

import chromadb

sys.path.insert(0, str(Path(__file__).parent.parent))

from evals.retrieval_cases import CASES, TOP_K  # noqa: E402
from rag import DATA_FOLDER  # noqa: E402
from store import add_documents, get_collection, search  # noqa: E402

RUNS_FOLDER = Path(__file__).parent / "retrieval_runs"
# How far down the results to look for the right passage.
DEPTH = 10
RECALL_AT = (1, 3, 5, 10)


def rank_of(expected, passages):
    """Return the 1-based position of the passage holding `expected`.

    Return None if no passage holds it.  Line breaks in a passage are
    treated as spaces, because the documents are wrapped.
    """
    for position, passage in enumerate(passages, start=1):
        if expected in " ".join(passage.split()):
            return position
    return None


def summarise(ranks):
    """Return recall at each k, and mean reciprocal rank, for `ranks`.

    A rank of None means the right passage was not found; it counts as
    a miss for recall and as zero for the reciprocal rank.
    """
    total = len(ranks)
    return {
        "questions": total,
        "recall": {
            str(k): sum(1 for rank in ranks if rank and rank <= k)
            for k in RECALL_AT
        },
        "mean_reciprocal_rank": round(
            sum(1 / rank for rank in ranks if rank) / total, 3
        ) if total else 0.0,
    }


def measure(collection, cases):
    """Return the summary for `cases`, with the questions not ranked first."""
    ranks = []
    not_first = []
    for question, expected in cases:
        passages = [result["text"]
                    for result in search(collection, question, k=DEPTH)]
        rank = rank_of(expected, passages)
        ranks.append(rank)
        if rank != 1:
            not_first.append({"question": question, "rank": rank})
    summary = summarise(ranks)
    summary["not_ranked_first"] = not_first
    return summary


def main():
    """Measure retrieval on the real documents and save the run."""
    collection = get_collection(client=chromadb.EphemeralClient(),
                                name=f"metrics-{uuid.uuid4().hex}")
    chunks = add_documents(collection, DATA_FOLDER)
    summary = measure(collection, CASES)
    run = {"run_date": date.today().isoformat(), "chunks": chunks,
           "retrieved_per_question": TOP_K, **summary}
    RUNS_FOLDER.mkdir(exist_ok=True)
    run_file = RUNS_FOLDER / f"{run['run_date']}.json"
    run_file.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")

    total = summary["questions"]
    for k, hits in summary["recall"].items():
        print(f"recall at {k}: {hits}/{total} = {100 * hits / total:.0f}%")
    print(f"mean reciprocal rank: {summary['mean_reciprocal_rank']}")
    print(f"Saved to {os.path.relpath(run_file)}. "
          "Now run: python -m evals.report")


if __name__ == "__main__":
    main()
