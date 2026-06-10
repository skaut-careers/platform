import pytest
from pydantic import ValidationError

from app.domain.job_signals import JobSignals
from app.domain.models import (
    DecisionType,
    UserProfile,
    WorkflowDecision,
    WorkflowOutput,
)
from app.domain.state_machine import WorkflowStateMachine
from app.domain.workflow_run import (
    WorkflowEventType,
    WorkflowPlan,
    WorkflowRun,
    default_workflow_plan,
)
from app.domain.workflow_state import InvalidTransitionError, WorkflowState
from tests.fixture_helpers import workflow_input


@pytest.mark.parametrize(
    "path",
    [
        [
            WorkflowState.SIGNAL_EXTRACTION,
            WorkflowState.PROFILE_MATCHING,
            WorkflowState.POLICY_EVALUATION,
            WorkflowState.DECISION,
        ],
        [
            WorkflowState.SIGNAL_EXTRACTION,
            WorkflowState.PROFILE_MATCHING,
            WorkflowState.POLICY_EVALUATION,
            WorkflowState.HUMAN_REVIEW,
            WorkflowState.DECISION,
        ],
    ],
    ids=["direct", "via_review"],
)
def test_valid_state_transitions(path: list[WorkflowState]):
    machine = WorkflowStateMachine()

    for target in path:
        machine.transition_to(target)

    assert machine.current_state == WorkflowState.DECISION
    assert machine.history == [WorkflowState.INTAKE, *path]


@pytest.mark.parametrize(
    "current,target",
    [
        (WorkflowState.INTAKE, WorkflowState.DECISION),
        (WorkflowState.DECISION, WorkflowState.INTAKE),
    ],
)
def test_invalid_state_transition(current: WorkflowState, target: WorkflowState):
    machine = WorkflowStateMachine(initial_state=current)

    with pytest.raises(InvalidTransitionError):
        machine.transition_to(target)

    assert machine.current_state == current


def test_workflow_run_records_transition():
    run = WorkflowRun(
        input=workflow_input("strong_match.json"),
        plan=default_workflow_plan(),
    )

    run.transition_to(WorkflowState.SIGNAL_EXTRACTION, "extracting signals")

    assert run.current_state == WorkflowState.SIGNAL_EXTRACTION
    assert run.events[-1].event_type == WorkflowEventType.STATE_ENTERED
    assert run.events[-1].message == "extracting signals"


def test_default_workflow_plan():
    assert default_workflow_plan().stages == [
        WorkflowState.INTAKE,
        WorkflowState.SIGNAL_EXTRACTION,
        WorkflowState.PROFILE_MATCHING,
        WorkflowState.POLICY_EVALUATION,
        WorkflowState.DECISION,
    ]


def _run_through_evaluation(plan: WorkflowPlan) -> WorkflowRun:
    """Build a run that executed the direct path (no human review)."""
    run = WorkflowRun(input=workflow_input("strong_match.json"), plan=plan)
    for state in [
        WorkflowState.SIGNAL_EXTRACTION,
        WorkflowState.PROFILE_MATCHING,
        WorkflowState.POLICY_EVALUATION,
    ]:
        run.transition_to(state)
    return run


def test_complete_populates_followed_plan_report():
    run = _run_through_evaluation(default_workflow_plan())
    output = WorkflowOutput(
        input_summary="summary",
        decision=WorkflowDecision(decision=DecisionType.PREPARE, score=0.8),
        job_signals=JobSignals(),
    )

    run.complete(output)

    report = run.plan_report
    assert report is not None
    assert report.followed_plan is True
    assert report.executed_stages == run.state_history
    assert report.unplanned_stages == []
    assert report.skipped_stages == []


def test_compare_plan_flags_skipped_human_review():
    plan = WorkflowPlan(
        stages=[
            WorkflowState.INTAKE,
            WorkflowState.SIGNAL_EXTRACTION,
            WorkflowState.PROFILE_MATCHING,
            WorkflowState.POLICY_EVALUATION,
            WorkflowState.HUMAN_REVIEW,
            WorkflowState.DECISION,
        ],
    )
    run = _run_through_evaluation(plan)
    run.transition_to(WorkflowState.DECISION)

    report = run.compare_plan()

    assert report.followed_plan is False
    assert report.skipped_stages == [WorkflowState.HUMAN_REVIEW]
    assert report.unplanned_stages == []


def _escalated_decision() -> WorkflowDecision:
    return WorkflowDecision(
        decision=DecisionType.ESCALATE,
        score=0.5,
        risks=["ambiguous scope"],
    )


def _run_in_human_review() -> WorkflowRun:
    run = _run_through_evaluation(default_workflow_plan())
    run.transition_to(WorkflowState.HUMAN_REVIEW)
    return run


def test_request_review_stores_pending_record():
    run = _run_in_human_review()

    record = run.request_review("Risky posting.", _escalated_decision())

    assert run.review is record
    assert record.reason == "Risky posting."
    assert record.is_pending is True


def test_request_review_outside_review_state_raises():
    run = _run_through_evaluation(default_workflow_plan())

    with pytest.raises(ValueError):
        run.request_review("Risky posting.", _escalated_decision())


def test_resolve_review_approves_decision():
    run = _run_in_human_review()
    decision = _escalated_decision()
    run.request_review("Risky posting.", decision)

    record = run.resolve_review(final_decision=decision, approved=True)

    assert record.approved is True
    assert record.is_revised is False
    assert run.events[-1].event_type == WorkflowEventType.REVIEW_COMPLETED


def test_resolve_review_revises_decision():
    run = _run_in_human_review()
    run.request_review("Risky posting.", _escalated_decision())
    revised = WorkflowDecision(decision=DecisionType.QUEUE, score=0.5)

    record = run.resolve_review(final_decision=revised, approved=False)

    assert record.is_revised is True
    assert record.final_decision == revised


def test_resolve_review_without_request_raises():
    run = _run_in_human_review()

    with pytest.raises(ValueError):
        run.resolve_review(final_decision=_escalated_decision(), approved=True)


def test_user_profile_rejects_null_list_fields():
    with pytest.raises(ValidationError):
        UserProfile(name="Ana", skills=None)


def test_workflow_decision_rejects_invalid_score():
    with pytest.raises(ValidationError):
        WorkflowDecision(decision=DecisionType.SKIP, score=1.5)
