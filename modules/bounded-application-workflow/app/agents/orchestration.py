from app.agents.contracts import (
    DecisionPolicy,
    DecisionPolicyInput,
    HumanReviewGate,
    HumanReviewGateInput,
    ProfileMatcher,
    ProfileMatcherInput,
    SignalExtractor,
    SignalExtractorInput,
)
from app.domain.models import (
    DecisionType,
    JobDescription,
    UserProfile,
    WorkflowInput,
    WorkflowOutput,
)
from app.domain.workflow_run import WorkflowEventType, WorkflowRun, default_workflow_plan
from app.domain.workflow_state import WorkflowState

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


def _input_summary(profile: UserProfile, job: JobDescription) -> str:
    company = job.company or "an unspecified company"
    return (
        f"{profile.name} is being evaluated for {job.title} at {company}."
    )


def run_workflow_evaluation(
    workflow_input: WorkflowInput,
    *,
    extractor: SignalExtractor,
    matcher: ProfileMatcher,
    policy: DecisionPolicy,
    review_gate: HumanReviewGate | None = None,
) -> tuple[WorkflowOutput, WorkflowRun]:
    profile = workflow_input.user_profile
    job = workflow_input.job_description
    run = WorkflowRun(input=workflow_input, plan=default_workflow_plan())
    run.record_event(
        WorkflowEventType.RUN_STARTED,
        WorkflowState.INTAKE,
        "Workflow run started.",
    )

    run.transition_to(WorkflowState.SIGNAL_EXTRACTION)
    signals = extractor.run(
        SignalExtractorInput(job_description=job)
    ).signals

    run.transition_to(WorkflowState.PROFILE_MATCHING)
    match = matcher.run(
        ProfileMatcherInput(
            user_profile=profile,
            job_description=job,
            signals=signals,
        )
    ).match

    run.transition_to(WorkflowState.POLICY_EVALUATION)
    decision = policy.run(
        DecisionPolicyInput(match=match, signals=signals)
    ).decision

    if decision.decision == DecisionType.ESCALATE:
        run.transition_to(WorkflowState.HUMAN_REVIEW)
        if review_gate is not None:
            decision = review_gate.run(
                HumanReviewGateInput(
                    decision=decision,
                    match=match,
                    signals=signals,
                )
            ).decision

    run.transition_to(WorkflowState.DECISION)

    output = WorkflowOutput(
        input_summary=_input_summary(profile, job),
        decision=decision,
        job_signals=signals,
        recommended_next_steps=list(_NEXT_STEPS[decision.decision]),
    )
    run.complete(output)
    return output, run


def evaluate_workflow(
    workflow_input: WorkflowInput,
    *,
    extractor: SignalExtractor,
    matcher: ProfileMatcher,
    policy: DecisionPolicy,
    review_gate: HumanReviewGate | None = None,
) -> WorkflowOutput:
    output, _ = run_workflow_evaluation(
        workflow_input,
        extractor=extractor,
        matcher=matcher,
        policy=policy,
        review_gate=review_gate,
    )
    return output
