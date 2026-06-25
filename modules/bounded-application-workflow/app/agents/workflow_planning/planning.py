from app.agents.signal_extraction.deterministic import extract_job_signals
from app.domain.job_signals import JobSignals
from app.domain.models import WorkflowInput
from app.domain.workflow_run import WorkflowPlan
from app.domain.workflow_state import WorkflowState

_CORE_STAGES = [
    WorkflowState.INTAKE,
    WorkflowState.SIGNAL_EXTRACTION,
    WorkflowState.PROFILE_MATCHING,
    WorkflowState.POLICY_EVALUATION,
]


def _predict_human_review(pre_scan: JobSignals) -> bool:
    # Decision rules escalate risky postings to review; mirror that here so the
    # plan anticipates the HUMAN_REVIEW stage instead of always omitting it.
    return bool(pre_scan.risk_indicators)


def create_workflow_plan(workflow_input: WorkflowInput) -> WorkflowPlan:
    """Estimate the stages of a run before executing it."""
    # Cheap pre-scan of the posting; the execution re-extracts signals inside
    # its own SIGNAL_EXTRACTION stage.
    pre_scan = extract_job_signals(workflow_input.job_description)

    stages = list(_CORE_STAGES)
    if _predict_human_review(pre_scan):
        stages.append(WorkflowState.HUMAN_REVIEW)
    stages.append(WorkflowState.DECISION)

    return WorkflowPlan(stages=stages)
