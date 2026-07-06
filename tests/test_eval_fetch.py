import json
from unittest.mock import MagicMock, patch

from multi_agent_code_review.evaluation.fetch import (
    build_draft,
    fetch_review_comments,
    write_draft,
)
from multi_agent_code_review.evaluation.store import load_case


@patch("multi_agent_code_review.evaluation.fetch.Github")
def test_fetch_review_comments_extracts_fields(mock_github_cls):
    c = MagicMock()
    c.user.login = "reviewer1"
    c.path = "httpx/_client.py"
    c.line = 42
    c.body = "This leaks the auth token."
    gh = mock_github_cls.return_value.__enter__.return_value
    gh.get_repo.return_value.get_pull.return_value.get_review_comments.return_value = [c]

    comments = fetch_review_comments(token="t", repo_full_name="encode/httpx", pr_number=1)

    assert comments == [{
        "author": "reviewer1", "file": "httpx/_client.py",
        "line": 42, "body": "This leaks the auth token.",
    }]


@patch("multi_agent_code_review.evaluation.fetch.fetch_review_comments")
@patch("multi_agent_code_review.evaluation.fetch.get_pr_diff")
def test_build_draft_assembles_case(mock_diff, mock_comments):
    mock_diff.return_value = "DIFF TEXT"
    mock_comments.return_value = [{"author": "r", "file": "a.py", "line": 1, "body": "x"}]

    draft = build_draft(token="t", repo_full_name="encode/httpx", pr_number=99)

    assert draft["repo"] == "encode/httpx"
    assert draft["diff"] == "DIFF TEXT"
    assert draft["labeled_issues"] == []
    assert draft["url"] == "https://github.com/encode/httpx/pull/99"
    assert len(draft["reviewer_comments"]) == 1


def test_write_draft_loads_as_valid_evalcase(tmp_path):
    draft = {
        "repo": "encode/httpx", "pr_number": 5,
        "url": "https://github.com/encode/httpx/pull/5",
        "diff": "some diff", "labeled_issues": [],
        "reviewer_comments": [{"author": "r", "file": "a.py", "line": 1, "body": "x"}],
    }
    path = write_draft(draft, cases_dir=tmp_path)

    on_disk = json.loads(path.read_text())
    assert len(on_disk["reviewer_comments"]) == 1     # context is in the file
    case = load_case(path)                             # and it loads as an EvalCase
    assert case.repo == "encode/httpx"
    assert case.labeled_issues == []