from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class WorkflowEventType(str, Enum):
    RUN_STARTED = "run_started"
    PLAN_CREATED = "plan_created"
    STAGE_ENTERED = "stage_entered"
    AGENT_COMPLETED = "agent_completed"
    RUN_COMPLETED = "run_completed"


class WorkflowEvent(BaseModel):
    event_type: WorkflowEventType
    stage: str
    timestamp: datetime
    message: str = ""


__all__ = [
    "WorkflowEvent",
    "WorkflowEventType",
]
