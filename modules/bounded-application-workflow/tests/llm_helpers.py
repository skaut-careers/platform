from typing import Any
from unittest.mock import MagicMock

from app.agents.contracts import SignalExtractorInput
from app.domain.models import JobDescription

SIGNAL_FIELDS = (
    "required_skills",
    "preferred_skills",
    "seniority_signals",
    "production_expectations",
    "risk_indicators",
    "missing_signals",
)


def signals_payload(**overrides: list[str]) -> dict[str, list[str]]:
    payload = {field: [] for field in SIGNAL_FIELDS}
    payload.update(overrides)
    return payload


def sample_input() -> SignalExtractorInput:
    return SignalExtractorInput(
        job_description=JobDescription(
            title="AI Engineer",
            description="- Python\n+ FastAPI",
        )
    )


def mock_llm_client(*responses: dict[str, Any] | BaseException) -> MagicMock:
    client = MagicMock()
    if not responses:
        return client
    if len(responses) == 1 and not isinstance(responses[0], BaseException):
        client.complete_json.return_value = responses[0]
    else:
        client.complete_json.side_effect = list(responses)
    return client
