from dataclasses import dataclass
from uuid import uuid4

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command

from app.agents.contracts import DecisionPolicy, ProfileMatcher, SignalExtractor
from app.agents.human_review import HumanReviewInterrupt, HumanReviewResume
from app.agents.orchestration.graph import compile_workflow_graph
from app.agents.orchestration.state import WorkflowGraphState
from app.domain.models import WorkflowInput
from app.agents.workflow_planning.plan import WorkflowPlan


def _thread_config(workflow_id: str) -> RunnableConfig:
    return {"configurable": {"thread_id": workflow_id}}


@dataclass(frozen=True)
class WorkflowPipelineResult:
    """Invoke handle: compiled graph + thread id, plus interrupt side-channel if paused."""

    graph: CompiledStateGraph
    workflow_id: str
    review_interrupt: HumanReviewInterrupt | None = None

    @property
    def state(self) -> WorkflowGraphState:
        snapshot = self.graph.get_state(_thread_config(self.workflow_id))
        return WorkflowGraphState.model_validate(snapshot.values)

    @property
    def is_interrupted(self) -> bool:
        return self.review_interrupt is not None


def _result_from_graph(
    compiled: CompiledStateGraph,
    workflow_id: str,
) -> WorkflowPipelineResult:
    snapshot = compiled.get_state(_thread_config(workflow_id))
    interrupts = list(snapshot.interrupts)
    if interrupts:
        return WorkflowPipelineResult(
            graph=compiled,
            workflow_id=workflow_id,
            review_interrupt=HumanReviewInterrupt.model_validate(interrupts[0].value),
        )
    return WorkflowPipelineResult(graph=compiled, workflow_id=workflow_id)


def execute_workflow_pipeline(
    workflow_input: WorkflowInput,
    *,
    plan: WorkflowPlan,
    extractor: SignalExtractor,
    matcher: ProfileMatcher,
    policy: DecisionPolicy,
    graph: CompiledStateGraph | None = None,
    checkpointer: MemorySaver | None = None,
    thread_id: str | None = None,
) -> WorkflowPipelineResult:
    """Run the workflow via LangGraph; may pause on escalation for human review."""
    compiled = graph or compile_workflow_graph(
        extractor=extractor,
        matcher=matcher,
        policy=policy,
        checkpointer=checkpointer,
    )
    workflow_id = thread_id or str(uuid4())
    initial = WorkflowGraphState.from_workflow_input(
        workflow_input,
        plan,
        workflow_id=workflow_id,
    )
    compiled.invoke(initial, _thread_config(workflow_id))
    return _result_from_graph(compiled, workflow_id)


def resume_workflow_pipeline(
    pipeline: WorkflowPipelineResult,
    resume: HumanReviewResume,
) -> WorkflowPipelineResult:
    """Apply an approve/revise Command and continue to the final decision."""
    if not pipeline.is_interrupted:
        raise RuntimeError("Pipeline is not waiting for human review")
    pipeline.graph.invoke(
        Command(resume=resume.model_dump(mode="json")),
        _thread_config(pipeline.workflow_id),
    )
    return _result_from_graph(pipeline.graph, pipeline.workflow_id)
