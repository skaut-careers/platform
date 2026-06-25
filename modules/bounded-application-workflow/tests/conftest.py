import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.agents.contracts import SignalExtractorInput
from app.domain.models import DecisionType, JobDescription, UserProfile, WorkflowInput

FIXTURES_DIR = Path(__file__).parent / "fixtures"

WORKFLOW_FIXTURES = (
    "strong_match.json",
    "weak_match.json",
    "ambiguous_match.json",
)

SIGNAL_EXTRACTION_FIXTURES = (
    "skill_extraction.json",
    "risk_extraction.json",
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

SIGNAL_FIELDS = (
    "required_skills",
    "preferred_skills",
    "seniority_signals",
    "production_expectations",
    "risk_indicators",
    "missing_signals",
)


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text())


def expected_decision(fixture_name: str) -> DecisionType:
    return DecisionType(load_fixture(fixture_name)["expected_decision"])


def workflow_input(fixture_name: str) -> WorkflowInput:
    data = load_fixture(fixture_name)
    return WorkflowInput(
        user_profile=UserProfile(**data["user_profile"]),
        job_description=JobDescription(**data["job_description"]),
    )


def escalating_workflow_input() -> WorkflowInput:
    fixture = load_fixture("risk_extraction.json")
    return WorkflowInput(
        user_profile=workflow_input("ambiguous_match.json").user_profile,
        job_description=JobDescription(**fixture["job_description"]),
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


def mock_llm_client(*responses: dict[str, Any] | BaseException) -> MagicMock:
    client = MagicMock()
    if not responses:
        return client
    if len(responses) == 1 and not isinstance(responses[0], BaseException):
        client.complete_json.return_value = responses[0]
    else:
        client.complete_json.side_effect = list(responses)
    return client


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
            config_id="runtime",
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
