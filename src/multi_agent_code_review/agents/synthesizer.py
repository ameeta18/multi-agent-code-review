"""Synthesizer: turn filtered specialist findings into one PR comment.

A single LLM call decides which findings matter most and writes a short summary;
the markdown itself is rendered deterministically from the original Finding
objects. The model can only *select and order* findings by index — it cannot
invent findings or alter their file, line, severity, or text, because those are
read back from the validated Finding objects, not from the model's output.
"""

from google import genai
from pydantic import BaseModel

from multi_agent_code_review.llm_client import generate_structured
from multi_agent_code_review.schemas import Finding

MAX_FINDINGS = 7

SYNTHESIZER_SYSTEM_PROMPT = """\
You are the lead reviewer. You are given a numbered list of validated findings
from specialist reviewers, plus the pull request diff for context.

Your job:
- Decide which findings are worth surfacing in the final review, most important first.
- Prioritize by severity and genuine impact.
- Write a short (one or two sentence) summary of the review.

Return JSON with:
- "summary": your short summary.
- "finding_indices": indices (from the numbered list) of findings to include,
  ordered most important first.

Rules:
- Only use indices from the numbered list. Never invent findings.
- Do not restate file names, line numbers, or severities; those are handled separately.
"""


class SynthesisPlan(BaseModel):
    """What the synthesizer LLM returns: a summary and an ordering of findings."""

    summary: str
    finding_indices: list[int]


def _select(plan: SynthesisPlan, findings: list[Finding]) -> list[Finding]:
    """Resolve indices into findings: in-range, de-duplicated, capped."""
    seen: set[int] = set()
    selected: list[Finding] = []
    for i in plan.finding_indices:
        if 0 <= i < len(findings) and i not in seen:
            seen.add(i)
            selected.append(findings[i])
        if len(selected) >= MAX_FINDINGS:
            break
    return selected


def render_comment(summary: str, findings: list[Finding]) -> str:
    """Render the final PR comment markdown deterministically from findings."""
    lines = ["## Automated code review", "", summary, ""]
    if not findings:
        return "\n".join(lines).rstrip() + "\n"
    lines += ["### Findings", ""]
    for n, f in enumerate(findings, start=1):
        sev = f.severity.value.upper()
        cat = f.category.value if f.category else "general"
        lines.append(
            f"{n}. **[{sev}]** {f.title} — `{f.file}:{f.line_start}-{f.line_end}` ({cat})"
        )
        lines.append(f"   {f.explanation}")
        if f.suggested_fix:
            lines.append(f"   *Suggested fix:* {f.suggested_fix}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def synthesize(
    *, client: genai.Client, model: str, diff: str, findings: list[Finding]
) -> str:
    """Produce the final PR comment markdown from filtered findings."""
    if not findings:
        return render_comment("No significant issues found.", [])

    numbered = "\n".join(
        f"{i}: [{f.severity.value}] {f.file}:{f.line_start}-{f.line_end} "
        f"({f.category.value if f.category else 'general'}) {f.title} — {f.explanation}"
        for i, f in enumerate(findings)
    )
    user_content = f"FINDINGS:\n{numbered}\n\nDIFF:\n{diff}"

    plan = generate_structured(
        client=client,
        model=model,
        system_prompt=SYNTHESIZER_SYSTEM_PROMPT,
        user_content=user_content,
        schema=SynthesisPlan,
    )
    return render_comment(plan.summary, _select(plan, findings))