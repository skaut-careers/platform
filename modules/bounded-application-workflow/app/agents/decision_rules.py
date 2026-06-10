from app.domain.job_signals import JobSignals
from app.domain.models import (
    DecisionType,
    ProfileMatchResult,
    WorkflowDecision,
)

# MVP thresholds — docs/PRD.md
_PREPARE_MIN = 0.75
_QUEUE_MIN = 0.55
_ESCALATE_MIN = 0.35


def decision_from_score(score: float) -> DecisionType:
    if score >= _PREPARE_MIN:
        return DecisionType.PREPARE
    if score >= _QUEUE_MIN:
        return DecisionType.QUEUE
    if score >= _ESCALATE_MIN:
        return DecisionType.ESCALATE
    return DecisionType.SKIP


def decision_from_signals(
    score: float,
    signals: JobSignals,
    *,
    severe_seniority_mismatch: bool = False,
) -> DecisionType:
    """Map match score to a decision, then apply job-signal guardrails."""
    if severe_seniority_mismatch:
        return DecisionType.SKIP

    base = decision_from_score(score)

    # Risky postings require human review even when the profile match is strong.
    if base == DecisionType.PREPARE and signals.risk_indicators:
        return DecisionType.ESCALATE

    return base


def review_reason(decision: WorkflowDecision) -> str:
    """Explain why an escalated decision needs human review."""
    parts: list[str] = []
    if decision.risks:
        parts.append("risks: " + "; ".join(decision.risks))
    if decision.missing_information:
        parts.append("missing information: " + "; ".join(decision.missing_information))
    if not parts:
        parts.append(f"match score {decision.score:.2f} is in the escalation band")
    return "Escalated for human review: " + " | ".join(parts)


def build_workflow_decision(
    match: ProfileMatchResult,
    signals: JobSignals,
) -> WorkflowDecision:
    return WorkflowDecision(
        decision=decision_from_signals(
            match.score,
            signals,
            severe_seniority_mismatch=match.severe_seniority_mismatch,
        ),
        score=match.score,
        reasons=list(match.reasons),
        risks=list(match.risks),
        missing_information=[
            f"Job posting missing signal: {signal}"
            for signal in signals.missing_signals
        ],
    )
