import inspect
from functools import lru_cache
from pathlib import Path
from typing import NamedTuple

_AGENTS_DIR = Path(__file__).resolve().parent.parent / "agents"


class AgentDiscovery(NamedTuple):
    packages: list[str]
    runtime_agents: list[str]


@lru_cache
def discover_agents() -> AgentDiscovery:
    """Scan ``app/agents`` once per process.

    ``packages`` — folders with ``__init__.py``.
    ``runtime_agents`` — folders with ``prompts/`` (LLM runtime participants).
    """
    packages: list[str] = []
    runtime_agents: list[str] = []
    for path in sorted(_AGENTS_DIR.iterdir()):
        if not path.is_dir() or path.name.startswith("_"):
            continue
        if (path / "__init__.py").is_file():
            packages.append(path.name)
        if (path / "prompts").is_dir():
            runtime_agents.append(path.name)
    return AgentDiscovery(packages=packages, runtime_agents=runtime_agents)


def agent_name_for(agent_type: type) -> str:
    """Derive the registry agent name from the agent package folder.

    Classes defined inside an agent package (e.g. ``signal_extraction/llm.py``)
    resolve to the package directory name (``signal_extraction``).
    """
    module_path = Path(inspect.getfile(agent_type)).resolve()
    parent = module_path.parent
    if (parent / "__init__.py").is_file() and parent.name != "agents":
        return parent.name
    return module_path.stem
