from multi_agent_code_review.cli import extract_pr_number


def test_extract_pr_number_reads_the_pull_request_number():
    event = {"action": "opened", "number": 7, "pull_request": {"number": 7}}
    assert extract_pr_number(event) == 7