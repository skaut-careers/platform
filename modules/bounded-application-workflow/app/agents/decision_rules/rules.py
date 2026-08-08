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

_UNUSABLE_MISSING_SIGNAL_MIN = 3
# Only nonsense / empty-posting cues — not normal JD risks like ownership or scope.
_UNUSABLE_RISK_MARKERS = (
    "gibberish",
    "nonsens",
    "unusable",
    "no requirements",
    "no responsibilities",
    "unclear hiring",
)


def decision_from_score(score: float) -> DecisionType:
    if score >= _PREPARE_MIN:
        return DecisionType.PREPARE
    if score >= _QUEUE_MIN:
        return DecisionType.QUEUE
    if score >= _ESCALATE_MIN:
        return DecisionType.ESCALATE
    return DecisionType.SKIP


def _flagged_unusable(*risk_groups: list[str]) -> bool:
    for group in risk_groups:
        for risk in group:
            text = risk.casefold()
            if any(marker in text for marker in _UNUSABLE_RISK_MARKERS):
                return True
    return False


def unusable_job_posting(
    signals: JobSignals,
    *,
    match_risks: list[str] | None = None,
) -> bool:
    """Hard-pass hollow/gibberish text only — not real jobs with ordinary risk flags."""
    many_gaps = len(signals.missing_signals) >= _UNUSABLE_MISSING_SIGNAL_MIN
    hollow = _flagged_unusable(signals.risk_indicators, match_risks or [])
    has_skills = bool(signals.required_skills or signals.preferred_skills)

    if not has_skills:
        return many_gaps or hollow

    # Invented skills on nonsense text: need explicit hollow cues, not "high ownership".
    return many_gaps and hollow


def decision_from_signals(
    score: float,
    signals: JobSignals,
    *,
    severe_seniority_mismatch: bool = False,
    match_risks: list[str] | None = None,
) -> DecisionType:
    """Map match score to a decision, then apply job-signal guardrails."""
    if severe_seniority_mismatch or unusable_job_posting(
        signals, match_risks=match_risks
    ):
        return DecisionType.SKIP

    base = decision_from_score(score)

    # Risky but still usable postings need human review even on a strong match.
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
    decision = decision_from_signals(
        match.score,
        signals,
        severe_seniority_mismatch=match.severe_seniority_mismatch,
        match_risks=match.risks,
    )
    reasons = list(match.reasons)
    risks = list(match.risks)
    score = match.score
    if unusable_job_posting(signals, match_risks=match.risks):
        # Empty skill lists otherwise inflate coverage scores — hard-pass instead.
        score = 0.0
        reasons = [
            "Job posting is too incomplete or unclear to evaluate — hard pass.",
            *reasons,
        ]

    return WorkflowDecision(
        decision=decision,
        score=score,
        reasons=reasons,
        risks=risks,
        missing_information=[
            f"Job posting missing signal: {signal}"
            for signal in signals.missing_signals
        ],
    )
