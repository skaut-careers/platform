import json
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_evals import Case, Dataset

from app.domain.job_signals import JobSignals
from app.domain.models import JobDescription
from app.evaluation.evaluators import SignalExtractionEvaluator

DEFAULT_DATASET_DIR = Path(__file__).resolve().parents[2] / "eval" / "dataset"
DATASET_NAME = "signal_extractor_golden"


class CaseMetadata(BaseModel):
    description: str = ""
    tags: list[str] = Field(default_factory=list)


SignalCase = Case[JobDescription, JobSignals, CaseMetadata]
SignalDataset = Dataset[JobDescription, JobSignals, CaseMetadata]


def load_cases(dataset_dir: Path | None = None) -> list[SignalCase]:
    root = dataset_dir or DEFAULT_DATASET_DIR
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
    if not cases:
        raise FileNotFoundError(f"No evaluation cases found in {root}")
    return cases


def load_dataset(
    dataset_dir: Path | None = None,
    *,
    cases: list[SignalCase] | None = None,
) -> SignalDataset:
    return SignalDataset(
        name=DATASET_NAME,
        cases=cases if cases is not None else load_cases(dataset_dir),
        evaluators=[SignalExtractionEvaluator()],
    )
