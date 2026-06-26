from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from multi_agent_code_review.llm_client import generate_findings, generate_structured
from multi_agent_code_review.schemas import Finding, Severity


def _client_returning(json_text: str):
    response = MagicMock()
    response.text = json_text
    client = MagicMock()
    client.models.generate_content.return_value = response
    return client


def test_generate_findings_validates_model_output():
    client = _client_returning(
        '[{"severity": "high", "file": "src/app.py", "line_start": 10,'
        ' "line_end": 10, "title": "Hardcoded secret",'
        ' "explanation": "An API key is committed in source.",'
        ' "suggested_fix": "Use an environment variable."}]'
    )

    findings = generate_findings(
        client=client,
        model="gemini-2.5-flash",
        system_prompt="You are a security reviewer.",
        user_content="diff here",
        schema=Finding,
    )

    assert len(findings) == 1
    assert findings[0].severity is Severity.HIGH

    _, kwargs = client.models.generate_content.call_args
    assert kwargs["config"].response_mime_type == "application/json"


def test_bad_model_output_is_rejected():
    client = _client_returning(
        '[{"severity": "catastrophic", "file": "a.py", "line_start": 1,'
        ' "line_end": 1, "title": "x", "explanation": "y",'
        ' "suggested_fix": null}]'
    )

    with pytest.raises(ValidationError):
        generate_findings(
            client=client,
            model="gemini-2.5-flash",
            system_prompt="s",
            user_content="c",
            schema=Finding,
        )
def test_generate_structured_returns_validated_object():
    from pydantic import BaseModel

    class Plan(BaseModel):
        summary: str
        n: int

    client = _client_returning('{"summary": "ok", "n": 3}')
    result = generate_structured(
        client=client, model="m", system_prompt="s", user_content="c", schema=Plan
    )
    assert result.summary == "ok"
    assert result.n == 3