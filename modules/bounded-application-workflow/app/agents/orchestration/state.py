from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field

from app.agents.orchestration.audit import (
    HumanReviewRecord,
    WorkflowEvent,
    WorkflowEventType,
)
from app.domain.job_signals import JobSignals
from app.domain.models import (
    JobDescription,
    ProfileMatchResult,
    UserProfile,
    WorkflowDecision,
    WorkflowInput,
    WorkflowOutput,
)
from app.agents.workflow_planning.plan import INTAKE, PlanExecutionReport, WorkflowPlan


class WorkflowGraphState(BaseModel):
    """Data + thin audit trail that flow through / are checkpointed by the graph."""

    workflow_id: str = Field(default_factory=lambda: str(uuid4()))
    user_profile: UserProfile
    job_description: JobDescription
    plan: WorkflowPlan
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    signals: JobSignals | None = None
    match: ProfileMatchResult | None = None
    decision: WorkflowDecision | None = None
    output: WorkflowOutput | None = None
    review: HumanReviewRecord | None = None

    events: list[WorkflowEvent] = Field(default_factory=list)
    completed_at: datetime | None = None
    plan_report: PlanExecutionReport | None = None

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

    @property
    def executed_stages(self) -> list[str]:
        """Stages visited, derived from STAGE_ENTERED events (intake is implicit)."""
        entered = [
            event.stage
            for event in self.events
            if event.event_type == WorkflowEventType.STAGE_ENTERED
        ]
        return [INTAKE, *entered]

    @property
    def current_stage(self) -> str:
        return self.executed_stages[-1]

    @property
    def is_complete(self) -> bool:
        return self.output is not None and self.completed_at is not None
