"""Fetch a merged PR's diff and reviewer comments to seed a labeling draft.

Produces a draft EvalCase JSON: the diff is frozen in, and the reviewers'
inline comments are included as context. A human then reads those comments and
writes the labeled_issues (importance and category) that human judgment is the
ground truth, so we deliberately do NOT auto-label.
"""

import json
from pathlib import Path

from github import Auth, Github

from multi_agent_code_review.evaluation.store import DEFAULT_CASES_DIR
from multi_agent_code_review.github_client import get_pr_diff


def fetch_review_comments(*, token: str, repo_full_name: str, pr_number: int) -> list[dict]:
    """Return reviewers' inline comments as {author, file, line, body}."""
    auth = Auth.Token(token)
    with Github(auth=auth) as gh:
        pull = gh.get_repo(repo_full_name).get_pull(pr_number)
        comments = []
        for c in pull.get_review_comments():
            comments.append({
                "author": c.user.login if c.user else None,
                "file": c.path,
                "line": c.line if c.line is not None else c.original_line,
                "body": c.body,
            })
    return comments


def build_draft(*, token: str, repo_full_name: str, pr_number: int) -> dict:
    """Assemble a draft EvalCase dict: diff + reviewer comments as context."""
    diff = get_pr_diff(token=token, repo_full_name=repo_full_name, pr_number=pr_number)
    comments = fetch_review_comments(
        token=token, repo_full_name=repo_full_name, pr_number=pr_number
    )
    return {
        "repo": repo_full_name,
        "pr_number": pr_number,
        "url": f"https://github.com/{repo_full_name}/pull/{pr_number}",
        "diff": diff,
        "labeled_issues": [],            # you fill this in
        "reviewer_comments": comments,   # context to label from (ignored on load)
    }


def write_draft(draft: dict, *, cases_dir: Path = DEFAULT_CASES_DIR) -> Path:
    """Write the draft to <cases_dir>/<repo>_<pr>.json."""
    cases_dir.mkdir(parents=True, exist_ok=True)
    case_id = f"{draft['repo'].replace('/', '_')}_{draft['pr_number']}"
    path = cases_dir / f"{case_id}.json"
    path.write_text(json.dumps(draft, indent=2), encoding="utf-8")
    return path