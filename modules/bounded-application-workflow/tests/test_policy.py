import pytest

from app.domain.models import (
    DecisionType,
    JobDescription,
    ProfileMatchResult,
    UserProfile,
)
from app.services.policy import (
    build_workflow_decision,
    decision_from_score,
    evaluate_workflow,
)
from tests.fixture_helpers import workflow_input as load_workflow_input


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


def test_build_workflow_decision_carries_match_signals():
    profile = UserProfile(name="Ana", skills=["Python"])
    job = JobDescription(title="AI Engineer", description="Build AI systems.")
    match = ProfileMatchResult(
        score=0.82,
        reasons=["Strong skill overlap"],
        risks=["Seniority unclear"],
        required_skills_missing=["Kubernetes"],
    )

    decision = build_workflow_decision(match, profile, job)

    assert decision.decision == DecisionType.PREPARE
    assert decision.score == 0.82
    assert decision.reasons == ["Strong skill overlap"]
    assert decision.risks == ["Seniority unclear"]
    assert any("Kubernetes" in item for item in decision.missing_information)


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


def test_evaluate_workflow_strong_match_uses_score_policy():
    output = evaluate_workflow(load_workflow_input("strong_match.json"))

    assert 0.5 <= output.decision.score <= 1.0
    assert output.decision.decision == decision_from_score(output.decision.score)
    assert output.recommended_next_steps
