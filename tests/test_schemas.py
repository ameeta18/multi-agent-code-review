import pytest
from pydantic import ValidationError

from multi_agent_code_review.schemas import Finding, Severity, Category 


def _valid_finding_data():
    return {
        "severity": "high",
        "file": "src/app.py",
        "line_start": 10,
        "line_end": 12,
        "title": "Hardcoded secret",
        "explanation": "An API key is committed directly in the source.",
        "suggested_fix": "Load it from an environment variable.",
    }


def test_valid_finding_parses():
    finding = Finding.model_validate(_valid_finding_data())
    assert finding.severity is Severity.HIGH
    assert finding.line_start == 10


def test_suggested_fix_is_optional():
    data = _valid_finding_data()
    data["suggested_fix"] = None
    assert Finding.model_validate(data).suggested_fix is None


def test_invalid_severity_is_rejected():
    data = _valid_finding_data()
    data["severity"] = "catastrophic"
    with pytest.raises(ValidationError):
        Finding.model_validate(data)


def test_line_end_before_line_start_is_rejected():
    data = _valid_finding_data()
    data["line_start"], data["line_end"] = 20, 5
    with pytest.raises(ValidationError):
        Finding.model_validate(data)


def test_extra_fields_are_ignored():
    # Deliberately NOT forbidden: OpenAI strict mode requires
    # additionalProperties:false while Gemini forbids it, so the shared schema
    # stays dialect-neutral and each provider adapter adds what it needs.
    data = _valid_finding_data()
    data["confidence"] = 0.9
    finding = Finding.model_validate(data)
    assert not hasattr(finding, "confidence")


def test_empty_title_is_rejected():
    data = _valid_finding_data()
    data["title"] = ""
    with pytest.raises(ValidationError):
        Finding.model_validate(data)

def test_category_defaults_to_none():
    assert Finding.model_validate(_valid_finding_data()).category is None


def test_category_accepts_enum_value():
    data = _valid_finding_data()
    data["category"] = "security"
    assert Finding.model_validate(data).category is Category.SECURITY