from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.agents.default import create_agents
from app.api.main import app, create_app
from tests.fixture_helpers import load_fixture
from tests.llm_helpers import mock_llm_client

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_run_workflow():
    fixture = load_fixture("strong_match.json")
    response = client.post(
        "/workflow/run",
        json={
            "user_profile": fixture["user_profile"],
            "job_description": fixture["job_description"],
        },
    )

    assert response.status_code == 200
    assert response.json()["decision"]["decision"] == fixture["expected_decision"]


def test_run_workflow_rejects_invalid_payload():
    assert client.post("/workflow/run", json={}).status_code == 422


def test_run_workflow_with_llm_orchestrator(monkeypatch):
    monkeypatch.setenv("SIGNAL_EXTRACTOR", "llm")
    skill_fixture = load_fixture("skill_extraction.json")
    strong_fixture = load_fixture("strong_match.json")

    mock_client = mock_llm_client(skill_fixture["expected_signals"])
    api = TestClient(create_app(orchestrator=create_agents(client=mock_client)[-1]))
    response = api.post(
        "/workflow/run",
        json={
            "user_profile": strong_fixture["user_profile"],
            "job_description": skill_fixture["job_description"],
        },
    )

    assert response.status_code == 200
    assert mock_client.complete_json.call_count == 1
    assert (
        response.json()["job_signals"]["required_skills"]
        == skill_fixture["expected_signals"]["required_skills"]
    )

    failing_client = MagicMock()
    failing_client.complete_json.side_effect = RuntimeError("offline")
    api = TestClient(create_app(orchestrator=create_agents(client=failing_client)[-1]))
    response = api.post(
        "/workflow/run",
        json={
            "user_profile": strong_fixture["user_profile"],
            "job_description": strong_fixture["job_description"],
        },
    )

    assert response.status_code == 200
    assert response.json()["decision"]["decision"] == strong_fixture["expected_decision"]
