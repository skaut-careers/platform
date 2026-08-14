import pytest

from app.agents.signal_extraction import LLMSignalExtractor
from app.runtime.agent_identity import agent_name_for, discover_agents
from app.runtime.config_loader import load_runtime_config
from app.runtime.config_registry import (
    ConfigNotFoundError,
    ConfigRegistry,
    compute_config_hash,
    default_config_registry,
)
from app.runtime.prompt_registry import (
    PromptNotFoundError,
    PromptRegistry,
    compute_content_hash,
    default_prompt_registry,
)
from tests.conftest import (
    RecordingSignalModel,
    runtime_config,
    sample_signal_extractor_input,
    signals_payload,
)

_AGENT = agent_name_for(LLMSignalExtractor)


def test_default_config_registry():
    registry = default_config_registry()
    assert registry.list_versions() == ["v1", "v2"]

    spec = registry.get("v2")
    assert spec.settings == {
        "mode": "llm",
        "model": "gpt-5.4-mini",
        "max_attempts": 2,
        "prompt_version": "v1",
    }
    assert spec.content_hash == compute_config_hash(spec.settings)


def test_default_prompt_registry():
    registry = default_prompt_registry()
    assert registry.list_versions(_AGENT) == ["v1"]

    spec = registry.get(_AGENT, "v1")
    assert "required_skills" in spec.content
    assert spec.content_hash == compute_content_hash(spec.content)
    assert registry.get_for(LLMSignalExtractor, "v1").agent_name == _AGENT


def test_discover_agents_finds_runtime_packages():
    discovery = discover_agents()
    assert "signal_extraction" in discovery.packages
    assert discovery.runtime_agents == [
        "decision_rules",
        "profile_extraction",
        "profile_matching",
        "signal_extraction",
    ]


def test_registries_reject_unknown_versions():
    with pytest.raises(ConfigNotFoundError, match="version 'missing'"):
        default_config_registry().get("missing")
    with pytest.raises(PromptNotFoundError, match="version 'missing'"):
        default_prompt_registry().get(_AGENT, "missing")


def test_config_registry_from_directory(tmp_path):
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()
    settings = {
        "mode": "llm",
        "model": "gpt-test",
        "max_attempts": 1,
        "prompt_version": "v2",
    }
    (configs_dir / "runtime_v3.json").write_text(
        '{"mode":"llm","model":"gpt-test","max_attempts":1,"prompt_version":"v2"}'
    )

    registry = ConfigRegistry.from_directory(configs_dir)
    assert registry.get("v3").settings == settings
    assert registry.list_versions() == ["v3"]


def test_prompt_registry_from_agents_directory(tmp_path):
    prompts_dir = tmp_path / "signal_extraction" / "prompts"
    prompts_dir.mkdir(parents=True)
    (prompts_dir / "v2.txt").write_text("prompt v2")

    registry = PromptRegistry.from_agents_directory(tmp_path)
    assert registry.get("signal_extraction", "v2").content == "prompt v2"
    assert registry.list_versions("signal_extraction") == ["v2"]


@pytest.mark.parametrize(
    "version, mode, prompt_version",
    [("v1", "deterministic", None), ("v2", "llm", "v1")],
)
def test_load_runtime_config(version, mode, prompt_version):
    config = runtime_config(version)
    agent = config.agent_for(LLMSignalExtractor)

    assert agent.mode == mode
    if mode == "deterministic":
        assert config.config_version == "v1"
        assert config.config_hash == compute_config_hash({"mode": "deterministic"})
    else:
        assert config.config_version == version
        assert agent.model == "gpt-5.4-mini"
        assert agent.prompt and agent.prompt.version == prompt_version


def test_load_runtime_config_rejects_unknown_version():
    with pytest.raises(ConfigNotFoundError):
        runtime_config("missing")


def test_load_runtime_config_rejects_unknown_prompt_reference(tmp_path):
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()
    (configs_dir / "runtime_v9.json").write_text(
        '{"mode":"llm","model":"gpt-test","max_attempts":1,"prompt_version":"missing"}'
    )

    with pytest.raises(PromptNotFoundError, match="unknown prompt version 'missing'"):
        load_runtime_config(
            env={"RUNTIME_CONFIG_VERSION": "v9"},
            config_registry=ConfigRegistry.from_directory(configs_dir),
        )


def test_llm_runtime_sends_configured_prompt_version_to_model():
    prompt = default_prompt_registry().get(_AGENT, "v1")
    model = RecordingSignalModel(signals_payload(required_skills=["Python"]))
    output = LLMSignalExtractor(
        model=model.as_model(),
        runtime_config=runtime_config("v2"),
    ).run(sample_signal_extractor_input())

    assert model.system_prompts == [prompt.content]
    assert output.execution
    assert output.execution.config_version == "v2"
    assert output.execution.prompt_hash == prompt.content_hash
