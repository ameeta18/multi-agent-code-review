"""Filter: drop placeholder / non-substantive findings.

A finding can pass schema validation and still be useless: a title of "N/A",
an explanation of "none", a file of "unknown". This filter removes findings
whose key text fields are placeholder tokens or too short to be meaningful.
Pure function, deterministic, no LLM judgement involved.
"""

from multi_agent_code_review.schemas import Finding

_PLACEHOLDER_TOKENS = {
    "", "n/a", "na", "none", "null", "unknown", "tbd", "todo", "-", ".",
}

_MIN_EXPLANATION_LEN = 15


def _is_placeholder(text: str) -> bool:
    return text.strip().lower() in _PLACEHOLDER_TOKENS


def is_substantive(finding: Finding) -> bool:
    """True if a finding looks like a real, usable report."""
    if _is_placeholder(finding.title):
        return False
    if _is_placeholder(finding.file):
        return False
    if _is_placeholder(finding.explanation):
        return False
    if len(finding.explanation.strip()) < _MIN_EXPLANATION_LEN:
        return False
    return True


def drop_placeholder_findings(findings: list[Finding]) -> list[Finding]:
    """Remove findings whose core fields are placeholders or too thin."""
    return [f for f in findings if is_substantive(f)]