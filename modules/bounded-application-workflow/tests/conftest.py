import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic_ai.messages import (
    ModelMessage,
    ModelResponse,
    SystemPromptPart,
    ToolCallPart,
    UserPromptPart,
)
from pydantic_ai.models import Model
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

from app.agents.contracts import JobSignalExtractorInput
from app.domain.models import DecisionType, SIGNAL_FIELDS, WorkflowInput

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SIGNAL_FIXTURES_DIR = FIXTURES_DIR / "signal"
PROFILE_FIXTURES_DIR = FIXTURES_DIR / "profile"
MATCH_FIXTURES_DIR = FIXTURES_DIR / "match"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text())


def load_signal_fixture(name: str) -> dict:
    return json.loads((SIGNAL_FIXTURES_DIR / name).read_text())


def load_profile_fixture(name: str) -> dict:
    return json.loads((PROFILE_FIXTURES_DIR / name).read_text())


def load_match_fixture(name: str) -> dict:
    return json.loads((MATCH_FIXTURES_DIR / name).read_text())


WORKFLOW_FIXTURES = (
    "strong_match.json",
    "weak_match.json",
    "ambiguous_match.json",
)

JOB_SIGNAL_EXTRACTION_FIXTURES = tuple(
    path.name for path in sorted(SIGNAL_FIXTURES_DIR.glob("*.json"))
)

PROFILE_EXTRACTION_FIXTURES = tuple(
    path.name for path in sorted(PROFILE_FIXTURES_DIR.glob("*.json"))
)

MATCH_FIXTURES = tuple(
    path.name for path in sorted(MATCH_FIXTURES_DIR.glob("*.json"))
)

def expected_decision(fixture_name: str) -> DecisionType:
    return DecisionType(load_fixture(fixture_name)["expected_decision"])


def workflow_input(fixture_name: str) -> WorkflowInput:
    data = load_fixture(fixture_name)
    return WorkflowInput(
        profile_text=data["profile_text"],
        job_description_text=data["job_description_text"],
    )


def signals_payload(**overrides: list[str]) -> dict[str, list[str]]:
    payload = {field: [] for field in SIGNAL_FIELDS}
    payload.update(overrides)
    return payload


def sample_job_signal_extractor_input() -> JobSignalExtractorInput:
    return JobSignalExtractorInput(
        job_description_text=(
            "Build LLM product workflows.\n\n"
            "Requirements:\n• Python\n\n"
            "Nice to have:\n• FastAPI"
        ),
    )


def signals_test_model(**overrides: list[str]) -> TestModel:
    """A Pydantic AI TestModel that returns a fixed JobSignals payload."""
    return TestModel(custom_output_args=signals_payload(**overrides))


class RecordingSignalModel:
    def __init__(self, *responses: dict[str, Any] | BaseException) -> None:
        self._responses: list[dict[str, Any] | BaseException] = list(responses) or [
            signals_payload()
        ]
        self.system_prompts: list[str] = []
        self.user_prompts: list[str] = []
        self.call_count = 0

    def as_model(self) -> Model:
        return FunctionModel(self._respond)

    def _respond(
        self, messages: list[ModelMessage], info: AgentInfo
    ) -> ModelResponse:
        for message in messages:
            for part in message.parts:
                if isinstance(part, SystemPromptPart):
                    self.system_prompts.append(part.content)
                elif isinstance(part, UserPromptPart):
                    self.user_prompts.append(part.content)

        response = self._responses[min(self.call_count, len(self._responses) - 1)]
        self.call_count += 1
        if isinstance(response, BaseException):
            raise response

        output_tool = info.output_tools[0].name
        return ModelResponse(parts=[ToolCallPart(output_tool, dict(response))])


def runtime_config(version: str | None = None, **env: str):
    """Load a runtime config with an explicit env mapping (never reads `.env`).

    Omitting ``version`` selects the built-in default (``v1`` / deterministic).
    """
    from app.runtime.config_loader import load_runtime_config

    return load_runtime_config(version=version, env=env)


@pytest.fixture
def api_client() -> TestClient:
    """HTTP client over a v1 (deterministic) app — independent of local `.env`."""
    from app.agents.wiring import create_agents
    from app.api.main import create_app

    config = runtime_config(version="v1")
    return TestClient(
        create_app(orchestrator=create_agents(runtime_config=config))
    )
