from app.agents.contracts import (
    DecisionPolicy,
    HumanReviewGate,
    ProfileMatcher,
    SignalExtractor,
)
from app.agents.orchestration.graph import compile_workflow_graph
from app.agents.orchestration.state import WorkflowGraphState
from app.domain.models import WorkflowInput, WorkflowOutput
from app.domain.workflow_run import WorkflowPlan, WorkflowRun


def execute_workflow_pipeline(
    workflow_input: WorkflowInput,
    *,
    plan: WorkflowPlan,
    extractor: SignalExtractor,
    matcher: ProfileMatcher,
    policy: DecisionPolicy,
    review_gate: HumanReviewGate | None = None,
) -> tuple[WorkflowOutput, WorkflowRun]:

    run = WorkflowRun(input=workflow_input, plan=plan)
    graph = compile_workflow_graph(
        extractor=extractor,
        matcher=matcher,
        policy=policy,
        review_gate=review_gate,
        run=run,
    )
    initial = WorkflowGraphState.from_workflow_input(
        workflow_input,
        plan,
        workflow_id=run.workflow_id,
    )
    result = graph.invoke(
        initial,
        {"configurable": {"thread_id": run.workflow_id}},
    )
    state = (
        result
        if isinstance(result, WorkflowGraphState)
        else WorkflowGraphState.model_validate(result)
    )
    if state.output is None or run.output is None:
        raise RuntimeError("Workflow graph completed without producing output")
    return run.output, run
