from pathlib import Path

from pydantic_ai.models import Model
from pydantic_evals.reporting import EvaluationReport

from app.agents.contracts import (
    DecisionPolicyInput,
    ProfileExtractorInput,
    ProfileMatcherInput,
    SignalExtractorInput,
)
from app.agents.wiring import (
    create_decision_policy,
    create_profile_extractor,
    create_profile_matcher,
    create_signal_extractor,
)
from app.domain.job_signals import JobSignals
from app.domain.models import ProfileMatchResult, UserProfile, WorkflowDecision
from app.evaluation.dataset import (
    CaseMetadata,
    DecisionCase,
    MatchCase,
    ProfileCase,
    SignalCase,
    load_decision_dataset,
    load_match_dataset,
    load_profile_dataset,
    load_signal_dataset,
)
from app.evaluation.report import evaluate_dataset, record_fallback
from app.runtime import RuntimeConfig, load_runtime_config


def run_signal_evaluation(
    *,
    label: str | None = None,
    runtime_version: str | None = None,
    runtime_config: RuntimeConfig | None = None,
    model: Model | str | None = None,
    dataset_dir: Path | None = None,
    cases: list[SignalCase] | None = None,
    progress: bool = False,
    max_concurrency: int | None = 1,
) -> EvaluationReport[str, JobSignals, CaseMetadata]:
    """Run the signal-extraction golden dataset via Pydantic Evals."""
    config = runtime_config or load_runtime_config(version=runtime_version)
    extractor = create_signal_extractor(runtime_config=config, model=model)

    def task(job_text: str) -> JobSignals:
        output = extractor.run(SignalExtractorInput(job_description_text=job_text))
        record_fallback(output)
        return output.job_signals

    return evaluate_dataset(
        load_signal_dataset(dataset_dir, cases=cases),
        task,
        runtime_config=config,
        label=label,
        progress=progress,
        max_concurrency=max_concurrency,
    )


def run_profile_extraction_evaluation(
    *,
    label: str | None = None,
    runtime_version: str | None = None,
    runtime_config: RuntimeConfig | None = None,
    model: Model | str | None = None,
    dataset_dir: Path | None = None,
    cases: list[ProfileCase] | None = None,
    progress: bool = False,
    max_concurrency: int | None = 1,
) -> EvaluationReport[str, UserProfile, CaseMetadata]:
    """Run the profile-extraction golden dataset via Pydantic Evals."""
    config = runtime_config or load_runtime_config(version=runtime_version)
    extractor = create_profile_extractor(runtime_config=config, model=model)

    def task(profile_text: str) -> UserProfile:
        output = extractor.run(ProfileExtractorInput(profile_text=profile_text))
        record_fallback(output)
        return output.profile

    return evaluate_dataset(
        load_profile_dataset(dataset_dir, cases=cases),
        task,
        runtime_config=config,
        label=label,
        progress=progress,
        max_concurrency=max_concurrency,
    )


def run_profile_matching_evaluation(
    *,
    label: str | None = None,
    runtime_version: str | None = None,
    runtime_config: RuntimeConfig | None = None,
    model: Model | str | None = None,
    dataset_dir: Path | None = None,
    cases: list[MatchCase] | None = None,
    progress: bool = False,
    max_concurrency: int | None = 1,
) -> EvaluationReport[ProfileMatcherInput, ProfileMatchResult, CaseMetadata]:
    """Run the profile-matching golden dataset via Pydantic Evals."""
    config = runtime_config or load_runtime_config(version=runtime_version)
    matcher = create_profile_matcher(runtime_config=config, model=model)

    def task(agent_input: ProfileMatcherInput) -> ProfileMatchResult:
        output = matcher.run(agent_input)
        record_fallback(output)
        return output.match

    return evaluate_dataset(
        load_match_dataset(dataset_dir, cases=cases),
        task,
        runtime_config=config,
        label=label,
        progress=progress,
        max_concurrency=max_concurrency,
    )


def run_decision_policy_evaluation(
    *,
    label: str | None = None,
    runtime_version: str | None = None,
    runtime_config: RuntimeConfig | None = None,
    model: Model | str | None = None,
    dataset_dir: Path | None = None,
    cases: list[DecisionCase] | None = None,
    progress: bool = False,
    max_concurrency: int | None = 1,
) -> EvaluationReport[DecisionPolicyInput, WorkflowDecision, CaseMetadata]:
    """Run the decision-policy golden dataset via Pydantic Evals."""
    config = runtime_config or load_runtime_config(version=runtime_version)
    policy = create_decision_policy(runtime_config=config, model=model)

    def task(agent_input: DecisionPolicyInput) -> WorkflowDecision:
        output = policy.run(agent_input)
        record_fallback(output)
        return output.decision

    return evaluate_dataset(
        load_decision_dataset(dataset_dir, cases=cases),
        task,
        runtime_config=config,
        label=label,
        progress=progress,
        max_concurrency=max_concurrency,
    )
