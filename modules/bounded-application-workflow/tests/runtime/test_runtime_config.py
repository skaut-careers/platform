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
    PromptSpec,
    compute_content_hash,
    default_prompt_registry,
)
from tests.conftest import (
    mock_llm_client,
    register_runtime_bundle,
    runtime_config,
    sample_signal_extractor_input,
    signals_payload,
)

_AGENT = agent_name_for(LLMSignalExtractor)


def test_default_config_registry():
    registry = default_config_registry()
    assert registry.list_versions() == ["v1", "v2", "v3", "v4"]

    spec = registry.get("v2")
    assert spec.settings == {
        "mode": "llm",
        "model": "gpt-5-mini",
        "max_attempts": 2,
        "prompt_version": "v1",
    }
    assert spec.content_hash == compute_config_hash(spec.settings)


def test_default_prompt_registry():
    registry = default_prompt_registry()
    assert registry.list_versions(_AGENT) == ["v1", "v2", "v3"]

    spec = registry.get(_AGENT, "v1")
    assert "required_skills" in spec.content
    assert spec.content_hash == compute_content_hash(spec.content)
    assert registry.get_for(LLMSignalExtractor, "v1").agent_name == _AGENT


def test_discover_agents_finds_runtime_packages():
    discovery = discover_agents()
    assert "signal_extraction" in discovery.packages
    assert discovery.runtime_agents == ["signal_extraction"]


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
        "prompt_version": "v3",
    }
    (configs_dir / "runtime_v4.json").write_text(
        '{"mode":"llm","model":"gpt-test","max_attempts":1,"prompt_version":"v3"}'
    )

    registry = ConfigRegistry.from_directory(configs_dir)
    assert registry.get("v4").settings == settings
    assert registry.list_versions() == ["v4"]


def test_prompt_registry_from_agents_directory(tmp_path):
    prompts_dir = tmp_path / "signal_extraction" / "prompts"
    prompts_dir.mkdir(parents=True)
    (prompts_dir / "v3.txt").write_text("prompt v3")

    registry = PromptRegistry.from_agents_directory(tmp_path)
    assert registry.get("signal_extraction", "v3").content == "prompt v3"
    assert registry.list_versions("signal_extraction") == ["v3"]


def test_prompt_registry_register_overrides_existing_entry():
    registry = PromptRegistry()
    registry.register(
        PromptSpec(
            agent_name=_AGENT,
            version="v9",
            content="custom prompt",
            content_hash=compute_content_hash("custom prompt"),
        )
    )
    assert registry.get(_AGENT, "v9").content == "custom prompt"


@pytest.mark.parametrize(
    "version, mode, prompt_version",
    [(None, "deterministic", None), ("v2", "llm", "v1")],
)
def test_load_runtime_config(version, mode, prompt_version):
    config = runtime_config(version) if version else runtime_config()
    agent = config.agent_for(LLMSignalExtractor)

    assert agent.mode == mode
    if mode == "deterministic":
        assert config.config_version == "v1"
        assert config.config_hash == compute_config_hash({"mode": "deterministic"})
    else:
        assert config.config_version == version
        assert agent.model == "gpt-5-mini"
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


def test_execution_links_config_and_prompt_metadata():
    settings = {
        "mode": "llm",
        "model": "gpt-test",
        "max_attempts": 2,
        "prompt_version": "v9",
    }
    config_registry, prompt_registry = register_runtime_bundle(
        version="bundle_v9",
        settings=settings,
        prompt_version="v9",
        prompt_content="registry prompt v9",
    )
    client = mock_llm_client(signals_payload(required_skills=["Python"]))
    output = LLMSignalExtractor(
        client=client,
        runtime_config=load_runtime_config(
            env={"RUNTIME_CONFIG_VERSION": "bundle_v9"},
            config_registry=config_registry,
            prompt_registry=prompt_registry,
        ),
    ).run(sample_signal_extractor_input())

    assert output.execution
    assert output.execution.config_version == "bundle_v9"
    assert output.execution.config_hash == compute_config_hash(settings)
    assert client.complete_json.call_args.kwargs["system"] == "registry prompt v9"


def test_runtime_version_switch_changes_prompt_and_settings():
    client = mock_llm_client(signals_payload(required_skills=["Python"]))

    LLMSignalExtractor(
        client=client,
        runtime_config=runtime_config("v2"),
    ).run(sample_signal_extractor_input())
    prompt_from_runtime_v2 = client.complete_json.call_args.kwargs["system"]

    client.reset_mock()
    client.complete_json.return_value = signals_payload(required_skills=["Python"])
    output = LLMSignalExtractor(
        client=client,
        runtime_config=runtime_config("v3"),
    ).run(sample_signal_extractor_input())
    prompt_from_runtime_v3 = client.complete_json.call_args.kwargs["system"]

    assert "(v2)" not in prompt_from_runtime_v2
    assert "(v2)" in prompt_from_runtime_v3
    assert prompt_from_runtime_v2 != prompt_from_runtime_v3
    assert output.execution
    assert output.execution.config_version == "v3"
    assert output.execution.config_hash == compute_config_hash(
        {
            "mode": "llm",
            "model": "gpt-5-mini",
            "max_attempts": 3,
            "prompt_version": "v2",
        }
    )
