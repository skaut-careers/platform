from app.domain.workflow_run import (
    WorkflowEventType,
    WorkflowPlan,
    WorkflowRun,
    default_workflow_plan,
)
from app.domain.workflow_state import WorkflowState
from tests.fixture_helpers import workflow_input as load_workflow_input


def test_workflow_run_has_unique_id():
    workflow_input = load_workflow_input("strong_match.json")

    run_a = WorkflowRun(input=workflow_input, plan=default_workflow_plan())
    run_b = WorkflowRun(input=workflow_input, plan=default_workflow_plan())

    assert run_a.workflow_id
    assert run_b.workflow_id
    assert run_a.workflow_id != run_b.workflow_id


def test_workflow_run_transition_records_event():
    run = WorkflowRun(
        input=load_workflow_input("strong_match.json"),
        plan=default_workflow_plan(),
    )

    run.transition_to(WorkflowState.SIGNAL_EXTRACTION, "extracting signals")

    assert run.current_state == WorkflowState.SIGNAL_EXTRACTION
    assert run.events[-1].event_type == WorkflowEventType.STATE_ENTERED
    assert run.events[-1].state == WorkflowState.SIGNAL_EXTRACTION
    assert run.events[-1].message == "extracting signals"


def test_workflow_run_stores_plan_output_and_events():
    workflow_input = load_workflow_input("strong_match.json")
    plan = WorkflowPlan(
        stages=[WorkflowState.INTAKE, WorkflowState.DECISION],
        evaluation_focus=["role fit"],
        required_signals=["seniority"],
    )
    run = WorkflowRun(input=workflow_input, plan=plan)
    run.record_event(
        WorkflowEventType.RUN_STARTED,
        WorkflowState.INTAKE,
        "started",
    )

    assert run.plan == plan
    assert run.output is None
    assert len(run.events) == 1
    assert run.events[0].event_type == WorkflowEventType.RUN_STARTED


def test_default_workflow_plan_defines_standard_stages():
    plan = default_workflow_plan()

    assert plan.stages == [
        WorkflowState.INTAKE,
        WorkflowState.SIGNAL_EXTRACTION,
        WorkflowState.PROFILE_MATCHING,
        WorkflowState.POLICY_EVALUATION,
        WorkflowState.DECISION,
    ]
