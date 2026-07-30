from fastapi import FastAPI
from pydantic import BaseModel, field_validator

from app.agents import WorkflowOrchestrator, WorkflowOrchestratorInput, create_agents
from app.agents.contracts import ProfileExtractor, ProfileExtractorInput
from app.agents.wiring import create_profile_extractor
from app.domain.models import WorkflowInput, WorkflowOutput
from app.observability import instrument_app
from app.parser import parse_job_description


class WorkflowRunRequest(BaseModel):
    """Raw profile text (concatenated frontend fields) + raw job posting text."""

    profile_text: str
    job_description_text: str

    @field_validator("profile_text", "job_description_text")
    @classmethod
    def _require_nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value


def create_app(
    *,
    orchestrator: WorkflowOrchestrator | None = None,
    profile_extractor: ProfileExtractor | None = None,
) -> FastAPI:
    """HTTP app; `/workflow/run` extracts the profile, parses the job, then runs the graph."""
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
        return workflow.run(
            WorkflowOrchestratorInput(
                workflow_input=WorkflowInput(
                    user_profile=profile,
                    job_description=parse_job_description(
                        request.job_description_text
                    ),
                )
            )
        ).output

    return app


app = create_app()
