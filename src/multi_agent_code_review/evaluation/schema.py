"""Schema for the labeled evaluation dataset.

An EvalCase is one merged pull request plus the issues human reviewers raised on
it, hand-labeled by importance. This is the ground truth the bot is scored
against: recall on must-fix issues, precision, and severity calibration.
"""

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

from multi_agent_code_review.schemas import Category


class Importance(StrEnum):
    """Human judgment of how much an issue matters."""

    MUST_FIX = "must_fix"
    NICE_TO_HAVE = "nice_to_have"
    STYLISTIC = "stylistic"


class LabeledIssue(BaseModel):
    """One issue a human reviewer raised on the PR, hand-labeled."""

    file: str = Field(min_length=1)
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)
    importance: Importance
    # The bot specialty this falls under, or None if outside its scope
    # (e.g. a business-logic bug the bot is not designed to catch).
    category: Category | None = None
    description: str = Field(min_length=1)

    @model_validator(mode="after")
    def line_end_not_before_line_start(self) -> "LabeledIssue":
        if self.line_end < self.line_start:
            raise ValueError("line_end is before line_start")
        return self


class EvalCase(BaseModel):
    """A merged PR plus its hand-labeled issues — one ground-truth example."""

    repo: str = Field(min_length=1)  # e.g. "encode/httpx"
    pr_number: int = Field(ge=1)
    url: str = Field(min_length=1)
    diff: str = Field(min_length=1)
    labeled_issues: list[LabeledIssue] = Field(default_factory=list)

    @property
    def case_id(self) -> str:
        """Stable id like 'encode_httpx_1234' for filenames and reports."""
        return f"{self.repo.replace('/', '_')}_{self.pr_number}"