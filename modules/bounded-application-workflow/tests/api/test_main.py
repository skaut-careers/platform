from app.api.copilot_runtime import AGUI_WORKFLOW_AGENT_NAME


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
    empty = api_client.post(
        "/workflow/run",
        json={"profile_text": "   ", "job_description_text": "AI Engineer\n\nPython"},
    )
    assert empty.status_code == 422
    assert "must not be empty" in empty.text


def test_run_workflow_returns_decision(api_client):
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
