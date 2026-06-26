import json
from unittest.mock import MagicMock, patch

from multi_agent_code_review.cli import extract_pr_number, main


def test_extract_pr_number_reads_the_pull_request_number():
    event = {"action": "opened", "number": 7, "pull_request": {"number": 7}}
    assert extract_pr_number(event) == 7


def _set_env(tmp_path, monkeypatch, pr_number):
    event_file = tmp_path / "event.json"
    event_file.write_text(json.dumps({"pull_request": {"number": pr_number}}))
    monkeypatch.setenv("GITHUB_TOKEN", "tok")
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_file))


@patch("multi_agent_code_review.cli.post_pr_comment")
@patch("multi_agent_code_review.cli.build_graph")
@patch("multi_agent_code_review.cli.genai.Client")
@patch("multi_agent_code_review.cli.get_pr_diff")
def test_main_runs_graph_and_posts_comment(
    mock_get_diff, mock_client, mock_build_graph, mock_post, tmp_path, monkeypatch
):
    _set_env(tmp_path, monkeypatch, 42)
    mock_get_diff.return_value = "some diff"
    graph = MagicMock()
    graph.invoke.return_value = {"comment": "REVIEW COMMENT"}
    mock_build_graph.return_value = graph

    main()

    graph.invoke.assert_called_once_with({"diff": "some diff"})
    _, kwargs = mock_post.call_args
    assert kwargs["body"] == "REVIEW COMMENT"
    assert kwargs["pr_number"] == 42


@patch("multi_agent_code_review.cli.post_pr_comment")
@patch("multi_agent_code_review.cli.build_graph")
@patch("multi_agent_code_review.cli.genai.Client")
@patch("multi_agent_code_review.cli.get_pr_diff")
def test_main_empty_diff_skips_graph(
    mock_get_diff, mock_client, mock_build_graph, mock_post, tmp_path, monkeypatch
):
    _set_env(tmp_path, monkeypatch, 1)
    mock_get_diff.return_value = "   \n  "  # effectively empty

    main()

    mock_build_graph.assert_not_called()  # no graph, no paid calls
    mock_post.assert_called_once()        # but a comment is still posted