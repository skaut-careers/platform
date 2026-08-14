from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, Protocol

from pydantic import BaseModel

from app.domain.models import (
    JobSignals,
    ProfileMatchResult,
    UserProfile,
    WorkflowDecision,
    WorkflowInput,
    WorkflowOutput,
)
from app.runtime.result import AgentExecutionResult

if TYPE_CHECKING:
    from app.agents.orchestration.state import WorkflowGraphState


class AgentOutput(BaseModel):
    """Base for LLM-backed agent outputs carrying execution provenance."""

    execution: Optional[AgentExecutionResult[Any]] = None


class SignalExtractorInput(BaseModel):
    """Raw job posting text to parse into structured signals."""

    job_description_text: str


class SignalExtractorOutput(AgentOutput):
    job_signals: JobSignals


class SignalExtractor(Protocol):
    """Parse job descriptions into structured signal categories."""

    def run(self, agent_input: SignalExtractorInput) -> SignalExtractorOutput: ...


class ProfileExtractorInput(BaseModel):

    profile_text: str


class ProfileExtractorOutput(AgentOutput):
    profile: UserProfile


class ProfileExtractor(Protocol):

    def run(self, agent_input: ProfileExtractorInput) -> ProfileExtractorOutput: ...


class ProfileMatcherInput(BaseModel):

    user_profile: UserProfile
    job_signals: JobSignals


class ProfileMatcherOutput(AgentOutput):
    match: ProfileMatchResult


class ProfileMatcher(Protocol):

    def run(self, agent_input: ProfileMatcherInput) -> ProfileMatcherOutput: ...


class DecisionPolicyInput(BaseModel):

    match: ProfileMatchResult
    job_signals: JobSignals


class DecisionPolicyOutput(AgentOutput):
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
