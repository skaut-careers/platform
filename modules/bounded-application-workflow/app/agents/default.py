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
from app.agents.decision_rules import build_workflow_decision
from app.agents.orchestration import run_workflow_evaluation as _run_workflow_evaluation
from app.agents.profile_matching import match_profile_to_job
from app.agents.signal_extraction import extract_job_signals
from app.domain.models import WorkflowInput, WorkflowOutput
from app.domain.workflow_run import WorkflowRun


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
    def __init__(
        self,
        *,
        extractor: SignalExtractor | None = None,
        matcher: ProfileMatcher | None = None,
        policy: DecisionPolicy | None = None,
        review_gate: HumanReviewGate | None = None,
    ) -> None:
        self._extractor = extractor or DefaultSignalExtractor()
        self._matcher = matcher or DefaultProfileMatcher()
        self._policy = policy or DefaultDecisionPolicy()
        self._review_gate = review_gate or PassthroughHumanReviewGate()

    def run(
        self, agent_input: WorkflowOrchestratorInput
    ) -> WorkflowOrchestratorOutput:
        output, run = _run_workflow_evaluation(
            agent_input.workflow_input,
            extractor=self._extractor,
            matcher=self._matcher,
            policy=self._policy,
            review_gate=self._review_gate,
        )
        return WorkflowOrchestratorOutput(output=output, run=run)


def default_agents() -> tuple[
    SignalExtractor,
    ProfileMatcher,
    DecisionPolicy,
    HumanReviewGate,
    WorkflowOrchestrator,
]:
    extractor = DefaultSignalExtractor()
    matcher = DefaultProfileMatcher()
    policy = DefaultDecisionPolicy()
    review_gate = PassthroughHumanReviewGate()
    orchestrator = DefaultWorkflowOrchestrator(
        extractor=extractor,
        matcher=matcher,
        policy=policy,
        review_gate=review_gate,
    )
    return extractor, matcher, policy, review_gate, orchestrator


def evaluate_workflow(workflow_input: WorkflowInput) -> WorkflowOutput:
    _, _, _, _, orchestrator = default_agents()
    return orchestrator.run(
        WorkflowOrchestratorInput(workflow_input=workflow_input)
    ).output


def run_workflow_evaluation(
    workflow_input: WorkflowInput,
) -> tuple[WorkflowOutput, WorkflowRun]:
    _, _, _, _, orchestrator = default_agents()
    result = orchestrator.run(
        WorkflowOrchestratorInput(workflow_input=workflow_input)
    )
    return result.output, result.run
