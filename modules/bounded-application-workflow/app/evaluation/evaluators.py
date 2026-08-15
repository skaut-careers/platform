from __future__ import annotations

from dataclasses import dataclass

from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from typing import cast

from app.agents.contracts import MatchDeciderInput
from app.domain.models import JobSignals
from app.domain.models import MatchDecision, UserProfile
from app.evaluation.dataset import CaseMetadata, MatchDecisionExpectation
from app.evaluation.metrics import score_match_decision, score_profile, score_job_signals


def _f1_with_reason(
    *,
    f1: float,
    exact_match: bool,
    missing: list[str],
    extra: list[str],
) -> float | EvaluationReason:
    if exact_match:
        return f1
    detail = []
    if missing:
        detail.append(f"missing={list(missing)}")
    if extra:
        detail.append(f"extra={list(extra)}")
    return EvaluationReason(value=f1, reason="; ".join(detail))


def _flag_with_reason(ok: bool, *, expected: object, got: object) -> float | EvaluationReason:
    if ok:
        return 1.0
    return EvaluationReason(value=0.0, reason=f"expected {expected}, got {got}")


def _range_with_reason(
    ok: bool,
    *,
    score: float,
    score_min: float,
    score_max: float,
) -> float | EvaluationReason:
    if ok:
        return 1.0
    return EvaluationReason(
        value=0.0,
        reason=f"score={score}, expected {score_min}-{score_max}",
    )


@dataclass
class JobSignalExtractionEvaluator(Evaluator[object, JobSignals, object]):
    """Precision / recall / F1 per signal field + macro F1 (set-based, case-insensitive)."""

    def evaluate(self, ctx: EvaluatorContext[object, JobSignals, object]) -> EvaluatorOutput:
        if ctx.expected_output is None:
            raise ValueError("expected_output is required")

        scored = score_job_signals(ctx.expected_output, ctx.output)
        scores: dict[str, float | bool | EvaluationReason] = {
            "macro_f1": scored.macro_f1,
            "exact_match": scored.exact_match,
        }
        for field in scored.fields:
            scores[f"{field.field}_precision"] = field.precision
            scores[f"{field.field}_recall"] = field.recall
            scores[f"{field.field}_f1"] = _f1_with_reason(
                f1=field.f1,
                exact_match=field.exact_match,
                missing=field.missing,
                extra=field.extra,
            )
        return scores


@dataclass
class ProfileExtractionEvaluator(Evaluator[str, UserProfile, object]):
    """Set-based precision / recall / F1 per profile field + macro F1."""

    def evaluate(self, ctx: EvaluatorContext[str, UserProfile, object]) -> EvaluatorOutput:
        if ctx.expected_output is None:
            raise ValueError("expected_output is required")

        scored = score_profile(ctx.expected_output, ctx.output)
        scores: dict[str, float | bool | EvaluationReason] = {
            "macro_f1": scored.macro_f1,
            "exact_match": scored.exact_match,
        }
        for field in scored.fields:
            scores[f"{field.field}_f1"] = _f1_with_reason(
                f1=field.f1,
                exact_match=field.exact_match,
                missing=field.missing,
                extra=field.extra,
            )
        return scores


@dataclass
class MatchDecisionEvaluator(
    Evaluator[MatchDeciderInput, MatchDecision, CaseMetadata]
):
    """Decision accuracy + score band + alignment flags + match/decision set F1."""

    def evaluate(
        self,
        ctx: EvaluatorContext[MatchDeciderInput, MatchDecision, CaseMetadata],
    ) -> EvaluatorOutput:
        if ctx.expected_output is None:
            raise ValueError("expected_output is required")

        # Goldens store a MatchDecisionExpectation in expected_output (see MatchCase).
        expected = cast(MatchDecisionExpectation, ctx.expected_output)
        result = ctx.output
        scored = score_match_decision(expected, result)
        scores: dict[str, float | EvaluationReason] = {
            "macro_f1": scored.macro_f1,
            "decision_accuracy": _flag_with_reason(
                scored.decision_correct,
                expected=expected.decision,
                got=result.decision,
            ),
            "score_in_range": _range_with_reason(
                scored.score_in_range,
                score=result.score,
                score_min=scored.score_min,
                score_max=scored.score_max,
            ),
            "work_arrangement_aligned_correct": _flag_with_reason(
                scored.work_arrangement_aligned_correct,
                expected=expected.work_arrangement_aligned,
                got=result.work_arrangement_aligned,
            ),
            "location_aligned_correct": _flag_with_reason(
                scored.location_aligned_correct,
                expected=expected.location_aligned,
                got=result.location_aligned,
            ),
            "severe_seniority_mismatch_correct": _flag_with_reason(
                scored.severe_seniority_mismatch_correct,
                expected=expected.severe_seniority_mismatch,
                got=result.severe_seniority_mismatch,
            ),
        }
        for field in scored.fields:
            scores[f"{field.field}_f1"] = _f1_with_reason(
                f1=field.f1,
                exact_match=field.exact_match,
                missing=field.missing,
                extra=field.extra,
            )
        return scores
