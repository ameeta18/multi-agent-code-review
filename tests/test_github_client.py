from unittest.mock import patch

from multi_agent_code_review.github_client import post_pr_comment


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