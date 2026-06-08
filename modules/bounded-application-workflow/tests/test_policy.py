import pytest

from app.domain.job_signals import JobSignals
from app.domain.models import (
    DecisionType,
    JobDescription,
    ProfileMatchResult,
    UserProfile,
    WorkflowInput,
)
from app.parser import parse_job_description
from app.domain.workflow_state import WorkflowState
from app.services.policy import (
    build_workflow_decision,
    decision_from_score,
    decision_from_signals,
    evaluate_workflow,
    run_workflow_evaluation,
)
from tests.fixture_helpers import (
    WORKFLOW_FIXTURES,
    expected_decision,
    load_fixture,
    workflow_input as load_workflow_input,
)
from tests.test_extractor import RAW_JOB_TEXT


@pytest.mark.parametrize(
    "score,expected",
    [
        (0.0, DecisionType.SKIP),
        (0.34, DecisionType.SKIP),
        (0.35, DecisionType.ESCALATE),
        (0.54, DecisionType.ESCALATE),
        (0.55, DecisionType.QUEUE),
        (0.74, DecisionType.QUEUE),
        (0.75, DecisionType.PREPARE),
        (1.0, DecisionType.PREPARE),
    ],
)
def test_decision_from_score_thresholds(score: float, expected: DecisionType):
    assert decision_from_score(score) == expected


def test_decision_from_signals_escalates_on_risk_indicators():
    signals = JobSignals(risk_indicators=["ambiguous scope"])

    assert decision_from_signals(0.9, signals) == DecisionType.ESCALATE


def test_decision_from_signals_keeps_prepare_without_risks():
    assert decision_from_signals(0.9, JobSignals()) == DecisionType.PREPARE


def test_decision_from_signals_skips_on_severe_seniority_mismatch():
    signals = JobSignals(risk_indicators=["ambiguous scope"])

    assert (
        decision_from_signals(0.9, signals, severe_seniority_mismatch=True)
        == DecisionType.SKIP
    )


def test_build_workflow_decision_maps_match_and_signals():
    match = ProfileMatchResult(
        score=0.82,
        reasons=["Matched 1 of 2 required skills."],
        risks=["Missing required skills: Kubernetes."],
    )
    signals = JobSignals(
        risk_indicators=["ambiguous scope"],
        missing_signals=["salary range"],
    )

    decision = build_workflow_decision(match, signals)

    assert decision.decision == DecisionType.ESCALATE
    assert decision.score == match.score
    assert decision.reasons == match.reasons
    assert decision.risks == match.risks
    assert decision.missing_information == [
        "Job posting missing signal: salary range"
    ]


@pytest.mark.parametrize("fixture_name", WORKFLOW_FIXTURES)
def test_evaluate_workflow_fixture_decisions(fixture_name: str):
    output = evaluate_workflow(load_workflow_input(fixture_name))

    assert output.decision.decision == expected_decision(fixture_name)


def test_evaluate_workflow_from_parsed_job_description():
    profile = UserProfile(**load_fixture("strong_match.json")["user_profile"])
    job = parse_job_description(RAW_JOB_TEXT)

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
    _, state_machine = run_workflow_evaluation(load_workflow_input("strong_match.json"))

    assert state_machine.history == [
        WorkflowState.INTAKE,
        WorkflowState.SIGNAL_EXTRACTION,
        WorkflowState.PROFILE_MATCHING,
        WorkflowState.POLICY_EVALUATION,
        WorkflowState.DECISION,
    ]


def test_run_workflow_evaluation_state_trace_for_escalate():
    fixture = load_fixture("risk_extraction.json")
    job = JobDescription(**fixture["job_description"])
    profile = load_workflow_input("ambiguous_match.json").user_profile
    workflow_input = WorkflowInput(user_profile=profile, job_description=job)

    output, state_machine = run_workflow_evaluation(workflow_input)

    assert output.decision.decision == DecisionType.ESCALATE
    assert state_machine.history == [
        WorkflowState.INTAKE,
        WorkflowState.SIGNAL_EXTRACTION,
        WorkflowState.PROFILE_MATCHING,
        WorkflowState.POLICY_EVALUATION,
        WorkflowState.HUMAN_REVIEW,
        WorkflowState.DECISION,
    ]
