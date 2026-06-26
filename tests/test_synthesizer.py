from unittest.mock import patch

from multi_agent_code_review.agents.synthesizer import (
    SynthesisPlan,
    _select,
    render_comment,
    synthesize,
)
from multi_agent_code_review.schemas import Category, Finding, Severity


def _f(title, sev=Severity.HIGH, file="a.py", line=1, cat=Category.SECURITY):
    return Finding(
        severity=sev, file=file, line_start=line, line_end=line,
        title=title, explanation="some explanation text", suggested_fix="do x",
        category=cat,
    )


def test_select_keeps_in_range_dedupes_and_caps():
    findings = [_f(f"t{i}") for i in range(10)]
    plan = SynthesisPlan(summary="s", finding_indices=[0, 0, 1, 99, 2, 3, 4, 5, 6, 7])
    selected = _select(plan, findings)
    assert len(selected) == 7           # capped
    assert selected[0] is findings[0]   # order preserved, duplicate 0 ignored


def test_render_includes_severity_file_and_fix():
    md = render_comment("Two issues found.", [_f("Hardcoded key")])
    assert "Two issues found." in md
    assert "[HIGH]" in md and "Hardcoded key" in md
    assert "a.py:1-1" in md and "Suggested fix" in md


def test_render_empty_is_no_issues():
    md = render_comment("No significant issues found.", [])
    assert "No significant issues found." in md
    assert "### Findings" not in md


def test_synthesize_empty_findings_skips_llm():
    with patch("multi_agent_code_review.agents.synthesizer.generate_structured") as m:
        out = synthesize(client=object(), model="x", diff="d", findings=[])
        m.assert_not_called()
    assert "No significant issues found." in out


@patch("multi_agent_code_review.agents.synthesizer.generate_structured")
def test_synthesize_renders_selected_findings(mock_gen):
    findings = [_f("Critical bug", sev=Severity.CRITICAL), _f("Minor", sev=Severity.LOW)]
    mock_gen.return_value = SynthesisPlan(summary="One critical issue.", finding_indices=[0])
    out = synthesize(client=object(), model="x", diff="d", findings=findings)
    assert "One critical issue." in out and "Critical bug" in out
    assert "Minor" not in out


@patch("multi_agent_code_review.agents.synthesizer.generate_structured")
def test_synthesizer_cannot_invent_findings(mock_gen):
    findings = [_f("Real finding")]
    mock_gen.return_value = SynthesisPlan(summary="s", finding_indices=[5])  # invalid index
    out = synthesize(client=object(), model="x", diff="d", findings=findings)
    assert "Real finding" not in out      # nothing fabricated
    assert "### Findings" not in out