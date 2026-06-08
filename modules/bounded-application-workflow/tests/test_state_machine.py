import pytest

from app.domain.workflow_state import (
    VALID_TRANSITIONS,
    InvalidTransitionError,
    WorkflowState,
)
from app.services.state_machine import WorkflowStateMachine


def test_workflow_states_are_explicitly_defined():
    assert {state.value for state in WorkflowState} == {
        "intake",
        "signal_extraction",
        "profile_matching",
        "policy_evaluation",
        "human_review",
        "decision",
    }


def test_valid_transitions_are_defined_centrally():
    assert WorkflowState.INTAKE in VALID_TRANSITIONS
    assert WorkflowState.SIGNAL_EXTRACTION in VALID_TRANSITIONS[WorkflowState.INTAKE]
    assert WorkflowState.DECISION in VALID_TRANSITIONS[WorkflowState.HUMAN_REVIEW]
    assert VALID_TRANSITIONS[WorkflowState.DECISION] == frozenset()


def test_state_machine_starts_at_intake():
    machine = WorkflowStateMachine()

    assert machine.current_state == WorkflowState.INTAKE
    assert machine.history == [WorkflowState.INTAKE]


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
)
def test_valid_transition_paths(path: list[WorkflowState]):
    machine = WorkflowStateMachine()

    for target in path:
        machine.transition_to(target)

    assert machine.current_state == WorkflowState.DECISION
    assert machine.history == [WorkflowState.INTAKE, *path]


@pytest.mark.parametrize(
    "current,target",
    [
        (WorkflowState.INTAKE, WorkflowState.DECISION),
        (WorkflowState.INTAKE, WorkflowState.HUMAN_REVIEW),
        (WorkflowState.SIGNAL_EXTRACTION, WorkflowState.DECISION),
        (WorkflowState.PROFILE_MATCHING, WorkflowState.INTAKE),
        (WorkflowState.POLICY_EVALUATION, WorkflowState.INTAKE),
        (WorkflowState.HUMAN_REVIEW, WorkflowState.POLICY_EVALUATION),
        (WorkflowState.DECISION, WorkflowState.INTAKE),
    ],
)
def test_invalid_transitions_fail_with_clear_error(
    current: WorkflowState,
    target: WorkflowState,
):
    machine = WorkflowStateMachine(initial_state=current)

    with pytest.raises(InvalidTransitionError) as exc_info:
        machine.transition_to(target)

    error = exc_info.value
    assert error.current == current
    assert error.target == target
    assert current.value in str(error)
    assert target.value in str(error)
    assert machine.current_state == current
    assert machine.history == [current]


def test_terminal_state_rejects_all_transitions():
    machine = WorkflowStateMachine(initial_state=WorkflowState.DECISION)

    with pytest.raises(InvalidTransitionError, match="terminal state"):
        machine.transition_to(WorkflowState.INTAKE)

    assert machine.current_state == WorkflowState.DECISION


def test_can_transition_to_reflects_valid_targets():
    machine = WorkflowStateMachine()

    assert machine.can_transition_to(WorkflowState.SIGNAL_EXTRACTION) is True
    assert machine.can_transition_to(WorkflowState.DECISION) is False
