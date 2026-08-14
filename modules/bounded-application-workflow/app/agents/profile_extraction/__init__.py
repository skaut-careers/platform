from app.agents.contracts import ProfileExtractorInput, ProfileExtractorOutput
from app.agents.profile_extraction.deterministic import extract_user_profile
from app.agents.profile_extraction.llm import LLMProfileExtractor

__all__ = ["DefaultProfileExtractor", "LLMProfileExtractor"]


class DefaultProfileExtractor:
    def run(self, agent_input: ProfileExtractorInput) -> ProfileExtractorOutput:
        profile = extract_user_profile(agent_input.profile_text)
        return ProfileExtractorOutput(profile=profile)
