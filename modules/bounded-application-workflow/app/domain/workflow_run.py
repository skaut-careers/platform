from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, computed_field

from app.domain.models import WorkflowDecision, WorkflowInput, WorkflowOutput
from app.domain.state_machine import WorkflowStateMachine
from app.domain.workflow_state import InvalidTransitionError, WorkflowState


class WorkflowEventType(str, Enum):
    RUN_STARTED = "run_started"
    STATE_ENTERED = "state_entered"
    REVIEW_COMPLETED = "review_completed"
    RUN_COMPLETED = "run_completed"


class WorkflowEvent(BaseModel):
    event_type: WorkflowEventType
    state: WorkflowState
    timestamp: datetime
    message: str = ""


class HumanReviewRecord(BaseModel):
    """Why a run entered human review and how the review was resolved."""

    reason: str
    original_decision: WorkflowDecision
    final_decision: Optional[WorkflowDecision] = None
    approved: Optional[bool] = None
    reviewer_notes: str = ""
    requested_at: datetime
    reviewed_at: Optional[datetime] = None

    @property
    def is_pending(self) -> bool:
        return self.approved is None

    @property
    def is_revised(self) -> bool:
        return (
            self.final_decision is not None
            and self.final_decision != self.original_decision
        )


class WorkflowPlan(BaseModel):
    """Describes intended workflow stages before execution."""

    stages: list[WorkflowState] = Field(default_factory=list)


class PlanExecutionReport(BaseModel):
    """Comparison of planned stages against the executed state history."""

    planned_stages: list[WorkflowState]
    executed_stages: list[WorkflowState]
    unplanned_stages: list[WorkflowState]
    skipped_stages: list[WorkflowState]
    followed_plan: bool


def default_workflow_plan() -> WorkflowPlan:
    return WorkflowPlan(
        stages=[
            WorkflowState.INTAKE,
            WorkflowState.SIGNAL_EXTRACTION,
            WorkflowState.PROFILE_MATCHING,
            WorkflowState.POLICY_EVALUATION,
            WorkflowState.DECISION,
        ],
    )


class WorkflowRun(BaseModel):
    """Runtime record of a single workflow execution."""

    model_config = ConfigDict(validate_assignment=True)

    workflow_id: str = Field(default_factory=lambda: str(uuid4()))
    input: WorkflowInput
    plan: WorkflowPlan
    output: Optional[WorkflowOutput] = None
    review: Optional[HumanReviewRecord] = None
    plan_report: Optional[PlanExecutionReport] = None
    events: list[WorkflowEvent] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

    _state_machine: WorkflowStateMachine = PrivateAttr()

    def model_post_init(self, __context: object) -> None:
        self._state_machine = WorkflowStateMachine()

    @computed_field
    @property
    def current_state(self) -> WorkflowState:
        return self._state_machine.current_state

    @property
    def state_history(self) -> list[WorkflowState]:
        return self._state_machine.history

    @property
    def is_complete(self) -> bool:
        return (
            self.current_state == WorkflowState.DECISION
            and self.output is not None
            and self.completed_at is not None
        )

    def can_transition_to(self, target: WorkflowState) -> bool:
        return self._state_machine.can_transition_to(target)

    def record_event(
        self,
        event_type: WorkflowEventType,
        state: WorkflowState,
        message: str = "",
        *,
        timestamp: Optional[datetime] = None,
    ) -> WorkflowEvent:
        event = WorkflowEvent(
            event_type=event_type,
            state=state,
            timestamp=timestamp or datetime.now(timezone.utc),
            message=message,
        )
        self.events.append(event)
        return event

    def transition_to(self, target: WorkflowState, message: str = "") -> WorkflowState:
        self._state_machine.transition_to(target)
        self.record_event(WorkflowEventType.STATE_ENTERED, target, message)
        return target

    def request_review(
        self, reason: str, decision: WorkflowDecision
    ) -> HumanReviewRecord:
        if self.current_state != WorkflowState.HUMAN_REVIEW:
            raise ValueError(
                "Review can only be requested while the run is in the "
                f"'{WorkflowState.HUMAN_REVIEW.value}' state, "
                f"not '{self.current_state.value}'."
            )
        if self.review is not None:
            raise ValueError("A review was already requested for this run.")
        self.review = HumanReviewRecord(
            reason=reason,
            original_decision=decision,
            requested_at=datetime.now(timezone.utc),
        )
        return self.review

    def resolve_review(
        self,
        *,
        final_decision: WorkflowDecision,
        approved: bool,
        reviewer_notes: str = "",
    ) -> HumanReviewRecord:
        if self.review is None:
            raise ValueError("No review was requested for this run.")
        if not self.review.is_pending:
            raise ValueError("The review for this run was already resolved.")
        self.review.final_decision = final_decision
        self.review.approved = approved
        self.review.reviewer_notes = reviewer_notes
        self.review.reviewed_at = datetime.now(timezone.utc)
        outcome = (
            "approved"
            if not self.review.is_revised
            else f"revised to '{final_decision.decision.value}'"
        )
        self.record_event(
            WorkflowEventType.REVIEW_COMPLETED,
            WorkflowState.HUMAN_REVIEW,
            f"Human review {outcome}.",
        )
        return self.review

    def compare_plan(self) -> PlanExecutionReport:
        planned = list(self.plan.stages)
        executed = list(self.state_history)
        return PlanExecutionReport(
            planned_stages=planned,
            executed_stages=executed,
            unplanned_stages=[
                stage for stage in executed if stage not in planned
            ],
            skipped_stages=[
                stage for stage in planned if stage not in executed
            ],
            followed_plan=planned == executed,
        )

    def complete(self, output: WorkflowOutput) -> None:
        if self.current_state != WorkflowState.DECISION:
            self.transition_to(WorkflowState.DECISION)
        self.output = output
        self.completed_at = datetime.now(timezone.utc)
        self.plan_report = self.compare_plan()
        self.record_event(
            WorkflowEventType.RUN_COMPLETED,
            WorkflowState.DECISION,
            "Workflow run completed.",
        )


__all__ = [
    "HumanReviewRecord",
    "InvalidTransitionError",
    "PlanExecutionReport",
    "WorkflowEvent",
    "WorkflowEventType",
    "WorkflowPlan",
    "WorkflowRun",
    "default_workflow_plan",
]
