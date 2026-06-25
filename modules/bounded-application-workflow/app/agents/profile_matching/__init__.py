from app.agents.contracts import ProfileMatcherInput, ProfileMatcherOutput
from app.agents.profile_matching.matching import match_profile_to_job

__all__ = ["DefaultProfileMatcher"]


class DefaultProfileMatcher:
    def run(self, agent_input: ProfileMatcherInput) -> ProfileMatcherOutput:
        match = match_profile_to_job(
            agent_input.user_profile,
            agent_input.job_description,
            agent_input.signals,
        )
        return ProfileMatcherOutput(match=match)
