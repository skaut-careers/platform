from __future__ import annotations

import hashlib
import re
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from app.runtime.agent_identity import agent_name_for

_AGENTS_DIR = Path(__file__).resolve().parent.parent / "agents"
_PROMPT_VERSION = re.compile(r"^v\d+$")


class PromptNotFoundError(LookupError):
    """Raised when a prompt version is not registered for an agent."""


class PromptSpec(BaseModel):
    """Immutable, versioned prompt for one agent."""

    model_config = ConfigDict(frozen=True)

    agent_name: str
    version: str
    content: str
    content_hash: str


def compute_content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class PromptRegistry:
    """Stores and resolves versioned prompts for runtime agents."""

    def __init__(self, prompts: dict[tuple[str, str], PromptSpec] | None = None) -> None:
        self._prompts = prompts or {}

    def register(self, spec: PromptSpec) -> None:
        self._prompts[(spec.agent_name, spec.version)] = spec

    def get(self, agent_name: str, version: str) -> PromptSpec:
        try:
            return self._prompts[(agent_name, version)]
        except KeyError as exc:
            raise PromptNotFoundError(
                f"No prompt registered for agent '{agent_name}' version '{version}'"
            ) from exc

    def get_for(self, agent_type: type, version: str) -> PromptSpec:
        return self.get(agent_name_for(agent_type), version)

    def list_versions(self, agent_name: str) -> list[str]:
        versions = [
            version
            for registered_agent, version in self._prompts
            if registered_agent == agent_name
        ]
        return sorted(versions)

    @classmethod
    def from_agents_directory(cls, agents_dir: Path) -> PromptRegistry:
        registry = cls()
        for agent_dir in sorted(agents_dir.iterdir()):
            if not agent_dir.is_dir() or agent_dir.name.startswith("_"):
                continue

            prompts_dir = agent_dir / "prompts"
            if not prompts_dir.is_dir():
                continue

            agent_name = agent_dir.name
            for path in sorted(prompts_dir.glob("*.txt")):
                version = path.stem
                if _PROMPT_VERSION.fullmatch(version) is None:
                    continue

                content = path.read_text(encoding="utf-8").strip()
                registry.register(
                    PromptSpec(
                        agent_name=agent_name,
                        version=version,
                        content=content,
                        content_hash=compute_content_hash(content),
                    )
                )

        return registry


@lru_cache
def default_prompt_registry() -> PromptRegistry:
    return PromptRegistry.from_agents_directory(_AGENTS_DIR)
