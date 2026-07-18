from pydantic import BaseModel, Field

from app.domain.job_signals import SIGNAL_FIELDS, JobSignals
from app.domain.signal_text import casefold_for_match
from app.evaluation.dataset import EvalCase


def _signal_set(signals: list[str]) -> set[str]:
    return {casefold_for_match(signal) for signal in signals if signal.strip()}


class FieldMetrics(BaseModel):
    field: str
    precision: float = Field(ge=0.0, le=1.0)
    recall: float = Field(ge=0.0, le=1.0)
    f1: float = Field(ge=0.0, le=1.0)
    exact_match: bool
    expected: list[str] = Field(default_factory=list)
    predicted: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    extra: list[str] = Field(default_factory=list)


class CaseResult(BaseModel):
    case_id: str
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    field_metrics: list[FieldMetrics] = Field(default_factory=list)
    macro_f1: float = Field(ge=0.0, le=1.0)
    exact_match: bool
    used_fallback: bool = False


class AggregateMetrics(BaseModel):
    case_count: int
    exact_match_rate: float = Field(ge=0.0, le=1.0)
    macro_f1: float = Field(ge=0.0, le=1.0)
    field_macro_f1: dict[str, float] = Field(default_factory=dict)
    fallback_count: int = 0


def _field_metrics(
    field: str, expected: list[str], predicted: list[str]
) -> FieldMetrics:
    expected_set = _signal_set(expected)
    predicted_set = _signal_set(predicted)
    overlap = expected_set & predicted_set

    if not expected_set and not predicted_set:
        precision = recall = f1 = 1.0
    elif not predicted_set:
        precision = recall = f1 = 0.0
    elif not expected_set:
        precision = 0.0
        recall = 1.0
        f1 = 0.0
    else:
        precision = len(overlap) / len(predicted_set)
        recall = len(overlap) / len(expected_set)
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall)
            else 0.0
        )

    return FieldMetrics(
        field=field,
        precision=precision,
        recall=recall,
        f1=f1,
        exact_match=expected_set == predicted_set,
        expected=sorted(expected_set),
        predicted=sorted(predicted_set),
        missing=sorted(expected_set - predicted_set),
        extra=sorted(predicted_set - expected_set),
    )


def score_case(
    case: EvalCase,
    predicted: JobSignals,
    *,
    used_fallback: bool = False,
) -> CaseResult:
    field_metrics = [
        _field_metrics(
            field,
            getattr(case.expected_signals, field),
            getattr(predicted, field),
        )
        for field in SIGNAL_FIELDS
    ]
    macro_f1 = sum(metric.f1 for metric in field_metrics) / len(field_metrics)

    return CaseResult(
        case_id=case.id,
        description=case.description,
        tags=case.tags,
        field_metrics=field_metrics,
        macro_f1=macro_f1,
        exact_match=all(metric.exact_match for metric in field_metrics),
        used_fallback=used_fallback,
    )


def aggregate_metrics(case_results: list[CaseResult]) -> AggregateMetrics:
    if not case_results:
        return AggregateMetrics(case_count=0, exact_match_rate=0.0, macro_f1=0.0)

    case_count = len(case_results)
    field_scores: dict[str, list[float]] = {field: [] for field in SIGNAL_FIELDS}
    for result in case_results:
        for metric in result.field_metrics:
            field_scores[metric.field].append(metric.f1)

    field_macro_f1 = {
        field: sum(scores) / case_count
        for field, scores in field_scores.items()
    }

    return AggregateMetrics(
        case_count=case_count,
        exact_match_rate=sum(result.exact_match for result in case_results)
        / case_count,
        macro_f1=sum(result.macro_f1 for result in case_results) / case_count,
        field_macro_f1=field_macro_f1,
        fallback_count=sum(result.used_fallback for result in case_results),
    )
