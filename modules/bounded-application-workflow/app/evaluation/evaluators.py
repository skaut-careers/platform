from __future__ import annotations

from dataclasses import dataclass

from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from app.agents.contracts import DecisionPolicyInput, ProfileMatcherInput
from app.domain.job_signals import JobSignals
from app.domain.models import ProfileMatchResult, UserProfile, WorkflowDecision
from app.evaluation.dataset import CaseMetadata
from app.evaluation.metrics import score_decision, score_match, score_profile, score_signals


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
class ProfileMatchEvaluator(
    Evaluator[ProfileMatcherInput, ProfileMatchResult, CaseMetadata]
):
    """Score band + role/seniority flags + skill/production set F1."""

    def evaluate(
        self,
        ctx: EvaluatorContext[ProfileMatcherInput, ProfileMatchResult, CaseMetadata],
    ) -> EvaluatorOutput:
        if ctx.expected_output is None:
            raise ValueError("expected_output is required")

        expected = ctx.expected_output
        match = ctx.output
        scored = score_match(expected, match)  # type: ignore[arg-type]
        scores: dict[str, float | EvaluationReason] = {
            "macro_f1": scored.macro_f1,
            "score_in_range": _range_with_reason(
                scored.score_in_range,
                score=match.score,
                score_min=scored.score_min,
                score_max=scored.score_max,
            ),
            "role_aligned_correct": _flag_with_reason(
                scored.role_aligned_correct,
                expected=expected.role_aligned,
                got=match.role_aligned,
            ),
            "work_arrangement_aligned_correct": _flag_with_reason(
                scored.work_arrangement_aligned_correct,
                expected=expected.work_arrangement_aligned,
                got=match.work_arrangement_aligned,
            ),
            "location_aligned_correct": _flag_with_reason(
                scored.location_aligned_correct,
                expected=expected.location_aligned,
                got=match.location_aligned,
            ),
            "severe_seniority_mismatch_correct": _flag_with_reason(
                scored.severe_seniority_mismatch_correct,
                expected=expected.severe_seniority_mismatch,
                got=match.severe_seniority_mismatch,
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


@dataclass
class DecisionPolicyEvaluator(
    Evaluator[DecisionPolicyInput, WorkflowDecision, CaseMetadata]
):
    """Exact decision + score band + reasons/risks/missing_information set F1."""

    def evaluate(
        self,
        ctx: EvaluatorContext[DecisionPolicyInput, WorkflowDecision, CaseMetadata],
    ) -> EvaluatorOutput:
        if ctx.expected_output is None:
            raise ValueError("expected_output is required")

        expected = ctx.expected_output
        decision = ctx.output
        scored = score_decision(expected, decision)  # type: ignore[arg-type]
        scores: dict[str, float | EvaluationReason] = {
            "macro_f1": scored.macro_f1,
            "decision_accuracy": _flag_with_reason(
                scored.decision_correct,
                expected=expected.decision,
                got=decision.decision,
            ),
            "score_in_range": _range_with_reason(
                scored.score_in_range,
                score=decision.score,
                score_min=scored.score_min,
                score_max=scored.score_max,
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
