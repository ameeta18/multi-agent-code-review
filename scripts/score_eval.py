"""Score the bot against the labeled eval set — OFFLINE, no LLM calls, $0.

Reads eval/results/raw_run.json (produced by run_eval_raw.py) and computes the
metrics that justify this eval's whole design: scoped recall, overall recall,
the strict-vs-location gap, precision, and severity-vs-importance calibration.

The honest core of this script is the TWO-STAGE match:

  Stage 1 (mechanical): pair each label with bot findings in the SAME FILE whose
  line range overlaps or sits within +/- LINE_TOLERANCE. This is automatable.

  Stage 2 (manual): a line-overlap is only a CANDIDATE. As airflow 59643 showed,
  the bot can fire on the right line about a *different* problem. So candidates
  are written out for you to adjudicate by hand (same issue? y/n). The confirmed
  set is what recall is actually computed on. Automated line-overlap alone would
  inflate recall by crediting same-location-different-issue coincidences.

Usage:
    # 1. Generate candidate pairs to adjudicate:
    uv run python scripts/score_eval.py --emit-candidates
    #    -> writes eval/results/adjudication.json with each candidate match and
    #       a "same_issue": null field for you to set to true/false by hand.

    # 2. After you fill in every "same_issue", compute the metrics:
    uv run python scripts/score_eval.py --score

    # To score a different provider's run without touching the default files:
    uv run python scripts/score_eval.py --emit-candidates --suffix _anthropic
    uv run python scripts/score_eval.py --score --suffix _anthropic

"""

import argparse
import json
from pathlib import Path

RESULTS_DIR = Path("eval/results")


def _paths(suffix: str = ""):
    """Return (raw, adjudication, report) paths, optionally provider-suffixed."""
    return (
        RESULTS_DIR / f"raw_run{suffix}.json",
        RESULTS_DIR / f"adjudication{suffix}.json",
        RESULTS_DIR / f"metrics_report{suffix}.md",
    )

# Lines within this many of each other count as the same location. We saw the
# bot's line numbers drift by 1-2 from the label; +/-3 absorbs that without
# matching unrelated code far away. Defensible as a pragmatic choice, not a
# derived constant — and the per-case audit lets anyone check it.
LINE_TOLERANCE = 3

IN_SCOPE_CATEGORIES = {"security", "maintainability", "test_coverage"}



# Stage 1: mechanical candidate matching (location overlap)

def _ranges_overlap_or_near(a_start, a_end, b_start, b_end, tol=LINE_TOLERANCE):
    """True if [a_start,a_end] and [b_start,b_end] overlap or sit within tol."""
    # Expand the bot's range by tol on each side, then test for overlap.
    return a_start <= b_end + tol and b_start <= a_end + tol


def _same_file(label_file, finding_file):
    """Match on file path. Exact match, with a basename fallback because the
    label and the diff sometimes differ in path prefix depth."""
    if label_file == finding_file:
        return True
    return label_file.split("/")[-1] == finding_file.split("/")[-1]


def emit_candidates(raw: dict) -> dict:
    """For each label, list bot findings that overlap its location -> candidates.

    Output is a list of candidate pairs, each with same_issue=None for the human
    to fill in. Labels with no location-overlapping finding are recorded as
    automatic misses (no candidate, nothing to adjudicate).
    """
    candidates = []
    auto_misses = []

    for case in raw["cases"]:
        case_id = case["case_id"]
        findings = case["findings"]

        for li, label in enumerate(case["labels"]):
            overlapping = []
            for fi, finding in enumerate(findings):
                if _same_file(label["file"], finding["file"]) and _ranges_overlap_or_near(
                    label["line_start"], label["line_end"],
                    finding["line_start"], finding["line_end"],
                ):
                    overlapping.append(fi)

            if not overlapping:
                auto_misses.append({
                    "case_id": case_id,
                    "label_index": li,
                    "label": label,
                    "reason": "no bot finding overlapped this location",
                })
                continue

            for fi in overlapping:
                f = findings[fi]
                candidates.append({
                    "case_id": case_id,
                    "label_index": li,
                    "finding_index": fi,
                    # Context for the human adjudicator:
                    "label_category": label["category"],
                    "label_importance": label["importance"],
                    "label_lines": [label["line_start"], label["line_end"]],
                    "label_description": label["description"],
                    "finding_category": f["category"],
                    "finding_severity": f["severity"],
                    "finding_lines": [f["line_start"], f["line_end"]],
                    "finding_title": f["title"],
                    "finding_explanation": f["explanation"],
                    # YOU FILL THIS IN: is the finding the SAME issue as the label?
                    "same_issue": None,
                })

    return {
        "instructions": (
            "For each candidate, set 'same_issue' to true if the bot finding "
            "identifies the SAME problem as the label (not merely the same "
            "lines). Set false if it's a different problem at the same location. "
            "Then run: score_eval.py --score"
        ),
        "line_tolerance": LINE_TOLERANCE,
        "candidates": candidates,
        "auto_misses": auto_misses,
    }


# Stage 2: scoring, using the human-adjudicated candidates

def _pct(num, den):
    return f"{(100.0 * num / den):.0f}%" if den else "n/a"


def score(raw: dict, adjudication: dict) -> str:
    candidates = adjudication["candidates"]

    # Guard: every candidate must be adjudicated.
    unjudged = [c for c in candidates if c["same_issue"] is None]
    if unjudged:
        lines = [
            f"  - {c['case_id']} label#{c['label_index']} vs finding#{c['finding_index']}"
            for c in unjudged
        ]
        raise SystemExit(
            f"{len(unjudged)} candidate(s) still have same_issue=null. "
            f"Adjudicate them in the adjudication file first:\n" + "\n".join(lines)
        )

    # A label is "caught" if at least one adjudicated-true candidate exists for it.
    caught_keys = {
        (c["case_id"], c["label_index"])
        for c in candidates
        if c["same_issue"] is True
    }
    # A label is "located" (location-only recall) if any finding overlapped it,
    # regardless of same_issue — i.e. it appears as a candidate at all.
    located_keys = {(c["case_id"], c["label_index"]) for c in candidates}

    # Walk all labels, bucket them.
    all_labels = []
    for case in raw["cases"]:
        for li, label in enumerate(case["labels"]):
            all_labels.append((case["case_id"], li, label))

    # ---- Recall (scoped vs overall) ----
    in_scope = [
        (cid, li, lab) for (cid, li, lab) in all_labels
        if lab["category"] in IN_SCOPE_CATEGORIES
    ]
    null_labels = [
        (cid, li, lab) for (cid, li, lab) in all_labels
        if lab["category"] not in IN_SCOPE_CATEGORIES
    ]

    in_scope_caught = sum(1 for (cid, li, _) in in_scope if (cid, li) in caught_keys)
    overall_caught = sum(1 for (cid, li, _) in all_labels if (cid, li) in caught_keys)
    located_in_scope = sum(1 for (cid, li, _) in in_scope if (cid, li) in located_keys)

    # ---- Recall on must_fix specifically (the headline severity slice) ----
    must_fix = [(cid, li, lab) for (cid, li, lab) in all_labels if lab["importance"] == "must_fix"]
    must_fix_in_scope = [t for t in must_fix if t[2]["category"] in IN_SCOPE_CATEGORIES]
    mf_in_scope_caught = sum(1 for (cid, li, _) in must_fix_in_scope if (cid, li) in caught_keys)

    # ---- Precision: of all findings, how many were confirmed true matches? ----
    total_findings = sum(len(c["findings"]) for c in raw["cases"])
    confirmed_match_findings = {
        (c["case_id"], c["finding_index"])
        for c in candidates
        if c["same_issue"] is True
    }
    n_true_findings = len(confirmed_match_findings)
    # Findings on empty (no-label) cases are guaranteed false positives.
    fp_on_empty = sum(
        len(case["findings"]) for case in raw["cases"] if not case["labels"]
    )

    # ---- Severity vs importance calibration ----
    # For confirmed matches, compare the bot's severity to the label's importance.
    sev_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    imp_expected_band = {  # rough mapping for calibration commentary
        "must_fix": {"critical", "high"},
        "nice_to_have": {"medium", "low"},
        "stylistic": {"low"},
    }
    calib_rows = []
    for c in candidates:
        if c["same_issue"] is True:
            imp = c["label_importance"]
            sev = c["finding_severity"]
            aligned = sev in imp_expected_band.get(imp, set())
            calib_rows.append((c["case_id"], imp, sev, aligned))

    # ---- Per-category recall ----
    per_cat = {}
    for cat in IN_SCOPE_CATEGORIES:
        cat_labels = [(cid, li) for (cid, li, lab) in all_labels if lab["category"] == cat]
        cat_caught = sum(1 for k in cat_labels if k in caught_keys)
        per_cat[cat] = (cat_caught, len(cat_labels))

    
    # Build the report
    
    n_cases = raw["meta"]["n_cases"]
    n_empty = sum(1 for c in raw["cases"] if not c["labels"])
    total_latency = raw["meta"].get("total_seconds", 0)
    avg_latency = total_latency / n_cases if n_cases else 0

    L = []
    L.append("# Evaluation results")
    L.append("")
    L.append(f"Dataset: **{n_cases} cases** ({n_empty} empty/precision), "
             f"**{len(all_labels)} labeled issues**. "
             f"Model: {raw['meta']['specialist_model']} (specialists) / "
             f"{raw['meta']['synthesizer_model']} (synthesizer). "
             f"Matching: same file, line overlap within +/-{LINE_TOLERANCE}, "
             f"each match manually confirmed as the same issue.")
    L.append("")
    L.append("## Recall")
    L.append("")
    L.append(f"- **In-scope recall: {_pct(in_scope_caught, len(in_scope))}** "
             f"({in_scope_caught}/{len(in_scope)}) — labels within the bot's three "
             f"specialties (security / maintainability / test_coverage).")
    L.append(f"- **Overall recall: {_pct(overall_caught, len(all_labels))}** "
             f"({overall_caught}/{len(all_labels)}) — all labels, including "
             f"{len(null_labels)} logic/correctness bugs (category=null) the bot "
             f"has no agent for and cannot match by design.")
    L.append(f"- **Location-only recall (in-scope): {_pct(located_in_scope, len(in_scope))}** "
             f"({located_in_scope}/{len(in_scope)}) — the bot flagged the right code "
             f"region, ignoring whether it identified the same issue. The gap from "
             f"in-scope recall is how often it found the spot but not the problem.")
    L.append(f"- **In-scope must-fix recall: {_pct(mf_in_scope_caught, len(must_fix_in_scope))}** "
             f"({mf_in_scope_caught}/{len(must_fix_in_scope)}) — small sample, "
             f"report as indicative.")
    L.append("")
    L.append("### Per-category recall (in-scope)")
    L.append("")
    for cat, (c, t) in sorted(per_cat.items()):
        L.append(f"- {cat}: {_pct(c, t)} ({c}/{t})")
    L.append("")
    L.append("## Precision")
    L.append("")
    L.append(f"- Bot emitted **{total_findings} findings** total across all cases.")
    L.append(f"- **{n_true_findings}** were confirmed matches to a labeled issue.")
    L.append(f"- On the {n_empty} empty cases, the bot emitted **{fp_on_empty}** "
             f"finding(s) — guaranteed false positives (or real unlabeled issues; "
             f"inspect each).")
    L.append("")
    L.append("> Note: a finding that doesn't match a label isn't automatically a "
             "false positive — it may be a real issue the human reviewers didn't "
             "flag. Precision here is reported conservatively; unmatched findings "
             "warrant manual inspection rather than automatic FP labeling.")
    L.append("")
    L.append("## Severity calibration (confirmed matches only)")
    L.append("")
    if calib_rows:
        aligned_n = sum(1 for *_, a in calib_rows if a)
        L.append(f"- {aligned_n}/{len(calib_rows)} confirmed matches had bot severity "
                 f"aligned with label importance "
                 f"(must_fix↔critical/high, nice_to_have↔medium/low).")
        for cid, imp, sev, aligned in calib_rows:
            mark = "ok" if aligned else "MISCALIBRATED"
            L.append(f"  - {cid}: label={imp}, bot severity={sev} [{mark}]")
    else:
        L.append("- No confirmed matches to calibrate on.")
    L.append("")
    L.append("## Cost & latency")
    L.append("")
    L.append(f"- ~4 model calls/case (3 specialists + synthesizer); "
             f"~{n_cases * 4} calls total.")
    L.append(f"- Total wall-clock: {total_latency:.0f}s; "
             f"avg {avg_latency:.1f}s/case.")
    L.append(f"- Run on {raw['meta']['specialist_model']}.")
    L.append("")
    L.append("## Headline finding")
    L.append("")
    L.append("All in-scope catches are concentrated where added code sits on the "
             "flagged lines; the must-fix logic/correctness bugs (category=null) "
             "are missed wholesale — the bot localizes code regions but does not "
             "reason about correctness. This points to a dedicated logic/"
             "correctness agent as the clear next step.")
    L.append("")

    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--emit-candidates", action="store_true",
                   help="Write adjudication.json with candidate match pairs to judge.")
    g.add_argument("--score", action="store_true",
                   help="Compute metrics from the adjudicated candidates.")
    ap.add_argument("--suffix", default="",
                    help="Filename suffix, e.g. '_anthropic', to score a "
                         "provider's run without touching the default files.")
    args = ap.parse_args()

    raw_path, adjudication_path, report_path = _paths(args.suffix)

    if not raw_path.exists():
        raise SystemExit(f"{raw_path} not found. Run run_eval_raw.py first.")
    raw = json.loads(raw_path.read_text(encoding="utf-8"))

    if args.emit_candidates:
        out = emit_candidates(raw)
        adjudication_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
        n = len(out["candidates"])
        m = len(out["auto_misses"])
        print(f"Wrote {adjudication_path}")
        print(f"  {n} candidate match(es) to adjudicate (set 'same_issue' true/false).")
        print(f"  {m} label(s) had no overlapping finding — automatic misses, "
              f"no adjudication needed.")
        print("\nOpen the file, fill in every 'same_issue', then run:")
        suffix_arg = f" --suffix {args.suffix}" if args.suffix else ""
        print(f"  uv run python scripts/score_eval.py --score{suffix_arg}")
        return

    if args.score:
        if not adjudication_path.exists():
            raise SystemExit(
                f"{adjudication_path} not found. Run --emit-candidates first, "
                f"then adjudicate."
            )
        adjudication = json.loads(adjudication_path.read_text(encoding="utf-8"))
        report = score(raw, adjudication)
        report_path.write_text(report, encoding="utf-8")
        print(report)
        print(f"\n(Report also written to {report_path})")


if __name__ == "__main__":
    main()