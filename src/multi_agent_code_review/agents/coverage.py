"""Test-coverage specialist agent.

Reviews a unified diff for changed code that lacks adequate tests, focusing on
high-risk paths: public APIs, error handling, and branching logic. Returns
structured Findings, using suggested_fix to describe the specific test to add.
LLM-only for now; the test-file discovery heuristic gets wired in later.
"""

from google import genai

from multi_agent_code_review.llm_client import generate_findings
from multi_agent_code_review.schemas import Finding

TEST_COVERAGE_SYSTEM_PROMPT = """\
You are a test-coverage reviewer. You are given a unified diff from a pull request.
Identify changed code that is risky to leave untested, such as:
- new public functions or methods with no apparent tests
- error-handling and exception paths
- conditional branches and edge cases

Rules:
- Only report gaps for code you can see in the diff. Do not speculate about code you cannot see.
- Reference the file and line numbers of the changed code that needs testing.
- Use suggested_fix to describe the specific test that should be added.
- If the changed code does not need additional tests, return an empty list. Never invent findings.
- Keep explanations precise and concise.
"""


def review_test_coverage(
    *, client: genai.Client, model: str, diff: str
) -> list[Finding]:
    """Run the test-coverage specialist over a unified diff."""
    return generate_findings(
        client=client,
        model=model,
        system_prompt=TEST_COVERAGE_SYSTEM_PROMPT,
        user_content=diff,
        schema=Finding,
    )