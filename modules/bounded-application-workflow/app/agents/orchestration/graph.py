from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agents.contracts import (
    ProfileExtractor,
    ProfileExtractorInput,
    MatchDecider,
    MatchDeciderInput,
    SignalExtractor,
    SignalExtractorInput,
)
from app.agents.orchestration.audit import (
    WorkflowEvent,
    WorkflowEventType,
)
from app.agents.orchestration.state import (
    MATCH_DECISION,
    PROFILE_EXTRACTION,
    SIGNAL_EXTRACTION,
    WorkflowGraphState,
)
from app.domain.models import JobSignals
from app.domain.models import (
    DecisionType,
    MatchDecision,
    UserProfile,
    WorkflowInput,
    WorkflowOutput,
)
from app.runtime.result import AgentExecutionResult, ExecutionStatus

_CHECKPOINT_TYPES = (
    UserProfile,
    WorkflowInput,
    WorkflowOutput,
    MatchDecision,
    DecisionType,
    JobSignals,
    WorkflowEvent,
    WorkflowEventType,
    AgentExecutionResult,
    ExecutionStatus,
)


def default_checkpointer() -> MemorySaver:
    """In-memory checkpointer with an allowlist for workflow domain types."""
    return MemorySaver(
        serde=JsonPlusSerializer(allowed_msgpack_modules=_CHECKPOINT_TYPES)
    )


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _event(
    event_type: WorkflowEventType,
    stage: str,
    message: str = "",
    *,
    timestamp: datetime | None = None,
) -> WorkflowEvent:
    return WorkflowEvent(
        event_type=event_type,
        stage=stage,
        timestamp=timestamp or _now(),
        message=message,
    )


def _enter_stage(
    events: list[WorkflowEvent],
    stage: str,
    message: str = "",
) -> list[WorkflowEvent]:
    return [*events, _event(WorkflowEventType.STAGE_ENTERED, stage, message)]


def _record_agent_completed(
    events: list[WorkflowEvent],
    *,
    stage: str,
    agent: str,
) -> list[WorkflowEvent]:
    return [
        *events,
        _event(
            WorkflowEventType.AGENT_COMPLETED,
            stage,
            f"Agent '{agent}' completed.",
        ),
    ]


def build_workflow_graph(
    *,
    profile_extractor: ProfileExtractor,
    extractor: SignalExtractor,
    match_decider: MatchDecider,
) -> StateGraph:

    def profile_extraction(state: WorkflowGraphState) -> dict[str, Any]:
        if state.profile_text is None:
            raise RuntimeError("profile_extraction requires profile_text")
        events = _enter_stage(state.events, PROFILE_EXTRACTION)
        user_profile = profile_extractor.run(
            ProfileExtractorInput(profile_text=state.profile_text)
        ).profile
        events = _record_agent_completed(
            events,
            stage=PROFILE_EXTRACTION,
            agent=type(profile_extractor).__name__,
        )
        return {
            "user_profile": user_profile,
            "events": events,
        }

    def signal_extraction(state: WorkflowGraphState) -> dict[str, Any]:
        if state.job_description_text is None:
            raise RuntimeError("signal_extraction requires job_description_text")
        events = _enter_stage(state.events, SIGNAL_EXTRACTION)
        output = extractor.run(
            SignalExtractorInput(job_description_text=state.job_description_text)
        )
        events = _record_agent_completed(
            events,
            stage=SIGNAL_EXTRACTION,
            agent=type(extractor).__name__,
        )
        return {
            "job_signals": output.job_signals,
            "events": events,
        }

    def match_decision(state: WorkflowGraphState) -> dict[str, Any]:
        if state.job_signals is None or state.user_profile is None:
            raise RuntimeError(
                "match_decision requires job_signals and user_profile"
            )
        events = _enter_stage(state.events, MATCH_DECISION)
        result = match_decider.run(
            MatchDeciderInput(
                user_profile=state.user_profile,
                job_signals=state.job_signals,
            )
        ).result
        events = _record_agent_completed(
            events,
            stage=MATCH_DECISION,
            agent=type(match_decider).__name__,
        )
        output = WorkflowOutput(
            decision=result.decision,
            score=result.score,
            reasons=list(result.reasons),
            risks=list(result.risks),
            missing_information=list(result.missing_information),
        )
        completed_at = _now()
        events.append(
            _event(
                WorkflowEventType.RUN_COMPLETED,
                MATCH_DECISION,
                "Workflow run completed.",
            )
        )
        return {
            "match_decision": result,
            "output": output,
            "events": events,
            "completed_at": completed_at,
        }

    graph = StateGraph(WorkflowGraphState)
    graph.add_node(PROFILE_EXTRACTION, profile_extraction)
    graph.add_node(SIGNAL_EXTRACTION, signal_extraction)
    graph.add_node(MATCH_DECISION, match_decision)

    graph.add_edge(START, PROFILE_EXTRACTION)
    graph.add_edge(PROFILE_EXTRACTION, SIGNAL_EXTRACTION)
    graph.add_edge(SIGNAL_EXTRACTION, MATCH_DECISION)
    graph.add_edge(MATCH_DECISION, END)
    return graph


def compile_workflow_graph(
    *,
    profile_extractor: ProfileExtractor,
    extractor: SignalExtractor,
    match_decider: MatchDecider,
    checkpointer: MemorySaver | None = None,
) -> CompiledStateGraph:
    return build_workflow_graph(
        profile_extractor=profile_extractor,
        extractor=extractor,
        match_decider=match_decider,
    ).compile(checkpointer=checkpointer or default_checkpointer())
