from multi_agent_code_review.filters.pipeline import apply_filters
from multi_agent_code_review.schemas import Finding, Severity

DIFF = """\
diff --git a/src/auth.py b/src/auth.py
--- a/src/auth.py
+++ b/src/auth.py
@@ -1,2 +1,5 @@
 import os
+API_KEY = "secret"
+password = "hunter2"
+token = "abc"
 x = 1
"""
# added lines in src/auth.py: 2, 3, 4


def _f(file, start, end=None, *, severity=Severity.HIGH,
       title="Hardcoded secret", explanation="A credential is in source code."):
    end = start if end is None else end
    return Finding(
        severity=severity, file=file, line_start=start, line_end=end,
        title=title, explanation=explanation, suggested_fix=None,
    )


def test_pipeline_applies_all_filters():
    findings = [
        _f("src/auth.py", 3),                          # real -> kept
        _f("src/auth.py", 3, severity=Severity.LOW),   # overlaps -> deduped away
        _f("other.py", 3),                             # outside diff -> dropped
        _f("src/auth.py", 4, explanation="none"),      # placeholder -> dropped
    ]
    kept = apply_filters(findings, diff=DIFF)
    assert len(kept) == 1
    assert kept[0].file == "src/auth.py"
    assert kept[0].severity is Severity.HIGH  # dedupe kept the more severe


def test_pipeline_matches_manual_chain():
    from multi_agent_code_review.filters.cap import cap_findings_per_file
    from multi_agent_code_review.filters.dedupe import dedupe_overlapping_findings
    from multi_agent_code_review.filters.placeholder import drop_placeholder_findings
    from multi_agent_code_review.filters.scope import drop_findings_outside_diff

    findings = [_f("src/auth.py", 2), _f("src/auth.py", 4), _f("nope.py", 1)]

    manual = drop_findings_outside_diff(findings, diff=DIFF)
    manual = drop_placeholder_findings(manual)
    manual = dedupe_overlapping_findings(manual)
    manual = cap_findings_per_file(manual)

    assert apply_filters(findings, diff=DIFF) == manual


def test_empty_findings():
    assert apply_filters([], diff=DIFF) == []