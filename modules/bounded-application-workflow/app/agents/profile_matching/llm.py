from app.agents.contracts import (
    ProfileMatcher,
    ProfileMatcherInput,
    ProfileMatcherOutput,
)
from app.agents.llm_support import BoundedLLMAgent
from app.domain.models import ProfileMatchResult


class ProfileMatchError(Exception):
    """Base error for LLM-backed profile matching."""


class ProfileMatchLLMError(ProfileMatchError):
    """The Pydantic AI agent failed while matching a profile."""


def _bullet(label: str, values: list[str]) -> str:
    return f"- {label}: {', '.join(values) if values else 'none'}"


def format_match_input(agent_input: ProfileMatcherInput) -> str:
    profile = agent_input.user_profile
    job_signals = agent_input.job_signals
    lines = [
        "Candidate profile:",
        _bullet("Skills", profile.skills),
        f"- Seniority: {profile.seniority or 'unspecified'}",
        f"- Location: {profile.location or 'unspecified'}",
        _bullet("Production experience", profile.production_experience),
        _bullet("Work preferences", profile.work_preferences),
        "",
        "Extracted job signals:",
        _bullet("required_skills", job_signals.required_skills),
        _bullet("preferred_skills", job_signals.preferred_skills),
        _bullet("seniority_signals", job_signals.seniority_signals),
        _bullet("production_expectations", job_signals.production_expectations),
        _bullet("work_arrangements", job_signals.work_arrangements),
        _bullet("location_signals", job_signals.location_signals),
        _bullet("risk_indicators", job_signals.risk_indicators),
        _bullet("missing_signals", job_signals.missing_signals),
    ]
    return "\n".join(lines)


class LLMProfileMatcher(
    BoundedLLMAgent[ProfileMatcherInput, ProfileMatchResult, ProfileMatcherOutput]
):

    output_type = ProfileMatchResult
    error_cls = ProfileMatchError
    llm_error_cls = ProfileMatchLLMError

    def _default_fallback(self) -> ProfileMatcher:
        from app.agents.profile_matching import DefaultProfileMatcher

        return DefaultProfileMatcher()

    def _format_input(self, agent_input: ProfileMatcherInput) -> str:
        return format_match_input(agent_input)

    def _build_output(self, output: ProfileMatchResult) -> ProfileMatcherOutput:
        return ProfileMatcherOutput(match=output)
