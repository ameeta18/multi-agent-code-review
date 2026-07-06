"""Forward-adjudicated precision + disagreement analysis

Two-axis adjudication: each finding is judged on is_factually_correct (technically
true about the code) and is_actionable (worth surfacing to a developer). This yields
two precision metrics — Actionable precision ( how often useful) and
Factual precision ( how often correct)and the gap between them, which
captures the bot's prioritization behavior (correct-but-not-worth-raising findings).

Precision is scored FORWARD from bot output (judged on merits, independent of human
labels), avoiding the incompleteness bias where a backward scorer counts a real issue
humans didn't flag as a false positive.

Usage:
    uv run python scripts/adjudicate_findings.py --emit
    uv run python scripts/adjudicate_findings.py --report
"""

import argparse
import json
from pathlib import Path

RESULTS_DIR = Path("eval/results")
RAW_PATH = RESULTS_DIR / "raw_run.json"
VERDICTS_PATH = RESULTS_DIR / "finding_verdicts.json"
REPORT_PATH = RESULTS_DIR / "disagreement_report.md"

LINE_TOLERANCE = 3
IN_SCOPE_CATEGORIES = {"security", "maintainability", "test_coverage"}


def _overlap(a_s, a_e, b_s, b_e, tol=LINE_TOLERANCE):
    return a_s <= b_e + tol and b_s <= a_e + tol


def _same_file(lf, ff):
    return lf == ff or lf.split("/")[-1] == ff.split("/")[-1]


def _finding_matches_a_label(finding, labels):
    for label in labels:
        if _same_file(label["file"], finding["file"]) and _overlap(
            label["line_start"], label["line_end"],
            finding["line_start"], finding["line_end"],
        ):
            return label
    return None


def emit(raw):
    rows = []
    for case in raw["cases"]:
        for fi, f in enumerate(case["findings"]):
            overlapped = _finding_matches_a_label(f, case["labels"])
            rows.append({
                "case_id": case["case_id"],
                "finding_index": fi,
                "finding_category": f["category"],
                "finding_severity": f["severity"],
                "finding_lines": [f["line_start"], f["line_end"]],
                "finding_title": f["title"],
                "finding_explanation": f["explanation"],
                "overlaps_human_label": overlapped is not None,
                "overlapped_label_desc": overlapped["description"] if overlapped else None,
                "is_factually_correct": None,
                "is_actionable": None,
                "same_as_label": None,
            })
    return {
        "instructions": (
            "For EVERY finding set BOTH 'is_factually_correct' (true=technically true) "
            "and 'is_actionable' (true=worth surfacing, false=trivia/noise). A "
            "factually-false finding must have is_actionable=false. Where "
            "overlaps_human_label is true, also set 'same_as_label'; else leave null. "
            "Then run: adjudicate_findings.py --report"
        ),
        "line_tolerance": LINE_TOLERANCE,
        "findings": rows,
    }


def _pct(n, d):
    return f"{(100.0 * n / d):.0f}%" if d else "n/a"


def report(raw, verdicts):
    rows = verdicts["findings"]

    missing = [r for r in rows
               if r["is_factually_correct"] is None or r["is_actionable"] is None]
    if missing:
        lines = [f"  - {r['case_id']} finding#{r['finding_index']}: {r['finding_title']}"
                 for r in missing]
        raise SystemExit(
            f"{len(missing)} finding(s) missing is_factually_correct/is_actionable:\n"
            + "\n".join(lines))
    bad = [r for r in rows if not r["is_factually_correct"] and r["is_actionable"]]
    if bad:
        lines = [f"  - {r['case_id']} finding#{r['finding_index']}" for r in bad]
        raise SystemExit(
            "A factually-false finding cannot be actionable (set is_actionable=false):\n"
            + "\n".join(lines))
    missing_same = [r for r in rows
                    if r["overlaps_human_label"] and r["same_as_label"] is None]
    if missing_same:
        lines = [f"  - {r['case_id']} finding#{r['finding_index']}" for r in missing_same]
        raise SystemExit(
            f"{len(missing_same)} overlap a label but same_as_label=null:\n"
            + "\n".join(lines))

    total = len(rows)
    factual = [r for r in rows if r["is_factually_correct"]]
    actionable = [r for r in rows if r["is_actionable"]]

    bucket_a = [r for r in rows if r["overlaps_human_label"] and r["same_as_label"]]
    bucket_b = [r for r in rows if not (r["overlaps_human_label"] and r["same_as_label"])]
    b_actionable = [r for r in bucket_b if r["is_actionable"]]
    b_not = [r for r in bucket_b if not r["is_actionable"]]

    caught_labels = set()
    for c in raw["cases"]:
        for li, lab in enumerate(c["labels"]):
            for r in rows:
                if (r["case_id"] == c["case_id"] and r["overlaps_human_label"]
                        and r["same_as_label"]
                        and _same_file(lab["file"], c["findings"][r["finding_index"]]["file"])
                        and _overlap(lab["line_start"], lab["line_end"], *r["finding_lines"])):
                    caught_labels.add((c["case_id"], li))
    n_labels = sum(len(c["labels"]) for c in raw["cases"])
    n_caught = len(caught_labels)
    bucket_c = n_labels - n_caught

    sev = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for r in actionable:
        sev[r["finding_severity"]] = sev.get(r["finding_severity"], 0) + 1

    L = []
    L.append("# Forward-adjudicated precision & disagreement analysis")
    L.append("")
    L.append("Precision is scored forward from bot output, judged on merits "
             "independent of human labels — avoiding the incompleteness bias where a "
             "backward scorer counts real issues humans missed as false positives.")
    L.append("")
    L.append(f"- **Actionable precision: {_pct(len(actionable), total)}** "
             f"({len(actionable)}/{total}) — how often the bot produces a finding worth "
             f"surfacing (real defect or coverage gap that matters).")
    L.append(f"- **Factual precision: {_pct(len(factual), total)}** "
             f"({len(factual)}/{total}) — how often the bot is technically correct, "
             f"regardless of whether the point is worth raising.")
    L.append(f"- **Gap (factual − actionable): {len(factual) - len(actionable)}** — "
             f"technically-correct-but-not-worth-raising findings (the coverage agent's "
             f"over-firing on trivial gaps).")
    L.append("")
    L.append("## Severity of actionable findings")
    L.append("")
    L.append(f"- critical {sev['critical']}, high {sev['high']}, medium {sev['medium']}, "
             f"low {sev['low']} (of {len(actionable)}).")
    L.append("")
    L.append("## Three-bucket disagreement table")
    L.append("")
    L.append(f"**A. Bot caught + human labeled same issue: {len(bucket_a)}** — recall hits.")
    L.append(f"**B. Bot raised + human silent/different: {len(bucket_b)}** — split:")
    L.append(f"   - **{len(b_actionable)} actionable (value-add humans didn't flag)**")
    L.append(f"   - {len(b_not)} not actionable (trivia or false alarms)")
    L.append(f"**C. Human labeled + bot missed: {bucket_c}** — recall misses "
             f"(of {n_labels}, {n_caught} caught).")
    L.append("")
    L.append("## Headline: value beyond human review")
    L.append("")
    L.append(f"Of findings the bot raised that humans did NOT confirm, "
             f"**{len(b_actionable)} were actionable issues humans missed** — value a "
             f"backward scorer structurally counts as false positives.")
    L.append("")
    if b_actionable:
        for r in b_actionable:
            L.append(f"- **{r['case_id']}** [{r['finding_category']}/{r['finding_severity']}] "
                     f"{r['finding_title']}")
    else:
        L.append("- (none)")
    L.append("")
    L.append("## Definitions & caveats")
    L.append("")
    L.append("- Actionable = worth surfacing; Factual = technically correct. Both judged "
             "by the author against source (not an LLM, avoiding circularity). Single "
             "adjudicator. Coverage findings that are correct but low-severity count "
             "toward factual, not actionable precision. n=21, indicative.")
    L.append("")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--emit", action="store_true")
    g.add_argument("--report", action="store_true")
    args = ap.parse_args()

    if not RAW_PATH.exists():
        raise SystemExit(f"{RAW_PATH} not found. Run run_eval_raw.py first.")
    raw = json.loads(RAW_PATH.read_text(encoding="utf-8"))

    if args.emit:
        out = emit(raw)
        VERDICTS_PATH.write_text(json.dumps(out, indent=2), encoding="utf-8")
        n = len(out["findings"])
        n_overlap = sum(1 for r in out["findings"] if r["overlaps_human_label"])
        print(f"Wrote {VERDICTS_PATH}")
        print(f"  {n} findings to judge (set is_factually_correct AND is_actionable).")
        print(f"  {n_overlap} overlap a human label — also set same_as_label.")
        return

    if args.report:
        if not VERDICTS_PATH.exists():
            raise SystemExit(f"{VERDICTS_PATH} not found. Run --emit first.")
        verdicts = json.loads(VERDICTS_PATH.read_text(encoding="utf-8"))
        out = report(raw, verdicts)
        REPORT_PATH.write_text(out, encoding="utf-8")
        print(out)
        print(f"\n(Report  written to {REPORT_PATH})")


if __name__ == "__main__":
    main()