"""The single boundary between this project and the GitHub API.

Nothing else imports PyGithub directly. Keeping all GitHub I/O here means
the rest of the codebase stays pure and testable, and this one function is
the only thing we mock in tests.
"""

from github import Auth, Github


def post_pr_comment(
    token: str, repo_full_name: str, pr_number: int, body: str
) -> str:
    """Post a general conversation comment on a pull request.

    Returns the HTML URL of the created comment.

    Args:
        token: A GitHub token with `pull-requests: write` permission.
        repo_full_name: "owner/repo".
        pr_number: The pull request number.
        body: Markdown body of the comment.
    """
    auth = Auth.Token(token)
    with Github(auth=auth) as gh:
        repo = gh.get_repo(repo_full_name)
        pull = repo.get_pull(pr_number)
        comment = pull.create_issue_comment(body)
        return comment.html_url