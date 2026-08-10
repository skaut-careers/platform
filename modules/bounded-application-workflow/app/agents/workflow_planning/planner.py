from app.agents.contracts import WorkflowPlannerInput, WorkflowPlannerOutput
from app.agents.workflow_planning.plan import (
    DECISION,
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
    DECISION,
]


def create_workflow_plan(
    _user_profile: UserProfile,
    _signals: JobSignals,
) -> WorkflowPlan:
    """Return the canonical product stages for a run."""
    return WorkflowPlan(stages=list(_CORE_STAGES))


class DefaultWorkflowPlanner:
    def run(self, agent_input: WorkflowPlannerInput) -> WorkflowPlannerOutput:
        plan = create_workflow_plan(
            agent_input.user_profile,
            agent_input.signals,
        )
        return WorkflowPlannerOutput(plan=plan)
