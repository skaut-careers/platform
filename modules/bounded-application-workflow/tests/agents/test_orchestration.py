import pytest

from app.agents import run_workflow, run_workflow_with_state
from app.agents.decision_rules import DefaultDecisionPolicy
from app.agents.orchestration.audit import WorkflowEventType
from app.agents.orchestration.graph import compile_workflow_graph
from app.agents.orchestration.state import WorkflowGraphState
from app.agents.profile_extraction import DefaultProfileExtractor
from app.agents.profile_matching import DefaultProfileMatcher
from app.agents.signal_extraction import DefaultSignalExtractor
from app.agents.wiring import create_agents
from app.agents.workflow_planning import DefaultWorkflowPlanner
from app.agents.workflow_planning.plan import default_workflow_plan
from app.domain.models import DecisionType
from tests.conftest import (
    WORKFLOW_FIXTURES,
    expected_decision,
    runtime_config,
    signals_test_model,
    workflow_input,
)


def _v1(**kwargs):
    return runtime_config(version="v1", **kwargs)


@pytest.mark.parametrize("fixture_name", WORKFLOW_FIXTURES)
def test_fixture_decisions(fixture_name):
    assert (
        run_workflow(workflow_input(fixture_name), runtime_config=_v1()).decision.decision
        == expected_decision(fixture_name)
    )


@pytest.mark.parametrize(
    "runtime_version, extractor_name",
    [("v1", "DefaultSignalExtractor"), ("v2", "LLMSignalExtractor")],
)
def test_create_agents_selects_extractor(runtime_version, extractor_name):
    config = runtime_config(version=runtime_version)
    name = create_agents(
        signal_model=signals_test_model(), runtime_config=config
    )[-1].signal_extractor.__class__.__name__
    assert name == extractor_name


def test_create_agents_rejects_unknown_mode():
    with pytest.raises(ValueError, match="Unsupported signal extractor mode"):
        create_agents(signal_extractor="magic", runtime_config=_v1())


def test_prepare_path_executed_stages():
    _, run = run_workflow_with_state(
        workflow_input("strong_match.json"), runtime_config=_v1()
    )
    expected = default_workflow_plan().stages
    assert run.executed_stages == expected
    assert run.plan.stages == expected
    assert run.plan_report and run.plan_report.followed_plan
    assert run.events[0].event_type == WorkflowEventType.RUN_STARTED
    assert run.events[-1].event_type == WorkflowEventType.RUN_COMPLETED


def test_escalate_is_terminal_product_result():
    output, run = run_workflow_with_state(
        workflow_input("ambiguous_match.json"), runtime_config=_v1()
    )
    assert output.decision.decision == DecisionType.ESCALATE
    assert run.is_complete
    assert run.executed_stages == default_workflow_plan().stages
    assert run.plan_report and run.plan_report.followed_plan


def test_langgraph_checkpointer_reconstructs_run():
    graph = compile_workflow_graph(
        profile_extractor=DefaultProfileExtractor(),
        planner=DefaultWorkflowPlanner(),
        extractor=DefaultSignalExtractor(),
        matcher=DefaultProfileMatcher(),
        policy=DefaultDecisionPolicy(),
    )
    initial = WorkflowGraphState.from_workflow_input(
        workflow_input("strong_match.json")
    )
    config = {"configurable": {"thread_id": initial.workflow_id}}
    result = WorkflowGraphState.model_validate(graph.invoke(initial, config))
    restored = WorkflowGraphState.model_validate(graph.get_state(config).values)

    assert restored.is_complete
    assert restored.output == result.output
    assert restored.executed_stages == result.executed_stages
