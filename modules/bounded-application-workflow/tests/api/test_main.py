from app.api.copilot_runtime import AGUI_WORKFLOW_AGENT_NAME
from app.domain.models import DecisionType
from tests.conftest import workflow_input

_DECISIONS = {d.value for d in DecisionType}


def test_health(api_client):
    assert api_client.get("/health").json() == {"status": "ok"}
    assert api_client.get("/copilotkit/health").json() == {
        "status": "ok",
        "agent": {"name": AGUI_WORKFLOW_AGENT_NAME},
    }


def test_cors_allows_local_next(api_client):
    for origin in ("http://localhost:3000", "http://127.0.0.1:3000"):
        response = api_client.options(
            "/health",
            headers={"Origin": origin, "Access-Control-Request-Method": "GET"},
        )
        assert response.headers.get("access-control-allow-origin") == origin


def test_run_workflow_validates_body(api_client):
    assert api_client.post("/workflow/run", json={}).status_code == 422
    for payload in (
        {"profile_text": "   ", "job_description_text": "AI Engineer\n\nPython"},
        {"profile_text": "Roles: Backend\nSkills: Python", "job_description_text": "  "},
    ):
        response = api_client.post("/workflow/run", json=payload)
        assert response.status_code == 422
        assert "must not be empty" in response.text


def test_run_workflow_returns_decision(api_client):
    wi = workflow_input("strong_match.json")
    response = api_client.post(
        "/workflow/run",
        json={
            "profile_text": wi.profile_text,
            "job_description_text": wi.job_description_text,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["decision"] in _DECISIONS
    assert isinstance(body["score"], (int, float))
    assert isinstance(body["reasons"], list)
    assert isinstance(body["risks"], list)
    assert isinstance(body["missing_information"], list)
