from app.agents.contracts import ProfileMatcherInput, ProfileMatcherOutput
from app.agents.profile_matching.llm import LLMProfileMatcher
from app.agents.profile_matching.deterministic import match_profile_to_job

__all__ = ["DefaultProfileMatcher", "LLMProfileMatcher"]


class DefaultProfileMatcher:
    def run(self, agent_input: ProfileMatcherInput) -> ProfileMatcherOutput:
        match = match_profile_to_job(
            agent_input.user_profile,
            agent_input.job_signals,
        )
        return ProfileMatcherOutput(match=match)
