from typing import Any

from app.agents.contracts import (
    SignalExtractor,
    SignalExtractorInput,
    SignalExtractorOutput,
)
from app.agents.llm_support import BoundedLLMAgent
from app.domain.job_signals import SIGNAL_FIELDS, JobSignals


class SignalExtractionError(Exception):
    """Base error for LLM-backed signal extraction."""


class SignalExtractionLLMError(SignalExtractionError):
    """The Pydantic AI agent failed while extracting signals."""


def job_signals_schema() -> dict[str, Any]:
    schema = JobSignals.model_json_schema()
    schema["additionalProperties"] = False
    # OpenAI strict structured output requires every property in `required`.
    schema["required"] = list(SIGNAL_FIELDS)
    return schema


class LLMSignalExtractor(
    BoundedLLMAgent[SignalExtractorInput, JobSignals, SignalExtractorOutput]
):
    """Pydantic AI signal extractor with bounded runtime execution and fallback."""

    output_type = JobSignals
    error_cls = SignalExtractionError
    llm_error_cls = SignalExtractionLLMError

    def _default_fallback(self) -> SignalExtractor:
        from app.agents.signal_extraction import DefaultSignalExtractor

        return DefaultSignalExtractor()

    def _format_input(self, agent_input: SignalExtractorInput) -> str:
        return agent_input.job_description_text

    def _build_output(self, output: JobSignals) -> SignalExtractorOutput:
        return SignalExtractorOutput(job_signals=output)
