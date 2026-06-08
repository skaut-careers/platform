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
from app.domain.workflow_state import WorkflowState
from app.services.extractor import extract_job_signals
from app.services.matcher import match_profile_to_job
from app.services.state_machine import WorkflowStateMachine

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


def _input_summary(profile: UserProfile, job: JobDescription) -> str:
    company = job.company or "an unspecified company"
    return (
        f"{profile.name} is being evaluated for {job.title} at {company}."
    )


def run_workflow_evaluation(
    workflow_input: WorkflowInput,
) -> tuple[WorkflowOutput, WorkflowStateMachine]:
    profile = workflow_input.user_profile
    job = workflow_input.job_description
    state_machine = WorkflowStateMachine()

    state_machine.transition_to(WorkflowState.SIGNAL_EXTRACTION)
    signals = extract_job_signals(job)

    state_machine.transition_to(WorkflowState.PROFILE_MATCHING)
    match = match_profile_to_job(profile, job, signals)

    state_machine.transition_to(WorkflowState.POLICY_EVALUATION)
    decision = build_workflow_decision(match, signals)

    if decision.decision == DecisionType.ESCALATE:
        state_machine.transition_to(WorkflowState.HUMAN_REVIEW)

    state_machine.transition_to(WorkflowState.DECISION)

    output = WorkflowOutput(
        input_summary=_input_summary(profile, job),
        decision=decision,
        job_signals=signals,
        recommended_next_steps=list(_NEXT_STEPS[decision.decision]),
    )
    return output, state_machine


def evaluate_workflow(workflow_input: WorkflowInput) -> WorkflowOutput:
    output, _ = run_workflow_evaluation(workflow_input)
    return output
