"""The shared schema every specialist agent must conform to.

Single source of truth for what a 'finding' looks like. Each specialist's
raw LLM output is validated against this before any filter or the
synthesizer is allowed to use it. Malformed output fails loudly here
instead of silently corrupting the review downstream.
"""

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

class Severity(StrEnum):
    """How serious a finding is, most to least severe."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    @property
    def rank(self) -> int:
        """Sort key: 0 is most severe, so lower sorts first."""
        return _SEVERITY_RANK[self]


_SEVERITY_RANK = {
    Severity.CRITICAL: 0,
    Severity.HIGH: 1,
    Severity.MEDIUM: 2,
    Severity.LOW: 3,
}

class Category(StrEnum):
    """Which specialist produced a finding."""

    SECURITY = "security"
    MAINTAINABILITY = "maintainability"
    TEST_COVERAGE = "test_coverage"

class Finding(BaseModel):
    """One issue a specialist raises about a single location in the diff."""

    #model_config = ConfigDict(extra="forbid")

    severity: Severity
    file: str = Field(min_length=1)
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)
    title: str = Field(min_length=1)
    explanation: str = Field(min_length=1)
    suggested_fix: str | None = None
    category: Category | None = None
    @model_validator(mode="after")
    def line_end_not_before_line_start(self) -> "Finding":
        if self.line_end < self.line_start:
            raise ValueError(
                f"line_end ({self.line_end}) is before line_start ({self.line_start})"
            )
        return self