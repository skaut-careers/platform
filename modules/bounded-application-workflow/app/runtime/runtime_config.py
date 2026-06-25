from typing import Any, Literal, Self

from pydantic import BaseModel, Field, field_validator

from app.runtime.agent_identity import agent_name_for, discover_agents
from app.runtime.config_registry import ConfigSpec, compute_config_hash
from app.runtime.prompt_registry import PromptNotFoundError, PromptRegistry, PromptSpec

_AGENT_SETTING_FIELDS = frozenset({"mode", "model", "max_attempts", "prompt_version"})


class AgentRuntimeConfig(BaseModel):
    """Per-agent runtime settings used during execution."""

    mode: Literal["deterministic", "llm"] = "deterministic"
    model: str = Field(default="gpt-5-mini", min_length=1)
    max_attempts: int = Field(default=2, ge=1, le=5)
    prompt: PromptSpec | None = None

    @field_validator("mode", mode="before")
    @classmethod
    def _normalize_mode(cls, value: object) -> object:
        if isinstance(value, str):
            return value.casefold()
        return value


class RuntimeConfig(BaseModel):
    """Versioned runtime settings bundle loaded from the config registry."""

    config_id: str = Field(default="runtime", min_length=1)
    config_version: str = Field(default="v1", min_length=1)
    config_hash: str = Field(default="")
    agents: dict[str, AgentRuntimeConfig] = Field(default_factory=dict)

    @classmethod
    def from_spec(
        cls,
        spec: ConfigSpec,
        *,
        prompt_registry: PromptRegistry | None = None,
    ) -> Self:
        agents = _agents_from_settings(spec.settings, prompt_registry)
        if not agents:
            raise ValueError("Runtime config must define at least one agent")

        return cls(
            config_id=spec.config_id,
            config_version=spec.version,
            config_hash=spec.content_hash,
            agents=agents,
        )

    @classmethod
    def build(
        cls,
        *,
        agent_name: str | None = None,
        config_version: str = "v1",
        mode: Literal["deterministic", "llm"] = "llm",
        model: str = "gpt-5-mini",
        max_attempts: int = 2,
        prompt_version: str = "v1",
        prompt_registry: PromptRegistry | None = None,
    ) -> Self:
        agent_settings = {
            "mode": mode,
            "model": model,
            "max_attempts": max_attempts,
            "prompt_version": prompt_version,
        }
        settings: dict[str, Any]
        if agent_name is None:
            settings = agent_settings
        else:
            settings = {agent_name: agent_settings}
        spec = ConfigSpec(
            config_id="runtime",
            version=config_version,
            settings=settings,
            content_hash=compute_config_hash(settings),
        )
        if mode != "llm":
            return cls.from_spec(spec)

        from app.runtime.prompt_registry import default_prompt_registry

        return cls.from_spec(
            spec,
            prompt_registry=prompt_registry or default_prompt_registry(),
        )

    def agent_config(self, agent_name: str) -> AgentRuntimeConfig:
        try:
            return self.agents[agent_name]
        except KeyError as exc:
            raise ValueError(
                f"No runtime settings registered for agent '{agent_name}'"
            ) from exc

    def agent_for(self, agent_type: type) -> AgentRuntimeConfig:
        return self.agent_config(agent_name_for(agent_type))

    def execution_snapshot(self) -> dict[str, str]:
        return {
            "config_id": self.config_id,
            "config_version": self.config_version,
            "config_hash": self.config_hash,
        }


def _settings_per_agent(settings: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if is_flat_agent_settings(settings):
        agent_names = discover_agents().runtime_agents
        if not agent_names:
            raise ValueError(
                "Flat runtime config requires at least one agent package under app/agents/"
            )
        return {name: settings for name in agent_names}

    agents: dict[str, dict[str, Any]] = {}
    for agent_name, agent_settings in settings.items():
        if not isinstance(agent_settings, dict):
            raise ValueError(
                f"Runtime config for agent '{agent_name}' must be an object"
            )
        agents[agent_name] = agent_settings
    return agents


def _agents_from_settings(
    settings: dict[str, Any],
    registry: PromptRegistry | None,
) -> dict[str, AgentRuntimeConfig]:
    agents: dict[str, AgentRuntimeConfig] = {}
    for agent_name, raw_settings in _settings_per_agent(settings).items():
        agent = AgentRuntimeConfig.model_validate(raw_settings)
        if agent.mode == "llm" and registry is not None:
            prompt_version = str(raw_settings.get("prompt_version", "v1"))
            try:
                prompt = registry.get(agent_name, prompt_version)
            except PromptNotFoundError as exc:
                raise PromptNotFoundError(
                    f"Runtime config references unknown prompt version "
                    f"'{prompt_version}' for agent '{agent_name}'"
                ) from exc
            agent.prompt = prompt
        agents[agent_name] = agent
    return agents


def is_flat_agent_settings(settings: dict[str, Any]) -> bool:
    if not settings:
        return False
    return bool(_AGENT_SETTING_FIELDS.intersection(settings.keys()))
