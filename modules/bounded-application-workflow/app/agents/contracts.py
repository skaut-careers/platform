from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, Protocol

from pydantic import BaseModel

from app.domain.job_signals import JobSignals
from app.domain.models import (
    JobDescription,
    ProfileMatchResult,
    UserProfile,
    WorkflowDecision,
    WorkflowInput,
    WorkflowOutput,
)
from app.agents.workflow_planning.plan import WorkflowPlan
from app.runtime.result import AgentExecutionResult

if TYPE_CHECKING:
    from app.agents.orchestration.state import WorkflowGraphState


class AgentOutput(BaseModel):
    """Base for LLM-backed agent outputs carrying execution provenance."""

    execution: Optional[AgentExecutionResult[Any]] = None


class WorkflowPlannerInput(BaseModel):
    """Profile + extracted signals used to estimate the execution plan."""

    user_profile: UserProfile
    signals: JobSignals


class WorkflowPlannerOutput(BaseModel):
    plan: WorkflowPlan


class WorkflowPlanner(Protocol):
    """Estimate stages (incl. optional human_review) from extracted signals."""

    def run(self, agent_input: WorkflowPlannerInput) -> WorkflowPlannerOutput: ...


class SignalExtractorInput(BaseModel):
    """Raw job description to parse into structured signals."""

    job_description: JobDescription


class SignalExtractorOutput(AgentOutput):
    signals: JobSignals


class SignalExtractor(Protocol):
    """Parse job descriptions into structured signal categories."""

    def run(self, agent_input: SignalExtractorInput) -> SignalExtractorOutput: ...


class ProfileExtractorInput(BaseModel):

    raw_text: str


class ProfileExtractorOutput(AgentOutput):
    profile: UserProfile


class ProfileExtractor(Protocol):

    def run(self, agent_input: ProfileExtractorInput) -> ProfileExtractorOutput: ...


class ProfileMatcherInput(BaseModel):

    user_profile: UserProfile
    job_description: JobDescription
    signals: JobSignals


class ProfileMatcherOutput(AgentOutput):
    match: ProfileMatchResult


class ProfileMatcher(Protocol):

    def run(self, agent_input: ProfileMatcherInput) -> ProfileMatcherOutput: ...


class DecisionPolicyInput(BaseModel):

    match: ProfileMatchResult
    signals: JobSignals


class DecisionPolicyOutput(BaseModel):
    decision: WorkflowDecision


class DecisionPolicy(Protocol):

    def run(self, agent_input: DecisionPolicyInput) -> DecisionPolicyOutput: ...


class WorkflowOrchestratorInput(BaseModel):

    workflow_input: WorkflowInput


class WorkflowOrchestratorOutput(BaseModel):
    output: WorkflowOutput
    run: WorkflowGraphState


class WorkflowOrchestrator(Protocol):
    """Coordinate graph execution from raw product texts."""

    def run(
        self, agent_input: WorkflowOrchestratorInput
    ) -> WorkflowOrchestratorOutput: ...
