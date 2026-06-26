from unittest.mock import patch

from multi_agent_code_review.agents.coverage import review_test_coverage
from multi_agent_code_review.schemas import Finding, Severity


@patch("multi_agent_code_review.agents.coverage.generate_findings")
def test_review_test_coverage_passes_diff_and_prompt(mock_generate):
    mock_generate.return_value = [
        Finding(
            severity=Severity.LOW, file="a.py", line_start=10, line_end=14,
            title="Untested error path", explanation="The except branch has no test.",
            suggested_fix="Add a test that triggers the exception.",
        )
    ]

    findings = review_test_coverage(client=object(), model="gemini-2.5-flash", diff="THE DIFF")

    assert len(findings) == 1
    _, kwargs = mock_generate.call_args
    assert kwargs["user_content"] == "THE DIFF"
    assert "coverage" in kwargs["system_prompt"].lower()
    assert kwargs["schema"] is Finding