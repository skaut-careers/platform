import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agents import create_agents
from app.agents.contracts import WorkflowOrchestratorInput
from app.agents.orchestration.orchestrator import DefaultWorkflowOrchestrator
from app.api.copilot_runtime import mount_copilotkit_runtime
from app.domain.models import WorkflowInput, WorkflowOutput
from app.observability import instrument_app


_DEFAULT_CORS_ORIGINS = (
    "http://localhost:3000,http://127.0.0.1:3000"
)


def _cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", _DEFAULT_CORS_ORIGINS)
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def create_app(
    *,
    orchestrator: DefaultWorkflowOrchestrator | None = None,
) -> FastAPI:
    """HTTP app: REST workflow run + CopilotKit AG-UI agent endpoint."""
    app = FastAPI(
        title="Bounded Application Workflow",
        description="Run the opportunity workflow against a user profile.",
        version="0.1.0",
    )
    instrument_app(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    workflow = orchestrator or create_agents()[-1]

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/workflow/run", response_model=WorkflowOutput)
    def run_workflow(request: WorkflowInput) -> WorkflowOutput:
        return workflow.run(
            WorkflowOrchestratorInput(workflow_input=request)
        ).output

    mount_copilotkit_runtime(app, graph=workflow.graph)

    return app


app = create_app()
