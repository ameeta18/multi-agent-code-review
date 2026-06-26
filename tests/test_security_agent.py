from unittest.mock import patch

from multi_agent_code_review.agents.security import review_security
from multi_agent_code_review.schemas import Finding, Severity


@patch("multi_agent_code_review.agents.security.generate_findings")
def test_review_security_passes_diff_and_prompt(mock_generate):
    mock_generate.return_value = [
        Finding(
            severity=Severity.HIGH, file="a.py", line_start=1, line_end=1,
            title="Hardcoded secret", explanation="An API key is in source.",
            suggested_fix=None,
        )
    ]

    findings = review_security(client=object(), model="gemini-2.5-flash", diff="THE DIFF")

    assert len(findings) == 1
    _, kwargs = mock_generate.call_args
    assert kwargs["user_content"] == "THE DIFF"
    assert "security" in kwargs["system_prompt"].lower()
    assert kwargs["schema"] is Finding