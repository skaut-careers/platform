from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path

from dotenv import dotenv_values

from app.runtime.config_registry import ConfigRegistry, default_config_registry
from app.runtime.prompt_registry import PromptRegistry, default_prompt_registry
from app.runtime.runtime_config import RuntimeConfig

_ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"


@lru_cache(maxsize=1)
def local_env() -> dict[str, str]:
    """Read module-local .env (cached). Missing file => empty dict."""
    return {k: v for k, v in dotenv_values(_ENV_PATH).items() if v is not None}


def load_runtime_config(
    *,
    version: str | None = None,
    env: Mapping[str, str] | None = None,
    config_registry: ConfigRegistry | None = None,
    prompt_registry: PromptRegistry | None = None,
) -> RuntimeConfig:
    """Load the versioned runtime config bundle from the registry.

    If ``version`` is set, it overrides ``RUNTIME_CONFIG_VERSION`` in ``env``.
    If both ``version`` and ``env`` are omitted, reads from ``local_env()``.
    """
    if env is not None or version is not None:
        resolved_env = dict(env) if env is not None else {}
        if version is not None:
            resolved_env = {"RUNTIME_CONFIG_VERSION": version, **resolved_env}
    else:
        resolved_env = local_env()

    resolved_config_registry = config_registry or default_config_registry()
    resolved_prompt_registry = prompt_registry or default_prompt_registry()

    config_version = resolved_env.get("RUNTIME_CONFIG_VERSION", "v1")
    spec = resolved_config_registry.get(config_version)
    return RuntimeConfig.from_spec(spec, prompt_registry=resolved_prompt_registry)
