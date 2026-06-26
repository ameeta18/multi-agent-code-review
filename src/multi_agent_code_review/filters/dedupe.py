"""Filter: remove duplicate findings on overlapping line ranges.

When two findings target the same file and their line ranges overlap, they are
treated as the same issue and we keep only the most severe (ties: the one seen
first). This collapses the common case of one problem being reported twice.

NOTE: The dedupe key is (file + overlapping line range + category): two findings are
the same issue only if they target the same file, overlap in lines, and come
from the same specialist. Different specialists flagging the same lines are
kept separately, since they raise different concerns.
"""

from multi_agent_code_review.schemas import Finding


def _overlaps(a: Finding, b: Finding) -> bool:
    return a.line_start <= b.line_end and b.line_start <= a.line_end


def dedupe_overlapping_findings(findings: list[Finding]) -> list[Finding]:
    """Collapse findings on the same file with overlapping line ranges."""
    survivors: list[int] = []  # indices into `findings` we keep

    for i, finding in enumerate(findings):
        merged = False
        for j, keep_idx in enumerate(survivors):
            kept = findings[keep_idx]
            if (
                kept.file == finding.file
                and kept.category == finding.category
                and _overlaps(kept, finding)
                ):
                # Same location: keep whichever is more severe.
                if finding.severity.rank < kept.severity.rank:
                    survivors[j] = i  # new one is more severe; replace
                merged = True
                break
        if not merged:
            survivors.append(i)

    return [findings[i] for i in survivors]