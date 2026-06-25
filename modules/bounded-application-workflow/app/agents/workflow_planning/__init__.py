from app.agents.contracts import WorkflowPlannerInput, WorkflowPlannerOutput
from app.agents.workflow_planning.planning import create_workflow_plan

__all__ = ["DefaultWorkflowPlanner"]


class DefaultWorkflowPlanner:
    def run(self, agent_input: WorkflowPlannerInput) -> WorkflowPlannerOutput:
        plan = create_workflow_plan(agent_input.workflow_input)
        return WorkflowPlannerOutput(plan=plan)
