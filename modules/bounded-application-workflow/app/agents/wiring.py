"""Compose the workflow pipeline from concrete agent implementations."""

from app.agents.contracts import (
    DecisionPolicy,
    HumanReviewGate,
    ProfileMatcher,
    SignalExtractor,
    WorkflowOrchestrator,
    WorkflowOrchestratorInput,
    WorkflowPlanner,
)
from app.agents.decision_rules import DefaultDecisionPolicy
from app.agents.human_review import PassthroughHumanReviewGate
from app.agents.orchestration.orchestrator import DefaultWorkflowOrchestrator
from app.agents.profile_matching import DefaultProfileMatcher
from app.agents.signal_extraction import DefaultSignalExtractor, LLMSignalExtractor
from app.agents.workflow_planning import DefaultWorkflowPlanner
from app.domain.models import WorkflowInput, WorkflowOutput
from app.domain.workflow_run import WorkflowRun
from app.llm.client import LLMClient, OpenAILLMClient
from app.runtime import BoundedAgentRuntime, RuntimeConfig
from app.runtime.config_loader import load_runtime_config


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
    config: RuntimeConfig | None = None,
) -> tuple[
    WorkflowPlanner,
    SignalExtractor,
    ProfileMatcher,
    DecisionPolicy,
    HumanReviewGate,
    WorkflowOrchestrator,
]:
    """Wire the workflow with an LLM-backed signal extractor and deterministic fallback."""
    config = config or load_runtime_config()
    planner = DefaultWorkflowPlanner()
    extractor = LLMSignalExtractor(
        client=client or OpenAILLMClient(
            model=config.agent_for(LLMSignalExtractor).model
        ),
        runtime_config=config,
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


def create_agents(
    *,
    signal_extractor: str | None = None,
    runtime_config: RuntimeConfig | None = None,
    client: LLMClient | None = None,
) -> tuple[
    WorkflowPlanner,
    SignalExtractor,
    ProfileMatcher,
    DecisionPolicy,
    HumanReviewGate,
    WorkflowOrchestrator,
]:
    """Select agent wiring from the runtime config registry or explicit overrides."""
    config = runtime_config or load_runtime_config()
    extractor = config.agent_for(LLMSignalExtractor)
    mode = (signal_extractor or extractor.mode).casefold()
    if mode not in {"deterministic", "llm"}:
        raise ValueError(
            f"Unsupported signal extractor mode {mode!r}; "
            "expected 'deterministic' or 'llm'"
        )
    if mode == "llm":
        return llm_agents(client=client, config=config)
    return default_agents()


def evaluate_workflow(workflow_input: WorkflowInput) -> WorkflowOutput:
    output, _ = run_workflow_evaluation(workflow_input)
    return output


def run_workflow_evaluation(
    workflow_input: WorkflowInput,
) -> tuple[WorkflowOutput, WorkflowRun]:
    result = create_agents()[-1].run(
        WorkflowOrchestratorInput(workflow_input=workflow_input)
    )
    return result.output, result.run
