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

from app.agents.contracts import SignalExtractorInput
from app.domain.job_signals import SIGNAL_FIELDS
from app.domain.models import DecisionType, JobDescription, UserProfile, WorkflowInput

MODULE_ROOT = Path(__file__).parent.parent
FIXTURES_DIR = Path(__file__).parent / "fixtures"
SIGNAL_FIXTURES_DIR = FIXTURES_DIR / "signal"
EVAL_DATASET_DIR = MODULE_ROOT / "eval" / "dataset"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text())


def load_signal_fixture(name: str) -> dict:
    return json.loads((SIGNAL_FIXTURES_DIR / name).read_text())


def load_eval_case(name: str) -> dict:
    return json.loads((EVAL_DATASET_DIR / name).read_text())


WORKFLOW_FIXTURES = (
    "strong_match.json",
    "weak_match.json",
    "ambiguous_match.json",
)

SIGNAL_EXTRACTION_FIXTURES = tuple(
    path.name for path in sorted(SIGNAL_FIXTURES_DIR.glob("*.json"))
)

AI_ENGINEER_JOB_TEXT = """
AI Engineer

Company: Frontier AI Startup
Location: Remote Europe
Seniority: mid-senior
Employment Type: full-time

- Python
- LLM applications
- evaluation pipelines
- agentic workflows
- product ownership

+ research background
+ startup experience

Build and own LLM-based product workflows.
"""


def expected_decision(fixture_name: str) -> DecisionType:
    return DecisionType(load_fixture(fixture_name)["expected_decision"])


def workflow_input(fixture_name: str) -> WorkflowInput:
    data = load_fixture(fixture_name)
    return WorkflowInput(
        user_profile=UserProfile(**data["user_profile"]),
        job_description=JobDescription(**data["job_description"]),
    )


def escalating_workflow_input() -> WorkflowInput:
    case = load_signal_fixture("risk_extraction.json")
    return WorkflowInput(
        user_profile=workflow_input("ambiguous_match.json").user_profile,
        job_description=JobDescription(**case["job_description"]),
    )


def signals_payload(**overrides: list[str]) -> dict[str, list[str]]:
    payload = {field: [] for field in SIGNAL_FIELDS}
    payload.update(overrides)
    return payload


def sample_signal_extractor_input() -> SignalExtractorInput:
    return SignalExtractorInput(
        job_description=JobDescription(
            title="AI Engineer",
            description="- Python\n+ FastAPI",
        )
    )


def signals_test_model(**overrides: list[str]) -> TestModel:
    """A Pydantic AI TestModel that returns a fixed JobSignals payload."""
    return TestModel(custom_output_args=signals_payload(**overrides))


class RecordingSignalModel:
    """Scripted FunctionModel that records prompts and replays signal responses.

    Each positional response is either a ``JobSignals`` payload dict (returned as
    the agent's structured output) or an exception instance (raised to simulate a
    provider failure). Responses are consumed by call index; the final response is
    reused once exhausted, so a single payload is returned for every call.
    """

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
    from app.runtime.config_loader import load_runtime_config

    if version is not None:
        env = {"RUNTIME_CONFIG_VERSION": version, **env}
    return load_runtime_config(env=env)


def register_runtime_bundle(
    *,
    version: str,
    settings: dict[str, Any],
    prompt_version: str,
    prompt_content: str,
):
    from app.agents.signal_extraction import LLMSignalExtractor
    from app.runtime.agent_identity import agent_name_for
    from app.runtime.config_registry import ConfigRegistry, ConfigSpec, compute_config_hash
    from app.runtime.prompt_registry import PromptRegistry, PromptSpec, compute_content_hash

    agent_name = agent_name_for(LLMSignalExtractor)
    prompt_registry = PromptRegistry()
    prompt_registry.register(
        PromptSpec(
            agent_name=agent_name,
            version=prompt_version,
            content=prompt_content,
            content_hash=compute_content_hash(prompt_content),
        )
    )
    config_registry = ConfigRegistry()
    config_registry.register(
        ConfigSpec(
            version=version,
            settings=settings,
            content_hash=compute_config_hash(settings),
        )
    )
    return config_registry, prompt_registry


@pytest.fixture
def api_client() -> TestClient:
    from app.api.main import app

    return TestClient(app)
