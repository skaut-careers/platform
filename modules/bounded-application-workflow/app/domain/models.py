from __future__ import annotations

from enum import Enum
from typing import Any, List, Mapping, Optional

from pydantic import BaseModel, Field, ValidationError, field_validator

from app.domain.job_signals import JobSignals


class DecisionType(str, Enum):
    PREPARE = "prepare"
    QUEUE = "queue"
    SKIP = "skip"
    ESCALATE = "escalate"


class UserProfile(BaseModel):
    target_roles: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    experience_summary: str = ""
    location: str = ""
    seniority: str = ""
    production_experience: List[str] = Field(default_factory=list)
    work_preferences: List[str] = Field(default_factory=list)

    @field_validator(
        "target_roles",
        "skills",
        "production_experience",
        "work_preferences",
        mode="before",
    )
    @classmethod
    def _reject_none_list_fields(cls, value: object) -> object:
        if value is None:
            raise ValueError("must be a list, not null")
        return value

    @field_validator("experience_summary", "location", "seniority", mode="before")
    @classmethod
    def _reject_none_string_fields(cls, value: object) -> object:
        if value is None:
            raise ValueError("must be a string, not null")
        return value


class JobDescription(BaseModel):
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    description: str
    seniority: Optional[str] = None
    employment_type: Optional[str] = None


class ProfileMatchResult(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    required_skills_matched: List[str] = Field(default_factory=list)
    required_skills_missing: List[str] = Field(default_factory=list)
    preferred_skills_matched: List[str] = Field(default_factory=list)
    production_expectations_matched: List[str] = Field(default_factory=list)
    production_expectations_missing: List[str] = Field(default_factory=list)
    role_aligned: bool = False
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


class WorkflowDecision(BaseModel):
    decision: DecisionType
    score: float = Field(ge=0.0, le=1.0)
    reasons: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)


class WorkflowOutput(BaseModel):
    input_summary: str
    decision: WorkflowDecision
    job_signals: JobSignals
    recommended_next_steps: List[str] = Field(default_factory=list)