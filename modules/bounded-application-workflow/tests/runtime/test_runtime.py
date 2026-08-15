import pytest

from app.agents.contracts import JobSignalExtractorInput, JobSignalExtractorOutput
from app.domain.models import JobSignals
from app.runtime import (
    AgentRuntime,
    BoundedAgentRuntime,
    ExecutionStatus,
    RetryPolicy,
    RuntimeExecutionError,
    RuntimeConfig,
)

_AGENT = "job_signal_extractor"


def _input() -> JobSignalExtractorInput:
    return JobSignalExtractorInput(job_description_text="- Python")


def _ok(_: JobSignalExtractorInput) -> JobSignalExtractorOutput:
    return JobSignalExtractorOutput(job_signals=JobSignals(required_skills=["Python"]))


def _fail(_: JobSignalExtractorInput) -> JobSignalExtractorOutput:
    raise RuntimeError("model unavailable")


class _Flaky:
    def __init__(self, failures: int) -> None:
        self.failures = failures
        self.calls = 0

    def __call__(self, agent_input: JobSignalExtractorInput) -> JobSignalExtractorOutput:
        self.calls += 1
        if self.calls <= self.failures:
            raise ValueError("transient failure")
        return _ok(agent_input)


def _runtime(**overrides) -> RuntimeConfig:
    return RuntimeConfig.build(agent_name=_AGENT, mode="deterministic", **overrides)


def _execute(operation, **config):
    return BoundedAgentRuntime().execute(operation, _input(), _runtime(**config), _AGENT)


def test_runtime_satisfies_protocol():
    assert isinstance(BoundedAgentRuntime(), AgentRuntime)


def test_success_and_failure_paths():
    success = _execute(_ok)
    assert success.succeeded and success.attempts == 1 and not success.used_fallback

    failure = _execute(_fail)
    assert failure.status == ExecutionStatus.FAILED and failure.output is None
    assert "model unavailable" in (failure.error or "")


def test_retries_until_success_or_exhausted():
    flaky = _Flaky(failures=2)
    assert _execute(flaky, max_attempts=3).succeeded
    assert flaky.calls == 3

    exhausted = _Flaky(failures=5)
    assert not _execute(exhausted, max_attempts=2).succeeded
    assert exhausted.calls == 2


def test_unwrap_returns_output_or_raises():
    assert _execute(_ok).unwrap().job_signals.required_skills == ["Python"]
    with pytest.raises(RuntimeExecutionError):
        _execute(_fail).unwrap()


@pytest.mark.parametrize("overrides", [{"max_attempts": 0}, {"max_attempts": 6}])
def test_config_enforces_bounds(overrides):
    with pytest.raises(ValueError):
        RuntimeConfig.build(**{"agent_name": _AGENT, **overrides})


def test_fallback_runs_after_primary_failure():
    result = BoundedAgentRuntime().execute(
        _fail,
        _input(),
        _runtime(max_attempts=1),
        _AGENT,
        fallback=_ok,
    )
    assert result.succeeded and result.used_fallback
    assert "model unavailable" in (result.error or "")


def test_fallback_failure_preserves_primary_error():
    def fallback_fail(_: JobSignalExtractorInput) -> JobSignalExtractorOutput:
        raise RuntimeError("fallback unavailable")

    result = BoundedAgentRuntime().execute(
        _fail,
        _input(),
        _runtime(max_attempts=1),
        _AGENT,
        fallback=fallback_fail,
    )
    assert not result.succeeded and "model unavailable" in (result.error or "")


def test_retry_policy_skips_non_retryable_errors():
    calls = 0

    def fail_once(_: JobSignalExtractorInput) -> JobSignalExtractorOutput:
        nonlocal calls
        calls += 1
        raise ValueError("bad config")

    result = BoundedAgentRuntime().execute(
        fail_once,
        _input(),
        _runtime(max_attempts=3),
        _AGENT,
        retry_policy=RetryPolicy(retryable=(RuntimeError,)),
    )
    assert not result.succeeded and result.attempts == calls == 1
