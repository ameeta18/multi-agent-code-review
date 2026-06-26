from multi_agent_code_review.filters.dedupe import dedupe_overlapping_findings
from multi_agent_code_review.schemas import Finding, Severity, Category 


def _f(file, start, end, severity=Severity.HIGH):
    return Finding(
        severity=severity, file=file, line_start=start, line_end=end,
        title="t", explanation="some explanation text", suggested_fix=None,
    )


def test_non_overlapping_kept():
    assert len(dedupe_overlapping_findings([_f("a.py", 1, 2), _f("a.py", 10, 12)])) == 2


def test_different_files_not_deduped():
    assert len(dedupe_overlapping_findings([_f("a.py", 1, 5), _f("b.py", 1, 5)])) == 2


def test_overlapping_same_file_deduped():
    assert len(dedupe_overlapping_findings([_f("a.py", 1, 5), _f("a.py", 3, 8)])) == 1


def test_adjacent_non_overlapping_kept():
    assert len(dedupe_overlapping_findings([_f("a.py", 1, 2), _f("a.py", 3, 4)])) == 2


def test_dedupe_keeps_most_severe():
    findings = [_f("a.py", 1, 5, Severity.LOW), _f("a.py", 2, 6, Severity.CRITICAL)]
    kept = dedupe_overlapping_findings(findings)
    assert len(kept) == 1 and kept[0].severity is Severity.CRITICAL


def test_tie_keeps_first():
    first, second = _f("a.py", 1, 5), _f("a.py", 2, 6)
    kept = dedupe_overlapping_findings([first, second])
    assert len(kept) == 1 and kept[0] is first
def test_same_lines_different_category_both_kept():
    a = _f("a.py", 1, 5).model_copy(update={"category": Category.SECURITY})
    b = _f("a.py", 2, 6).model_copy(update={"category": Category.MAINTAINABILITY})
    assert len(dedupe_overlapping_findings([a, b])) == 2