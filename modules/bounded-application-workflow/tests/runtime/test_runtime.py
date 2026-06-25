import pytest

from app.agents.contracts import SignalExtractorInput, SignalExtractorOutput
from app.domain.job_signals import JobSignals
from app.domain.models import JobDescription
from app.runtime import (
    AgentRuntime,
    BoundedAgentRuntime,
    ExecutionStatus,
    OutputValidationError,
    PydanticOutputValidator,
    RetryPolicy,
    RuntimeExecutionError,
    RuntimeConfig,
)

_AGENT = "signal_extractor"


def _input() -> SignalExtractorInput:
    return SignalExtractorInput(
        job_description=JobDescription(title="AI Engineer", description="- Python")
    )


def _ok(_: SignalExtractorInput) -> SignalExtractorOutput:
    return SignalExtractorOutput(signals=JobSignals(required_skills=["Python"]))


def _fail(_: SignalExtractorInput) -> SignalExtractorOutput:
    raise RuntimeError("model unavailable")


class _Flaky:
    def __init__(self, failures: int) -> None:
        self.failures = failures
        self.calls = 0

    def __call__(self, agent_input: SignalExtractorInput) -> SignalExtractorOutput:
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
    assert _execute(_ok).unwrap().signals.required_skills == ["Python"]
    with pytest.raises(RuntimeExecutionError):
        _execute(_fail).unwrap()


@pytest.mark.parametrize("overrides", [{"max_attempts": 0}, {"max_attempts": 6}])
def test_config_enforces_bounds(overrides):
    with pytest.raises(ValueError):
        RuntimeConfig.build(**{"agent_name": _AGENT, **overrides})


def _invalid_output(_: SignalExtractorInput) -> SignalExtractorOutput:
    return SignalExtractorOutput(
        signals=JobSignals.model_construct(required_skills="Python")
    )


def test_validator_rejects_invalid_output():
    result = BoundedAgentRuntime().execute(
        _invalid_output,
        _input(),
        _runtime(max_attempts=1),
        _AGENT,
        validator=PydanticOutputValidator(SignalExtractorOutput),
    )
    assert not result.succeeded and result.error.startswith("OutputValidationError")


def test_validator_retries_before_failing():
    calls = 0

    def flaky_invalid(_: SignalExtractorInput) -> SignalExtractorOutput:
        nonlocal calls
        calls += 1
        if calls == 1:
            return _invalid_output(_)
        return _ok(_)

    result = BoundedAgentRuntime().execute(
        flaky_invalid,
        _input(),
        _runtime(max_attempts=2),
        _AGENT,
        validator=PydanticOutputValidator(SignalExtractorOutput),
    )
    assert result.succeeded and result.attempts == calls == 2


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
    def fallback_fail(_: SignalExtractorInput) -> SignalExtractorOutput:
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

    def fail_once(_: SignalExtractorInput) -> SignalExtractorOutput:
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
