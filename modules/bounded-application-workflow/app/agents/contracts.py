from typing import Optional, Protocol

from pydantic import BaseModel, Field

from app.domain.job_signals import JobSignals
from app.runtime.result import ExecutionStatus
from app.domain.models import (
    JobDescription,
    ProfileMatchResult,
    UserProfile,
    WorkflowDecision,
    WorkflowInput,
    WorkflowOutput,
)
from app.domain.workflow_run import WorkflowPlan, WorkflowRun


class WorkflowPlannerInput(BaseModel):
    """Workflow input from which to estimate an execution plan."""

    workflow_input: WorkflowInput


class WorkflowPlannerOutput(BaseModel):
    plan: WorkflowPlan


class WorkflowPlanner(Protocol):
    """Estimate stages, evaluation focus and required signals before execution."""

    def run(self, agent_input: WorkflowPlannerInput) -> WorkflowPlannerOutput: ...


class SignalExtractorInput(BaseModel):
    """Raw job description to parse into structured signals."""

    job_description: JobDescription


class SignalExtractionMetadata(BaseModel):
    """Runtime metadata for auditable LLM-backed extraction."""

    agent_name: str
    config_version: str
    status: ExecutionStatus
    attempts: int
    duration_ms: float
    used_fallback: bool = False
    error: Optional[str] = None


class SignalExtractorOutput(BaseModel):
    signals: JobSignals
    metadata: Optional[SignalExtractionMetadata] = None


class SignalExtractor(Protocol):
    """Parse job descriptions into structured signal categories."""

    def run(self, agent_input: SignalExtractorInput) -> SignalExtractorOutput: ...


class ProfileMatcherInput(BaseModel):
    """Extracted signals plus candidate profile for alignment scoring."""

    user_profile: UserProfile
    job_description: JobDescription
    signals: JobSignals


class ProfileMatcherOutput(BaseModel):
    match: ProfileMatchResult


class ProfileMatcher(Protocol):
    """Score profile alignment against extracted signals."""

    def run(self, agent_input: ProfileMatcherInput) -> ProfileMatcherOutput: ...


class DecisionPolicyInput(BaseModel):
    """Match outcome and job signals for bounded decision rules."""

    match: ProfileMatchResult
    signals: JobSignals


class DecisionPolicyOutput(BaseModel):
    decision: WorkflowDecision


class DecisionPolicy(Protocol):
    """Apply bounded thresholds and escalation rules."""

    def run(self, agent_input: DecisionPolicyInput) -> DecisionPolicyOutput: ...


class HumanReviewGateInput(BaseModel):
    """Escalated decision with evaluation context for human review."""

    decision: WorkflowDecision
    match: ProfileMatchResult
    signals: JobSignals
    reason: str = Field(default="")


class HumanReviewGateOutput(BaseModel):
    """Human-approved or revised decision."""

    decision: WorkflowDecision
    approved: bool
    reviewer_notes: str = Field(default="")


class HumanReviewGate(Protocol):
    """Pause execution for ambiguous or high-stakes decisions."""

    def run(self, agent_input: HumanReviewGateInput) -> HumanReviewGateOutput: ...


class WorkflowOrchestratorInput(BaseModel):
    workflow_input: WorkflowInput


class WorkflowOrchestratorOutput(BaseModel):
    output: WorkflowOutput
    run: WorkflowRun


class WorkflowOrchestrator(Protocol):
    """Manage state transitions and coordinate agent stages."""

    def run(
        self, agent_input: WorkflowOrchestratorInput
    ) -> WorkflowOrchestratorOutput: ...
