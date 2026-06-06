from fastapi.testclient import TestClient

from app.api.main import app
from app.domain.models import DecisionType
from tests.fixture_helpers import load_fixture

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_run_workflow_returns_structured_output():
    fixture = load_fixture("strong_match.json")
    response = client.post(
        "/workflow/run",
        json={
            "user_profile": fixture["user_profile"],
            "job_description": fixture["job_description"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["input_summary"]
    assert body["decision"]["score"] >= 0.0
    assert body["decision"]["decision"] in {d.value for d in DecisionType}
    assert body["recommended_next_steps"]
    assert "required_skills" in body["job_signals"]
    assert "risk_indicators" in body["job_signals"]


def test_run_workflow_ambiguous_match_escalates():
    fixture = load_fixture("ambiguous_match.json")
    response = client.post(
        "/workflow/run",
        json={
            "user_profile": fixture["user_profile"],
            "job_description": fixture["job_description"],
        },
    )

    assert response.status_code == 200
    assert response.json()["decision"]["decision"] == DecisionType.ESCALATE.value


def test_run_workflow_weak_match_skips():
    fixture = load_fixture("weak_match.json")
    response = client.post(
        "/workflow/run",
        json={
            "user_profile": fixture["user_profile"],
            "job_description": fixture["job_description"],
        },
    )

    assert response.status_code == 200
    assert response.json()["decision"]["decision"] == DecisionType.SKIP.value


def test_run_workflow_rejects_invalid_payload():
    response = client.post("/workflow/run", json={})
    assert response.status_code == 422
