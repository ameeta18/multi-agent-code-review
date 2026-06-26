import pytest

from multi_agent_code_review.filters.cap import cap_findings_per_file
from multi_agent_code_review.schemas import Finding, Severity


def _f(file: str, severity: Severity, line: int) -> Finding:
    return Finding(
        severity=severity, file=file, line_start=line, line_end=line,
        title="t", explanation="e", suggested_fix=None,
    )


def test_keeps_all_when_under_cap():
    findings = [_f("a.py", Severity.LOW, 1), _f("a.py", Severity.HIGH, 2)]
    assert cap_findings_per_file(findings, max_per_file=5) == findings


def test_caps_per_file_keeping_most_severe():
    findings = [
        _f("a.py", Severity.LOW, 1),
        _f("a.py", Severity.CRITICAL, 2),
        _f("a.py", Severity.MEDIUM, 3),
    ]
    kept = cap_findings_per_file(findings, max_per_file=2)
    severities = {f.severity for f in kept}
    assert len(kept) == 2
    assert Severity.CRITICAL in severities and Severity.MEDIUM in severities
    assert Severity.LOW not in severities


def test_cap_is_per_file_not_global():
    findings = [_f("a.py", Severity.HIGH, 1), _f("b.py", Severity.HIGH, 1),
                _f("c.py", Severity.HIGH, 1)]
    assert len(cap_findings_per_file(findings, max_per_file=1)) == 3


def test_preserves_original_order():
    findings = [_f("a.py", Severity.CRITICAL, 1), _f("a.py", Severity.HIGH, 2)]
    assert cap_findings_per_file(findings, max_per_file=2) == findings


def test_negative_cap_raises():
    with pytest.raises(ValueError):
        cap_findings_per_file([], max_per_file=-1)