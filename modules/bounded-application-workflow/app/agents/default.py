import os

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
    SignalExtractionMetadata,
    SignalExtractor,
    SignalExtractorInput,
    SignalExtractorOutput,
    WorkflowOrchestrator,
    WorkflowOrchestratorInput,
    WorkflowOrchestratorOutput,
    WorkflowPlanner,
    WorkflowPlannerInput,
    WorkflowPlannerOutput,
)
from app.agents.decision_rules import build_workflow_decision
from app.agents.llm_signal_extraction import LLMSignalExtractor
from app.agents.orchestration import run_workflow_evaluation as _run_workflow_evaluation
from app.agents.profile_matching import match_profile_to_job
from app.agents.signal_extraction import extract_job_signals
from app.agents.workflow_planning import create_workflow_plan
from app.domain.models import WorkflowDecision, WorkflowInput, WorkflowOutput
from app.domain.workflow_run import WorkflowRun
from app.llm.client import LLMClient, OpenAILLMClient
from app.runtime import BoundedAgentRuntime, SignalExtractorRuntimeConfig


class DefaultWorkflowPlanner:
    def run(self, agent_input: WorkflowPlannerInput) -> WorkflowPlannerOutput:
        plan = create_workflow_plan(agent_input.workflow_input)
        return WorkflowPlannerOutput(plan=plan)


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


class DefaultWorkflowOrchestrator:
    def __init__(
        self,
        *,
        planner: WorkflowPlanner | None = None,
        extractor: SignalExtractor | None = None,
        matcher: ProfileMatcher | None = None,
        policy: DecisionPolicy | None = None,
        review_gate: HumanReviewGate | None = None,
    ) -> None:
        self._planner = planner or DefaultWorkflowPlanner()
        self._extractor = extractor or DefaultSignalExtractor()
        self._matcher = matcher or DefaultProfileMatcher()
        self._policy = policy or DefaultDecisionPolicy()
        self._review_gate = review_gate or PassthroughHumanReviewGate()

    def run(
        self, agent_input: WorkflowOrchestratorInput
    ) -> WorkflowOrchestratorOutput:
        plan = self._planner.run(
            WorkflowPlannerInput(workflow_input=agent_input.workflow_input)
        ).plan
        output, run = _run_workflow_evaluation(
            agent_input.workflow_input,
            plan=plan,
            extractor=self._extractor,
            matcher=self._matcher,
            policy=self._policy,
            review_gate=self._review_gate,
        )
        return WorkflowOrchestratorOutput(output=output, run=run)


def default_agents() -> tuple[
    WorkflowPlanner,
    SignalExtractor,
    ProfileMatcher,
    DecisionPolicy,
    HumanReviewGate,
    WorkflowOrchestrator,
]:
    planner = DefaultWorkflowPlanner()
    extractor = DefaultSignalExtractor()
    matcher = DefaultProfileMatcher()
    policy = DefaultDecisionPolicy()
    review_gate = PassthroughHumanReviewGate()
    orchestrator = DefaultWorkflowOrchestrator(
        planner=planner,
        extractor=extractor,
        matcher=matcher,
        policy=policy,
        review_gate=review_gate,
    )
    return planner, extractor, matcher, policy, review_gate, orchestrator


def llm_agents(
    *,
    client: LLMClient | None = None,
    config: SignalExtractorRuntimeConfig | None = None,
) -> tuple[
    WorkflowPlanner,
    SignalExtractor,
    ProfileMatcher,
    DecisionPolicy,
    HumanReviewGate,
    WorkflowOrchestrator,
]:
    """Wire the workflow with an LLM-backed signal extractor and deterministic fallback."""
    planner = DefaultWorkflowPlanner()
    extractor = LLMSignalExtractor(
        client=client or OpenAILLMClient(model=(config or SignalExtractorRuntimeConfig()).model),
        config=config,
        runtime=BoundedAgentRuntime(),
        fallback=DefaultSignalExtractor(),
    )
    matcher = DefaultProfileMatcher()
    policy = DefaultDecisionPolicy()
    review_gate = PassthroughHumanReviewGate()
    orchestrator = DefaultWorkflowOrchestrator(
        planner=planner,
        extractor=extractor,
        matcher=matcher,
        policy=policy,
        review_gate=review_gate,
    )
    return planner, extractor, matcher, policy, review_gate, orchestrator


def _signal_extractor_mode(mode: str | None = None) -> str:
    resolved = (mode or os.environ.get("SIGNAL_EXTRACTOR", "deterministic")).casefold()
    if resolved in {"deterministic", "llm"}:
        return resolved
    raise ValueError(
        f"Unsupported SIGNAL_EXTRACTOR value {resolved!r}; expected 'deterministic' or 'llm'"
    )


def _signal_extractor_config_from_env() -> SignalExtractorRuntimeConfig:
    return SignalExtractorRuntimeConfig(
        model=os.environ.get("LLM_SIGNAL_MODEL", "gpt-5-mini"),
    )


def create_agents(
    *,
    signal_extractor: str | None = None,
    client: LLMClient | None = None,
    config: SignalExtractorRuntimeConfig | None = None,
) -> tuple[
    WorkflowPlanner,
    SignalExtractor,
    ProfileMatcher,
    DecisionPolicy,
    HumanReviewGate,
    WorkflowOrchestrator,
]:
    """Select agent wiring from env or an explicit override."""
    if _signal_extractor_mode(signal_extractor) == "llm":
        return llm_agents(
            client=client,
            config=config or _signal_extractor_config_from_env(),
        )
    return default_agents()


def evaluate_workflow(workflow_input: WorkflowInput) -> WorkflowOutput:
    *_, orchestrator = create_agents()
    return orchestrator.run(
        WorkflowOrchestratorInput(workflow_input=workflow_input)
    ).output


def run_workflow_evaluation(
    workflow_input: WorkflowInput,
) -> tuple[WorkflowOutput, WorkflowRun]:
    *_, orchestrator = create_agents()
    result = orchestrator.run(
        WorkflowOrchestratorInput(workflow_input=workflow_input)
    )
    return result.output, result.run
