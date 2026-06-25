"""Entry point the GitHub Action runs.

GitHub gives us three things via the environment: a token, the repository
name, and a path to a file describing the event. We read those, find which
pull request triggered the run, and post a comment.
"""

import json
import os

from multi_agent_code_review.github_client import post_pr_comment


def extract_pr_number(event: dict) -> int:
    """Find the pull request number inside a GitHub pull_request event."""
    return event["pull_request"]["number"]


def main() -> None:
    token = os.environ["GITHUB_TOKEN"]
    repo_full_name = os.environ["GITHUB_REPOSITORY"]
    event_path = os.environ["GITHUB_EVENT_PATH"]

    with open(event_path, encoding="utf-8") as f:
        event = json.load(f)

    pr_number = extract_pr_number(event)

    url = post_pr_comment(
        token=token,
        repo_full_name=repo_full_name,
        pr_number=pr_number,
        body="Hello from the multi-agent code review bot — setup check, no review yet.",
    )
    print(f"Posted comment: {url}")