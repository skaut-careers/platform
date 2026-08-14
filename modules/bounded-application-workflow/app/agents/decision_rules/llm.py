from app.agents.contracts import (
    DecisionPolicy,
    DecisionPolicyInput,
    DecisionPolicyOutput,
)
from app.agents.llm_support import BoundedLLMAgent
from app.domain.models import WorkflowDecision


class DecisionPolicyError(Exception):
    """Base error for LLM-backed decision policy."""


class DecisionPolicyLLMError(DecisionPolicyError):
    """The Pydantic AI agent failed while applying decision policy."""


def _bullet(label: str, values: list[str]) -> str:
    return f"- {label}: {', '.join(values) if values else 'none'}"


def format_policy_input(agent_input: DecisionPolicyInput) -> str:
    match = agent_input.match
    job_signals = agent_input.job_signals
    lines = [
        "Profile match result:",
        f"- score: {match.score:.2f}",
        f"- work_arrangement_aligned: {match.work_arrangement_aligned}",
        f"- location_aligned: {match.location_aligned}",
        f"- severe_seniority_mismatch: {match.severe_seniority_mismatch}",
        _bullet("required_skills_matched", match.required_skills_matched),
        _bullet("required_skills_missing", match.required_skills_missing),
        _bullet("preferred_skills_matched", match.preferred_skills_matched),
        _bullet(
            "experience_requirements_matched",
            match.experience_requirements_matched,
        ),
        _bullet(
            "experience_requirements_missing",
            match.experience_requirements_missing,
        ),
        _bullet("match reasons", match.reasons),
        _bullet("match risks", match.risks),
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


class LLMDecisionPolicy(
    BoundedLLMAgent[DecisionPolicyInput, WorkflowDecision, DecisionPolicyOutput]
):
    """Pydantic AI decision policy with bounded runtime execution and fallback."""

    output_type = WorkflowDecision
    error_cls = DecisionPolicyError
    llm_error_cls = DecisionPolicyLLMError

    def _default_fallback(self) -> DecisionPolicy:
        from app.agents.decision_rules import DefaultDecisionPolicy

        return DefaultDecisionPolicy()

    def _format_input(self, agent_input: DecisionPolicyInput) -> str:
        return format_policy_input(agent_input)

    def _build_output(self, output: WorkflowDecision) -> DecisionPolicyOutput:
        return DecisionPolicyOutput(decision=output)
