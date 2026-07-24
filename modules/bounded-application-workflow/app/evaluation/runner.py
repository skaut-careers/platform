from pathlib import Path

from pydantic_ai.models import Model
from pydantic_evals import set_eval_attribute
from pydantic_evals.reporting import EvaluationReport

from app.agents.contracts import SignalExtractorInput
from app.agents.wiring import create_agents
from app.domain.job_signals import JobSignals
from app.domain.models import JobDescription
from app.evaluation.dataset import CaseMetadata, SignalCase, load_dataset
from app.runtime import RuntimeConfig
from app.runtime.config_loader import load_runtime_config


def run_evaluation(
    *,
    label: str | None = None,
    runtime_version: str | None = None,
    runtime_config: RuntimeConfig | None = None,
    model: Model | str | None = None,
    dataset_dir: Path | None = None,
    cases: list[SignalCase] | None = None,
    progress: bool = False,
    max_concurrency: int | None = 1,
) -> EvaluationReport[JobDescription, JobSignals, CaseMetadata]:
    """Run the golden dataset via Pydantic Evals (visible in Logfire when configured)."""
    env = {"RUNTIME_CONFIG_VERSION": runtime_version} if runtime_version else None
    config = runtime_config or load_runtime_config(env=env)
    _, extractor, *_ = create_agents(runtime_config=config, model=model)
    experiment = label or f"runtime_{config.config_version}"
    dataset = load_dataset(dataset_dir, cases=cases)

    def task(job_description: JobDescription) -> JobSignals:
        output = extractor.run(SignalExtractorInput(job_description=job_description))
        set_eval_attribute(
            "used_fallback",
            bool(output.execution and output.execution.used_fallback),
        )
        return output.signals

    return dataset.evaluate_sync(
        task,
        name=experiment,
        progress=progress,
        max_concurrency=max_concurrency,
        metadata={"runtime_config_version": config.config_version},
    )


def macro_f1(report: EvaluationReport) -> float:
    averages = report.averages()
    if averages is None or "macro_f1" not in averages.scores:
        return 0.0
    return float(averages.scores["macro_f1"])


def fallback_rate(report: EvaluationReport) -> float:
    """Fraction of cases that used deterministic fallback (0.0–1.0)."""
    if not report.cases:
        return 0.0
    fallbacks = sum(1 for case in report.cases if case.attributes.get("used_fallback"))
    return fallbacks / len(report.cases)
