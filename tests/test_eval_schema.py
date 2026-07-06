import pytest
from pydantic import ValidationError

from multi_agent_code_review.evaluation.schema import EvalCase, Importance, LabeledIssue
from multi_agent_code_review.schemas import Category


def _issue(**kw):
    base = dict(
        file="httpx/_client.py", line_start=10, line_end=10,
        importance=Importance.MUST_FIX, category=Category.SECURITY,
        description="Auth token logged in plaintext.",
    )
    base.update(kw)
    return LabeledIssue(**base)


def test_labeled_issue_valid():
    issue = _issue()
    assert issue.importance is Importance.MUST_FIX
    assert issue.category is Category.SECURITY


def test_category_optional_for_out_of_scope_issue():
    assert _issue(category=None).category is None


def test_line_range_validated():
    with pytest.raises(ValidationError):
        _issue(line_start=20, line_end=5)


def test_eval_case_id_is_filesystem_safe():
    case = EvalCase(
        repo="encode/httpx", pr_number=1234,
        url="https://github.com/encode/httpx/pull/1234",
        diff="diff --git ...", labeled_issues=[_issue()],
    )
    assert case.case_id == "encode_httpx_1234"


def test_eval_case_allows_no_issues():
    case = EvalCase(repo="encode/httpx", pr_number=1, url="u", diff="d")
    assert case.labeled_issues == []