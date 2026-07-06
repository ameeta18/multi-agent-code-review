from multi_agent_code_review.evaluation.schema import EvalCase, Importance, LabeledIssue
from multi_agent_code_review.evaluation.store import load_all_cases, load_case, save_case
from multi_agent_code_review.schemas import Category


def _case(pr=1):
    return EvalCase(
        repo="encode/httpx", pr_number=pr,
        url=f"https://github.com/encode/httpx/pull/{pr}",
        diff="diff --git a/x.py b/x.py\n--- a/x.py\n+++ b/x.py\n@@ -1 +1,2 @@\n a\n+b",
        labeled_issues=[LabeledIssue(
            file="x.py", line_start=2, line_end=2,
            importance=Importance.MUST_FIX, category=Category.SECURITY,
            description="bad",
        )],
    )


def test_save_then_load_roundtrip(tmp_path):
    case = _case()
    path = save_case(case, cases_dir=tmp_path)
    assert path.exists()
    assert load_case(path) == case


def test_load_all_cases(tmp_path):
    save_case(_case(1), cases_dir=tmp_path)
    save_case(_case(2), cases_dir=tmp_path)
    cases = load_all_cases(cases_dir=tmp_path)
    assert {c.pr_number for c in cases} == {1, 2}


def test_load_all_empty_dir_returns_empty(tmp_path):
    assert load_all_cases(cases_dir=tmp_path / "nope") == []