from fastapi import FastAPI

from app.agents import WorkflowOrchestrator, WorkflowOrchestratorInput, create_agents
from app.domain.models import WorkflowInput, WorkflowOutput


def create_app(*, orchestrator: WorkflowOrchestrator | None = None) -> FastAPI:
    resolved_orchestrator = orchestrator or create_agents()[-1]

    app = FastAPI(
        title="Bounded Application Workflow",
        description="Evaluate opportunities against a user profile.",
        version="0.1.0",
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/workflow/run", response_model=WorkflowOutput)
    def run_workflow(workflow_input: WorkflowInput) -> WorkflowOutput:
        result = resolved_orchestrator.run(
            WorkflowOrchestratorInput(workflow_input=workflow_input)
        )
        return result.output

    return app


app = create_app()
