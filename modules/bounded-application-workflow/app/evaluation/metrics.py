from __future__ import annotations

from pydantic import BaseModel, Field

from app.domain.models import SIGNAL_FIELDS, JobSignals
from app.domain.models import MatchDecision, UserProfile
from app.domain.text_processing import normalize_for_match
from app.evaluation.dataset import MatchDecisionExpectation

# Mirrors UserProfile: list fields scored as sets; string fields as single-value sets.
PROFILE_LIST_FIELDS = (
    "skills",
    "relevant_experience",
    "work_preferences",
)
PROFILE_TEXT_FIELDS = ("location", "seniority")
PROFILE_SCORED_FIELDS = PROFILE_LIST_FIELDS + PROFILE_TEXT_FIELDS

# List fields on MatchDecision scored as sets against goldens.
# reasons/risks are free-form LLM text and are not F1-scored.
MATCH_DECISION_LIST_FIELDS = (
    "required_skills_matched",
    "required_skills_missing",
    "preferred_skills_matched",
    "experience_requirements_matched",
    "experience_requirements_missing",
    "missing_information",
)


def _normalized_set(values: list[str]) -> set[str]:
    return {normalize_for_match(value) for value in values if value.strip()}


class FieldScore(BaseModel):
    field: str
    precision: float = Field(ge=0.0, le=1.0)
    recall: float = Field(ge=0.0, le=1.0)
    f1: float = Field(ge=0.0, le=1.0)
    exact_match: bool
    missing: list[str] = Field(default_factory=list)
    extra: list[str] = Field(default_factory=list)


class JobSignalsScore(BaseModel):
    fields: list[FieldScore] = Field(default_factory=list)
    macro_f1: float = Field(ge=0.0, le=1.0)
    exact_match: bool


class ProfileScore(BaseModel):
    fields: list[FieldScore] = Field(default_factory=list)
    macro_f1: float = Field(ge=0.0, le=1.0)
    exact_match: bool


class MatchDecisionScore(BaseModel):
    fields: list[FieldScore] = Field(default_factory=list)
    macro_f1: float = Field(ge=0.0, le=1.0)
    decision_correct: bool
    score_in_range: bool
    score_min: float = Field(ge=0.0, le=1.0)
    score_max: float = Field(ge=0.0, le=1.0)
    work_arrangement_aligned_correct: bool
    location_aligned_correct: bool
    severe_seniority_mismatch_correct: bool


def score_field(field: str, expected: list[str], predicted: list[str]) -> FieldScore:
    expected_set = _normalized_set(expected)
    predicted_set = _normalized_set(predicted)
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


def score_job_signals(expected: JobSignals, predicted: JobSignals) -> JobSignalsScore:
    fields = [
        score_field(field, getattr(expected, field), getattr(predicted, field))
        for field in SIGNAL_FIELDS
    ]
    return JobSignalsScore(
        fields=fields,
        macro_f1=sum(f.f1 for f in fields) / len(fields),
        exact_match=all(f.exact_match for f in fields),
    )


def _profile_field_as_list(profile: UserProfile, field: str) -> list[str]:
    value = getattr(profile, field)
    if isinstance(value, list):
        return value
    return [value] if value.strip() else []


def score_profile(expected: UserProfile, predicted: UserProfile) -> ProfileScore:
    fields = [
        score_field(
            field,
            _profile_field_as_list(expected, field),
            _profile_field_as_list(predicted, field),
        )
        for field in PROFILE_SCORED_FIELDS
    ]
    return ProfileScore(
        fields=fields,
        macro_f1=sum(f.f1 for f in fields) / len(fields),
        exact_match=all(f.exact_match for f in fields),
    )


def score_match_decision(expected: MatchDecisionExpectation, predicted: MatchDecision) -> MatchDecisionScore:
    fields = [
        score_field(field, getattr(expected, field), getattr(predicted, field))
        for field in MATCH_DECISION_LIST_FIELDS
    ]
    score_in_range = expected.score_min <= predicted.score <= expected.score_max
    work_ok = (
        predicted.work_arrangement_aligned == expected.work_arrangement_aligned
    )
    location_ok = predicted.location_aligned == expected.location_aligned
    seniority_ok = (
        predicted.severe_seniority_mismatch
        == expected.severe_seniority_mismatch
    )
    return MatchDecisionScore(
        fields=fields,
        macro_f1=sum(f.f1 for f in fields) / len(fields),
        decision_correct=predicted.decision == expected.decision,
        score_in_range=score_in_range,
        score_min=expected.score_min,
        score_max=expected.score_max,
        work_arrangement_aligned_correct=work_ok,
        location_aligned_correct=location_ok,
        severe_seniority_mismatch_correct=seniority_ok,
    )
