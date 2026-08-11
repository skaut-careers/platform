from typing import Generic, Protocol, TypeVar

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.exceptions import (
    AgentRunError,
    ModelAPIError,
    ModelHTTPError,
    UnexpectedModelBehavior,
    UserError,
)
from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIChatModelSettings

from app.agents.contracts import AgentOutput
from app.runtime.config_loader import local_env
from app.runtime import AgentRuntime, BoundedAgentRuntime, RetryPolicy
from app.runtime.agent_identity import agent_name_for
from app.runtime.runtime_config import RuntimeConfig

# Provider failures worth retrying / falling back on (vs. programmer errors).
PROVIDER_ERRORS: tuple[type[Exception], ...] = (
    ModelHTTPError,
    ModelAPIError,
    UnexpectedModelBehavior,
    AgentRunError,
    UserError,
)

# Reasoning tokens inflate "output" usage and latency on GPT-5.x; keep effort off
# for this extraction/match/policy path.
_DEFAULT_MODEL_SETTINGS: OpenAIChatModelSettings = {
    "openai_reasoning_effort": "none",
}


def build_openai_model(
    model_name: str,
    *,
    api_key: str | None = None,
    error_cls: type[Exception] = RuntimeError,
) -> Model:
    from pydantic_ai.models.openai import OpenAIChatModel
    from pydantic_ai.providers.openai import OpenAIProvider

    resolved_key = api_key if api_key is not None else local_env().get("OPENAI_API_KEY")
    if not resolved_key:
        raise error_cls("OPENAI_API_KEY is not configured")
    return OpenAIChatModel(model_name, provider=OpenAIProvider(api_key=resolved_key))


InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)
ContractT = TypeVar("ContractT", bound=AgentOutput)


class _Fallback(Protocol[InputT, ContractT]):
    def run(self, agent_input: InputT) -> ContractT: ...


class BoundedLLMAgent(Generic[InputT, OutputT, ContractT]):
    output_type: type[OutputT]
    error_cls: type[Exception] = Exception
    llm_error_cls: type[Exception] = Exception

    def __init__(
        self,
        *,
        model: Model | str | None = None,
        agent: Agent[None, OutputT] | None = None,
        runtime_config: RuntimeConfig | None = None,
        runtime: AgentRuntime | None = None,
        fallback: _Fallback[InputT, ContractT] | None = None,
    ) -> None:
        agent_type = type(self)
        self._agent_name = agent_name_for(agent_type)
        self._runtime_config = runtime_config or RuntimeConfig.build()
        self._agent_config = self._runtime_config.agent_for(agent_type)
        self._runtime = runtime or BoundedAgentRuntime()
        self._fallback = fallback or self._default_fallback()
        prompt = self._agent_config.prompt
        if prompt is None:
            raise self.error_cls(
                f"LLM mode for '{self._agent_name}' requires a resolved prompt"
            )
        self._prompt = prompt
        self._model = model
        self._agent = agent

    def run(self, agent_input: InputT) -> ContractT:
        result = self._runtime.execute(
            self._run_agent,
            agent_input,
            self._runtime_config,
            self._agent_name,
            fallback=self._fallback.run,
            retry_policy=RetryPolicy(retryable=(self.llm_error_cls,)),
        )
        output = result.unwrap()
        output.execution = result.without_output()
        return output

    def _get_agent(self) -> Agent[None, OutputT]:
        if self._agent is None:
            model = self._model
            if model is None:
                model = build_openai_model(
                    self._agent_config.model, error_cls=self.llm_error_cls
                )
            self._agent = Agent(
                model,
                output_type=self.output_type,
                system_prompt=self._prompt.content,
                model_settings=_DEFAULT_MODEL_SETTINGS,
            )
        return self._agent

    def _run_agent(self, agent_input: InputT) -> ContractT:
        try:
            result = self._get_agent().run_sync(self._format_input(agent_input))
        except PROVIDER_ERRORS as exc:
            raise self.llm_error_cls(str(exc)) from exc
        return self._build_output(result.output)

    def _default_fallback(self) -> _Fallback[InputT, ContractT]:
        raise NotImplementedError

    def _format_input(self, agent_input: InputT) -> str:
        raise NotImplementedError

    def _build_output(self, output: OutputT) -> ContractT:
        raise NotImplementedError
