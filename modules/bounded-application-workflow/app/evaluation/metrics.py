from __future__ import annotations

from pydantic import BaseModel, Field

from app.domain.job_signals import SIGNAL_FIELDS, JobSignals
from app.domain.models import ProfileMatchResult, UserProfile
from app.domain.signal_text import casefold_for_match
from app.evaluation.dataset import MatchExpectation

# Mirrors UserProfile: list fields scored as sets; string fields as single-value sets.
PROFILE_LIST_FIELDS = (
    "target_roles",
    "skills",
    "production_experience",
    "work_preferences",
)
PROFILE_TEXT_FIELDS = ("experience_summary", "location", "seniority")
PROFILE_SCORED_FIELDS = PROFILE_LIST_FIELDS + PROFILE_TEXT_FIELDS

MATCH_LIST_FIELDS = (
    "required_skills_matched",
    "required_skills_missing",
    "preferred_skills_matched",
    "production_expectations_matched",
    "production_expectations_missing",
)


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


class ProfileScore(BaseModel):
    fields: list[FieldScore] = Field(default_factory=list)
    macro_f1: float = Field(ge=0.0, le=1.0)
    exact_match: bool


class MatchScore(BaseModel):
    fields: list[FieldScore] = Field(default_factory=list)
    macro_f1: float = Field(ge=0.0, le=1.0)
    score_in_range: bool
    score_min: float = Field(ge=0.0, le=1.0)
    score_max: float = Field(ge=0.0, le=1.0)
    role_aligned_correct: bool
    work_arrangement_aligned_correct: bool
    location_aligned_correct: bool
    severe_seniority_mismatch_correct: bool


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


def _profile_field_values(profile: UserProfile, field: str) -> list[str]:
    value = getattr(profile, field)
    if isinstance(value, list):
        return value
    return [value] if value.strip() else []


def score_profile(expected: UserProfile, predicted: UserProfile) -> ProfileScore:
    fields = [
        score_field(
            field,
            _profile_field_values(expected, field),
            _profile_field_values(predicted, field),
        )
        for field in PROFILE_SCORED_FIELDS
    ]
    return ProfileScore(
        fields=fields,
        macro_f1=sum(f.f1 for f in fields) / len(fields),
        exact_match=all(f.exact_match for f in fields),
    )


def score_match(expected: MatchExpectation, predicted: ProfileMatchResult) -> MatchScore:
    fields = [
        score_field(field, getattr(expected, field), getattr(predicted, field))
        for field in MATCH_LIST_FIELDS
    ]
    score_in_range = expected.score_min <= predicted.score <= expected.score_max
    role_ok = predicted.role_aligned == expected.role_aligned
    work_ok = predicted.work_arrangement_aligned == expected.work_arrangement_aligned
    location_ok = predicted.location_aligned == expected.location_aligned
    seniority_ok = (
        predicted.severe_seniority_mismatch == expected.severe_seniority_mismatch
    )
    return MatchScore(
        fields=fields,
        macro_f1=sum(f.f1 for f in fields) / len(fields),
        score_in_range=score_in_range,
        score_min=expected.score_min,
        score_max=expected.score_max,
        role_aligned_correct=role_ok,
        work_arrangement_aligned_correct=work_ok,
        location_aligned_correct=location_ok,
        severe_seniority_mismatch_correct=seniority_ok,
    )
