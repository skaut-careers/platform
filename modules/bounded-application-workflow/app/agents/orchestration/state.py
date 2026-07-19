from __future__ import annotations

from uuid import uuid4

from pydantic import BaseModel, Field

from app.domain.job_signals import JobSignals
from app.domain.models import (
    JobDescription,
    ProfileMatchResult,
    UserProfile,
    WorkflowDecision,
    WorkflowInput,
    WorkflowOutput,
)
from app.domain.workflow_run import WorkflowPlan


class WorkflowGraphState(BaseModel):
    """Data that flows through the StateGraph nodes."""

    workflow_id: str = Field(default_factory=lambda: str(uuid4()))
    user_profile: UserProfile
    job_description: JobDescription
    plan: WorkflowPlan

    signals: JobSignals | None = None
    match: ProfileMatchResult | None = None
    decision: WorkflowDecision | None = None
    output: WorkflowOutput | None = None

    @classmethod
    def from_workflow_input(
        cls,
        workflow_input: WorkflowInput,
        plan: WorkflowPlan,
        *,
        workflow_id: str | None = None,
    ) -> WorkflowGraphState:
        kwargs: dict = {
            "user_profile": workflow_input.user_profile,
            "job_description": workflow_input.job_description,
            "plan": plan,
        }
        if workflow_id is not None:
            kwargs["workflow_id"] = workflow_id
        return cls(**kwargs)

    def to_workflow_input(self) -> WorkflowInput:
        return WorkflowInput(
            user_profile=self.user_profile,
            job_description=self.job_description,
        )
