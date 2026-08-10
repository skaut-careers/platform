import pytest

from app.agents import run_workflow, run_workflow_with_state
from app.agents.decision_rules import DefaultDecisionPolicy
from app.agents.orchestration.audit import WorkflowEventType
from app.agents.orchestration.graph import compile_workflow_graph
from app.agents.orchestration.stages import CANONICAL_STAGES
from app.agents.orchestration.state import WorkflowGraphState
from app.agents.profile_extraction import DefaultProfileExtractor
from app.agents.profile_matching import DefaultProfileMatcher
from app.agents.signal_extraction import DefaultSignalExtractor
from app.agents.wiring import create_agents, create_signal_extractor
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
    "runtime_version, profile_name, signal_name, match_name, policy_name",
    [
        (
            "v1",
            "DefaultProfileExtractor",
            "DefaultSignalExtractor",
            "DefaultProfileMatcher",
            "DefaultDecisionPolicy",
        ),
        (
            "v2",
            "LLMProfileExtractor",
            "LLMSignalExtractor",
            "LLMProfileMatcher",
            "LLMDecisionPolicy",
        ),
    ],
)
def test_create_agents_selects_agents_from_runtime(
    runtime_version, profile_name, signal_name, match_name, policy_name
):
    config = runtime_config(version=runtime_version)
    orchestrator = create_agents(
        signal_model=signals_test_model(), runtime_config=config
    )
    assert orchestrator.profile_extractor.__class__.__name__ == profile_name
    assert orchestrator.signal_extractor.__class__.__name__ == signal_name
    assert orchestrator.matcher.__class__.__name__ == match_name
    assert orchestrator.policy.__class__.__name__ == policy_name


def test_create_agent_rejects_unknown_mode():
    with pytest.raises(ValueError, match="Unsupported agent mode"):
        create_signal_extractor(mode="magic", runtime_config=_v1())


def test_prepare_path_executed_stages():
    _, run = run_workflow_with_state(
        workflow_input("strong_match.json"), runtime_config=_v1()
    )
    assert run.executed_stages == list(CANONICAL_STAGES)
    assert run.events[0].event_type == WorkflowEventType.RUN_STARTED
    assert run.events[-1].event_type == WorkflowEventType.RUN_COMPLETED


def test_escalate_is_terminal_product_result():
    output, run = run_workflow_with_state(
        workflow_input("ambiguous_match.json"), runtime_config=_v1()
    )
    assert output.decision.decision == DecisionType.ESCALATE
    assert run.is_complete
    assert run.executed_stages == list(CANONICAL_STAGES)


def test_langgraph_checkpointer_reconstructs_run():
    graph = compile_workflow_graph(
        profile_extractor=DefaultProfileExtractor(),
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
