"""Thin evaluation pass: run the review graph over every labeled case and dump
the raw bot findings next to the human labels .


"""

import json
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from anthropic import Anthropic
from openai import OpenAI
from multi_agent_code_review.evaluation.store import load_all_cases
from multi_agent_code_review.graph import build_graph

load_dotenv()

# Provider switch for the Week 7 benchmark. Flip PROVIDER to run each provider;
# each writes to its own results file so runs don't overwrite each other.
PROVIDER = "openai"  # "gemini", "anthropic", or "openai"

if PROVIDER == "anthropic":
    SPECIALIST_MODEL = "claude-haiku-4-5"
    SYNTHESIZER_MODEL = "claude-haiku-4-5"
    RESULTS_FILENAME = "raw_run_anthropic.json"
elif PROVIDER == "openai":
    SPECIALIST_MODEL = "gpt-5.4-mini"
    SYNTHESIZER_MODEL = "gpt-5.4-mini"
    RESULTS_FILENAME = "raw_run_openai.json"
else:
    SPECIALIST_MODEL = "gemini-2.5-flash"
    SYNTHESIZER_MODEL = "gemini-2.5-flash"
    RESULTS_FILENAME = "raw_run.json"

RESULTS_DIR = Path("eval/results")

RESULTS_DIR = Path("eval/results")

# Gemini returns transient 503 ("model is currently experiencing high demand")
# under load. Those are server-side and retryable — they must not punch holes in
# the eval set. We retry with exponential backoff. Substring-matched on the error
# text so we only retry the genuinely-transient ones, not real bugs.
MAX_RETRIES = 4
BASE_BACKOFF_SECONDS = 5
TRANSIENT_MARKERS = ("503", "UNAVAILABLE", "high demand", "429", "RESOURCE_EXHAUSTED")


def _is_transient(exc: Exception) -> bool:
    text = str(exc)
    return any(marker in text for marker in TRANSIENT_MARKERS)


def invoke_with_retry(graph, diff: str):
    """Invoke the graph, retrying transient 503/429 errors with backoff.

    Returns (findings, error_string). error_string is None on success, or the
    final exception text if all retries were exhausted (or the error was not
    transient, in which case we don't retry).
    """
    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = graph.invoke({"diff": diff})
            return result.get("filtered", []), None
        except Exception as e:  # noqa: BLE001 - classify, then retry or give up
            last_exc = e
            if not _is_transient(e) or attempt == MAX_RETRIES:
                return [], f"{type(e).__name__}: {e}"
            backoff = BASE_BACKOFF_SECONDS * (2 ** (attempt - 1))
            print(f"(transient error, retry {attempt}/{MAX_RETRIES - 1} in {backoff}s) ", end="", flush=True)
            time.sleep(backoff)
    # Unreachable, but keeps the type checker happy.
    return [], f"{type(last_exc).__name__}: {last_exc}"


def _label_to_dict(issue) -> dict:
    """Flatten a LabeledIssue for the dump (category may be None)."""
    return {
        "file": issue.file,
        "line_start": issue.line_start,
        "line_end": issue.line_end,
        "importance": issue.importance.value,
        "category": issue.category.value if issue.category else None,
        "description": issue.description,
    }


def _finding_to_dict(f) -> dict:
    """Flatten a bot Finding for the dump."""
    return {
        "file": f.file,
        "line_start": f.line_start,
        "line_end": f.line_end,
        "severity": f.severity.value,
        "category": f.category.value if f.category else None,
        "title": f.title,
        "explanation": f.explanation,
    }


def main() -> None:
    cases = load_all_cases()
    if not cases:
        print("No cases found in eval/cases/. Nothing to run.")
        raise SystemExit(1)

    n_labels = sum(len(c.labeled_issues) for c in cases)
    n_calls = len(cases) * 4
    print(f"Loaded {len(cases)} cases, {n_labels} labeled issues.")
    print(
        f"About to make ~{n_calls} Gemini calls "
        f"(~4 per case) on {SPECIALIST_MODEL}."
    )
    print("Estimated cost: roughly $0.10 total. Proceeding\n")

    if PROVIDER == "anthropic":
        client = Anthropic()
    elif PROVIDER == "openai":
        client = OpenAI()
    else:
        client = genai.Client()
    graph = build_graph(
        client=client,
        specialist_model=SPECIALIST_MODEL,
        synthesizer_model=SYNTHESIZER_MODEL,
    )

    records = []
    total_start = time.perf_counter()

    for i, case in enumerate(cases, 1):
        print(f"[{i}/{len(cases)}] {case.case_id} ", end=" ", flush=True)
        case_start = time.perf_counter()
        findings, error = invoke_with_retry(graph, case.diff)
        elapsed = time.perf_counter() - case_start

        records.append(
            {
                "case_id": case.case_id,
                "repo": case.repo,
                "pr_number": case.pr_number,
                "n_labels": len(case.labeled_issues),
                "n_findings": len(findings),
                "latency_seconds": round(elapsed, 2),
                "error": error,
                "labels": [_label_to_dict(li) for li in case.labeled_issues],
                "findings": [_finding_to_dict(f) for f in findings],
            }
        )

        if error:
            print(f"ERROR ({error}) [{elapsed:.1f}s]")
        else:
            print(f"{len(findings)} findings vs {len(case.labeled_issues)} labels [{elapsed:.1f}s]")

    total_elapsed = time.perf_counter() - total_start

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / RESULTS_FILENAME
    out_path.write_text(
        json.dumps(
            {
                "meta": {
                    "n_cases": len(cases),
                    "n_labels": n_labels,
                    "specialist_model": SPECIALIST_MODEL,
                    "synthesizer_model": SYNTHESIZER_MODEL,
                    "total_seconds": round(total_elapsed, 1),
                    "n_errors": sum(1 for r in records if r["error"]),
                },
                "cases": records,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    # Quick console summary so you don't have to open the file to get the shape.
    total_findings = sum(r["n_findings"] for r in records)
    empties = [r for r in records if r["n_labels"] == 0]
    bot_on_empties = sum(r["n_findings"] for r in empties)

    print("\n" + "=" * 60)
    print(f"Done in {total_elapsed:.1f}s. Wrote {out_path}")
    print(f"Total bot findings across all cases: {total_findings}")
    print(f"Total human labels: {n_labels}")
    print(
        f"On the {len(empties)} empty (precision) cases, the bot emitted "
        f"{bot_on_empties} findings "
        f"({'clean!' if bot_on_empties == 0 else 'these are false-positive candidates'})."
    )
    n_err = sum(1 for r in records if r["error"])
    if n_err:
        print(f"WARNING: {n_err} case(s) errored — see 'error' fields in the JSON.")
    


if __name__ == "__main__":
    main()