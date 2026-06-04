from app.domain.models import (
    DecisionType,
    JobDescription,
    ProfileMatchResult,
    UserProfile,
    WorkflowDecision,
    WorkflowInput,
    WorkflowOutput,
)
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


def _missing_information(
    profile: UserProfile, job: JobDescription, match: ProfileMatchResult
) -> list[str]:
    missing: list[str] = []

    for skill in match.required_skills_missing:
        missing.append(f"Required skill not evidenced in profile: {skill}")

    if not profile.experience_summary:
        missing.append("Profile experience summary is empty.")

    if not profile.target_roles:
        missing.append("Profile has no target roles defined.")

    if not job.seniority:
        missing.append("Job seniority level is not specified.")

    if not job.employment_type:
        missing.append("Job employment type is not specified.")

    return missing


def build_workflow_decision(
    match: ProfileMatchResult,
    profile: UserProfile,
    job: JobDescription,
) -> WorkflowDecision:
    return WorkflowDecision(
        decision=decision_from_score(match.score),
        score=match.score,
        reasons=list(match.reasons),
        risks=list(match.risks),
        missing_information=_missing_information(profile, job, match),
    )


def _input_summary(profile: UserProfile, job: JobDescription) -> str:
    company = job.company or "an unspecified company"
    return (
        f"{profile.name} is being evaluated for {job.title} at {company}."
    )


def evaluate_workflow(workflow_input: WorkflowInput) -> WorkflowOutput:
    profile = workflow_input.user_profile
    job = workflow_input.job_description

    match = match_profile_to_job(profile, job)
    decision = build_workflow_decision(match, profile, job)

    return WorkflowOutput(
        input_summary=_input_summary(profile, job),
        decision=decision,
        recommended_next_steps=list(_NEXT_STEPS[decision.decision]),
    )
