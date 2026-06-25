from app.agents.contracts import (
    DecisionPolicy,
    HumanReviewGate,
    ProfileMatcher,
    SignalExtractor,
    WorkflowOrchestratorInput,
    WorkflowOrchestratorOutput,
    WorkflowPlanner,
    WorkflowPlannerInput,
)
from app.agents.decision_rules import DefaultDecisionPolicy
from app.agents.human_review import PassthroughHumanReviewGate
from app.agents.orchestration.runner import execute_workflow_pipeline
from app.agents.profile_matching import DefaultProfileMatcher
from app.agents.signal_extraction import DefaultSignalExtractor
from app.agents.workflow_planning import DefaultWorkflowPlanner


class DefaultWorkflowOrchestrator:
    def __init__(
        self,
        *,
        planner: WorkflowPlanner | None = None,
        extractor: SignalExtractor | None = None,
        matcher: ProfileMatcher | None = None,
        policy: DecisionPolicy | None = None,
        review_gate: HumanReviewGate | None = None,
    ) -> None:
        self._planner = planner or DefaultWorkflowPlanner()
        self._extractor = extractor or DefaultSignalExtractor()
        self._matcher = matcher or DefaultProfileMatcher()
        self._policy = policy or DefaultDecisionPolicy()
        self._review_gate = review_gate or PassthroughHumanReviewGate()

    def run(
        self, agent_input: WorkflowOrchestratorInput
    ) -> WorkflowOrchestratorOutput:
        plan = self._planner.run(
            WorkflowPlannerInput(workflow_input=agent_input.workflow_input)
        ).plan
        output, run = execute_workflow_pipeline(
            agent_input.workflow_input,
            plan=plan,
            extractor=self._extractor,
            matcher=self._matcher,
            policy=self._policy,
            review_gate=self._review_gate,
        )
        return WorkflowOrchestratorOutput(output=output, run=run)
