from multi_agent_code_review.filters.placeholder import (
    drop_placeholder_findings,
    is_substantive,
)
from multi_agent_code_review.schemas import Finding, Severity


def _f(*, file="auth.py", title="SQL injection",
       explanation="User input is concatenated directly into a SQL query.") -> Finding:
    return Finding(
        severity=Severity.HIGH, file=file, line_start=1, line_end=1,
        title=title, explanation=explanation, suggested_fix=None,
    )


def test_real_finding_is_kept():
    assert is_substantive(_f()) is True


def test_placeholder_title_dropped():
    assert is_substantive(_f(title="N/A")) is False


def test_placeholder_file_dropped():
    assert is_substantive(_f(file="unknown")) is False


def test_placeholder_explanation_dropped():
    assert is_substantive(_f(explanation="none")) is False


def test_too_short_explanation_dropped():
    assert is_substantive(_f(explanation="bad")) is False


def test_placeholder_match_is_case_insensitive():
    assert is_substantive(_f(title="TBD")) is False


def test_filter_removes_only_placeholders():
    findings = [_f(), _f(title="N/A"), _f(), _f(explanation="todo")]
    kept = drop_placeholder_findings(findings)
    assert len(kept) == 2