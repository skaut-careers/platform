from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.agents.contracts import (
    SignalExtractionMetadata,
    SignalExtractor,
    SignalExtractorInput,
    SignalExtractorOutput,
)
from app.domain.job_signals import JobSignals
from app.domain.models import JobDescription
from app.llm.client import LLMClient, LLMClientError
from app.runtime import AgentRuntime, BoundedAgentRuntime
from app.runtime.result import AgentExecutionResult
from app.runtime.signal_extractor_config import SignalExtractorRuntimeConfig

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


class SignalExtractionError(Exception):
    """Base error for LLM-backed signal extraction."""


class SignalExtractionLLMError(SignalExtractionError):
    """The LLM provider failed during signal extraction."""


class SignalExtractionSchemaError(SignalExtractionError):
    """The LLM output did not match the JobSignals schema."""


@lru_cache
def load_system_prompt(config_version: str) -> str:
    prompt_path = _PROMPTS_DIR / f"signal_extraction_{config_version}.txt"
    if not prompt_path.is_file():
        raise FileNotFoundError(
            f"No signal extraction prompt for config version '{config_version}'"
        )
    return prompt_path.read_text(encoding="utf-8").strip()


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


def _build_metadata(
    result: AgentExecutionResult[SignalExtractorOutput],
    *,
    used_fallback: bool,
) -> SignalExtractionMetadata:
    return SignalExtractionMetadata(
        agent_name=result.agent_name,
        config_version=result.config_version,
        status=result.status,
        attempts=result.attempts,
        duration_ms=result.duration_ms,
        used_fallback=used_fallback,
        error=result.error if used_fallback else None,
    )


class LLMSignalExtractor:
    """LLM-backed signal extractor with bounded runtime execution and fallback."""

    def __init__(
        self,
        *,
        client: LLMClient,
        config: SignalExtractorRuntimeConfig | None = None,
        runtime: AgentRuntime | None = None,
        fallback: SignalExtractor | None = None,
    ) -> None:
        from app.agents.default import DefaultSignalExtractor

        self._client = client
        self._config = config or SignalExtractorRuntimeConfig()
        self._runtime = runtime or BoundedAgentRuntime()
        self._fallback = fallback or DefaultSignalExtractor()
        self._last_execution: AgentExecutionResult[SignalExtractorOutput] | None = None

    @property
    def last_execution(self) -> AgentExecutionResult[SignalExtractorOutput] | None:
        return self._last_execution

    def run(self, agent_input: SignalExtractorInput) -> SignalExtractorOutput:
        result = self._runtime.execute(
            self._extract_with_llm,
            agent_input,
            self._config,
        )
        self._last_execution = result

        if result.succeeded:
            output = result.output
            assert output is not None
            output.metadata = _build_metadata(result, used_fallback=False)
            return output

        fallback_output = self._fallback.run(agent_input)
        fallback_output.metadata = _build_metadata(result, used_fallback=True)
        return fallback_output

    def _extract_with_llm(
        self, agent_input: SignalExtractorInput
    ) -> SignalExtractorOutput:
        try:
            payload = self._client.complete_json(
                system=load_system_prompt(self._config.config_version),
                user=format_job_for_prompt(agent_input.job_description),
                response_schema=job_signals_schema(),
            )
        except LLMClientError as exc:
            # BoundedAgentRuntime catches this, records it, and run() falls back.
            raise SignalExtractionLLMError(str(exc)) from exc

        try:
            signals = JobSignals.model_validate(payload)
        except ValidationError as exc:
            # BoundedAgentRuntime catches this, records it, and run() falls back.
            raise SignalExtractionSchemaError(str(exc)) from exc

        return SignalExtractorOutput(signals=signals)
