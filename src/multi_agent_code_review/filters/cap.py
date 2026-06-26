"""Filter: cap the number of findings per file.

A noisy agent can pile many low-value findings onto one file and drown the
review. We keep at most `max_per_file` per file, preferring the most severe,
and otherwise preserve the original order. Pure function, no side effects.
"""

from collections import defaultdict

from multi_agent_code_review.schemas import Finding


def cap_findings_per_file(
    findings: list[Finding], *, max_per_file: int = 5
) -> list[Finding]:
    """Keep at most `max_per_file` findings per file, most severe kept first."""
    if max_per_file < 0:
        raise ValueError("max_per_file must be non-negative")

    indices_by_file: dict[str, list[int]] = defaultdict(list)
    for i, finding in enumerate(findings):
        indices_by_file[finding.file].append(i)

    keep: set[int] = set()
    for indices in indices_by_file.values():
        ranked = sorted(indices, key=lambda i: findings[i].severity.rank)
        keep.update(ranked[:max_per_file])

    return [finding for i, finding in enumerate(findings) if i in keep]