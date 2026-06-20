import pytest

from app.agents import (
    WorkflowOrchestratorInput,
    default_agents,
    evaluate_workflow,
    run_workflow_evaluation as run_default_workflow,
)
from app.agents.default import (
    DefaultDecisionPolicy,
    DefaultProfileMatcher,
    DefaultSignalExtractor,
    PassthroughHumanReviewGate,
    RecordedHumanReviewGate,
    create_agents,
)
from app.agents.orchestration import run_workflow_evaluation
from app.agents.workflow_planning import create_workflow_plan
from app.domain.models import DecisionType, JobDescription, UserProfile, WorkflowDecision, WorkflowInput
from app.domain.workflow_run import WorkflowEventType
from app.domain.workflow_state import WorkflowState
from app.parser import parse_job_description
from tests.conftest import (
    AI_ENGINEER_JOB_TEXT,
    WORKFLOW_FIXTURES,
    escalating_workflow_input,
    expected_decision,
    load_fixture,
    mock_llm_client,
    workflow_input,
)


def _run(
    workflow: WorkflowInput,
    *,
    review_gate: PassthroughHumanReviewGate | RecordedHumanReviewGate | None = None,
):
    return run_workflow_evaluation(
        workflow,
        plan=create_workflow_plan(workflow),
        extractor=DefaultSignalExtractor(),
        matcher=DefaultProfileMatcher(),
        policy=DefaultDecisionPolicy(),
        review_gate=review_gate or PassthroughHumanReviewGate(),
    )


@pytest.mark.parametrize("fixture_name", WORKFLOW_FIXTURES)
def test_fixture_decisions(fixture_name: str):
    output = evaluate_workflow(workflow_input(fixture_name))
    assert output.decision.decision == expected_decision(fixture_name)


def test_parsed_job_description():
    profile = UserProfile(**load_fixture("strong_match.json")["user_profile"])
    job = parse_job_description(AI_ENGINEER_JOB_TEXT)

    output = evaluate_workflow(WorkflowInput(user_profile=profile, job_description=job))

    assert output.decision.decision == DecisionType.PREPARE


def test_severe_seniority_gap_skips():
    output = evaluate_workflow(
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


def test_orchestrator_returns_inspectable_run():
    *_, orchestrator = default_agents()
    result = orchestrator.run(
        WorkflowOrchestratorInput(workflow_input=workflow_input("strong_match.json"))
    )

    run = result.run
    assert run.is_complete is True
    assert run.output == result.output
    assert run.events[0].event_type == WorkflowEventType.RUN_STARTED
    assert run.events[-1].event_type == WorkflowEventType.RUN_COMPLETED
    assert run.model_dump()["output"]["decision"]["decision"] == result.output.decision.decision.value


def test_run_workflow_evaluation_uses_default_wiring():
    output, run = run_default_workflow(workflow_input("strong_match.json"))

    assert output.decision.decision == DecisionType.PREPARE
    assert run.is_complete is True


@pytest.mark.parametrize(
    "env, extractor_name",
    [
        (None, "DefaultSignalExtractor"),
        ("llm", "LLMSignalExtractor"),
    ],
)
def test_create_agents_selects_extractor(monkeypatch, env, extractor_name):
    if env is None:
        monkeypatch.delenv("SIGNAL_EXTRACTOR", raising=False)
    else:
        monkeypatch.setenv("SIGNAL_EXTRACTOR", env)

    *_, orchestrator = create_agents(client=mock_llm_client())

    assert orchestrator._extractor.__class__.__name__ == extractor_name


def test_create_agents_rejects_unknown_mode(monkeypatch):
    monkeypatch.setenv("SIGNAL_EXTRACTOR", "magic")

    with pytest.raises(ValueError, match="Unsupported SIGNAL_EXTRACTOR"):
        create_agents()


def test_prepare_path_state_history():
    _, run = _run(workflow_input("strong_match.json"))

    assert run.state_history == [
        WorkflowState.INTAKE,
        WorkflowState.SIGNAL_EXTRACTION,
        WorkflowState.PROFILE_MATCHING,
        WorkflowState.POLICY_EVALUATION,
        WorkflowState.DECISION,
    ]
    assert run.plan.stages == run.state_history
    assert run.plan_report is not None
    assert run.plan_report.followed_plan is True


def test_risk_posting_escalates_through_human_review():
    output, run = _run(escalating_workflow_input())

    assert output.decision.decision == DecisionType.ESCALATE
    assert run.is_complete is True
    assert run.state_history == [
        WorkflowState.INTAKE,
        WorkflowState.SIGNAL_EXTRACTION,
        WorkflowState.PROFILE_MATCHING,
        WorkflowState.POLICY_EVALUATION,
        WorkflowState.HUMAN_REVIEW,
        WorkflowState.DECISION,
    ]
    assert WorkflowState.HUMAN_REVIEW in run.plan.stages
    assert run.plan_report is not None
    assert run.plan_report.followed_plan is True
    assert run.review is not None
    assert run.review.reason.startswith("Escalated for human review")
    assert run.review.approved is True


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

    output, run = _run(workflow)

    assert output.decision.decision == DecisionType.ESCALATE
    assert WorkflowState.HUMAN_REVIEW not in run.plan.stages
    report = run.plan_report
    assert report is not None
    assert report.followed_plan is False
    assert report.unplanned_stages == [WorkflowState.HUMAN_REVIEW]
    assert report.skipped_stages == []


def test_review_gate_revises_escalated_decision():
    revised = WorkflowDecision(decision=DecisionType.QUEUE, score=0.5)
    output, run = _run(
        escalating_workflow_input(),
        review_gate=RecordedHumanReviewGate(
            revised_decision=revised,
            reviewer_notes="Scope clarified with recruiter.",
        ),
    )

    assert output.decision == revised
    assert run.review is not None
    assert run.review.is_revised is True
    assert run.review.reviewer_notes == "Scope clarified with recruiter."


def test_review_gate_approves_escalated_decision():
    output, run = _run(
        escalating_workflow_input(),
        review_gate=RecordedHumanReviewGate(),
    )

    assert output.decision.decision == DecisionType.ESCALATE
    assert run.review is not None
    assert run.review.approved is True
    assert run.review.is_revised is False


def test_run_logs_planner_decision_and_agent_outputs():
    _, run = _run(workflow_input("strong_match.json"))

    assert run.events[1].event_type == WorkflowEventType.PLAN_CREATED
    assert "intake -> signal_extraction" in run.events[1].message

    assert [(trace.stage, trace.agent) for trace in run.traces] == [
        (WorkflowState.SIGNAL_EXTRACTION, "DefaultSignalExtractor"),
        (WorkflowState.PROFILE_MATCHING, "DefaultProfileMatcher"),
        (WorkflowState.POLICY_EVALUATION, "DefaultDecisionPolicy"),
    ]
    matcher_trace, policy_trace = run.traces[1], run.traces[2]
    assert policy_trace.output["decision"]["decision"] == DecisionType.PREPARE
    assert policy_trace.output["decision"]["score"] == matcher_trace.output["match"]["score"]


def test_escalated_run_decision_is_traceable():
    output, run = _run(escalating_workflow_input())

    chain = run.execution_trace()
    assert [trace.stage for trace in chain] == [
        WorkflowState.SIGNAL_EXTRACTION,
        WorkflowState.PROFILE_MATCHING,
        WorkflowState.POLICY_EVALUATION,
        WorkflowState.HUMAN_REVIEW,
        WorkflowState.DECISION,
    ]
    assert chain[3].agent == "PassthroughHumanReviewGate"
    assert chain[-1].agent == "workflow"
    assert chain[-1].output["decision"] == output.decision.decision
    assert chain[-1].timestamp == run.completed_at

    event_types = [event.event_type for event in run.events]
    assert event_types.index(WorkflowEventType.REVIEW_REQUESTED) < event_types.index(
        WorkflowEventType.REVIEW_COMPLETED
    )


def test_workflow_history_serializable_after_execution():
    _, run = _run(escalating_workflow_input())

    dumped = run.model_dump(mode="json")

    assert dumped["events"][0]["event_type"] == "run_started"
    assert dumped["events"][-1]["event_type"] == "run_completed"
    assert [trace["stage"] for trace in dumped["traces"]] == [
        "signal_extraction",
        "profile_matching",
        "policy_evaluation",
        "human_review",
    ]
    description = run.input.job_description.description
    assert all(description not in str(trace["output"]) for trace in dumped["traces"])
