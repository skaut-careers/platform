from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

_CONFIGS_DIR = Path(__file__).resolve().parent / "configs"
_CONFIG_FILENAME = re.compile(r"^(?P<config_id>[a-z0-9_]+)_(?P<version>v\d+)\.json$")


class ConfigNotFoundError(LookupError):
    """Raised when a config version is not registered."""


@dataclass(frozen=True)
class ConfigSpec:
    """Immutable, versioned runtime settings bundle."""

    config_id: str
    version: str
    settings: dict[str, Any]
    content_hash: str


def compute_config_hash(settings: dict[str, Any]) -> str:
    canonical = json.dumps(settings, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class ConfigRegistry:
    """Stores and resolves versioned runtime configuration bundles."""

    def __init__(
        self, configs: dict[tuple[str, str], ConfigSpec] | None = None
    ) -> None:
        self._configs = configs or {}

    def register(self, spec: ConfigSpec) -> None:
        self._configs[(spec.config_id, spec.version)] = spec

    def get(self, config_id: str, version: str) -> ConfigSpec:
        try:
            return self._configs[(config_id, version)]
        except KeyError as exc:
            raise ConfigNotFoundError(
                f"No config registered for '{config_id}' version '{version}'"
            ) from exc

    def list_versions(self, config_id: str) -> list[str]:
        versions = [
            version
            for registered_id, version in self._configs
            if registered_id == config_id
        ]
        return sorted(versions)

    @classmethod
    def from_directory(cls, configs_dir: Path) -> ConfigRegistry:
        registry = cls()
        for path in sorted(configs_dir.glob("*.json")):
            match = _CONFIG_FILENAME.match(path.name)
            if match is None:
                continue

            config_id = match.group("config_id")
            version = match.group("version")
            settings = json.loads(path.read_text(encoding="utf-8"))
            registry.register(
                ConfigSpec(
                    config_id=config_id,
                    version=version,
                    settings=settings,
                    content_hash=compute_config_hash(settings),
                )
            )

        return registry


@lru_cache
def default_config_registry() -> ConfigRegistry:
    return ConfigRegistry.from_directory(_CONFIGS_DIR)
