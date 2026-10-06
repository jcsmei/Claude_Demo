"""Compare language models on the same questions, data and prompts.

Run with `python -m evals.compare_models` from the project folder.

Every case states, before the run, the tool that should answer, the
status the answer should have, and a check on its text.  Each model is
put through the full decision flow, so the model is the only thing
that differs.  Results are printed and saved to `evals/results.json`.

This makes real model calls: about 14,000 tokens per model.  It is
therefore run by hand, and is not part of the automated tests.
"""

import json
import os
import sys
import time
from datetime import date
from pathlib import Path

import groq
from groq import Groq

sys.path.insert(0, str(Path(__file__).parent.parent))

import chat  # noqa: E402
import llm  # noqa: E402
import tools  # noqa: E402
from rag import DATA_FOLDER  # noqa: E402
from store import add_documents, get_collection  # noqa: E402

MODELS = ["openai/gpt-oss-20b", "openai/gpt-oss-120b"]
RESULTS_FILE = Path(__file__).parent / "results.json"
RETRY_SECONDS = 15
MAX_RETRIES = 8
MCP_HISTORY = [
    {"role": "user",
     "content": "what can you tell me about MCP in this project?"},
    {"role": "assistant",
     "content": ("MCP is the Model Context Protocol. This project runs "
                 "an MCP server named rag-demo that offers tools.")},
]


def normalise(text):
    """Return `text` in lower case with every run of spaces made one.

    Models sometimes write special spaces, such as the non-breaking
    space, which look identical but would make a plain comparison
    fail.
    """
    return " ".join(text.lower().split())


def contains(*phrases):
    """Return a check that passes if the answer has every phrase."""
    def check(answer):
        text = normalise(answer)
        return all(normalise(phrase) in text for phrase in phrases)
    return check


def contains_any(*phrases):
    """Return a check that passes if the answer has any phrase."""
    def check(answer):
        text = normalise(answer)
        return any(normalise(phrase) in text for phrase in phrases)
    return check


def excludes(phrase):
    """Return a check that passes if the answer lacks the phrase."""
    def check(answer):
        return normalise(phrase) not in normalise(answer)
    return check


def contains_number(number):
    """Return a check that passes if the answer states `number`.

    Separators such as commas and spaces inside the number are
    ignored, so 180521 matches "180,521".
    """
    def check(answer):
        digits = "".join(ch for ch in answer
                         if ch.isdigit() or ch.isalpha())
        return str(number) in digits
    return check


def score(case, result):
    """Return True if `result` meets every expectation of `case`."""
    return (result["tool"] == case["tool"]
            and result["status"] == case["status"]
            and bool(case["check"](result["answer"])))


def build_cases(total_drivers, expiring_2027):
    """Return the cases; the two totals come from the live data."""
    def case(name, question, tool, status, check, history=None):
        return {"name": name, "question": question, "tool": tool,
                "status": status, "check": check, "history": history}
    return [
        case("list tools", "What tools does the MCP server have?",
             "documents", "answered",
             contains("search_documents", "query_license_data")),
        case("fact: years",
             "How many years of experience does Jack have?",
             "documents", "answered", contains_any("9", "nine")),
        case("fact: codename", "What is the project's codename?",
             "documents", "answered", contains("Blue Heron")),
        case("concept",
             "What is the difference between the knowledge base and "
             "the index?",
             "documents", "answered",
             contains_any("rebuil", "source of truth")),
        case("abbreviation", "What does MCP stand for?",
             "documents", "answered", contains("Model Context Protocol")),
        case("refuse: off topic", "What is the capital of France?",
             "documents", "not_covered", excludes("Paris")),
        case("greeting", "hi", "documents", "unclear",
             lambda answer: True),
        case("follow-up", "what tools does it have?",
             "documents", "answered", contains("search_documents"),
             history=MCP_HISTORY),
        case("route: github", "What changed in the code most recently?",
             "github", "answered", lambda answer: len(answer) > 20),
        case("route: sql",
             "How many active medallion taxi drivers are there in "
             "New York?",
             "nyc_data", "answered", contains_number(total_drivers)),
        case("sql filter",
             "How many medallion taxi driver licenses expire in 2027?",
             "nyc_data", "answered", contains_number(expiring_2027)),
    ]


class Recorder:
    """A Groq client that uses one main model and records its usage.

    Calls meant for the project's default model are sent to `model`
    instead.  Calls to any other model, such as the screening
    classifier, pass through and are not counted.
    """

    def __init__(self, model):
        self.model = model
        self.real = Groq()
        self.tokens = 0
        self.calls = 0
        self.chat = self
        self.completions = self

    def create(self, **kwargs):
        counted = kwargs["model"] == llm.DEFAULT_MODEL
        if counted:
            kwargs["model"] = self.model
        for _ in range(MAX_RETRIES):
            try:
                response = self.real.chat.completions.create(**kwargs)
                break
            except groq.RateLimitError:
                time.sleep(RETRY_SECONDS)
        else:
            raise SystemExit(f"{self.model} is still rate limited")
        if counted:
            self.calls += 1
            self.tokens += response.usage.total_tokens
        return response


def run_case(case, collection, client):
    """Run one case with one model; return a row for the results."""
    started = time.perf_counter()
    try:
        result = chat.respond(case["question"], collection,
                              history=case["history"], client=client)
    except Exception as error:
        return {"case": case["name"], "tool": "-", "status": "error",
                "pass": False, "seconds": 0.0,
                "answer": f"{type(error).__name__}: {error}"[:200]}
    return {"case": case["name"], "tool": result["tool"],
            "status": result["status"], "pass": score(case, result),
            "seconds": round(time.perf_counter() - started, 1),
            "answer": " ".join(result["answer"].split())[:200]}


def main():
    """Run every case on every model, then print and save the results."""
    # Measure each model alone, and the documents path without the web.
    llm.FALLBACK_MODEL = ""
    tools.web_search_available = lambda: False

    collection = get_collection()
    add_documents(collection, DATA_FOLDER)
    rows = tools.license_counts()["rows"]
    cases = build_cases(
        total_drivers=sum(row[2] for row in rows),
        expiring_2027=sum(row[2] for row in rows if row[1] == 2027),
    )
    clients = {model: Recorder(model) for model in MODELS}
    results = {model: [] for model in MODELS}
    for case in cases:
        for model in MODELS:
            row = run_case(case, collection, clients[model])
            results[model].append(row)
            print(f"{'PASS' if row['pass'] else 'FAIL'} | "
                  f"{model.split('/')[-1]:<12} | {row['case']:<18} | "
                  f"{row['seconds']:>4}s | {row['answer'][:90]}",
                  flush=True)

    summary = {}
    for model in MODELS:
        timed = [row["seconds"] for row in results[model]]
        summary[model] = {
            "passed": sum(row["pass"] for row in results[model]),
            "cases": len(cases),
            "average_seconds": round(sum(timed) / len(timed), 1),
            "model_calls": clients[model].calls,
            "tokens": clients[model].tokens,
        }
        print(f"{model}: {summary[model]}")
    RESULTS_FILE.write_text(
        json.dumps({"run_date": date.today().isoformat(),
                    "summary": summary, "results": results}, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print(f"Saved to {os.path.relpath(RESULTS_FILE)}")


if __name__ == "__main__":
    main()
