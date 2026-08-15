from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph

from app.agents.contracts import (
    ProfileExtractor,
    MatchDecider,
    JobSignalExtractor,
    WorkflowOrchestratorInput,
    WorkflowOrchestratorOutput,
)
from app.agents.orchestration.graph import compile_workflow_graph, default_checkpointer
from app.agents.orchestration.runner import execute_workflow_pipeline
from app.agents.profile_extraction import DefaultProfileExtractor
from app.agents.match_decision import DefaultMatchDecider
from app.agents.job_signal_extraction import DefaultJobSignalExtractor


class DefaultWorkflowOrchestrator:
    def __init__(
        self,
        *,
        profile_extractor: ProfileExtractor | None = None,
        job_signal_extractor: JobSignalExtractor | None = None,
        match_decider: MatchDecider | None = None,
        graph: CompiledStateGraph | None = None,
        checkpointer: MemorySaver | None = None,
    ) -> None:
        self._profile_extractor = profile_extractor or DefaultProfileExtractor()
        self._job_signal_extractor = job_signal_extractor or DefaultJobSignalExtractor()
        self._match_decider = match_decider or DefaultMatchDecider()
        self._checkpointer = checkpointer or default_checkpointer()
        self._graph = graph or compile_workflow_graph(
            profile_extractor=self._profile_extractor,
            job_signal_extractor=self._job_signal_extractor,
            match_decider=self._match_decider,
            checkpointer=self._checkpointer,
        )

    @property
    def profile_extractor(self) -> ProfileExtractor:
        return self._profile_extractor

    @property
    def job_signal_extractor(self) -> JobSignalExtractor:
        return self._job_signal_extractor

    @property
    def match_decider(self) -> MatchDecider:
        return self._match_decider

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
            job_signal_extractor=self._job_signal_extractor,
            match_decider=self._match_decider,
            graph=self._graph,
        )
        if result.state.output is None:
            raise RuntimeError("Workflow completed without output")
        return WorkflowOrchestratorOutput(output=result.state.output, run=result.state)
