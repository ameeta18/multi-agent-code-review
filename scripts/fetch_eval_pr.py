"""Fetch a merged PR into a labeling draft.

Usage:
    uv run python scripts/fetch_eval_pr.py encode/httpx 3000
"""

import os
import sys

from dotenv import load_dotenv

from multi_agent_code_review.evaluation.fetch import build_draft, write_draft

load_dotenv()


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: fetch_eval_pr.py <owner/repo> <pr_number>")
        raise SystemExit(1)
    repo, pr_number = sys.argv[1], int(sys.argv[2])
    token = os.environ["GITHUB_TOKEN"]

    draft = build_draft(token=token, repo_full_name=repo, pr_number=pr_number)
    path = write_draft(draft)
    print(f"Wrote {path} with {len(draft['reviewer_comments'])} reviewer comment(s) to label.")


if __name__ == "__main__":
    main()