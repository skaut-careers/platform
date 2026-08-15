from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, Protocol

from pydantic import BaseModel

from app.domain.models import (
    JobSignals,
    MatchDecision,
    UserProfile,
    WorkflowInput,
    WorkflowOutput,
)
from app.runtime.result import AgentExecutionResult

if TYPE_CHECKING:
    from app.agents.orchestration.state import WorkflowGraphState


class AgentOutput(BaseModel):
    """Base for LLM-backed agent outputs carrying execution provenance."""

    execution: Optional[AgentExecutionResult[Any]] = None


class JobSignalExtractorInput(BaseModel):
    """Raw job posting text to parse into structured signals."""

    job_description_text: str


class JobSignalExtractorOutput(AgentOutput):
    job_signals: JobSignals


class JobSignalExtractor(Protocol):
    """Parse job descriptions into structured signal categories."""

    def run(self, agent_input: JobSignalExtractorInput) -> JobSignalExtractorOutput: ...


class ProfileExtractorInput(BaseModel):

    profile_text: str


class ProfileExtractorOutput(AgentOutput):
    profile: UserProfile


class ProfileExtractor(Protocol):

    def run(self, agent_input: ProfileExtractorInput) -> ProfileExtractorOutput: ...


class MatchDeciderInput(BaseModel):
    user_profile: UserProfile
    job_signals: JobSignals


class MatchDeciderOutput(AgentOutput):
    result: MatchDecision


class MatchDecider(Protocol):
    """Match a profile and produce one terminal decision atomically."""

    def run(
        self, agent_input: MatchDeciderInput
    ) -> MatchDeciderOutput: ...


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
