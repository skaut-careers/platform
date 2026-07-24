from __future__ import annotations

from pydantic import BaseModel, Field

from app.domain.job_signals import SIGNAL_FIELDS, JobSignals
from app.domain.signal_text import casefold_for_match


def _signal_set(signals: list[str]) -> set[str]:
    return {casefold_for_match(signal) for signal in signals if signal.strip()}


class FieldScore(BaseModel):
    field: str
    precision: float = Field(ge=0.0, le=1.0)
    recall: float = Field(ge=0.0, le=1.0)
    f1: float = Field(ge=0.0, le=1.0)
    exact_match: bool
    missing: list[str] = Field(default_factory=list)
    extra: list[str] = Field(default_factory=list)


class SignalScore(BaseModel):
    fields: list[FieldScore] = Field(default_factory=list)
    macro_f1: float = Field(ge=0.0, le=1.0)
    exact_match: bool


def score_field(field: str, expected: list[str], predicted: list[str]) -> FieldScore:
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

    return FieldScore(
        field=field,
        precision=precision,
        recall=recall,
        f1=f1,
        exact_match=expected_set == predicted_set,
        missing=sorted(expected_set - predicted_set),
        extra=sorted(predicted_set - expected_set),
    )


def score_signals(expected: JobSignals, predicted: JobSignals) -> SignalScore:
    fields = [
        score_field(field, getattr(expected, field), getattr(predicted, field))
        for field in SIGNAL_FIELDS
    ]
    return SignalScore(
        fields=fields,
        macro_f1=sum(f.f1 for f in fields) / len(fields),
        exact_match=all(f.exact_match for f in fields),
    )
