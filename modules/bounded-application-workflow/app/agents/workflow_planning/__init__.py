from app.agents.workflow_planning.plan import (
    DECISION,
    POLICY_APPLICATION,
    PROFILE_EXTRACTION,
    PROFILE_MATCHING,
    SIGNAL_EXTRACTION,
    WORKFLOW_PLANNING,
    PlanExecutionReport,
    WorkflowPlan,
    compare_plan,
    default_workflow_plan,
)

__all__ = [
    "DECISION",
    "DefaultWorkflowPlanner",
    "POLICY_APPLICATION",
    "PROFILE_EXTRACTION",
    "PROFILE_MATCHING",
    "PlanExecutionReport",
    "SIGNAL_EXTRACTION",
    "WORKFLOW_PLANNING",
    "WorkflowPlan",
    "compare_plan",
    "create_workflow_plan",
    "default_workflow_plan",
]


def __getattr__(name: str):
    if name in {"DefaultWorkflowPlanner", "create_workflow_plan"}:
        from app.agents.workflow_planning import planner

        return getattr(planner, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name}")
