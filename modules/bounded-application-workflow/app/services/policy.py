from app.domain.job_signals import JobSignals
from app.domain.models import (
    DecisionType,
    JobDescription,
    ProfileMatchResult,
    UserProfile,
    WorkflowDecision,
    WorkflowInput,
    WorkflowOutput,
)
from app.services.extractor import extract_job_signals
from app.services.matcher import match_profile_to_job

# MVP thresholds — docs/PRD.md
_PREPARE_MIN = 0.75
_QUEUE_MIN = 0.55
_ESCALATE_MIN = 0.35

_NEXT_STEPS: dict[DecisionType, list[str]] = {
    DecisionType.PREPARE: [
        "Tailor your CV to highlight matched skills and role alignment.",
        "Draft a concise cover letter addressing any remaining gaps.",
        "Prepare talking points for interviews based on the job description.",
    ],
    DecisionType.QUEUE: [
        "Save this opportunity for a later review cycle.",
        "Note what would need to change before actively pursuing it.",
        "Re-run evaluation if your profile or priorities shift.",
    ],
    DecisionType.ESCALATE: [
        "Review the opportunity manually before investing application time.",
        "Clarify ambiguous requirements with the recruiter or hiring team.",
        "Fill in missing profile or job signals, then re-evaluate.",
    ],
    DecisionType.SKIP: [
        "Record why this opportunity is not a fit for future reference.",
        "Focus search effort on roles that align with your target profile.",
    ],
}


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


def _missing_information_from_profile(
    profile: UserProfile, match: ProfileMatchResult
) -> list[str]:
    missing: list[str] = []

    for skill in match.required_skills_missing:
        missing.append(f"Required skill not evidenced in profile: {skill}")

    if not profile.experience_summary:
        missing.append("Profile experience summary is empty.")

    if not profile.target_roles:
        missing.append("Profile has no target roles defined.")

    return missing


def _missing_information_from_signals(signals: JobSignals) -> list[str]:
    return [
        f"Job posting missing signal: {signal}"
        for signal in signals.missing_signals
    ]


def build_workflow_decision(
    match: ProfileMatchResult,
    profile: UserProfile,
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
        missing_information=(
            _missing_information_from_profile(profile, match)
            + _missing_information_from_signals(signals)
        ),
    )


def _input_summary(profile: UserProfile, job: JobDescription) -> str:
    company = job.company or "an unspecified company"
    return (
        f"{profile.name} is being evaluated for {job.title} at {company}."
    )


def evaluate_workflow(workflow_input: WorkflowInput) -> WorkflowOutput:
    profile = workflow_input.user_profile
    job = workflow_input.job_description

    signals = extract_job_signals(job)
    match = match_profile_to_job(profile, job, signals)
    decision = build_workflow_decision(match, profile, signals)

    return WorkflowOutput(
        input_summary=_input_summary(profile, job),
        decision=decision,
        job_signals=signals,
        recommended_next_steps=list(_NEXT_STEPS[decision.decision]),
    )
