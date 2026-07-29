from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class SignalCategory(str, Enum):
    REQUIRED_SKILLS = "required_skills"
    PREFERRED_SKILLS = "preferred_skills"
    SENIORITY = "seniority_signals"
    PRODUCTION_EXPECTATIONS = "production_expectations"
    WORK_ARRANGEMENTS = "work_arrangements"
    LOCATION_SIGNALS = "location_signals"
    RISK_INDICATORS = "risk_indicators"
    MISSING_SIGNALS = "missing_signals"


class JobSignals(BaseModel):
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    seniority_signals: List[str] = Field(default_factory=list)
    production_expectations: List[str] = Field(default_factory=list)
    work_arrangements: List[str] = Field(default_factory=list)
    location_signals: List[str] = Field(default_factory=list)
    risk_indicators: List[str] = Field(default_factory=list)
    missing_signals: List[str] = Field(default_factory=list)


SIGNAL_FIELDS = tuple(JobSignals.model_fields.keys())
