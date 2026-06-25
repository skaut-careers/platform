import os
from collections.abc import Mapping

from app.runtime.config_registry import ConfigRegistry, default_config_registry
from app.runtime.prompt_registry import PromptRegistry, default_prompt_registry
from app.runtime.runtime_config import RuntimeConfig

def load_runtime_config(
    *,
    env: Mapping[str, str] | None = None,
    config_registry: ConfigRegistry | None = None,
    prompt_registry: PromptRegistry | None = None,
) -> RuntimeConfig:
    """Load the versioned runtime config bundle from the registry."""
    resolved_env = env or os.environ
    resolved_config_registry = config_registry or default_config_registry()
    resolved_prompt_registry = prompt_registry or default_prompt_registry()

    config_version = resolved_env.get("RUNTIME_CONFIG_VERSION", "v1")
    spec = resolved_config_registry.get("runtime", config_version)
    return RuntimeConfig.from_spec(spec, prompt_registry=resolved_prompt_registry)
