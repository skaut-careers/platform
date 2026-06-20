import pytest

from app.agents.default import create_agents
from tests.llm_helpers import mock_llm_client


@pytest.mark.parametrize(
    "env, extractor_name",
    [
        (None, "DefaultSignalExtractor"),
        ("llm", "LLMSignalExtractor"),
    ],
)
def test_create_agents_selects_extractor(monkeypatch, env, extractor_name):
    if env is None:
        monkeypatch.delenv("SIGNAL_EXTRACTOR", raising=False)
    else:
        monkeypatch.setenv("SIGNAL_EXTRACTOR", env)

    *_, orchestrator = create_agents(client=mock_llm_client())

    assert orchestrator._extractor.__class__.__name__ == extractor_name


def test_create_agents_rejects_unknown_mode(monkeypatch):
    monkeypatch.setenv("SIGNAL_EXTRACTOR", "magic")

    with pytest.raises(ValueError, match="Unsupported SIGNAL_EXTRACTOR"):
        create_agents()
