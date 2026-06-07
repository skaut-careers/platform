import pytest

from app.domain.job_signals import JobSignals
from app.domain.models import (
    DecisionType,
    JobDescription,
    ProfileMatchResult,
    UserProfile,
)
from app.services.extractor import extract_job_signals
from app.services.policy import (
    build_workflow_decision,
    decision_from_score,
    decision_from_signals,
    evaluate_workflow,
)
from tests.fixture_helpers import load_fixture, workflow_input as load_workflow_input


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


def test_decision_from_signals_escalates_when_risk_indicators_present():
    signals = JobSignals(risk_indicators=["ambiguous scope"])

    assert decision_from_signals(0.9, signals) == DecisionType.ESCALATE
    assert decision_from_signals(0.9, JobSignals()) == DecisionType.PREPARE


def test_build_workflow_decision_carries_match_and_job_signals():
    profile = UserProfile(name="Ana", skills=["Python"], seniority="senior")
    match = ProfileMatchResult(
        score=0.82,
        required_skills_matched=["Python"],
        required_skills_missing=["Kubernetes"],
        reasons=[
            "Matched 1 of 2 required skills.",
            "Seniority meets job expectations (job: senior, profile: senior).",
        ],
        risks=["Missing required skills: Kubernetes."],
    )
    signals = JobSignals(
        required_skills=["Python", "Kubernetes"],
        preferred_skills=[],
        seniority_signals=["senior"],
        production_expectations=["on-call rotation"],
        risk_indicators=["ambiguous scope"],
        missing_signals=["remote policy", "salary range"],
    )

    decision = build_workflow_decision(match, profile, signals)

    assert decision.decision == DecisionType.ESCALATE
    assert decision.score == match.score
    assert decision.reasons == match.reasons
    assert "Missing required skills: Kubernetes." in decision.risks
    assert "Job posting risk: ambiguous scope" in decision.risks
    assert "Job production expectation: on-call rotation" in decision.risks
    assert (
        "Required skill not evidenced in profile: Kubernetes"
        in decision.missing_information
    )
    assert "Job posting missing signal: remote policy" in decision.missing_information


@pytest.mark.parametrize(
    "fixture_name,expected_decision",
    [
        ("weak_match.json", DecisionType.SKIP),
        ("ambiguous_match.json", DecisionType.ESCALATE),
    ],
)
def test_evaluate_workflow_fixture_decisions(
    fixture_name: str, expected_decision: DecisionType
):
    output = evaluate_workflow(load_workflow_input(fixture_name))
    assert output.decision.decision == expected_decision
    assert output.input_summary
    assert output.recommended_next_steps
    assert output.job_signals.required_skills


def test_evaluate_workflow_ambiguous_match_uses_job_signal_risks():
    output = evaluate_workflow(load_workflow_input("ambiguous_match.json"))

    assert any(
        "ambiguous scope" in risk for risk in output.decision.risks
    )
    assert any(
        "remote policy" in item for item in output.decision.missing_information
    )
    assert any(
        "seniority level" in item for item in output.decision.missing_information
    )


def test_evaluate_workflow_strong_match_uses_score_policy():
    output = evaluate_workflow(load_workflow_input("strong_match.json"))

    assert 0.5 <= output.decision.score <= 1.0
    assert output.decision.decision == decision_from_signals(
        output.decision.score, output.job_signals
    )
    assert output.recommended_next_steps
    assert output.job_signals.required_skills == [
        "Python",
        "LLM applications",
        "evaluation pipelines",
        "agentic workflows",
        "product ownership",
    ]
    assert any(
        "Seniority meets job expectations" in reason
        for reason in output.decision.reasons
    )
    assert any(
        "salary range" in item for item in output.decision.missing_information
    )


def test_evaluate_workflow_risk_fixture_signals_flow_into_decision():
    fixture = load_fixture("risk_extraction.json")
    job = JobDescription(**fixture["job_description"])
    profile = load_workflow_input("ambiguous_match.json").user_profile
    signals = extract_job_signals(job)
    decision = build_workflow_decision(
        ProfileMatchResult(score=0.8, reasons=["Strong overlap"]),
        profile,
        signals,
    )

    assert decision.decision == DecisionType.ESCALATE
    assert any("ambiguous scope" in risk for risk in decision.risks)
    assert len(decision.missing_information) >= len(signals.missing_signals)
