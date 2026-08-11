from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agents.contracts import (
    DecisionPolicy,
    DecisionPolicyInput,
    ProfileExtractor,
    ProfileExtractorInput,
    ProfileMatcher,
    ProfileMatcherInput,
    SignalExtractor,
    SignalExtractorInput,
)
from app.agents.orchestration.audit import (
    WorkflowEvent,
    WorkflowEventType,
)
from app.agents.orchestration.stages import (
    DECISION,
    POLICY_APPLICATION,
    PROFILE_EXTRACTION,
    PROFILE_MATCHING,
    SIGNAL_EXTRACTION,
)
from app.agents.orchestration.state import WorkflowGraphState
from app.domain.job_signals import JobSignals
from app.domain.models import (
    DecisionType,
    JobDescription,
    ProfileMatchResult,
    UserProfile,
    WorkflowDecision,
    WorkflowInput,
    WorkflowOutput,
)
from app.parser import parse_job_description
from app.runtime.result import AgentExecutionResult, ExecutionStatus

_NEXT_STEPS: dict[DecisionType, list[str]] = {
    DecisionType.PREPARE: [
        "Tailor your CV to highlight matched skills and role alignment.",
        "Draft a concise cover letter addressing any remaining gaps.",
        "Prepare talking points for interviews based on the job description.",
    ],
    DecisionType.QUEUE: [
        "Save this opportunity for a later review cycle.",
        "Note what would need to change before actively pursuing it.",
        "Re-run the workflow if your profile or priorities shift.",
    ],
    DecisionType.ESCALATE: [
        "Review the opportunity manually before investing application time.",
        "Clarify ambiguous requirements with the recruiter or hiring team.",
        "Fill in missing profile or job signals, then run again.",
    ],
    DecisionType.SKIP: [
        "Record why this opportunity is not a fit for future reference.",
        "Focus search effort on roles that align with your target profile.",
    ],
}

_CHECKPOINT_TYPES = (
    UserProfile,
    JobDescription,
    WorkflowInput,
    WorkflowOutput,
    WorkflowDecision,
    ProfileMatchResult,
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


def _input_summary(state: WorkflowGraphState) -> str:
    if state.job_description is None:
        raise RuntimeError("input summary requires job_description")
    company = state.job_description.company or "an unspecified company"
    return (
        f"Profile is being matched against "
        f"{state.job_description.title} at {company}."
    )


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
    matcher: ProfileMatcher,
    policy: DecisionPolicy,
) -> StateGraph:

    def profile_extraction(state: WorkflowGraphState) -> dict[str, Any]:
        if state.profile_text is None:
            raise RuntimeError("profile_extraction requires profile_text")
        events = _enter_stage(state.events, PROFILE_EXTRACTION)
        user_profile = profile_extractor.run(
            ProfileExtractorInput(raw_text=state.profile_text)
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
        job_description = parse_job_description(state.job_description_text)
        output = extractor.run(
            SignalExtractorInput(job_description=job_description)
        )
        events = _record_agent_completed(
            events,
            stage=SIGNAL_EXTRACTION,
            agent=type(extractor).__name__,
        )
        return {
            "job_description": job_description,
            "signals": output.signals,
            "events": events,
        }

    def profile_matching(state: WorkflowGraphState) -> dict[str, Any]:
        if (
            state.signals is None
            or state.user_profile is None
            or state.job_description is None
        ):
            raise RuntimeError(
                "profile_matching requires signals, user_profile, and job_description"
            )
        events = _enter_stage(state.events, PROFILE_MATCHING)
        output = matcher.run(
            ProfileMatcherInput(
                user_profile=state.user_profile,
                job_description=state.job_description,
                signals=state.signals,
            )
        )
        events = _record_agent_completed(
            events,
            stage=PROFILE_MATCHING,
            agent=type(matcher).__name__,
        )
        return {
            "match": output.match,
            "events": events,
        }

    def policy_application(state: WorkflowGraphState) -> dict[str, Any]:
        if state.signals is None or state.match is None:
            raise RuntimeError("policy_application requires signals and match")
        events = _enter_stage(state.events, POLICY_APPLICATION)
        output = policy.run(
            DecisionPolicyInput(match=state.match, signals=state.signals)
        )
        events = _record_agent_completed(
            events,
            stage=POLICY_APPLICATION,
            agent=type(policy).__name__,
        )
        return {
            "decision": output.decision,
            "events": events,
        }

    def decision(state: WorkflowGraphState) -> dict[str, Any]:
        if state.decision is None or state.signals is None or state.match is None:
            raise RuntimeError("decision requires decision, signals, and match")

        events = _enter_stage(state.events, DECISION)
        output = WorkflowOutput(
            input_summary=_input_summary(state),
            decision=state.decision,
            job_signals=state.signals,
            recommended_next_steps=list(_NEXT_STEPS[state.decision.decision]),
        )
        completed_at = _now()
        events.append(
            _event(WorkflowEventType.RUN_COMPLETED, DECISION, "Workflow run completed.")
        )
        return {
            "output": output,
            "events": events,
            "completed_at": completed_at,
        }

    graph = StateGraph(WorkflowGraphState)
    graph.add_node(PROFILE_EXTRACTION, profile_extraction)
    graph.add_node(SIGNAL_EXTRACTION, signal_extraction)
    graph.add_node(PROFILE_MATCHING, profile_matching)
    graph.add_node(POLICY_APPLICATION, policy_application)
    graph.add_node(DECISION, decision)

    graph.add_edge(START, PROFILE_EXTRACTION)
    graph.add_edge(PROFILE_EXTRACTION, SIGNAL_EXTRACTION)
    graph.add_edge(SIGNAL_EXTRACTION, PROFILE_MATCHING)
    graph.add_edge(PROFILE_MATCHING, POLICY_APPLICATION)
    graph.add_edge(POLICY_APPLICATION, DECISION)
    graph.add_edge(DECISION, END)
    return graph


def compile_workflow_graph(
    *,
    profile_extractor: ProfileExtractor,
    extractor: SignalExtractor,
    matcher: ProfileMatcher,
    policy: DecisionPolicy,
    checkpointer: MemorySaver | None = None,
) -> CompiledStateGraph:
    return build_workflow_graph(
        profile_extractor=profile_extractor,
        extractor=extractor,
        matcher=matcher,
        policy=policy,
    ).compile(checkpointer=checkpointer or default_checkpointer())
