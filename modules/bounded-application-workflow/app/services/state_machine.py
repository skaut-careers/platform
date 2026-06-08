from app.domain.workflow_state import (
    VALID_TRANSITIONS,
    InvalidTransitionError,
    WorkflowState,
)


class WorkflowStateMachine:
    """Manages explicit workflow state and valid transitions."""

    def __init__(self, initial_state: WorkflowState = WorkflowState.INTAKE) -> None:
        self._current_state = initial_state
        self._history: list[WorkflowState] = [initial_state]

    @property
    def current_state(self) -> WorkflowState:
        return self._current_state

    @property
    def history(self) -> list[WorkflowState]:
        return list(self._history)

    def can_transition_to(self, target: WorkflowState) -> bool:
        return target in VALID_TRANSITIONS[self._current_state]

    def transition_to(self, target: WorkflowState) -> WorkflowState:
        if not self.can_transition_to(target):
            raise InvalidTransitionError(self._current_state, target)
        self._current_state = target
        self._history.append(target)
        return target
