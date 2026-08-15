from pathlib import Path

from pydantic_ai.models import Model
from pydantic_evals.reporting import EvaluationReport

from app.agents.contracts import (
    ProfileExtractorInput,
    MatchDeciderInput,
    SignalExtractorInput,
)
from app.agents.wiring import (
    create_profile_extractor,
    create_match_decider,
    create_signal_extractor,
)
from app.domain.models import JobSignals
from app.domain.models import MatchDecision, UserProfile
from app.evaluation.dataset import (
    CaseMetadata,
    MatchCase,
    ProfileCase,
    SignalCase,
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


def run_match_decision_evaluation(
    *,
    label: str | None = None,
    runtime_version: str | None = None,
    runtime_config: RuntimeConfig | None = None,
    model: Model | str | None = None,
    dataset_dir: Path | None = None,
    cases: list[MatchCase] | None = None,
    progress: bool = False,
    max_concurrency: int | None = 1,
) -> EvaluationReport[MatchDeciderInput, MatchDecision, CaseMetadata]:
    """Run the match+decision golden dataset via Pydantic Evals."""
    config = runtime_config or load_runtime_config(version=runtime_version)
    match_decider = create_match_decider(
        runtime_config=config, model=model
    )

    def task(agent_input: MatchDeciderInput) -> MatchDecision:
        output = match_decider.run(agent_input)
        record_fallback(output)
        return output.result

    return evaluate_dataset(
        load_match_dataset(dataset_dir, cases=cases),
        task,
        runtime_config=config,
        label=label,
        progress=progress,
        max_concurrency=max_concurrency,
    )
