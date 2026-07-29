"""Compose the workflow pipeline from concrete agent implementations."""

from collections.abc import Callable
from typing import Any, TypeVar, cast

from pydantic_ai.models import Model

from app.agents.contracts import (
    DecisionPolicy,
    ProfileExtractor,
    ProfileMatcher,
    SignalExtractor,
    WorkflowOrchestrator,
    WorkflowOrchestratorInput,
    WorkflowPlanner,
)
from app.agents.decision_rules import DefaultDecisionPolicy
from app.agents.orchestration.orchestrator import DefaultWorkflowOrchestrator
from app.agents.orchestration.state import WorkflowGraphState
from app.agents.profile_extraction import DefaultProfileExtractor, LLMProfileExtractor
from app.agents.profile_matching import DefaultProfileMatcher, LLMProfileMatcher
from app.agents.signal_extraction import DefaultSignalExtractor, LLMSignalExtractor
from app.agents.workflow_planning import DefaultWorkflowPlanner
from app.domain.models import WorkflowInput, WorkflowOutput
from app.runtime import BoundedAgentRuntime, RuntimeConfig
from app.runtime.config_loader import load_runtime_config

_AgentT = TypeVar("_AgentT")
_AgentBundle = tuple[
    WorkflowPlanner,
    SignalExtractor,
    ProfileMatcher,
    DecisionPolicy,
    WorkflowOrchestrator,
]


def _resolve_mode(mode: str) -> str:
    resolved = mode.casefold()
    if resolved not in {"deterministic", "llm"}:
        raise ValueError(
            f"Unsupported signal extractor mode {mode!r}; "
            "expected 'deterministic' or 'llm'"
        )
    return resolved


def _create_agent(
    *,
    llm_type: type[_AgentT],
    default_factory: Callable[[], _AgentT],
    runtime_config: RuntimeConfig | None = None,
    model: Model | str | None = None,
    mode: str | None = None,
) -> _AgentT:
    config = runtime_config or load_runtime_config()
    resolved = _resolve_mode(mode or config.agent_for(llm_type).mode)
    if resolved == "llm":
        # type[_AgentT] does not expose BoundedLLMAgent.__init__ kwargs to the checker.
        agent_cls = cast(Any, llm_type)
        return cast(
            _AgentT,
            agent_cls(
                model=model,
                runtime_config=config,
                runtime=BoundedAgentRuntime(),
                fallback=default_factory(),
            ),
        )
    return default_factory()


def create_signal_extractor(
    *,
    runtime_config: RuntimeConfig | None = None,
    model: Model | str | None = None,
    mode: str | None = None,
) -> SignalExtractor:
    """Select the signal extractor from the runtime config (LLM under v2/v3)."""
    return _create_agent(
        llm_type=LLMSignalExtractor,
        default_factory=DefaultSignalExtractor,
        runtime_config=runtime_config,
        model=model,
        mode=mode,
    )


def create_profile_extractor(
    *,
    runtime_config: RuntimeConfig | None = None,
    model: Model | str | None = None,
    mode: str | None = None,
) -> ProfileExtractor:
    """Select the profile extractor from the runtime config (LLM under v2/v3)."""
    return _create_agent(
        llm_type=LLMProfileExtractor,
        default_factory=DefaultProfileExtractor,
        runtime_config=runtime_config,
        model=model,
        mode=mode,
    )


def create_profile_matcher(
    *,
    runtime_config: RuntimeConfig | None = None,
    model: Model | str | None = None,
    mode: str | None = None,
) -> ProfileMatcher:
    """Select the profile matcher from the runtime config (LLM under v2/v3)."""
    return _create_agent(
        llm_type=LLMProfileMatcher,
        default_factory=DefaultProfileMatcher,
        runtime_config=runtime_config,
        model=model,
        mode=mode,
    )


def create_agents(
    *,
    signal_extractor: str | None = None,
    runtime_config: RuntimeConfig | None = None,
    signal_model: Model | str | None = None,
    match_model: Model | str | None = None,
) -> _AgentBundle:
    """Select agent wiring from the runtime config registry or explicit overrides."""
    config = runtime_config or load_runtime_config()
    mode = _resolve_mode(
        signal_extractor or config.agent_for(LLMSignalExtractor).mode
    )
    planner = DefaultWorkflowPlanner()
    extractor = create_signal_extractor(
        runtime_config=config, model=signal_model, mode=mode
    )
    matcher = create_profile_matcher(
        runtime_config=config, model=match_model, mode=mode
    )
    policy = DefaultDecisionPolicy()
    orchestrator = DefaultWorkflowOrchestrator(
        planner=planner,
        extractor=extractor,
        matcher=matcher,
        policy=policy,
    )
    return planner, extractor, matcher, policy, orchestrator


def evaluate_workflow(
    workflow_input: WorkflowInput,
    *,
    runtime_config: RuntimeConfig | None = None,
) -> WorkflowOutput:
    output, _ = run_workflow_evaluation(
        workflow_input, runtime_config=runtime_config
    )
    return output


def run_workflow_evaluation(
    workflow_input: WorkflowInput,
    *,
    runtime_config: RuntimeConfig | None = None,
) -> tuple[WorkflowOutput, WorkflowGraphState]:
    result = create_agents(runtime_config=runtime_config)[-1].run(
        WorkflowOrchestratorInput(workflow_input=workflow_input)
    )
    return result.output, result.run
