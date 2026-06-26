from unittest.mock import patch

from multi_agent_code_review.agents.maintainability import review_maintainability
from multi_agent_code_review.schemas import Finding, Severity


@patch("multi_agent_code_review.agents.maintainability.generate_findings")
def test_review_maintainability_passes_diff_and_prompt(mock_generate):
    mock_generate.return_value = [
        Finding(
            severity=Severity.MEDIUM, file="a.py", line_start=1, line_end=60,
            title="Function too long", explanation="This function exceeds 50 lines.",
            suggested_fix=None,
        )
    ]

    findings = review_maintainability(client=object(), model="gemini-2.5-flash", diff="THE DIFF")

    assert len(findings) == 1
    _, kwargs = mock_generate.call_args
    assert kwargs["user_content"] == "THE DIFF"
    assert "maintainability" in kwargs["system_prompt"].lower()
    assert kwargs["schema"] is Finding