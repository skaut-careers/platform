import pytest

from app.agents import (
    approve_escalation,
    evaluate_workflow,
    revise_escalation,
)
from app.agents.decision_rules import DefaultDecisionPolicy
from app.agents.orchestration.audit import WorkflowEventType
from app.agents.orchestration.graph import compile_workflow_graph
from app.agents.orchestration.runner import (
    execute_workflow_pipeline,
    resume_workflow_pipeline,
)
from app.agents.orchestration.state import WorkflowGraphState
from app.agents.profile_matching import DefaultProfileMatcher
from app.agents.signal_extraction import DefaultSignalExtractor
from app.agents.wiring import create_agents
from app.agents.workflow_planning.planner import create_workflow_plan
from app.domain.models import DecisionType, JobDescription, UserProfile, WorkflowDecision, WorkflowInput
from app.agents.workflow_planning.plan import (
    DECISION,
    HUMAN_REVIEW,
    INTAKE,
    POLICY_EVALUATION,
    PROFILE_MATCHING,
    SIGNAL_EXTRACTION,
)
from tests.conftest import (
    WORKFLOW_FIXTURES,
    escalating_workflow_input,
    expected_decision,
    runtime_config,
    signals_test_model,
    workflow_input,
)


def _run(workflow: WorkflowInput):
    result = execute_workflow_pipeline(
        workflow,
        plan=create_workflow_plan(workflow),
        extractor=DefaultSignalExtractor(),
        matcher=DefaultProfileMatcher(),
        policy=DefaultDecisionPolicy(),
    )
    if result.is_interrupted:
        assert result.review_interrupt is not None
        result = resume_workflow_pipeline(
            result,
            approve_escalation(
                result.review_interrupt.decision,
                requested_at=result.review_interrupt.requested_at,
            ),
        )
    assert result.state.output is not None
    return result.state.output, result.state


def _evaluate(workflow: WorkflowInput):
    return evaluate_workflow(workflow, runtime_config=runtime_config(version="v1"))


@pytest.mark.parametrize("fixture_name", WORKFLOW_FIXTURES)
def test_fixture_decisions(fixture_name):
    assert _evaluate(workflow_input(fixture_name)).decision.decision == expected_decision(
        fixture_name
    )


@pytest.mark.parametrize(
    "runtime_version, extractor_name",
    [("v1", "DefaultSignalExtractor"), ("v2", "LLMSignalExtractor")],
)
def test_create_agents_selects_extractor(runtime_version, extractor_name):
    config = runtime_config(version=runtime_version)
    assert (
        create_agents(signal_model=signals_test_model(), runtime_config=config)[-1]
        ._extractor.__class__.__name__
        == extractor_name
    )


def test_create_agents_rejects_unknown_mode():
    with pytest.raises(ValueError, match="Unsupported signal extractor mode"):
        create_agents(
            signal_extractor="magic",
            runtime_config=runtime_config(version="v1"),
        )


def test_prepare_path_executed_stages():
    _, run = _run(workflow_input("strong_match.json"))
    expected = [
        INTAKE,
        SIGNAL_EXTRACTION,
        PROFILE_MATCHING,
        POLICY_EVALUATION,
        DECISION,
    ]
    assert run.executed_stages == expected
    assert run.plan.stages == expected
    assert run.plan_report and run.plan_report.followed_plan
    assert run.events[0].event_type == WorkflowEventType.RUN_STARTED
    assert run.events[-1].event_type == WorkflowEventType.RUN_COMPLETED


def test_escalation_pauses_and_resumes():
    workflow = escalating_workflow_input()
    paused = execute_workflow_pipeline(
        workflow,
        plan=create_workflow_plan(workflow),
        extractor=DefaultSignalExtractor(),
        matcher=DefaultProfileMatcher(),
        policy=DefaultDecisionPolicy(),
    )
    assert paused.is_interrupted
    assert paused.state.output is None
    assert DECISION not in paused.state.executed_stages

    resumed = resume_workflow_pipeline(
        paused,
        revise_escalation(
            WorkflowDecision(decision=DecisionType.QUEUE, score=0.5),
            requested_at=paused.review_interrupt.requested_at,
            reviewer_notes="Scope clarified.",
        ),
    )
    assert resumed.state.output.decision.decision == DecisionType.QUEUE
    assert resumed.state.review is not None
    assert resumed.state.review.is_revised


def test_unplanned_human_review_is_reported():
    workflow = WorkflowInput(
        user_profile=UserProfile(
            target_roles=["Backend Engineer"],
            skills=["Go"],
            seniority="mid-senior",
        ),
        job_description=JobDescription(
            title="Backend Engineer",
            description="Backend role.\n\n- Python\n- Kubernetes\n- Terraform",
            seniority="mid-senior",
        ),
    )
    _, run = _run(workflow)
    assert run.plan_report
    assert not run.plan_report.followed_plan
    assert run.plan_report.unplanned_stages == [HUMAN_REVIEW]


def test_langgraph_checkpointer_reconstructs_run():
    workflow = workflow_input("strong_match.json")
    plan = create_workflow_plan(workflow)
    graph = compile_workflow_graph(
        extractor=DefaultSignalExtractor(),
        matcher=DefaultProfileMatcher(),
        policy=DefaultDecisionPolicy(),
    )
    initial = WorkflowGraphState.from_workflow_input(workflow, plan)
    config = {"configurable": {"thread_id": initial.workflow_id}}
    result = WorkflowGraphState.model_validate(graph.invoke(initial, config))
    restored = WorkflowGraphState.model_validate(graph.get_state(config).values)

    assert restored.workflow_id == result.workflow_id
    assert restored.is_complete
    assert restored.output == result.output
    assert restored.executed_stages == result.executed_stages
