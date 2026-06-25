from datetime import datetime
from enum import Enum
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, computed_field

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


class ExecutionStatus(str, Enum):
    """Outcome of a single runtime execution."""

    SUCCESS = "success"
    FAILED = "failed"


class RuntimeExecutionError(RuntimeError):
    """Raised when a failed execution result is unwrapped."""


class AgentExecutionResult(BaseModel, Generic[OutputT]):
    """Auditable record of one agent execution through the runtime."""

    agent_name: str
    config_id: str
    config_version: str
    config_hash: str
    status: ExecutionStatus
    attempts: int
    started_at: datetime
    completed_at: datetime
    output: Optional[OutputT] = None
    error: Optional[str] = None
    used_fallback: bool = False
    prompt_hash: Optional[str] = None

    @computed_field
    @property
    def duration_ms(self) -> float:
        return (self.completed_at - self.started_at).total_seconds() * 1000

    @property
    def succeeded(self) -> bool:
        return self.status == ExecutionStatus.SUCCESS

    def unwrap(self) -> OutputT:
        """Return the typed output or raise if the execution failed."""
        if not self.succeeded or self.output is None:
            raise RuntimeExecutionError(
                f"Agent '{self.agent_name}' execution failed after "
                f"{self.attempts} attempt(s): {self.error or 'no output produced'}"
            )
        return self.output

    def without_output(self) -> "AgentExecutionResult[OutputT]":
        """Return an audit copy without the nested agent output."""
        return self.model_copy(update={"output": None})
