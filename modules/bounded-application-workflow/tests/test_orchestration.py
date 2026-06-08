import pytest

from app.domain.models import (
    DecisionType,
    JobDescription,
    UserProfile,
    WorkflowInput,
)
from app.domain.workflow_run import WorkflowEventType
from app.parser import parse_job_description
from app.domain.workflow_state import WorkflowState
from app.agents import evaluate_workflow, run_workflow_evaluation
from tests.fixture_helpers import (
    AI_ENGINEER_JOB_TEXT,
    WORKFLOW_FIXTURES,
    expected_decision,
    load_fixture,
    workflow_input as load_workflow_input,
)


@pytest.mark.parametrize("fixture_name", WORKFLOW_FIXTURES)
def test_evaluate_workflow_fixture_decisions(fixture_name: str):
    output = evaluate_workflow(load_workflow_input(fixture_name))

    assert output.decision.decision == expected_decision(fixture_name)


def test_evaluate_workflow_from_parsed_job_description():
    profile = UserProfile(**load_fixture("strong_match.json")["user_profile"])
    job = parse_job_description(AI_ENGINEER_JOB_TEXT)

    output = evaluate_workflow(
        WorkflowInput(user_profile=profile, job_description=job)
    )

    assert output.decision.decision == expected_decision("strong_match.json")


def test_evaluate_workflow_surfaces_missing_job_signals():
    output = evaluate_workflow(load_workflow_input("ambiguous_match.json"))

    assert "Job posting missing signal: remote policy" in (
        output.decision.missing_information
    )


def test_evaluate_workflow_severe_seniority_gap_skips():
    profile = UserProfile(
        name="Ana",
        skills=["Python"],
        seniority="staff",
        experience_summary="Platform leadership background.",
        target_roles=["Engineer"],
    )
    job = JobDescription(
        title="Junior Engineer",
        description="Build features.\n\n- Python",
        seniority="junior",
    )

    output = evaluate_workflow(
        WorkflowInput(user_profile=profile, job_description=job)
    )

    assert output.decision.decision == DecisionType.SKIP


def test_evaluate_workflow_risk_fixture_escalates():
    fixture = load_fixture("risk_extraction.json")
    job = JobDescription(**fixture["job_description"])
    profile = load_workflow_input("ambiguous_match.json").user_profile

    output = evaluate_workflow(
        WorkflowInput(user_profile=profile, job_description=job)
    )

    assert output.decision.decision == DecisionType.ESCALATE


def test_run_workflow_evaluation_state_trace_for_prepare():
    _, run = run_workflow_evaluation(load_workflow_input("strong_match.json"))

    assert run.state_history == [
        WorkflowState.INTAKE,
        WorkflowState.SIGNAL_EXTRACTION,
        WorkflowState.PROFILE_MATCHING,
        WorkflowState.POLICY_EVALUATION,
        WorkflowState.DECISION,
    ]
    assert run.is_complete is True


def test_run_workflow_evaluation_state_trace_for_escalate():
    fixture = load_fixture("risk_extraction.json")
    job = JobDescription(**fixture["job_description"])
    profile = load_workflow_input("ambiguous_match.json").user_profile
    workflow_input = WorkflowInput(user_profile=profile, job_description=job)

    output, run = run_workflow_evaluation(workflow_input)

    assert output.decision.decision == DecisionType.ESCALATE
    assert run.state_history == [
        WorkflowState.INTAKE,
        WorkflowState.SIGNAL_EXTRACTION,
        WorkflowState.PROFILE_MATCHING,
        WorkflowState.POLICY_EVALUATION,
        WorkflowState.HUMAN_REVIEW,
        WorkflowState.DECISION,
    ]
    assert run.is_complete is True


def test_completed_workflow_run_is_inspectable():
    output, run = run_workflow_evaluation(load_workflow_input("strong_match.json"))

    assert run.is_complete is True
    assert run.output == output
    assert run.completed_at is not None
    assert run.workflow_id
    assert run.current_state == WorkflowState.DECISION
    assert run.events[0].event_type == WorkflowEventType.RUN_STARTED
    assert run.events[-1].event_type == WorkflowEventType.RUN_COMPLETED

    snapshot = run.model_dump()
    assert snapshot["workflow_id"] == run.workflow_id
    assert snapshot["current_state"] == WorkflowState.DECISION.value
    assert snapshot["output"]["decision"]["decision"] == output.decision.decision.value
    assert len(snapshot["events"]) >= 2
