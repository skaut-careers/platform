# Agent Runtime

Reusable execution path for agents behind the workflow's `Protocol` contracts. Wraps a single agent operation (including Pydantic AI calls) in a bounded, observable lifecycle so LLM-backed agents stay as safe to run as deterministic ones. The LangGraph orchestrator is unaware of it.

## Execute

`BoundedAgentRuntime.execute(operation, agent_input, runtime_config, agent_name, *, validator, fallback, retry_policy)` returns an `AgentExecutionResult[Output]`:

1. Run `operation(agent_input)` up to the agent's `max_attempts`.
2. If a `validator` is set, re-validate each candidate output; invalid output fails the attempt.
3. On a retryable error (`RetryPolicy.should_retry`), try again; otherwise stop.
4. If no attempt succeeds and a `fallback` is set, run it and mark `used_fallback=True`.
5. Always return a result — errors are contained in `error`, never raised.

## Result

`AgentExecutionResult` is the auditable record of one execution:

| Field | Meaning |
|-------|---------|
| `status` | `success` / `failed` |
| `attempts` | operation attempts made |
| `duration_ms` | timing (computed) |
| `output` | typed output, or `None` |
| `error` | contained error message |
| `used_fallback` | fallback produced the output |
| `config_version` · `config_hash` · `prompt_hash` | provenance for tracing |

`unwrap()` returns the output or raises `RuntimeExecutionError`; `without_output()` returns an audit copy for attaching as `SignalExtractorOutput.execution` (provenance without nesting the full typed output).

## Configuration

Runtime settings are versioned JSON bundles in [`configs/`](configs/) (`runtime_{version}.json`), selected via `RUNTIME_CONFIG_VERSION` and loaded by `load_runtime_config()`:

| Setting | Meaning |
|---------|---------|
| `mode` | `deterministic` or `llm` |
| `model` | LLM model id |
| `max_attempts` | bounded attempts (1–5) |
| `prompt_version` | prompt to resolve from the registry |

Flat settings (no per-agent keys) apply to every discovered runtime agent — a package under `app/agents/` with a `prompts/` folder. The loader attaches the matching `PromptSpec`; both config and prompt are content-hashed so every execution is traceable to exact inputs.

## Policies

- `PydanticOutputValidator(Model)` — re-validate output against a Pydantic model, raising `OutputValidationError` on mismatch.
- `RetryPolicy(retryable=(...))` — which exception types are worth another attempt.

## Files

| File | Purpose |
|------|---------|
| `runtime.py` | `AgentRuntime` protocol · `BoundedAgentRuntime` lifecycle |
| `result.py` | `AgentExecutionResult` · `ExecutionStatus` |
| `runtime_config.py` | `RuntimeConfig` · `AgentRuntimeConfig` |
| `config_registry.py` · `config_loader.py` | versioned config bundles |
| `prompt_registry.py` | versioned prompts (`PromptSpec`) |
| `policies.py` | validation and retry policies |
| `agent_identity.py` | agent discovery and registry names |
