import pytest

from app.agents import (
    WorkflowOrchestratorInput,
    default_agents,
    evaluate_workflow,
)
from app.agents.decision_rules import DefaultDecisionPolicy
from app.agents.human_review import PassthroughHumanReviewGate, RecordedHumanReviewGate
from app.agents.orchestration.runner import run_workflow_evaluation
from app.agents.profile_matching import DefaultProfileMatcher
from app.agents.signal_extraction import DefaultSignalExtractor
from app.agents.wiring import create_agents
from app.agents.workflow_planning.planning import create_workflow_plan
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
def test_fixture_decisions(fixture_name):
    assert evaluate_workflow(workflow_input(fixture_name)).decision.decision == expected_decision(
        fixture_name
    )


def test_parsed_job_description():
    profile = UserProfile(**load_fixture("strong_match.json")["user_profile"])
    output = evaluate_workflow(
        WorkflowInput(user_profile=profile, job_description=parse_job_description(AI_ENGINEER_JOB_TEXT))
    )
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


@pytest.mark.parametrize(
    "runtime_version, extractor_name",
    [("v1", "DefaultSignalExtractor"), ("v2", "LLMSignalExtractor")],
)
def test_create_agents_selects_extractor(monkeypatch, runtime_version, extractor_name):
    monkeypatch.setenv("RUNTIME_CONFIG_VERSION", runtime_version)
    assert create_agents(client=mock_llm_client())[-1]._extractor.__class__.__name__ == extractor_name


def test_create_agents_rejects_unknown_mode():
    with pytest.raises(ValueError, match="Unsupported signal extractor mode"):
        create_agents(signal_extractor="magic")


def test_orchestrator_returns_inspectable_run():
    *_, orchestrator = default_agents()
    result = orchestrator.run(
        WorkflowOrchestratorInput(workflow_input=workflow_input("strong_match.json"))
    )
    run = result.run
    assert run.is_complete and run.output == result.output
    assert run.events[0].event_type == WorkflowEventType.RUN_STARTED
    assert run.events[-1].event_type == WorkflowEventType.RUN_COMPLETED


def test_prepare_path_state_history():
    _, run = _run(workflow_input("strong_match.json"))
    expected = [
        WorkflowState.INTAKE,
        WorkflowState.SIGNAL_EXTRACTION,
        WorkflowState.PROFILE_MATCHING,
        WorkflowState.POLICY_EVALUATION,
        WorkflowState.DECISION,
    ]
    assert run.state_history == expected
    assert run.plan.stages == expected
    assert run.plan_report and run.plan_report.followed_plan


def test_risk_posting_escalates_through_human_review():
    output, run = _run(escalating_workflow_input())
    assert output.decision.decision == DecisionType.ESCALATE
    assert WorkflowState.HUMAN_REVIEW in run.state_history
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
    assert run.plan_report.unplanned_stages == [WorkflowState.HUMAN_REVIEW]


@pytest.mark.parametrize(
    "review_gate,expected_decision,is_revised",
    [
        (
            RecordedHumanReviewGate(
                revised_decision=WorkflowDecision(decision=DecisionType.QUEUE, score=0.5),
                reviewer_notes="Scope clarified with recruiter.",
            ),
            DecisionType.QUEUE,
            True,
        ),
        (RecordedHumanReviewGate(), DecisionType.ESCALATE, False),
    ],
)
def test_review_gate_outcomes(review_gate, expected_decision, is_revised):
    output, run = _run(escalating_workflow_input(), review_gate=review_gate)
    assert output.decision.decision == expected_decision
    assert run.review
    assert run.review.is_revised is is_revised


def test_run_logs_agent_traces():
    _, run = _run(workflow_input("strong_match.json"))
    assert run.events[1].event_type == WorkflowEventType.PLAN_CREATED
    assert [(trace.stage, trace.agent) for trace in run.traces] == [
        (WorkflowState.SIGNAL_EXTRACTION, "DefaultSignalExtractor"),
        (WorkflowState.PROFILE_MATCHING, "DefaultProfileMatcher"),
        (WorkflowState.POLICY_EVALUATION, "DefaultDecisionPolicy"),
    ]


def test_escalated_run_is_traceable():
    output, run = _run(escalating_workflow_input())
    chain = run.execution_trace()
    assert [trace.stage for trace in chain] == [
        WorkflowState.SIGNAL_EXTRACTION,
        WorkflowState.PROFILE_MATCHING,
        WorkflowState.POLICY_EVALUATION,
        WorkflowState.HUMAN_REVIEW,
        WorkflowState.DECISION,
    ]
    assert chain[-1].output["decision"] == output.decision.decision
