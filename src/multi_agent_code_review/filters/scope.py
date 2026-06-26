"""Filter: drop findings that fall outside the diff.

Enforces a locked rule: the review only comments on code the PR changed. A
finding is kept only if its file appears in the diff and its line range lands
on (or near) a line the diff added.

Two deliberate tolerances stop us from dropping *valid* findings over trivial
LLM imprecision:
- file paths match on trailing path segments, so "auth.py" matches
  "src/auth.py" (the model often abbreviates paths)
- line numbers match within a small tolerance, so an off-by-one in the model's
  reported line doesn't discard a real finding
Both are knobs we tune against real eval data in Week 6.
"""

from multi_agent_code_review.diff import added_lines_by_file
from multi_agent_code_review.schemas import Finding


def _segments(path: str) -> list[str]:
    return [p for p in path.replace("\\", "/").split("/") if p and p != "."]


def _paths_match(finding_path: str, diff_path: str) -> bool:
    """True if the two paths share a trailing run of path segments."""
    a, b = _segments(finding_path), _segments(diff_path)
    if not a or not b:
        return False
    n = min(len(a), len(b))
    return a[-n:] == b[-n:]


def _touched_lines_for(
    finding_path: str, touched: dict[str, set[int]]
) -> set[int] | None:
    for diff_path, lines in touched.items():
        if _paths_match(finding_path, diff_path):
            return lines
    return None


def drop_findings_outside_diff(
    findings: list[Finding], *, diff: str, line_tolerance: int = 2
) -> list[Finding]:
    """Keep only findings whose file and lines are part of the diff."""
    if line_tolerance < 0:
        raise ValueError("line_tolerance must be non-negative")

    touched = added_lines_by_file(diff)

    kept: list[Finding] = []
    for finding in findings:
        lines = _touched_lines_for(finding.file, touched)
        if lines is None:
            continue  # file not in the diff at all
        low = finding.line_start - line_tolerance
        high = finding.line_end + line_tolerance
        if any(low <= ln <= high for ln in lines):
            kept.append(finding)
    return kept