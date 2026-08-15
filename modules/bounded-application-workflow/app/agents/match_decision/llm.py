from app.agents.contracts import (
    MatchDecider,
    MatchDeciderInput,
    MatchDeciderOutput,
)
from app.agents.llm_support import BoundedLLMAgent
from app.domain.models import MatchDecision


class MatchDecisionError(Exception):
    """Base error for LLM-backed profile matching and decision."""


class MatchDecisionLLMError(MatchDecisionError):
    """The Pydantic AI agent failed while matching and deciding."""


def _bullet(label: str, values: list[str]) -> str:
    return f"- {label}: {', '.join(values) if values else 'none'}"


def format_match_decision_input(agent_input: MatchDeciderInput) -> str:
    profile = agent_input.user_profile
    job_signals = agent_input.job_signals
    lines = [
        "Candidate profile:",
        _bullet("Skills", profile.skills),
        f"- Seniority: {profile.seniority or 'unspecified'}",
        f"- Location: {profile.location or 'unspecified'}",
        _bullet("Production experience", profile.relevant_experience),
        _bullet("Work preferences", profile.work_preferences),
        "",
        "Extracted job signals:",
        _bullet("required_skills", job_signals.required_skills),
        _bullet("preferred_skills", job_signals.preferred_skills),
        _bullet("seniority_signals", job_signals.seniority_signals),
        _bullet("experience_requirements", job_signals.experience_requirements),
        _bullet("work_arrangements", job_signals.work_arrangements),
        _bullet("location_signals", job_signals.location_signals),
        _bullet("risk_indicators", job_signals.risk_indicators),
        _bullet("missing_signals", job_signals.missing_signals),
    ]
    return "\n".join(lines)


class LLMMatchDecider(
    BoundedLLMAgent[
        MatchDeciderInput,
        MatchDecision,
        MatchDeciderOutput,
    ]
):
    """Produce the match and terminal decision in one model call."""

    output_type = MatchDecision
    error_cls = MatchDecisionError
    llm_error_cls = MatchDecisionLLMError

    def _default_fallback(self) -> MatchDecider:
        from app.agents.match_decision import DefaultMatchDecider

        return DefaultMatchDecider()

    def _format_input(self, agent_input: MatchDeciderInput) -> str:
        return format_match_decision_input(agent_input)

    def _build_output(
        self, output: MatchDecision
    ) -> MatchDeciderOutput:
        return MatchDeciderOutput(result=output)
