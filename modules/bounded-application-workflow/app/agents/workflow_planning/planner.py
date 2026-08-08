from app.agents.contracts import WorkflowPlannerInput, WorkflowPlannerOutput
from app.agents.workflow_planning.plan import (
    DECISION,
    HUMAN_REVIEW,
    POLICY_APPLICATION,
    PROFILE_EXTRACTION,
    PROFILE_MATCHING,
    SIGNAL_EXTRACTION,
    WORKFLOW_PLANNING,
    WorkflowPlan,
)
from app.domain.job_signals import JobSignals
from app.domain.models import UserProfile

_CORE_STAGES = [
    PROFILE_EXTRACTION,
    SIGNAL_EXTRACTION,
    WORKFLOW_PLANNING,
    PROFILE_MATCHING,
    POLICY_APPLICATION,
]


def _predict_human_review(signals: JobSignals) -> bool:
    return bool(signals.risk_indicators)


def create_workflow_plan(
    _user_profile: UserProfile,
    signals: JobSignals,
) -> WorkflowPlan:
    """Estimate the stages of a run from already-extracted job signals."""
    stages = list(_CORE_STAGES)
    if _predict_human_review(signals):
        stages.append(HUMAN_REVIEW)
    stages.append(DECISION)

    return WorkflowPlan(stages=stages)


class DefaultWorkflowPlanner:
    def run(self, agent_input: WorkflowPlannerInput) -> WorkflowPlannerOutput:
        plan = create_workflow_plan(
            agent_input.user_profile,
            agent_input.signals,
        )
        return WorkflowPlannerOutput(plan=plan)
