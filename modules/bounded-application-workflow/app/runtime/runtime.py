from datetime import datetime, timezone
from typing import Protocol, runtime_checkable

from app.runtime.policies import OutputValidator, RetryPolicy
from app.runtime.result import (
    AgentExecutionResult,
    ExecutionStatus,
    InputT,
    OutputT,
)
from app.runtime.runtime_config import RuntimeConfig


class AgentOperation(Protocol[InputT, OutputT]):
    """A single unit of agent work the runtime executes."""

    def __call__(self, agent_input: InputT) -> OutputT: ...


@runtime_checkable
class AgentRuntime(Protocol):
    """Common execution path for agent operations behind Protocol contracts."""

    def execute(
        self,
        operation: AgentOperation[InputT, OutputT],
        agent_input: InputT,
        runtime_config: RuntimeConfig,
        agent_name: str,
        *,
        validator: OutputValidator[OutputT] | None = None,
        fallback: AgentOperation[InputT, OutputT] | None = None,
        retry_policy: RetryPolicy | None = None,
    ) -> AgentExecutionResult[OutputT]: ...


class BoundedAgentRuntime:
    """Executes an agent operation through a bounded, observable lifecycle."""

    def execute(
        self,
        operation: AgentOperation[InputT, OutputT],
        agent_input: InputT,
        runtime_config: RuntimeConfig,
        agent_name: str,
        *,
        validator: OutputValidator[OutputT] | None = None,
        fallback: AgentOperation[InputT, OutputT] | None = None,
        retry_policy: RetryPolicy | None = None,
    ) -> AgentExecutionResult[OutputT]:
        agent_config = runtime_config.agent_config(agent_name)
        started_at = datetime.now(timezone.utc)
        policy = retry_policy or RetryPolicy()
        attempts = 0
        output: OutputT | None = None
        last_error: str | None = None
        status = ExecutionStatus.FAILED

        while attempts < agent_config.max_attempts:
            attempts += 1
            try:
                candidate = operation(agent_input)
                if validator is not None:
                    candidate = validator.validate(candidate)
                output = candidate
            except Exception as exc:  # bounded: contain, optionally retry
                last_error = f"{type(exc).__name__}: {exc}"
                if not policy.should_retry(exc):
                    break
                continue
            status = ExecutionStatus.SUCCESS
            last_error = None
            break

        if status == ExecutionStatus.SUCCESS:
            return self._result(
                runtime_config,
                agent_name,
                started_at,
                status=status,
                attempts=attempts,
                output=output,
            )

        if fallback is not None:
            try:
                output = fallback(agent_input)
            except Exception:
                pass
            else:
                return self._result(
                    runtime_config,
                    agent_name,
                    started_at,
                    status=ExecutionStatus.SUCCESS,
                    attempts=attempts,
                    output=output,
                    error=last_error,
                    used_fallback=True,
                )

        return self._result(
            runtime_config,
            agent_name,
            started_at,
            status=status,
            attempts=attempts,
            error=last_error,
        )

    @staticmethod
    def _result(
        runtime_config: RuntimeConfig,
        agent_name: str,
        started_at: datetime,
        *,
        status: ExecutionStatus,
        attempts: int,
        output: OutputT | None = None,
        error: str | None = None,
        used_fallback: bool = False,
    ) -> AgentExecutionResult[OutputT]:
        agent_config = runtime_config.agent_config(agent_name)
        prompt_trace: dict[str, str] = {}
        if agent_config.prompt is not None:
            prompt_trace = {"prompt_hash": agent_config.prompt.content_hash}
        return AgentExecutionResult[OutputT](
            agent_name=agent_name,
            status=status,
            attempts=attempts,
            started_at=started_at,
            completed_at=datetime.now(timezone.utc),
            output=output,
            error=error,
            used_fallback=used_fallback,
            **runtime_config.execution_snapshot(),
            **prompt_trace,
        )
