from typing import Any

from pydantic_ai import Agent
from pydantic_ai.exceptions import (
    AgentRunError,
    ModelAPIError,
    ModelHTTPError,
    UnexpectedModelBehavior,
    UserError,
)
from pydantic_ai.models import Model

from app.agents.contracts import (
    SignalExtractor,
    SignalExtractorInput,
    SignalExtractorOutput,
)
from app.domain.job_signals import SIGNAL_FIELDS, JobSignals
from app.domain.models import JobDescription
from app.local_env import get_local_env
from app.runtime import (
    AgentRuntime,
    BoundedAgentRuntime,
    RetryPolicy,
)
from app.runtime.agent_identity import agent_name_for
from app.runtime.runtime_config import RuntimeConfig

_PROVIDER_ERRORS = (
    ModelHTTPError,
    ModelAPIError,
    UnexpectedModelBehavior,
    AgentRunError,
    UserError,
)


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


def build_openai_model(model_name: str, *, api_key: str | None = None) -> Model:
    """Construct the default OpenAI model used when no model is injected."""
    from pydantic_ai.models.openai import OpenAIChatModel
    from pydantic_ai.providers.openai import OpenAIProvider

    resolved_key = api_key if api_key is not None else get_local_env("OPENAI_API_KEY")
    if not resolved_key:
        raise SignalExtractionLLMError("OPENAI_API_KEY is not configured")
    return OpenAIChatModel(model_name, provider=OpenAIProvider(api_key=resolved_key))


class LLMSignalExtractor:
    """Pydantic AI signal extractor with bounded runtime execution and fallback."""

    def __init__(
        self,
        *,
        model: Model | str | None = None,
        agent: Agent[None, JobSignals] | None = None,
        runtime_config: RuntimeConfig | None = None,
        runtime: AgentRuntime | None = None,
        fallback: SignalExtractor | None = None,
    ) -> None:
        from app.agents.signal_extraction import DefaultSignalExtractor

        agent_type = type(self)
        self._agent_name = agent_name_for(agent_type)
        self._runtime_config = runtime_config or RuntimeConfig.build()
        self._agent_config = self._runtime_config.agent_for(agent_type)
        self._runtime = runtime or BoundedAgentRuntime()
        self._fallback = fallback or DefaultSignalExtractor()
        if self._agent_config.prompt is None:
            raise SignalExtractionError("LLM signal extraction requires a resolved prompt")

        self._model = model
        self._agent = agent

    def run(self, agent_input: SignalExtractorInput) -> SignalExtractorOutput:
        result = self._runtime.execute(
            self._extract_with_agent,
            agent_input,
            self._runtime_config,
            self._agent_name,
            fallback=self._fallback.run,
            retry_policy=RetryPolicy(retryable=(SignalExtractionLLMError,)),
        )

        output = result.unwrap()
        output.execution = result.without_output()
        return output

    def _build_agent(self) -> Agent[None, JobSignals]:
        model = self._model
        if model is None:
            model = build_openai_model(self._agent_config.model)
        return Agent(
            model,
            output_type=JobSignals,
            system_prompt=self._agent_config.prompt.content,
        )

    def _get_agent(self) -> Agent[None, JobSignals]:
        if self._agent is None:
            self._agent = self._build_agent()
        return self._agent

    def _extract_with_agent(
        self, agent_input: SignalExtractorInput
    ) -> SignalExtractorOutput:
        try:
            result = self._get_agent().run_sync(
                format_job_for_prompt(agent_input.job_description)
            )
        except _PROVIDER_ERRORS as exc:
            raise SignalExtractionLLMError(str(exc)) from exc

        return SignalExtractorOutput(signals=result.output)
