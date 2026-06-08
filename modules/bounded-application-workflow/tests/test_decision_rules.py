import pytest

from app.domain.job_signals import JobSignals
from app.domain.models import DecisionType, ProfileMatchResult
from app.agents import (
    build_workflow_decision,
    decision_from_score,
    decision_from_signals,
)


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
