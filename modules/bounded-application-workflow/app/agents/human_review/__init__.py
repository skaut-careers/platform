from app.agents.contracts import HumanReviewGateInput, HumanReviewGateOutput
from app.domain.models import WorkflowDecision


class PassthroughHumanReviewGate:
    """Approves escalated decisions unchanged; stands in for a live reviewer."""

    def run(self, agent_input: HumanReviewGateInput) -> HumanReviewGateOutput:
        return HumanReviewGateOutput(
            decision=agent_input.decision,
            approved=True,
            reviewer_notes="Auto-approved by passthrough review gate.",
        )


class RecordedHumanReviewGate:
    """Applies a pre-recorded human verdict instead of pausing for live review.

    With no revision configured it approves the escalated decision as-is;
    with a revision it replaces the decision and marks it as not approved.
    """

    def __init__(
        self,
        *,
        revised_decision: WorkflowDecision | None = None,
        reviewer_notes: str = "",
    ) -> None:
        self._revised_decision = revised_decision
        self._reviewer_notes = reviewer_notes

    def run(self, agent_input: HumanReviewGateInput) -> HumanReviewGateOutput:
        if self._revised_decision is None:
            return HumanReviewGateOutput(
                decision=agent_input.decision,
                approved=True,
                reviewer_notes=self._reviewer_notes,
            )
        return HumanReviewGateOutput(
            decision=self._revised_decision,
            approved=False,
            reviewer_notes=self._reviewer_notes,
        )
