from typing import Any

from app.agents.contracts import (
    SignalExtractor,
    SignalExtractorInput,
    SignalExtractorOutput,
)
from app.domain.job_signals import JobSignals
from app.domain.models import JobDescription
from app.llm.client import LLMClient, LLMClientError
from app.runtime import (
    AgentRuntime,
    BoundedAgentRuntime,
    OutputValidationError,
    PydanticOutputValidator,
    RetryPolicy,
)
from app.runtime.agent_identity import agent_name_for
from app.runtime.runtime_config import RuntimeConfig


class SignalExtractionError(Exception):
    """Base error for LLM-backed signal extraction."""


class SignalExtractionLLMError(SignalExtractionError):
    """The LLM provider failed during signal extraction."""


def job_signals_schema() -> dict[str, Any]:
    schema = JobSignals.model_json_schema()
    schema["additionalProperties"] = False
    return schema


def format_job_for_prompt(job: JobDescription) -> str:
    lines = [
        f"Title: {job.title}",
        f"Company: {job.company or 'unspecified'}",
        f"Location: {job.location or 'unspecified'}",
        f"Seniority: {job.seniority or 'unspecified'}",
        f"Employment type: {job.employment_type or 'unspecified'}",
        "",
        "Description:",
        job.description,
    ]
    return "\n".join(lines)


class LLMSignalExtractor:
    """LLM-backed signal extractor with bounded runtime execution and fallback."""

    def __init__(
        self,
        *,
        client: LLMClient,
        runtime_config: RuntimeConfig | None = None,
        runtime: AgentRuntime | None = None,
        fallback: SignalExtractor | None = None,
    ) -> None:
        from app.agents.signal_extraction import DefaultSignalExtractor

        self._client = client
        agent_type = type(self)
        self._agent_name = agent_name_for(agent_type)
        self._runtime_config = runtime_config or RuntimeConfig.build()
        self._agent_config = self._runtime_config.agent_for(agent_type)
        self._runtime = runtime or BoundedAgentRuntime()
        self._fallback = fallback or DefaultSignalExtractor()
        if self._agent_config.prompt is None:
            raise SignalExtractionError("LLM signal extraction requires a resolved prompt")

    def run(self, agent_input: SignalExtractorInput) -> SignalExtractorOutput:
        result = self._runtime.execute(
            self._extract_with_llm,
            agent_input,
            self._runtime_config,
            self._agent_name,
            validator=PydanticOutputValidator(SignalExtractorOutput),
            fallback=self._fallback.run,
            retry_policy=RetryPolicy(
                retryable=(SignalExtractionLLMError, OutputValidationError),
            ),
        )

        output = result.unwrap()
        output.execution = result.without_output()
        return output

    def _extract_with_llm(
        self, agent_input: SignalExtractorInput
    ) -> SignalExtractorOutput:
        try:
            payload = self._client.complete_json(
                system=self._agent_config.prompt.content,
                user=format_job_for_prompt(agent_input.job_description),
                response_schema=job_signals_schema(),
            )
        except LLMClientError as exc:
            raise SignalExtractionLLMError(str(exc)) from exc

        return SignalExtractorOutput(
            signals=JobSignals.model_construct(**payload),
        )

