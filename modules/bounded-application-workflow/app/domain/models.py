from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from app.domain.job_signals import JobSignals


class DecisionType(str, Enum):
    PREPARE = "prepare"
    QUEUE = "queue"
    SKIP = "skip"
    ESCALATE = "escalate"


class UserProfile(BaseModel):
    name: str
    target_roles: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    experience_summary: Optional[str] = None
    location: Optional[str] = None
    seniority: Optional[str] = None
    work_preferences: List[str] = Field(default_factory=list)


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
    role_aligned: bool = False
    reasons: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)


class WorkflowInput(BaseModel):
    user_profile: UserProfile
    job_description: JobDescription


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