from typing import Any

from app.agents.contracts import (
    JobSignalExtractor,
    JobSignalExtractorInput,
    JobSignalExtractorOutput,
)
from app.agents.llm_support import BoundedLLMAgent
from app.domain.models import SIGNAL_FIELDS, JobSignals


class JobSignalExtractionError(Exception):
    """Base error for LLM-backed signal extraction."""


class JobSignalExtractionLLMError(JobSignalExtractionError):
    """The Pydantic AI agent failed while extracting signals."""


def job_signals_schema() -> dict[str, Any]:
    schema = JobSignals.model_json_schema()
    schema["additionalProperties"] = False
    # OpenAI strict structured output requires every property in `required`.
    schema["required"] = list(SIGNAL_FIELDS)
    return schema


class LLMJobSignalExtractor(
    BoundedLLMAgent[JobSignalExtractorInput, JobSignals, JobSignalExtractorOutput]
):
    """Pydantic AI signal extractor with bounded runtime execution and fallback."""

    output_type = JobSignals
    error_cls = JobSignalExtractionError
    llm_error_cls = JobSignalExtractionLLMError

    def _default_fallback(self) -> JobSignalExtractor:
        from app.agents.job_signal_extraction import DefaultJobSignalExtractor

        return DefaultJobSignalExtractor()

    def _format_input(self, agent_input: JobSignalExtractorInput) -> str:
        return agent_input.job_description_text

    def _build_output(self, output: JobSignals) -> JobSignalExtractorOutput:
        return JobSignalExtractorOutput(job_signals=output)
