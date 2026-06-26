from unittest.mock import MagicMock, patch

from multi_agent_code_review.github_client import post_pr_comment,get_pr_diff 


@patch("multi_agent_code_review.github_client.Github")
def test_post_pr_comment_posts_to_the_conversation_thread(mock_github_cls):
    # The chain: with Github(...) as gh: gh.get_repo().get_pull().create_issue_comment()
    gh = mock_github_cls.return_value.__enter__.return_value
    created = gh.get_repo.return_value.get_pull.return_value.create_issue_comment.return_value
    created.html_url = "https://github.com/owner/repo/pull/1#issuecomment-123"

    url = post_pr_comment(
        token="fake-token",
        repo_full_name="owner/repo",
        pr_number=1,
        body="hello from the bot",
    )

    gh.get_repo.assert_called_once_with("owner/repo")
    gh.get_repo.return_value.get_pull.assert_called_once_with(1)
    gh.get_repo.return_value.get_pull.return_value.create_issue_comment.assert_called_once_with(
        "hello from the bot"
    )
    assert url == "https://github.com/owner/repo/pull/1#issuecomment-123"
@patch("multi_agent_code_review.github_client.Github")
def test_get_pr_diff_reconstructs_parseable_diff(mock_github_cls):
    from multi_agent_code_review.diff import added_lines_by_file

    code_file = MagicMock()
    code_file.filename = "auth.py"
    code_file.patch = "@@ -1,1 +1,2 @@\n keep\n+added"
    binary_file = MagicMock()
    binary_file.filename = "logo.png"
    binary_file.patch = None  # no patch -> skipped

    gh = mock_github_cls.return_value.__enter__.return_value
    gh.get_repo.return_value.get_pull.return_value.get_files.return_value = [
        code_file, binary_file
    ]

    diff = get_pr_diff(token="t", repo_full_name="o/r", pr_number=1)

    assert "--- a/auth.py" in diff and "+++ b/auth.py" in diff
    assert "logo.png" not in diff                       # binary file skipped
    assert added_lines_by_file(diff) == {"auth.py": {2}}  # our reconstruction parses