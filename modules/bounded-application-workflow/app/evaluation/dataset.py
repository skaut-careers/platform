import json
from pathlib import Path
from typing import cast

from pydantic import BaseModel, Field
from pydantic_evals import Case, Dataset

from app.agents.contracts import ProfileMatcherInput
from app.domain.job_signals import JobSignals
from app.domain.models import JobDescription, ProfileMatchResult, UserProfile

EVAL_ROOT = Path(__file__).resolve().parents[2] / "eval"
SIGNAL_DATASET_DIR = EVAL_ROOT / "signal_extraction"
PROFILE_DATASET_DIR = EVAL_ROOT / "profile_extraction"
MATCH_DATASET_DIR = EVAL_ROOT / "profile_matching"

SIGNAL_DATASET_NAME = "signal_extractor_golden"
PROFILE_DATASET_NAME = "profile_extractor_golden"
MATCH_DATASET_NAME = "profile_matcher_golden"


class CaseMetadata(BaseModel):
    description: str = ""
    tags: list[str] = Field(default_factory=list)


class MatchExpectation(BaseModel):

    score_min: float = Field(default=0.0, ge=0.0, le=1.0)
    score_max: float = Field(default=1.0, ge=0.0, le=1.0)
    role_aligned: bool = True
    work_arrangement_aligned: bool = True
    location_aligned: bool = True
    severe_seniority_mismatch: bool = False
    required_skills_matched: list[str] = Field(default_factory=list)
    required_skills_missing: list[str] = Field(default_factory=list)
    preferred_skills_matched: list[str] = Field(default_factory=list)
    production_expectations_matched: list[str] = Field(default_factory=list)
    production_expectations_missing: list[str] = Field(default_factory=list)


SignalCase = Case[JobDescription, JobSignals, CaseMetadata]
SignalDataset = Dataset[JobDescription, JobSignals, CaseMetadata]
ProfileCase = Case[str, UserProfile, CaseMetadata]
ProfileDataset = Dataset[str, UserProfile, CaseMetadata]
# OutputT is ProfileMatchResult (task output); goldens store MatchExpectation in expected_output.
MatchCase = Case[ProfileMatcherInput, ProfileMatchResult, CaseMetadata]
MatchDataset = Dataset[ProfileMatcherInput, ProfileMatchResult, CaseMetadata]


def _require_cases(cases: list, root: Path) -> list:
    if not cases:
        raise FileNotFoundError(f"No evaluation cases found in {root}")
    return cases


def load_signal_cases(dataset_dir: Path | None = None) -> list[SignalCase]:
    root = dataset_dir or SIGNAL_DATASET_DIR
    cases: list[SignalCase] = []
    for path in sorted(root.glob("*.json")):
        payload = json.loads(path.read_text())
        cases.append(
            Case(
                name=payload["id"],
                inputs=JobDescription.model_validate(payload["job_description"]),
                expected_output=JobSignals.model_validate(payload["expected_signals"]),
                metadata=CaseMetadata(
                    description=payload.get("description", ""),
                    tags=payload.get("tags", []),
                ),
            )
        )
    return _require_cases(cases, root)


def load_profile_cases(dataset_dir: Path | None = None) -> list[ProfileCase]:
    root = dataset_dir or PROFILE_DATASET_DIR
    cases: list[ProfileCase] = []
    for path in sorted(root.glob("*.json")):
        payload = json.loads(path.read_text())
        cases.append(
            Case(
                name=payload["id"],
                inputs=payload["raw_text"],
                expected_output=UserProfile.model_validate(payload["expected_profile"]),
                metadata=CaseMetadata(
                    description=payload.get("description", ""),
                    tags=payload.get("tags", []),
                ),
            )
        )
    return _require_cases(cases, root)


def _match_input(payload: dict) -> ProfileMatcherInput:
    return ProfileMatcherInput(
        user_profile=UserProfile.model_validate(payload["user_profile"]),
        job_description=JobDescription.model_validate(payload["job_description"]),
        signals=JobSignals.model_validate(payload["signals"]),
    )


def load_match_cases(dataset_dir: Path | None = None) -> list[MatchCase]:
    root = dataset_dir or MATCH_DATASET_DIR
    cases: list[MatchCase] = []
    for path in sorted(root.glob("*.json")):
        payload = json.loads(path.read_text())
        cases.append(
            cast(
                MatchCase,
                Case(
                    name=payload["id"],
                    inputs=_match_input(payload),
                    expected_output=MatchExpectation.model_validate(
                        payload["expected"]
                    ),
                    metadata=CaseMetadata(
                        description=payload.get("description", ""),
                        tags=payload.get("tags", []),
                    ),
                ),
            )
        )
    return _require_cases(cases, root)


def load_signal_dataset(
    dataset_dir: Path | None = None,
    *,
    cases: list[SignalCase] | None = None,
) -> SignalDataset:
    from app.evaluation.evaluators import SignalExtractionEvaluator

    return SignalDataset(
        name=SIGNAL_DATASET_NAME,
        cases=cases if cases is not None else load_signal_cases(dataset_dir),
        evaluators=[SignalExtractionEvaluator()],
    )


def load_profile_dataset(
    dataset_dir: Path | None = None,
    *,
    cases: list[ProfileCase] | None = None,
) -> ProfileDataset:
    from app.evaluation.evaluators import ProfileExtractionEvaluator

    return ProfileDataset(
        name=PROFILE_DATASET_NAME,
        cases=cases if cases is not None else load_profile_cases(dataset_dir),
        evaluators=[ProfileExtractionEvaluator()],
    )


def load_match_dataset(
    dataset_dir: Path | None = None,
    *,
    cases: list[MatchCase] | None = None,
) -> MatchDataset:
    from app.evaluation.evaluators import ProfileMatchEvaluator

    return MatchDataset(
        name=MATCH_DATASET_NAME,
        cases=cases if cases is not None else load_match_cases(dataset_dir),
        evaluators=[ProfileMatchEvaluator()],
    )
