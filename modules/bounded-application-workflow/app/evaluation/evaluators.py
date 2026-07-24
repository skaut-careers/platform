from __future__ import annotations

from dataclasses import dataclass

from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from app.domain.job_signals import JobSignals
from app.evaluation.metrics import score_signals


@dataclass
class SignalExtractionEvaluator(Evaluator[object, JobSignals, object]):
    """Precision / recall / F1 per signal field + macro F1 (set-based, case-insensitive)."""

    def evaluate(self, ctx: EvaluatorContext[object, JobSignals, object]) -> EvaluatorOutput:
        if ctx.expected_output is None:
            raise ValueError("expected_output is required")

        scored = score_signals(ctx.expected_output, ctx.output)
        scores: dict[str, float | bool | EvaluationReason] = {
            "macro_f1": scored.macro_f1,
            "exact_match": scored.exact_match,
        }
        for field in scored.fields:
            scores[f"{field.field}_precision"] = field.precision
            scores[f"{field.field}_recall"] = field.recall
            if field.exact_match:
                scores[f"{field.field}_f1"] = field.f1
            else:
                detail = []
                if field.missing:
                    detail.append(f"missing={list(field.missing)}")
                if field.extra:
                    detail.append(f"extra={list(field.extra)}")
                scores[f"{field.field}_f1"] = EvaluationReason(
                    value=field.f1,
                    reason="; ".join(detail),
                )
        return scores
