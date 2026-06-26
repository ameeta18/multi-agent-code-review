from unittest.mock import patch

from multi_agent_code_review.graph import build_graph
from multi_agent_code_review.schemas import Category, Finding, Severity

DIFF = """\
diff --git a/src/auth.py b/src/auth.py
--- a/src/auth.py
+++ b/src/auth.py
@@ -1,2 +1,4 @@
 import os
+API_KEY = "secret"
+def login(): pass
 x = 1
"""
# added lines: 2, 3


def _f(line, file="src/auth.py", title="t"):
    return Finding(
        severity=Severity.HIGH, file=file, line_start=line, line_end=line,
        title=title, explanation="some explanation text", suggested_fix=None,
    )


@patch("multi_agent_code_review.graph.synthesize")
@patch("multi_agent_code_review.graph.review_test_coverage")
@patch("multi_agent_code_review.graph.review_maintainability")
@patch("multi_agent_code_review.graph.review_security")
def test_graph_merges_and_categorizes(mock_sec, mock_maint, mock_cov, mock_synth):
    mock_sec.return_value = [_f(2, title="secret")]
    mock_maint.return_value = [_f(3, title="long function")]
    mock_cov.return_value = [_f(3, title="untested")]

    graph = build_graph(
        client=object(),
        specialist_model="gemini-2.5-flash",
        synthesizer_model="gemini-2.5-flash",
    )
    result = graph.invoke({"diff": DIFF})

    assert len(result["findings"]) == 3  # all three merged via the reducer
    assert {f.category for f in result["findings"]} == {
        Category.SECURITY, Category.MAINTAINABILITY, Category.TEST_COVERAGE
    }
    assert len(result["filtered"]) == 3


@patch("multi_agent_code_review.graph.synthesize")
@patch("multi_agent_code_review.graph.review_test_coverage")
@patch("multi_agent_code_review.graph.review_maintainability")
@patch("multi_agent_code_review.graph.review_security")
def test_graph_filter_drops_out_of_diff(mock_sec, mock_maint, mock_cov, mock_synth):
    mock_sec.return_value = [_f(2)]
    mock_maint.return_value = []
    mock_cov.return_value = [_f(99, file="other.py")]  # outside diff

    graph = build_graph(
        client=object(),
        specialist_model="gemini-2.5-flash",
        synthesizer_model="gemini-2.5-flash",
    )
    result = graph.invoke({"diff": DIFF})

    assert len(result["findings"]) == 2   # both raw findings merged
    assert len(result["filtered"]) == 1   # filter dropped the out-of-diff one