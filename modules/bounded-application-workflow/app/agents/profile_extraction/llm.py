from app.agents.contracts import (
    ProfileExtractor,
    ProfileExtractorInput,
    ProfileExtractorOutput,
)
from app.agents.llm_support import BoundedLLMAgent
from app.domain.models import UserProfile


class ProfileExtractionError(Exception):
    """Base error for LLM-backed profile extraction."""


class ProfileExtractionLLMError(ProfileExtractionError):
    """The Pydantic AI agent failed while extracting a profile."""


class LLMProfileExtractor(
    BoundedLLMAgent[ProfileExtractorInput, UserProfile, ProfileExtractorOutput]
):

    output_type = UserProfile
    error_cls = ProfileExtractionError
    llm_error_cls = ProfileExtractionLLMError

    def _default_fallback(self) -> ProfileExtractor:
        from app.agents.profile_extraction import DefaultProfileExtractor

        return DefaultProfileExtractor()

    def _format_input(self, agent_input: ProfileExtractorInput) -> str:
        return agent_input.profile_text

    def _build_output(self, output: UserProfile) -> ProfileExtractorOutput:
        return ProfileExtractorOutput(profile=output)
