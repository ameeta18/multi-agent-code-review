"""The deterministic filter pipeline.

Specialist findings pass through these pure filters, in this fixed order,
before the synthesizer ever sees them. The order is explicit and intentional:

1. drop findings outside the diff   (only review changed code)
2. drop placeholder findings        (remove schema-valid but empty findings)
3. dedupe overlapping findings      (collapse the same issue reported twice)
4. cap findings per file            (limit noise on any one file)

Schema validation and the severity enum are enforced earlier, when raw model
output is parsed into Finding objects, so they are not repeated here.
"""

from multi_agent_code_review.filters.cap import cap_findings_per_file
from multi_agent_code_review.filters.dedupe import dedupe_overlapping_findings
from multi_agent_code_review.filters.placeholder import drop_placeholder_findings
from multi_agent_code_review.filters.scope import drop_findings_outside_diff
from multi_agent_code_review.schemas import Finding


def apply_filters(
    findings: list[Finding],
    *,
    diff: str,
    line_tolerance: int = 2,
    max_per_file: int = 5,
) -> list[Finding]:
    """Run every deterministic filter in its fixed order."""
    findings = drop_findings_outside_diff(
        findings, diff=diff, line_tolerance=line_tolerance
    )
    findings = drop_placeholder_findings(findings)
    findings = dedupe_overlapping_findings(findings)
    findings = cap_findings_per_file(findings, max_per_file=max_per_file)
    return findings