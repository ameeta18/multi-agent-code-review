"""Entry point the GitHub Action runs.

Reads the GitHub-provided environment, fetches the PR diff, runs the review
graph, and posts the synthesized comment back on the pull request. This module
is thin glue: it wires collaborators together and holds no review logic itself.
"""

import json
import os

from google import genai

from multi_agent_code_review.github_client import get_pr_diff, post_pr_comment
from multi_agent_code_review.graph import build_graph

SPECIALIST_MODEL = "gemini-2.5-flash"
SYNTHESIZER_MODEL = "gemini-2.5-flash"  # swap to a Pro tier for higher quality later


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

    diff = get_pr_diff(token=token, repo_full_name=repo_full_name, pr_number=pr_number)

    if not diff.strip():
        post_pr_comment(
            token=token, repo_full_name=repo_full_name, pr_number=pr_number,
            body="No reviewable code changes found in this pull request.",
        )
        return

    client = genai.Client()  # reads GEMINI_API_KEY from the environment
    graph = build_graph(
        client=client,
        specialist_model=SPECIALIST_MODEL,
        synthesizer_model=SYNTHESIZER_MODEL,
    )
    result = graph.invoke({"diff": diff})

    url = post_pr_comment(
        token=token, repo_full_name=repo_full_name, pr_number=pr_number,
        body=result["comment"],
    )
    print(f"Posted review: {url}")