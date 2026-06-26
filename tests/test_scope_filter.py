import pytest

from multi_agent_code_review.filters.scope import drop_findings_outside_diff
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


def _f(file, start, end=None):
    end = start if end is None else end
    return Finding(
        severity=Severity.HIGH, file=file, line_start=start, line_end=end,
        title="t", explanation="some explanation text", suggested_fix=None,
    )


def test_finding_inside_diff_is_kept():
    assert len(drop_findings_outside_diff([_f("src/auth.py", 3)], diff=DIFF)) == 1


def test_finding_in_file_not_in_diff_is_dropped():
    assert drop_findings_outside_diff([_f("other.py", 3)], diff=DIFF) == []


def test_finding_far_outside_touched_lines_is_dropped():
    assert drop_findings_outside_diff([_f("src/auth.py", 50)], diff=DIFF) == []


def test_off_by_one_within_tolerance_is_kept():
    # touched lines are 2-4; line 6 is within tolerance 2 of line 4
    assert len(drop_findings_outside_diff([_f("src/auth.py", 6)], diff=DIFF)) == 1


def test_abbreviated_path_still_matches():
    # model wrote "auth.py"; diff file is "src/auth.py"
    assert len(drop_findings_outside_diff([_f("auth.py", 3)], diff=DIFF)) == 1


def test_same_filename_different_directory_not_matched():
    assert drop_findings_outside_diff([_f("lib/auth.py", 3)], diff=DIFF) == []


def test_negative_tolerance_raises():
    with pytest.raises(ValueError):
        drop_findings_outside_diff([], diff=DIFF, line_tolerance=-1)