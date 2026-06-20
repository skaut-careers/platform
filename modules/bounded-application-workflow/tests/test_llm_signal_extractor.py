import pytest

from app.agents.llm_signal_extraction import LLMSignalExtractor, job_signals_schema, load_system_prompt
from app.llm.client import LLMClientError
from app.runtime import ExecutionStatus, SignalExtractorRuntimeConfig
from tests.llm_helpers import mock_llm_client, sample_input, signals_payload


def test_prompt_and_schema():
    assert "required_skills" in load_system_prompt("v1")
    assert set(job_signals_schema()["properties"]) == set(signals_payload())


def test_llm_extractor_success():
    client = mock_llm_client(signals_payload(required_skills=["Python"], preferred_skills=["FastAPI"]))
    output = LLMSignalExtractor(client=client).run(sample_input())

    assert output.signals.required_skills == ["Python"]
    assert output.signals.preferred_skills == ["FastAPI"]
    assert output.metadata and not output.metadata.used_fallback


def test_llm_extractor_does_not_raise_on_failure():
    client = mock_llm_client(LLMClientError("down"))
    output = LLMSignalExtractor(
        client=client,
        config=SignalExtractorRuntimeConfig(max_attempts=1),
    ).run(sample_input())

    assert output.signals.required_skills == ["Python"]
    assert output.metadata
    assert output.metadata.used_fallback
    assert output.metadata.error.startswith("SignalExtractionLLMError")


@pytest.mark.parametrize(
    "responses, used_fallback, attempts, error_prefix",
    [
        ([LLMClientError("down")], True, 1, "SignalExtractionLLMError"),
        ([signals_payload(required_skills="Python")], True, 1, "SignalExtractionSchemaError"),
        (
            [LLMClientError("retry"), signals_payload(required_skills=["Python"])],
            False,
            2,
            None,
        ),
    ],
)
def test_llm_extractor_runtime_paths(responses, used_fallback, attempts, error_prefix):
    client = mock_llm_client(*responses)
    output = LLMSignalExtractor(
        client=client,
        config=SignalExtractorRuntimeConfig(max_attempts=attempts),
    ).run(sample_input())

    assert output.metadata
    assert output.metadata.used_fallback is used_fallback
    assert output.metadata.attempts == attempts
    if used_fallback:
        assert output.metadata.status == ExecutionStatus.FAILED
        assert output.metadata.error.startswith(error_prefix)
