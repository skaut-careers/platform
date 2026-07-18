import json
from typing import Any

from app.domain.job_signals import SIGNAL_FIELDS
from app.evaluation.runner import EvalRun, runtime_config_label, signal_extractor_config


def _pct(value: float) -> str:
    return f"{value * 100:5.1f}%"


def describe_run(run: EvalRun) -> str:
    agent = signal_extractor_config(run.runtime_config)
    parts = [run.label, runtime_config_label(run.runtime_config), agent.mode]
    if agent.mode == "llm":
        parts.append(agent.model)
    if agent.prompt:
        parts.append(f"prompt {agent.prompt.version}")
    return " | ".join(parts)


def format_report(run: EvalRun) -> str:
    lines = [
        "Signal Extractor Evaluation",
        "===========================",
        f"Run:             {describe_run(run)}",
    ]

    lines.extend(
        [
            "",
            "Aggregate",
            "---------",
            f"Cases:              {run.aggregate.case_count}",
            f"Fallback:           {run.aggregate.fallback_count}/{run.aggregate.case_count}",
            f"Exact match rate:   {_pct(run.aggregate.exact_match_rate)}",
            f"Macro F1:           {_pct(run.aggregate.macro_f1)}",
            "",
            "Field macro F1",
            "--------------",
        ]
    )

    for field in SIGNAL_FIELDS:
        score = run.aggregate.field_macro_f1.get(field, 0.0)
        lines.append(f"  {field:<24} {_pct(score)}")

    lines.extend(["", "Cases", "-----"])
    for result in run.case_results:
        status = "PASS" if result.exact_match else "FAIL"
        fallback = " fallback" if result.used_fallback else ""
        lines.append(
            f"  [{status}] {result.case_id:<24} "
            f"macro_f1={_pct(result.macro_f1)}{fallback}"
        )
        if not result.exact_match:
            for metric in result.field_metrics:
                if metric.exact_match:
                    continue
                if metric.missing:
                    lines.append(f"         missing {metric.field}: {metric.missing}")
                if metric.extra:
                    lines.append(f"         extra   {metric.field}: {metric.extra}")

    return "\n".join(lines)


def format_comparison_report(
    baseline: EvalRun, candidate: EvalRun, comparison: dict[str, Any]
) -> str:
    lines = [
        "Signal Extractor Comparison",
        "===========================",
        f"Baseline:  {describe_run(baseline)}",
        f"Candidate: {describe_run(candidate)}",
        "",
        "Aggregate",
        "---------",
        f"Macro F1:         {_pct(comparison['baseline_macro_f1'])} -> "
        f"{_pct(comparison['candidate_macro_f1'])} "
        f"(delta {comparison['delta_macro_f1']:+.3f})",
        f"Exact match rate: {_pct(comparison['baseline_exact_match_rate'])} -> "
        f"{_pct(comparison['candidate_exact_match_rate'])} "
        f"(delta {comparison['delta_exact_match_rate']:+.3f})",
        "",
        "Field delta F1 (candidate - baseline)",
        "-----------------------------------",
    ]

    for field in SIGNAL_FIELDS:
        delta = comparison["field_delta_f1"].get(field, 0.0)
        lines.append(f"  {field:<24} {delta:+.3f}")

    lines.extend(["", "Cases", "-----"])
    for case in comparison["cases"]:
        case_id = case["case_id"]
        base_f1 = case["baseline_macro_f1"]
        cand_f1 = case["candidate_macro_f1"]
        delta = case["delta_macro_f1"]
        if base_f1 is None or cand_f1 is None or delta is None:
            lines.append(f"  {case_id:<24} missing in one run")
            continue
        lines.append(
            f"  {case_id:<24} {_pct(base_f1)} -> {_pct(cand_f1)} (delta {delta:+.3f})"
        )

    return "\n".join(lines)


def report_to_json(run: EvalRun) -> dict[str, Any]:
    return run.model_dump()
