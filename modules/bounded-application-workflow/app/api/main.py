from fastapi import FastAPI
from pydantic import BaseModel

from app.agents import WorkflowOrchestrator, WorkflowOrchestratorInput, create_agents
from app.agents.contracts import ProfileExtractor, ProfileExtractorInput
from app.agents.wiring import create_profile_extractor
from app.domain.models import JobDescription, WorkflowInput, WorkflowOutput
from app.observability import instrument_app


class WorkflowRunRequest(BaseModel):
    """Raw candidate profile text (concatenated frontend fields / free text) plus
    the job to evaluate it against. The profile is structured server-side."""

    profile_text: str
    job_description: JobDescription


def create_app(
    *,
    orchestrator: WorkflowOrchestrator | None = None,
    profile_extractor: ProfileExtractor | None = None,
) -> FastAPI:
    """HTTP app; `/workflow/run` extracts the profile then runs the graph."""
    app = FastAPI(
        title="Bounded Application Workflow",
        description="Evaluate opportunities against a user profile.",
        version="0.1.0",
    )
    instrument_app(app)
    workflow = orchestrator or create_agents()[-1]
    extractor = profile_extractor or create_profile_extractor()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/workflow/run", response_model=WorkflowOutput)
    def run_workflow(request: WorkflowRunRequest) -> WorkflowOutput:
        profile = extractor.run(
            ProfileExtractorInput(raw_text=request.profile_text)
        ).profile
        workflow_input = WorkflowInput(
            user_profile=profile,
            job_description=request.job_description,
        )
        return workflow.run(
            WorkflowOrchestratorInput(workflow_input=workflow_input)
        ).output

    return app


app = create_app()
