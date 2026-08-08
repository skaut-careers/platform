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
from app.agents.workflow_planning.plan import PlanExecutionReport, WorkflowPlan


class WorkflowGraphState(BaseModel):
    """Data + thin audit trail that flow through / are checkpointed by the graph."""

    workflow_id: str = Field(default_factory=lambda: str(uuid4()))

    profile_text: str | None = None
    job_description_text: str | None = None

    user_profile: UserProfile | None = None
    job_description: JobDescription | None = None
    plan: WorkflowPlan = Field(default_factory=WorkflowPlan)

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
        *,
        workflow_id: str | None = None,
    ) -> WorkflowGraphState:
        """Build initial graph state: validated texts + ``RUN_STARTED`` audit event."""
        started_at = datetime.now(timezone.utc)
        kwargs: dict = {
            "profile_text": workflow_input.profile_text,
            "job_description_text": workflow_input.job_description_text,
            "started_at": started_at,
            "events": [
                WorkflowEvent(
                    event_type=WorkflowEventType.RUN_STARTED,
                    stage="run",
                    timestamp=started_at,
                    message="Workflow run started.",
                )
            ],
        }
        if workflow_id is not None:
            kwargs["workflow_id"] = workflow_id
        return cls(**kwargs)

    @property
    def executed_stages(self) -> list[str]:
        """Stages visited, derived from STAGE_ENTERED events."""
        return [
            event.stage
            for event in self.events
            if event.event_type == WorkflowEventType.STAGE_ENTERED
        ]

    @property
    def current_stage(self) -> str:
        stages = self.executed_stages
        if not stages:
            raise RuntimeError("No stages have been entered yet")
        return stages[-1]

    @property
    def is_complete(self) -> bool:
        return self.output is not None and self.completed_at is not None
