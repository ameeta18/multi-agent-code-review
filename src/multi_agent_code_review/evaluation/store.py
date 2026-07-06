"""Load and save labeled evaluation cases as JSON files on disk."""

import json  # noqa: F401  (kept for clarity; model handles (de)serialization)
from pathlib import Path

from multi_agent_code_review.evaluation.schema import EvalCase

DEFAULT_CASES_DIR = Path("eval/cases")


def save_case(case: EvalCase, *, cases_dir: Path = DEFAULT_CASES_DIR) -> Path:
    """Write one case to <cases_dir>/<case_id>.json. Returns the path."""
    cases_dir.mkdir(parents=True, exist_ok=True)
    path = cases_dir / f"{case.case_id}.json"
    path.write_text(case.model_dump_json(indent=2), encoding="utf-8")
    return path


def load_case(path: Path) -> EvalCase:
    """Read one case from a JSON file."""
    return EvalCase.model_validate_json(path.read_text(encoding="utf-8"))


def load_all_cases(*, cases_dir: Path = DEFAULT_CASES_DIR) -> list[EvalCase]:
    """Load every case JSON in the directory, sorted by filename."""
    if not cases_dir.exists():
        return []
    return [load_case(p) for p in sorted(cases_dir.glob("*.json"))]