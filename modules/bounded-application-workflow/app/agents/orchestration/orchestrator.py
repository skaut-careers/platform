from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph

from app.agents.contracts import (
    DecisionPolicy,
    ProfileExtractor,
    ProfileMatcher,
    SignalExtractor,
    WorkflowOrchestratorInput,
    WorkflowOrchestratorOutput,
)
from app.agents.decision_rules import DefaultDecisionPolicy
from app.agents.orchestration.graph import compile_workflow_graph, default_checkpointer
from app.agents.orchestration.runner import execute_workflow_pipeline
from app.agents.profile_extraction import DefaultProfileExtractor
from app.agents.profile_matching import DefaultProfileMatcher
from app.agents.signal_extraction import DefaultSignalExtractor


class DefaultWorkflowOrchestrator:
    def __init__(
        self,
        *,
        profile_extractor: ProfileExtractor | None = None,
        extractor: SignalExtractor | None = None,
        matcher: ProfileMatcher | None = None,
        policy: DecisionPolicy | None = None,
        graph: CompiledStateGraph | None = None,
        checkpointer: MemorySaver | None = None,
    ) -> None:
        self._profile_extractor = profile_extractor or DefaultProfileExtractor()
        self._extractor = extractor or DefaultSignalExtractor()
        self._matcher = matcher or DefaultProfileMatcher()
        self._policy = policy or DefaultDecisionPolicy()
        self._checkpointer = checkpointer or default_checkpointer()
        self._graph = graph or compile_workflow_graph(
            profile_extractor=self._profile_extractor,
            extractor=self._extractor,
            matcher=self._matcher,
            policy=self._policy,
            checkpointer=self._checkpointer,
        )

    @property
    def profile_extractor(self) -> ProfileExtractor:
        return self._profile_extractor

    @property
    def signal_extractor(self) -> SignalExtractor:
        return self._extractor

    @property
    def matcher(self) -> ProfileMatcher:
        return self._matcher

    @property
    def policy(self) -> DecisionPolicy:
        return self._policy

    @property
    def graph(self) -> CompiledStateGraph:
        """Canonical LangGraph workflow exposed to REST and AG-UI."""
        return self._graph

    @property
    def checkpointer(self) -> MemorySaver:
        return self._checkpointer

    def run(
        self, agent_input: WorkflowOrchestratorInput
    ) -> WorkflowOrchestratorOutput:
        result = execute_workflow_pipeline(
            agent_input.workflow_input,
            profile_extractor=self._profile_extractor,
            extractor=self._extractor,
            matcher=self._matcher,
            policy=self._policy,
            graph=self._graph,
        )
        if result.state.output is None:
            raise RuntimeError("Workflow completed without output")
        return WorkflowOrchestratorOutput(output=result.state.output, run=result.state)
