from datetime import datetime, timezone

import pytest

from app.agents import (
    WorkflowOrchestratorInput,
    approve_escalation,
    default_agents,
    evaluate_workflow,
    revise_escalation,
)
from app.agents.decision_rules import DefaultDecisionPolicy
from app.agents.orchestration.audit import HumanReviewRecord, WorkflowEventType
from app.agents.orchestration.graph import compile_workflow_graph
from app.agents.orchestration.runner import (
    execute_workflow_pipeline,
    resume_workflow_pipeline,
)
from app.agents.orchestration.state import WorkflowGraphState
from app.agents.profile_matching import DefaultProfileMatcher
from app.agents.signal_extraction import DefaultSignalExtractor, LLMSignalExtractor
from app.agents.wiring import create_agents
from app.agents.workflow_planning.planner import create_workflow_plan
from app.domain.models import DecisionType, JobDescription, UserProfile, WorkflowDecision, WorkflowInput
from app.agents.workflow_planning.plan import (
    DECISION,
    HUMAN_REVIEW,
    INTAKE,
    POLICY_EVALUATION,
    PROFILE_MATCHING,
    SIGNAL_EXTRACTION,
)
from app.runtime import RuntimeConfig
from app.runtime.result import ExecutionStatus
from app.parser import parse_job_description
from tests.conftest import (
    AI_ENGINEER_JOB_TEXT,
    WORKFLOW_FIXTURES,
    escalating_workflow_input,
    expected_decision,
    load_fixture,
    runtime_config,
    signals_test_model,
    workflow_input,
)


def _run(workflow: WorkflowInput):
    """Run to completion (auto-approve any escalation interrupt)."""
    result = execute_workflow_pipeline(
        workflow,
        plan=create_workflow_plan(workflow),
        extractor=DefaultSignalExtractor(),
        matcher=DefaultProfileMatcher(),
        policy=DefaultDecisionPolicy(),
    )
    if result.is_interrupted:
        assert result.review_interrupt is not None
        result = resume_workflow_pipeline(
            result,
            approve_escalation(
                result.review_interrupt.decision,
                requested_at=result.review_interrupt.requested_at,
            ),
        )
    assert result.state.output is not None
    return result.state.output, result.state


def _evaluate(workflow: WorkflowInput):
    """Deterministic path — pinned so local `.env` LLM configs cannot drift decisions."""
    return evaluate_workflow(workflow, runtime_config=runtime_config(version="v1"))


@pytest.mark.parametrize("fixture_name", WORKFLOW_FIXTURES)
def test_fixture_decisions(fixture_name):
    assert _evaluate(workflow_input(fixture_name)).decision.decision == expected_decision(
        fixture_name
    )


def test_parsed_job_description():
    profile = UserProfile(**load_fixture("strong_match.json")["user_profile"])
    output = _evaluate(
        WorkflowInput(user_profile=profile, job_description=parse_job_description(AI_ENGINEER_JOB_TEXT))
    )
    assert output.decision.decision == DecisionType.PREPARE


def test_severe_seniority_gap_skips():
    output = _evaluate(
        WorkflowInput(
            user_profile=UserProfile(
                name="Ana",
                skills=["Python"],
                seniority="staff",
                experience_summary="Platform leadership.",
                target_roles=["Engineer"],
            ),
            job_description=JobDescription(
                title="Junior Engineer",
                description="Build features.\n\n- Python",
                seniority="junior",
            ),
        )
    )
    assert output.decision.decision == DecisionType.SKIP


@pytest.mark.parametrize(
    "runtime_version, extractor_name",
    [("v1", "DefaultSignalExtractor"), ("v2", "LLMSignalExtractor")],
)
def test_create_agents_selects_extractor(runtime_version, extractor_name):
    config = runtime_config(version=runtime_version)
    assert (
        create_agents(model=signals_test_model(), runtime_config=config)[-1]
        ._extractor.__class__.__name__
        == extractor_name
    )


def test_create_agents_rejects_unknown_mode():
    with pytest.raises(ValueError, match="Unsupported signal extractor mode"):
        create_agents(
            signal_extractor="magic",
            runtime_config=runtime_config(version="v1"),
        )


def test_orchestrator_returns_inspectable_run():
    *_, orchestrator = default_agents()
    result = orchestrator.run(
        WorkflowOrchestratorInput(workflow_input=workflow_input("strong_match.json"))
    )
    run = result.run
    assert run.is_complete and run.output == result.output
    assert run.events[0].event_type == WorkflowEventType.RUN_STARTED
    assert run.events[-1].event_type == WorkflowEventType.RUN_COMPLETED


def test_prepare_path_executed_stages():
    _, run = _run(workflow_input("strong_match.json"))
    expected = [
        INTAKE,
        SIGNAL_EXTRACTION,
        PROFILE_MATCHING,
        POLICY_EVALUATION,
        DECISION,
    ]
    assert run.executed_stages == expected
    assert run.plan.stages == expected
    assert run.plan_report and run.plan_report.followed_plan


def test_risk_posting_escalates_through_human_review():
    output, run = _run(escalating_workflow_input())
    assert output.decision.decision == DecisionType.ESCALATE
    assert HUMAN_REVIEW in run.executed_stages
    assert run.review and run.review.approved


def test_unplanned_human_review_is_reported():
    workflow = WorkflowInput(
        user_profile=UserProfile(
            name="Ana",
            target_roles=["Backend Engineer"],
            skills=["Go"],
            seniority="mid-senior",
        ),
        job_description=JobDescription(
            title="Backend Engineer",
            description="Backend role.\n\n- Python\n- Kubernetes\n- Terraform",
            seniority="mid-senior",
        ),
    )
    _, run = _run(workflow)
    assert run.plan_report
    assert not run.plan_report.followed_plan
    assert run.plan_report.unplanned_stages == [HUMAN_REVIEW]


@pytest.mark.parametrize(
    "resume_factory,expected_decision,is_revised",
    [
        (
            lambda interrupt: revise_escalation(
                WorkflowDecision(decision=DecisionType.QUEUE, score=0.5),
                requested_at=interrupt.requested_at,
                reviewer_notes="Scope clarified with recruiter.",
            ),
            DecisionType.QUEUE,
            True,
        ),
        (
            lambda interrupt: approve_escalation(
                interrupt.decision,
                requested_at=interrupt.requested_at,
            ),
            DecisionType.ESCALATE,
            False,
        ),
    ],
)
def test_review_resume_outcomes(resume_factory, expected_decision, is_revised):
    workflow = escalating_workflow_input()
    paused = execute_workflow_pipeline(
        workflow,
        plan=create_workflow_plan(workflow),
        extractor=DefaultSignalExtractor(),
        matcher=DefaultProfileMatcher(),
        policy=DefaultDecisionPolicy(),
    )
    assert paused.is_interrupted
    assert paused.review_interrupt is not None
    assert paused.state.output is None

    resumed = resume_workflow_pipeline(
        paused,
        resume_factory(paused.review_interrupt),
    )
    assert resumed.state.output is not None
    assert resumed.state.output.decision.decision == expected_decision
    assert resumed.state.review is not None
    assert resumed.state.review.is_revised is is_revised
    assert resumed.state.review.requested_at == paused.review_interrupt.requested_at
    assert resumed.state.review.reviewed_at is not None
    assert resumed.state.review.reviewed_at >= resumed.state.review.requested_at


def test_escalation_pauses_before_decision():
    workflow = escalating_workflow_input()
    paused = execute_workflow_pipeline(
        workflow,
        plan=create_workflow_plan(workflow),
        extractor=DefaultSignalExtractor(),
        matcher=DefaultProfileMatcher(),
        policy=DefaultDecisionPolicy(),
    )

    assert paused.is_interrupted
    assert paused.review_interrupt is not None
    assert paused.review_interrupt.decision.decision == DecisionType.ESCALATE
    assert paused.state.decision is not None
    assert paused.state.decision.decision == DecisionType.ESCALATE
    assert paused.state.output is None
    assert paused.state.review is None
    assert HUMAN_REVIEW not in paused.state.executed_stages
    assert DECISION not in paused.state.executed_stages
    assert paused.graph.get_state(
        {"configurable": {"thread_id": paused.workflow_id}}
    ).next == (HUMAN_REVIEW,)


def test_run_logs_agent_completed_events():
    _, run = _run(workflow_input("strong_match.json"))
    assert run.events[1].event_type == WorkflowEventType.PLAN_CREATED
    agent_events = [
        (event.stage, event.message)
        for event in run.events
        if event.event_type == WorkflowEventType.AGENT_COMPLETED
    ]
    assert agent_events == [
        (SIGNAL_EXTRACTION, "Agent 'DefaultSignalExtractor' completed."),
        (PROFILE_MATCHING, "Agent 'DefaultProfileMatcher' completed."),
        (POLICY_EVALUATION, "Agent 'DefaultDecisionPolicy' completed."),
    ]


def test_llm_signal_extractor_includes_execution_metadata():
    from app.agents.contracts import SignalExtractorInput

    extractor = LLMSignalExtractor(
        model=signals_test_model(
            required_skills=["Python", "LLM applications"],
            preferred_skills=["research background"],
        ),
        runtime_config=RuntimeConfig.build(),
    )
    output = extractor.run(
        SignalExtractorInput(job_description=workflow_input("strong_match.json").job_description)
    )
    assert output.execution is not None
    assert output.execution.prompt_hash
    assert output.execution.config_version
    assert output.execution.config_hash
    assert output.execution.attempts == 1
    assert output.execution.used_fallback is False
    assert output.execution.status == ExecutionStatus.SUCCESS


def test_escalated_run_is_auditable():
    output, run = _run(escalating_workflow_input())
    assert [
        event.stage
        for event in run.events
        if event.event_type == WorkflowEventType.AGENT_COMPLETED
    ] == [SIGNAL_EXTRACTION, PROFILE_MATCHING, POLICY_EVALUATION]
    assert [
        event.event_type
        for event in run.events
        if event.stage == HUMAN_REVIEW
    ] == [
        WorkflowEventType.STAGE_ENTERED,
        WorkflowEventType.REVIEW_REQUESTED,
        WorkflowEventType.REVIEW_COMPLETED,
    ]
    assert run.events[-1].event_type == WorkflowEventType.RUN_COMPLETED
    assert run.output is not None
    assert run.output.decision.decision == output.decision.decision


def test_langgraph_checkpointer_reconstructs_run():
    workflow = workflow_input("strong_match.json")
    plan = create_workflow_plan(workflow)
    graph = compile_workflow_graph(
        extractor=DefaultSignalExtractor(),
        matcher=DefaultProfileMatcher(),
        policy=DefaultDecisionPolicy(),
    )
    initial = WorkflowGraphState.from_workflow_input(workflow, plan)
    config = {"configurable": {"thread_id": initial.workflow_id}}
    result = WorkflowGraphState.model_validate(graph.invoke(initial, config))
    restored = WorkflowGraphState.model_validate(graph.get_state(config).values)

    assert restored.workflow_id == result.workflow_id
    assert restored.is_complete
    assert restored.output == result.output
    assert restored.executed_stages == result.executed_stages
    assert [event.event_type for event in restored.events] == [
        event.event_type for event in result.events
    ]


def test_human_review_record_pending_and_revised():
    original = WorkflowDecision(
        decision=DecisionType.ESCALATE,
        score=0.5,
        risks=["ambiguous scope"],
    )
    pending = HumanReviewRecord(
        reason="Risky posting.",
        original_decision=original,
        requested_at=datetime.now(timezone.utc),
    )
    assert pending.is_pending is True
    assert pending.is_revised is False

    revised = pending.model_copy(
        update={
            "final_decision": WorkflowDecision(decision=DecisionType.QUEUE, score=0.5),
            "approved": False,
            "reviewed_at": datetime.now(timezone.utc),
        }
    )
    assert revised.is_pending is False
    assert revised.is_revised is True
