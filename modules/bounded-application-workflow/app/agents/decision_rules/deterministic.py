from app.domain.job_signals import JobSignals
from app.domain.models import (
    DecisionType,
    ProfileMatchResult,
    WorkflowDecision,
)

# MVP thresholds — docs/PRD.md
_PREPARE_MIN = 0.75
_QUEUE_MIN = 0.55


def decision_from_score(score: float) -> DecisionType:
    if score >= _PREPARE_MIN:
        return DecisionType.PREPARE
    if score >= _QUEUE_MIN:
        return DecisionType.QUEUE
    return DecisionType.SKIP


def decision_from_signals(
    score: float,
    job_signals: JobSignals,
    *,
    severe_seniority_mismatch: bool = False,
) -> DecisionType:
    """Map match score to a decision, then apply seniority skip."""
    if severe_seniority_mismatch:
        return DecisionType.SKIP
    return decision_from_score(score)


def build_workflow_decision(
    match: ProfileMatchResult,
    job_signals: JobSignals,
) -> WorkflowDecision:
    decision = decision_from_signals(
        match.score,
        job_signals,
        severe_seniority_mismatch=match.severe_seniority_mismatch,
    )

    return WorkflowDecision(
        decision=decision,
        score=match.score,
        reasons=list(match.reasons),
        risks=list(match.risks),
        missing_information=[
            f"Job posting missing signal: {signal}"
            for signal in job_signals.missing_signals
        ],
    )
