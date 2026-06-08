from app.agents.contracts import (
    DecisionPolicy,
    DecisionPolicyInput,
    DecisionPolicyOutput,
    HumanReviewGate,
    HumanReviewGateInput,
    HumanReviewGateOutput,
    ProfileMatcher,
    ProfileMatcherInput,
    ProfileMatcherOutput,
    SignalExtractor,
    SignalExtractorInput,
    SignalExtractorOutput,
    WorkflowOrchestrator,
    WorkflowOrchestratorInput,
    WorkflowOrchestratorOutput,
)
from app.services.extractor import extract_job_signals
from app.services.matcher import match_profile_to_job
from app.services.policy import build_workflow_decision, run_workflow_evaluation


class DefaultSignalExtractor:
    def run(self, agent_input: SignalExtractorInput) -> SignalExtractorOutput:
        signals = extract_job_signals(agent_input.job_description)
        return SignalExtractorOutput(signals=signals)


class DefaultProfileMatcher:
    def run(self, agent_input: ProfileMatcherInput) -> ProfileMatcherOutput:
        match = match_profile_to_job(
            agent_input.user_profile,
            agent_input.job_description,
            agent_input.signals,
        )
        return ProfileMatcherOutput(match=match)


class DefaultDecisionPolicy:
    def run(self, agent_input: DecisionPolicyInput) -> DecisionPolicyOutput:
        decision = build_workflow_decision(agent_input.match, agent_input.signals)
        return DecisionPolicyOutput(decision=decision)


class PassthroughHumanReviewGate:
    """Accepts escalated decisions without modification until review is wired."""

    def run(self, agent_input: HumanReviewGateInput) -> HumanReviewGateOutput:
        return HumanReviewGateOutput(
            decision=agent_input.decision,
            approved=True,
        )


class DefaultWorkflowOrchestrator:
    def run(
        self, agent_input: WorkflowOrchestratorInput
    ) -> WorkflowOrchestratorOutput:
        output, run = run_workflow_evaluation(agent_input.workflow_input)
        return WorkflowOrchestratorOutput(output=output, run=run)


def default_agents() -> tuple[
    SignalExtractor,
    ProfileMatcher,
    DecisionPolicy,
    HumanReviewGate,
    WorkflowOrchestrator,
]:
    return (
        DefaultSignalExtractor(),
        DefaultProfileMatcher(),
        DefaultDecisionPolicy(),
        PassthroughHumanReviewGate(),
        DefaultWorkflowOrchestrator(),
    )
