from __future__ import annotations

from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agents.contracts import (
    DecisionPolicy,
    DecisionPolicyInput,
    HumanReviewGate,
    HumanReviewGateInput,
    ProfileMatcher,
    ProfileMatcherInput,
    SignalExtractor,
    SignalExtractorInput,
)
from app.agents.decision_rules.rules import review_reason
from app.agents.orchestration.state import WorkflowGraphState
from app.domain.models import DecisionType, WorkflowOutput
from app.domain.workflow_run import WorkflowEventType, WorkflowRun
from app.domain.workflow_state import WorkflowState

_NEXT_STEPS: dict[DecisionType, list[str]] = {
    DecisionType.PREPARE: [
        "Tailor your CV to highlight matched skills and role alignment.",
        "Draft a concise cover letter addressing any remaining gaps.",
        "Prepare talking points for interviews based on the job description.",
    ],
    DecisionType.QUEUE: [
        "Save this opportunity for a later review cycle.",
        "Note what would need to change before actively pursuing it.",
        "Re-run evaluation if your profile or priorities shift.",
    ],
    DecisionType.ESCALATE: [
        "Review the opportunity manually before investing application time.",
        "Clarify ambiguous requirements with the recruiter or hiring team.",
        "Fill in missing profile or job signals, then re-evaluate.",
    ],
    DecisionType.SKIP: [
        "Record why this opportunity is not a fit for future reference.",
        "Focus search effort on roles that align with your target profile.",
    ],
}


def _input_summary(state: WorkflowGraphState) -> str:
    company = state.job_description.company or "an unspecified company"
    return (
        f"{state.user_profile.name} is being evaluated for "
        f"{state.job_description.title} at {company}."
    )


def build_workflow_graph(
    *,
    extractor: SignalExtractor,
    matcher: ProfileMatcher,
    policy: DecisionPolicy,
    review_gate: HumanReviewGate | None,
    run: WorkflowRun,
) -> StateGraph:

    def intake(state: WorkflowGraphState) -> dict[str, Any]:
        run.record_event(
            WorkflowEventType.RUN_STARTED,
            WorkflowState.INTAKE,
            "Workflow run started.",
        )
        run.record_plan()
        return {}

    def signal_extraction(state: WorkflowGraphState) -> dict[str, Any]:
        run.transition_to(WorkflowState.SIGNAL_EXTRACTION)
        output = extractor.run(
            SignalExtractorInput(job_description=state.job_description)
        )
        run.record_agent_trace(type(extractor).__name__, output)
        return {"signals": output.signals}

    def profile_matching(state: WorkflowGraphState) -> dict[str, Any]:
        if state.signals is None:
            raise RuntimeError("profile_matching requires signals on graph state")
        run.transition_to(WorkflowState.PROFILE_MATCHING)
        output = matcher.run(
            ProfileMatcherInput(
                user_profile=state.user_profile,
                job_description=state.job_description,
                signals=state.signals,
            )
        )
        run.record_agent_trace(type(matcher).__name__, output)
        return {"match": output.match}

    def policy_evaluation(state: WorkflowGraphState) -> dict[str, Any]:
        if state.signals is None or state.match is None:
            raise RuntimeError("policy_evaluation requires signals and match")
        run.transition_to(WorkflowState.POLICY_EVALUATION)
        output = policy.run(
            DecisionPolicyInput(match=state.match, signals=state.signals)
        )
        run.record_agent_trace(type(policy).__name__, output)
        return {"decision": output.decision}

    def decision(state: WorkflowGraphState) -> dict[str, Any]:
        if state.decision is None or state.signals is None or state.match is None:
            raise RuntimeError("decision requires decision, signals, and match")

        current = state.decision
        if current.decision == DecisionType.ESCALATE:
            reason = review_reason(current)
            run.transition_to(WorkflowState.HUMAN_REVIEW, reason)
            run.request_review(reason, current)
            if review_gate is not None:
                gate_output = review_gate.run(
                    HumanReviewGateInput(
                        decision=current,
                        match=state.match,
                        signals=state.signals,
                        reason=reason,
                    )
                )
                run.record_agent_trace(type(review_gate).__name__, gate_output)
                review = run.resolve_review(
                    final_decision=gate_output.decision,
                    approved=gate_output.approved,
                    reviewer_notes=gate_output.reviewer_notes,
                )
                current = review.final_decision or current

        run.transition_to(WorkflowState.DECISION)
        output = WorkflowOutput(
            input_summary=_input_summary(state),
            decision=current,
            job_signals=state.signals,
            recommended_next_steps=list(_NEXT_STEPS[current.decision]),
        )
        run.complete(output)
        return {"decision": current, "output": output}

    graph = StateGraph(WorkflowGraphState)
    graph.add_node("intake", intake)
    graph.add_node("signal_extraction", signal_extraction)
    graph.add_node("profile_matching", profile_matching)
    graph.add_node("policy_evaluation", policy_evaluation)
    graph.add_node("decision", decision)

    graph.add_edge(START, "intake")
    graph.add_edge("intake", "signal_extraction")
    graph.add_edge("signal_extraction", "profile_matching")
    graph.add_edge("profile_matching", "policy_evaluation")
    graph.add_edge("policy_evaluation", "decision")
    graph.add_edge("decision", END)
    return graph


def compile_workflow_graph(
    *,
    extractor: SignalExtractor,
    matcher: ProfileMatcher,
    policy: DecisionPolicy,
    review_gate: HumanReviewGate | None,
    run: WorkflowRun,
    checkpointer: MemorySaver | None = None,
) -> CompiledStateGraph:
    return build_workflow_graph(
        extractor=extractor,
        matcher=matcher,
        policy=policy,
        review_gate=review_gate,
        run=run,
    ).compile(checkpointer=checkpointer or MemorySaver())
