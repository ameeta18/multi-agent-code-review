# Multi-Agent AI Code Review System

A GitHub Action that reviews pull requests using three parallel LLM specialist
agents, then benchmarks that system across Gemini, OpenAI, and Anthropic with a
hand-built, human-labeled evaluation harness.

The interesting part of this project is not the bot — it's the **evaluation**. It
measures a multi-agent reviewer honestly across three providers and produces a
specific, defensible finding: these models **localize** issues far more often than
they **diagnose** them, and this holds regardless of provider.

---

## What it does

On each pull request, the system:

1. Fans out the diff to three specialist agents in parallel — **security**,
   **maintainability**, and **test-coverage** — each returning structured findings
   (severity, category, file, line range, explanation).
2. Passes all findings through **deterministic filters** (drop anything outside the
   diff's changed lines; validate against a strict schema).
3. Runs a **synthesizer** that selects and orders the findings and writes one PR
   comment. The synthesizer can only *choose and rank* findings by index — it cannot
   invent findings or alter their file, line, or severity, because the final comment
   is rendered deterministically from the validated finding objects.

The whole pipeline is provider-agnostic: a single `llm_client` boundary dispatches
to Gemini, OpenAI, or Anthropic based on the client object passed in. Swapping
providers is a one-line change, which is what makes the benchmark possible.

---

## Architecture

diff
 │
 ├─► security agent ──────┐
 ├─► maintainability ─────┤   (parallel fan-out, LangGraph)
 └─► test-coverage ───────┤
                          ▼
                  deterministic filters   (scope + schema validation)
                          ▼
                     synthesizer           (select + order, render markdown)
                          ▼
                    one PR comment

- `llm_client.py` — the single boundary to all three providers. Structured output
  via each SDK's native schema-constrained parsing; every response is re-validated
  against the project's Pydantic schema (the provider constraint is a hint; local
  validation is the law).
- `graph.py` — the LangGraph definition (`build_graph`) wiring the fan-out,
  filters, and synthesizer.
- `schemas.py` — the shared `Finding` schema every agent conforms to.
- `agents/` — the three specialists and the synthesizer.
- `filters/` — scope and schema filters.
- `evaluation/` — the eval-case loader.

Built with LangGraph, Pydantic, and `uv`. Python 3.11.

---

## The evaluation

Existing code-review benchmarks score a generated comment by text similarity against
a single human comment. That doesn't fit a system that emits *structured, categorized*
findings, so the evaluation here is purpose-built.

**Dataset.** 21 real merged pull requests from apache/airflow, django/django,
encode/httpx, pydantic/pydantic, home-assistant/core, and scikit-learn/scikit-learn.
18 issues hand-labeled on two axes — **importance** (must_fix / nice_to_have /
stylistic) and **category** (security / maintainability / test_coverage / logic).
Six cases are deliberately empty (no reviewer-flagged issue) to measure false-positive
behavior. Every label is auditable against its source PR.

**Two oracles, by design.** Recall and precision are measured against *different*
ground truths, because a reviewer-comment label set is trustworthy for one but not
the other:

- **Recall** is scored against human labels — of the issues reviewers confirmed real,
  how many did the bot catch? Each candidate match is *manually confirmed to be the
  same issue*, not merely the same location — because the bot frequently fires on the
  right lines about a different problem, and automated line-overlap alone would inflate
  recall.
- **Precision** is scored *forward from the bot's output* on two axes — **factual**
  (is the finding technically correct?) and **actionable** (is it worth surfacing?).
  This avoids penalizing the bot for correctly finding real issues that human reviewers
  simply didn't comment on.

---

## Results

### Three-provider recall comparison

Same 21 cases, same prompts, same matcher. Cheap-tier model from each provider.

| Metric | Gemini 2.5 Flash | GPT-5.4-mini | Claude Haiku 4.5 |
|---|---|---|---|
| In-scope recall | 8% | 14% | 14% |
| Location-only recall | 31% | **71%** | 57% |
| In-scope must-fix recall | 0% | **33%** | 0% |
| Total findings emitted | 21 | 56 | 68 |
| Findings on empty cases | 1 | 11 | 15 |
| Latency / case | ~15s | **~5.7s** | ~11s |

The providers occupy **different operating points**: Gemini is the quietest and
highest-precision; Haiku the most sensitive; GPT-5.4-mini the fastest with the highest
localization and the only non-zero must-fix catch. They also have **different blind
spots** — GPT-5.4-mini uniquely caught a validation-test gap the others missed, while
missing a SQL-injection catch the others got. No single provider dominates.

### Two findings that hold across all three providers

1. **Localization, not diagnosis.** Every provider's location-only recall far exceeds
   its in-scope recall (71→14, 57→14, 31→8). The bots reliably find the right *region*
   but not the right *problem*.
2. **Merge-blocking logic bugs are missed almost entirely** (0/3, 0/3, 1/3). These are
   correctness bugs outside the three specialists' scope — no model overcomes this by
   being better at the existing lanes.

Because both findings are provider-independent, the conclusion is architectural: the
next step is a dedicated **logic/correctness agent**, not a better model or better
prompts.

### Forward-adjudicated precision (Gemini)

Scoring each finding on merits, independent of human labels:

- **Factual precision: 86%** — usually technically correct.
- **Actionable precision: 29%** — far less often worth surfacing.
- The **57-point gap** is the test-coverage agent's tendency to raise correct-but-trivial
  findings. The bot also surfaced **real issues human reviewers never flagged** — a
  credential-exposure path, a `ZeroDivisionError`, a null-password crash, and two code
  duplications — which a naive scorer would have counted as false positives.



---

## Running it

Requires Python 3.11, `uv`, and API keys for whichever provider(s) you want to run.

```bash
# install
uv sync

# set keys (any subset — the provider is selected in the runner)
# .env:
#   GEMINI_API_KEY=...
#   OPENAI_API_KEY=...
#   ANTHROPIC_API_KEY=...

# run the eval over all 21 cases (set PROVIDER in the script: gemini | openai | anthropic)
uv run python scripts/run_eval_raw.py

# score recall (two-stage: emit candidates, adjudicate by hand, then score)
uv run python scripts/score_eval.py --emit-candidates --suffix _openai
#   ... fill in each "same_issue" in eval/results/adjudication_openai.json ...
uv run python scripts/score_eval.py --score --suffix _openai

# forward-adjudicated precision (two-axis: factual + actionable)
uv run python scripts/adjudicate_findings.py --emit
#   ... fill in verdicts ...
uv run python scripts/adjudicate_findings.py --report
```

---

## Scope and next steps

This is a **methodology demonstration** (n=21, single annotator) rather than a
statistically powered benchmark — the value is in the two-oracle design and the
provider-independent findings, not in the absolute numbers. The design scales along
clear next steps:

- **A logic/correctness agent** — the direct implication of the must-fix misses and the
  v1→v2 null result. The merge-blocking issues live in this gap.
- **Full forward-adjudicated precision for OpenAI and Anthropic** — done for Gemini;
  the two-axis adjudication (factual + actionable) applied to the other two providers
  gives a complete cross-provider precision comparison.
- **Repository context via MCP** — giving agents on-demand access to full files and
  test suites (beyond the diff) so they can diagnose rather than pattern-match — directly
  targeting the localization-vs-diagnosis gap.
- **Verifiable oracles at scale** — regression-test (red→green) pairs, CVE fix pairs,
  and complexity metrics as automatic ground truth for categories humans don't gate on
  in review comments.

---

## Stack

LangGraph · Pydantic · uv · Python 3.11 · Gemini, OpenAI, and Anthropic APIs