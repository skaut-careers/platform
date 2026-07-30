from fastapi.testclient import TestClient

from app.agents import WorkflowOrchestratorInput
from app.agents.wiring import create_agents
from app.api.main import create_app
from app.domain.models import WorkflowInput, WorkflowOutput
from app.parser import parse_job_description
from tests.conftest import StubProfileExtractor, load_fixture, runtime_config, workflow_input


def test_health(api_client):
    assert api_client.get("/health").json() == {"status": "ok"}


def test_run_workflow_rejects_invalid_payload(api_client):
    assert api_client.post("/workflow/run", json={}).status_code == 422


def test_run_workflow_rejects_empty_texts(api_client):
    response = api_client.post(
        "/workflow/run",
        json={"profile_text": "   ", "job_description_text": "AI Engineer\n\nPython"},
    )
    assert response.status_code == 422
    assert "must not be empty" in response.text


def test_run_workflow_extracts_profile_from_raw_text(api_client):
    response = api_client.post(
        "/workflow/run",
        json={
            "profile_text": "Roles: Backend Engineer\nSkills: Python, FastAPI",
            "job_description_text": (
                "Backend Engineer\n\nRequirements:\n• Python\n• FastAPI"
            ),
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["decision"]["decision"]
    assert body["job_signals"] is not None


def test_run_workflow_response_parity():
    fixture = load_fixture("strong_match.json")
    profile = workflow_input("strong_match.json").user_profile
    job = fixture["job_description"]
    job_text = f"{job['title']}\n\n{job['description']}"
    wf_input = WorkflowInput(
        user_profile=profile,
        job_description=parse_job_description(job_text),
    )
    orchestrator = create_agents(runtime_config=runtime_config(version="v1"))[-1]
    expected = orchestrator.run(
        WorkflowOrchestratorInput(workflow_input=wf_input)
    ).output
    extractor = StubProfileExtractor(profile)
    api = TestClient(create_app(orchestrator=orchestrator, profile_extractor=extractor))

    response = api.post(
        "/workflow/run",
        json={
            "profile_text": "concatenated frontend profile fields",
            "job_description_text": job_text,
        },
    )
    assert response.status_code == 200
    assert WorkflowOutput.model_validate(response.json()) == expected
    assert extractor.calls == ["concatenated frontend profile fields"]
