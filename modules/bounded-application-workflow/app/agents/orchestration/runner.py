from dataclasses import dataclass
from uuid import uuid4

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph

from app.agents.contracts import (
    ProfileExtractor,
    MatchDecider,
    JobSignalExtractor,
)
from app.agents.orchestration.graph import compile_workflow_graph
from app.agents.orchestration.state import WorkflowGraphState
from app.agents.profile_extraction import DefaultProfileExtractor
from app.domain.models import WorkflowInput


def _thread_config(workflow_id: str) -> RunnableConfig:
    return {"configurable": {"thread_id": workflow_id}}


@dataclass(frozen=True)
class WorkflowPipelineResult:
    """Invoke handle: compiled graph + thread id."""

    graph: CompiledStateGraph
    workflow_id: str

    @property
    def state(self) -> WorkflowGraphState:
        snapshot = self.graph.get_state(_thread_config(self.workflow_id))
        return WorkflowGraphState.model_validate(snapshot.values)


def execute_workflow_pipeline(
    workflow_input: WorkflowInput,
    *,
    profile_extractor: ProfileExtractor | None = None,
    job_signal_extractor: JobSignalExtractor,
    match_decider: MatchDecider,
    graph: CompiledStateGraph | None = None,
    checkpointer: MemorySaver | None = None,
    thread_id: str | None = None,
) -> WorkflowPipelineResult:
    """Run the workflow via LangGraph from a validated ``WorkflowInput``."""
    compiled = graph or compile_workflow_graph(
        profile_extractor=profile_extractor or DefaultProfileExtractor(),
        job_signal_extractor=job_signal_extractor,
        match_decider=match_decider,
        checkpointer=checkpointer,
    )
    workflow_id = thread_id or str(uuid4())
    initial = WorkflowGraphState.from_workflow_input(
        workflow_input,
        workflow_id=workflow_id,
    )
    compiled.invoke(initial, _thread_config(workflow_id))
    return WorkflowPipelineResult(graph=compiled, workflow_id=workflow_id)
