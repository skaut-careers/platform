from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from pydantic_evals import Dataset, set_eval_attribute
from pydantic_evals.reporting import EvaluationReport

from app.agents.contracts import AgentOutput
from app.runtime import RuntimeConfig

InputsT = TypeVar("InputsT")
OutputsT = TypeVar("OutputsT")
MetadataT = TypeVar("MetadataT")


def record_fallback(output: AgentOutput) -> None:
    set_eval_attribute(
        "used_fallback",
        bool(output.execution and output.execution.used_fallback),
    )


def evaluate_dataset(
    dataset: Dataset[InputsT, OutputsT, MetadataT],
    task: Callable[[InputsT], OutputsT],
    *,
    runtime_config: RuntimeConfig,
    label: str | None = None,
    progress: bool = False,
    max_concurrency: int | None = 1,
) -> EvaluationReport[InputsT, OutputsT, MetadataT]:
    return dataset.evaluate_sync(
        task,
        name=label or f"runtime_{runtime_config.config_version}",
        progress=progress,
        max_concurrency=max_concurrency,
        metadata={"runtime_config_version": runtime_config.config_version},
    )


def macro_f1(report: EvaluationReport) -> float:
    averages = report.averages()
    if averages is None or "macro_f1" not in averages.scores:
        return 0.0
    return float(averages.scores["macro_f1"])


def score_average(report: EvaluationReport, key: str) -> float:
    """Mean of a named score across cases (0.0 when absent)."""
    averages = report.averages()
    if averages is None or key not in averages.scores:
        return 0.0
    return float(averages.scores[key])


def fallback_rate(report: EvaluationReport) -> float:
    """Fraction of cases that used deterministic fallback (0.0-1.0)."""
    if not report.cases:
        return 0.0
    fallbacks = sum(1 for case in report.cases if case.attributes.get("used_fallback"))
    return fallbacks / len(report.cases)
