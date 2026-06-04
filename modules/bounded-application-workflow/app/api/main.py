from fastapi import FastAPI

from app.domain.models import WorkflowInput, WorkflowOutput
from app.services.policy import evaluate_workflow

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
    return evaluate_workflow(workflow_input)
