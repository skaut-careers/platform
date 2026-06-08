from enum import Enum


class WorkflowState(str, Enum):
    INTAKE = "intake"
    SIGNAL_EXTRACTION = "signal_extraction"
    PROFILE_MATCHING = "profile_matching"
    POLICY_EVALUATION = "policy_evaluation"
    HUMAN_REVIEW = "human_review"
    DECISION = "decision"


VALID_TRANSITIONS: dict[WorkflowState, frozenset[WorkflowState]] = {
    WorkflowState.INTAKE: frozenset({WorkflowState.SIGNAL_EXTRACTION}),
    WorkflowState.SIGNAL_EXTRACTION: frozenset({WorkflowState.PROFILE_MATCHING}),
    WorkflowState.PROFILE_MATCHING: frozenset({WorkflowState.POLICY_EVALUATION}),
    WorkflowState.POLICY_EVALUATION: frozenset(
        {WorkflowState.HUMAN_REVIEW, WorkflowState.DECISION}
    ),
    WorkflowState.HUMAN_REVIEW: frozenset({WorkflowState.DECISION}),
    WorkflowState.DECISION: frozenset(),
}


class InvalidTransitionError(ValueError):
    """Raised when a workflow state transition is not permitted."""

    def __init__(self, current: WorkflowState, target: WorkflowState) -> None:
        allowed = VALID_TRANSITIONS[current]
        if allowed:
            allowed_names = ", ".join(sorted(state.value for state in allowed))
            message = (
                f"Invalid transition from '{current.value}' to '{target.value}'. "
                f"Valid targets from '{current.value}': {allowed_names}"
            )
        else:
            message = (
                f"Invalid transition from '{current.value}' to '{target.value}'. "
                f"'{current.value}' is a terminal state."
            )
        super().__init__(message)
        self.current = current
        self.target = target
