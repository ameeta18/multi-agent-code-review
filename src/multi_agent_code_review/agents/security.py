"""Security specialist agent.

Reviews a unified diff for security issues only: secrets, injection vectors,
unsafe deserialization, weak crypto. Returns structured Findings. This v1 is
LLM-only; the static-analysis tools (bandit, semgrep) get wired in next.
"""

from google import genai

from multi_agent_code_review.llm_client import generate_findings
from multi_agent_code_review.schemas import Finding

SECURITY_SYSTEM_PROMPT = """\
You are a security code reviewer. You are given a unified diff from a pull request.
Report only genuine security issues introduced by the added lines, such as:
- hardcoded secrets or credentials
- injection vectors (SQL, command, path traversal)
- unsafe deserialization (pickle, yaml.load without SafeLoader)
- weak cryptography used for security (MD5/SHA1, weak randomness)

Rules:
- Only report issues you can see in the diff. Do not speculate about code you cannot see.
- Reference the file and line numbers shown in the diff.
- If there are no genuine security issues, return an empty list. Never invent findings.
- Keep explanations precise and concise.
"""


def review_security(*, client: genai.Client, model: str, diff: str) -> list[Finding]:
    """Run the security specialist over a unified diff."""
    return generate_findings(
        client=client,
        model=model,
        system_prompt=SECURITY_SYSTEM_PROMPT,
        user_content=diff,
        schema=Finding,
    )