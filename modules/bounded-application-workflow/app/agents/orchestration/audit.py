from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel

from app.domain.models import WorkflowDecision


class WorkflowEventType(str, Enum):
    RUN_STARTED = "run_started"
    PLAN_CREATED = "plan_created"
    STAGE_ENTERED = "stage_entered"
    AGENT_COMPLETED = "agent_completed"
    REVIEW_REQUESTED = "review_requested"
    REVIEW_COMPLETED = "review_completed"
    RUN_COMPLETED = "run_completed"


class WorkflowEvent(BaseModel):
    event_type: WorkflowEventType
    stage: str
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


__all__ = [
    "HumanReviewRecord",
    "WorkflowEvent",
    "WorkflowEventType",
]
