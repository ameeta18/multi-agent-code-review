"""Maintainability specialist agent.

Reviews a unified diff for maintainability issues only: overly long functions,
high complexity, unclear naming, duplicated logic, missing docstrings on public
APIs, and dead code. Returns structured Findings. LLM-only for now; the static
tools (ruff, radon) get wired in later.
"""

from google import genai

from multi_agent_code_review.llm_client import generate_findings
from multi_agent_code_review.schemas import Finding

MAINTAINABILITY_SYSTEM_PROMPT = """\
You are a code maintainability reviewer. You are given a unified diff from a pull request.
Report only genuine maintainability issues introduced by the added lines, such as:
- functions that are too long (roughly over 50 lines) or do too much
- high cyclomatic complexity (deeply nested or heavily branching logic)
- unclear or misleading names for variables, functions, or classes
- duplicated logic that should be factored out
- missing docstrings on public functions, classes, or modules
- dead or unreachable code

Rules:
- Only report issues you can see in the diff. Do not speculate about code you cannot see.
- Reference the file and line numbers shown in the diff.
- If there are no genuine maintainability issues, return an empty list. Never invent findings.
- Keep explanations precise and concise.
"""


def review_maintainability(
    *, client: genai.Client, model: str, diff: str
) -> list[Finding]:
    """Run the maintainability specialist over a unified diff."""
    return generate_findings(
        client=client,
        model=model,
        system_prompt=MAINTAINABILITY_SYSTEM_PROMPT,
        user_content=diff,
        schema=Finding,
    )