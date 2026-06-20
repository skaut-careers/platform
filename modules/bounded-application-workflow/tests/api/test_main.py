from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.agents.default import create_agents
from app.api.main import create_app
from tests.conftest import load_fixture, mock_llm_client


def test_health(api_client):
    response = api_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_run_workflow(api_client):
    fixture = load_fixture("strong_match.json")
    response = api_client.post(
        "/workflow/run",
        json={
            "user_profile": fixture["user_profile"],
            "job_description": fixture["job_description"],
        },
    )

    assert response.status_code == 200
    assert response.json()["decision"]["decision"] == fixture["expected_decision"]


def test_run_workflow_rejects_invalid_payload(api_client):
    assert api_client.post("/workflow/run", json={}).status_code == 422


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
