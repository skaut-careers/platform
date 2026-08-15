from __future__ import annotations

from enum import Enum
from typing import Any, List, Mapping

from pydantic import BaseModel, Field, ValidationError, field_validator


class DecisionType(str, Enum):
    STRONG = "strong"
    PREPARE = "prepare"
    QUEUE = "queue"
    SKIP = "skip"


class UserProfile(BaseModel):
    skills: List[str] = Field(default_factory=list)
    location: str = ""
    seniority: str = ""
    relevant_experience: List[str] = Field(default_factory=list)
    work_preferences: List[str] = Field(default_factory=list)

    @field_validator(
        "skills",
        "relevant_experience",
        "work_preferences",
        mode="before",
    )
    @classmethod
    def _reject_none_list_fields(cls, value: object) -> object:
        if value is None:
            raise ValueError("must be a list, not null")
        return value

    @field_validator("location", "seniority", mode="before")
    @classmethod
    def _reject_none_string_fields(cls, value: object) -> object:
        if value is None:
            raise ValueError("must be a string, not null")
        return value


class JobSignals(BaseModel):
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    seniority_signals: List[str] = Field(default_factory=list)
    experience_requirements: List[str] = Field(default_factory=list)
    work_arrangements: List[str] = Field(default_factory=list)
    location_signals: List[str] = Field(default_factory=list)


SIGNAL_FIELDS = tuple(JobSignals.model_fields.keys())


class MatchDecision(BaseModel):
    """Atomic match evidence and terminal workflow decision."""

    decision: DecisionType
    score: float = Field(ge=0.0, le=1.0)
    required_skills_matched: List[str] = Field(default_factory=list)
    required_skills_missing: List[str] = Field(default_factory=list)
    preferred_skills_matched: List[str] = Field(default_factory=list)
    experience_requirements_matched: List[str] = Field(default_factory=list)
    experience_requirements_missing: List[str] = Field(default_factory=list)
    work_arrangement_aligned: bool = False
    location_aligned: bool = False
    severe_seniority_mismatch: bool = False
    reasons: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)


class WorkflowInput(BaseModel):
    """Product workflow entry: pasted CV + job posting texts."""

    profile_text: str
    job_description_text: str

    @field_validator("profile_text", "job_description_text")
    @classmethod
    def _require_nonempty(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("must not be empty")
        return text

    @classmethod
    def try_from_mapping(cls, data: Mapping[str, Any]) -> WorkflowInput | None:
        try:
            return cls.model_validate(data)
        except ValidationError:
            return None


class WorkflowOutput(BaseModel):
    """Client-facing result: the fields the product UI renders."""

    decision: DecisionType
    score: float = Field(ge=0.0, le=1.0)
    reasons: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
