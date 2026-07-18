from pathlib import Path

from pydantic import BaseModel, Field

from app.agents.contracts import SignalExtractor, SignalExtractorInput
from app.agents.signal_extraction import LLMSignalExtractor
from app.agents.wiring import create_agents
from app.evaluation.dataset import EvalCase, load_eval_cases
from app.evaluation.metrics import AggregateMetrics, CaseResult, aggregate_metrics, score_case
from app.llm.client import LLMClient
from app.runtime import RuntimeConfig
from app.runtime.config_loader import load_runtime_config
from app.runtime.runtime_config import AgentRuntimeConfig


class EvalRun(BaseModel):
    label: str
    runtime_config: RuntimeConfig
    case_results: list[CaseResult] = Field(default_factory=list)
    aggregate: AggregateMetrics


def signal_extractor_config(config: RuntimeConfig) -> AgentRuntimeConfig:
    return config.agent_for(LLMSignalExtractor)


def runtime_config_label(config: RuntimeConfig) -> str:
    return f"runtime_{config.config_version}"


def build_signal_extractor(
    *,
    runtime_version: str | None = None,
    runtime_config: RuntimeConfig | None = None,
    client: LLMClient | None = None,
) -> tuple[SignalExtractor, RuntimeConfig]:
    env = {"RUNTIME_CONFIG_VERSION": runtime_version} if runtime_version else None
    config = runtime_config or load_runtime_config(env=env)
    _, extractor, *_ = create_agents(runtime_config=config, client=client)
    return extractor, config


def run_evaluation(
    *,
    label: str | None = None,
    runtime_version: str | None = None,
    runtime_config: RuntimeConfig | None = None,
    client: LLMClient | None = None,
    dataset_dir: Path | None = None,
    cases: list[EvalCase] | None = None,
) -> EvalRun:
    extractor, config = build_signal_extractor(
        runtime_version=runtime_version,
        runtime_config=runtime_config,
        client=client,
    )
    resolved_label = label or runtime_config_label(config)

    loaded_cases = cases if cases is not None else load_eval_cases(dataset_dir)
    case_results: list[CaseResult] = []
    for case in loaded_cases:
        output = extractor.run(
            SignalExtractorInput(job_description=case.job_description)
        )
        used_fallback = bool(output.execution and output.execution.used_fallback)
        case_results.append(
            score_case(case, output.signals, used_fallback=used_fallback)
        )

    return EvalRun(
        label=resolved_label,
        runtime_config=config,
        case_results=case_results,
        aggregate=aggregate_metrics(case_results),
    )


def compare_runs(baseline: EvalRun, candidate: EvalRun) -> dict[str, object]:
    baseline_by_id = {result.case_id: result for result in baseline.case_results}
    candidate_by_id = {result.case_id: result for result in candidate.case_results}
    case_ids = sorted(set(baseline_by_id) | set(candidate_by_id))

    per_case: list[dict[str, object]] = []
    for case_id in case_ids:
        base = baseline_by_id.get(case_id)
        cand = candidate_by_id.get(case_id)
        per_case.append(
            {
                "case_id": case_id,
                "baseline_macro_f1": base.macro_f1 if base else None,
                "candidate_macro_f1": cand.macro_f1 if cand else None,
                "delta_macro_f1": (
                    (cand.macro_f1 - base.macro_f1)
                    if base and cand
                    else None
                ),
                "baseline_exact_match": base.exact_match if base else None,
                "candidate_exact_match": cand.exact_match if cand else None,
            }
        )

    field_deltas = {
        field: candidate.aggregate.field_macro_f1.get(field, 0.0)
        - baseline.aggregate.field_macro_f1.get(field, 0.0)
        for field in sorted(
            set(baseline.aggregate.field_macro_f1)
            | set(candidate.aggregate.field_macro_f1)
        )
    }

    return {
        "baseline_macro_f1": baseline.aggregate.macro_f1,
        "candidate_macro_f1": candidate.aggregate.macro_f1,
        "delta_macro_f1": candidate.aggregate.macro_f1 - baseline.aggregate.macro_f1,
        "baseline_exact_match_rate": baseline.aggregate.exact_match_rate,
        "candidate_exact_match_rate": candidate.aggregate.exact_match_rate,
        "delta_exact_match_rate": (
            candidate.aggregate.exact_match_rate - baseline.aggregate.exact_match_rate
        ),
        "field_delta_f1": field_deltas,
        "cases": per_case,
    }
