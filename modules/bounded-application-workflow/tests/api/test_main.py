from fastapi.testclient import TestClient

from app.agents import WorkflowOrchestratorInput
from app.agents.wiring import create_agents
from app.api.main import create_app
from app.domain.models import WorkflowOutput
from tests.conftest import StubProfileExtractor, load_fixture, runtime_config, workflow_input


def test_health(api_client):
    assert api_client.get("/health").json() == {"status": "ok"}


def test_run_workflow_rejects_invalid_payload(api_client):
    assert api_client.post("/workflow/run", json={}).status_code == 422


def test_run_workflow_extracts_profile_from_raw_text(api_client):
    response = api_client.post(
        "/workflow/run",
        json={
            "profile_text": "Roles: Backend Engineer\nSkills: Python, FastAPI",
            "job_description": {
                "title": "Backend Engineer",
                "description": "Requirements:\n• Python\n• FastAPI",
            },
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["decision"]["decision"]
    assert body["job_signals"] is not None


def test_run_workflow_response_parity():
    fixture = load_fixture("strong_match.json")
    wf_input = workflow_input("strong_match.json")
    orchestrator = create_agents(runtime_config=runtime_config(version="v1"))[-1]
    expected = orchestrator.run(
        WorkflowOrchestratorInput(workflow_input=wf_input)
    ).output
    extractor = StubProfileExtractor(wf_input.user_profile)
    api = TestClient(create_app(orchestrator=orchestrator, profile_extractor=extractor))

    response = api.post(
        "/workflow/run",
        json={
            "profile_text": "concatenated frontend profile fields",
            "job_description": fixture["job_description"],
        },
    )
    assert response.status_code == 200
    body = WorkflowOutput.model_validate(response.json())
    assert body == expected
    assert extractor.calls == ["concatenated frontend profile fields"]
