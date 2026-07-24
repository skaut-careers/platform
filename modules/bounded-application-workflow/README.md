# Bounded Application Workflow

First executable Skaut Careers module. Evaluates whether an opportunity is worth pursuing based on user profile, job description, and a bounded decision policy.

Decisions: `prepare` · `queue` · `skip` · `escalate` (human review). Does not submit applications or take autonomous actions.

**Phase:** Milestones 1–4 complete — LLM-Backed Agent Runtime delivered. See [ROADMAP](../../docs/ROADMAP.md).

## Implemented

Evaluation engine:

- Signal extraction — structured signals from a job description (`JobSignals`)
- Profile matching — alignment scoring of profile against extracted signals (`ProfileMatchResult`)
- Decision policy — bounded thresholds and escalation rules (`WorkflowDecision`)
- API — `POST /workflow/run` runs the compiled LangGraph via the orchestrator; response is `WorkflowOutput`

Agentic workflow:

- LangGraph orchestration — `StateGraph` nodes with checkpointed `WorkflowGraphState`
- Planning layer — stages selected before execution, plan vs. execution compared (`WorkflowPlan`)
- Agent contracts — typed input/output Protocol per agent
- Orchestrator — coordinates planner + compiled graph
- Human review path — escalation pauses via LangGraph `interrupt`; approve/revise resumes with `Command` (`HumanReviewRecord` on graph state)
- Thin domain audit on graph state — lifecycle events and per-agent traces (`app/agents/orchestration/audit.py`) for plan-vs-execution and HITL; full-stack timing / tokens / cost / model settings via Pydantic Logfire (OpenTelemetry)

Agent runtime:

- Runtime — bounded, observable execution path for LLM-backed agents behind the existing contracts (`AgentRuntime`, `BoundedAgentRuntime`, `RuntimeConfig`, `AgentExecutionResult`), with runtime-level validation, retry, and fallback policies (`PydanticOutputValidator`, `RetryPolicy`)
- LLM signal extractor — `LLMSignalExtractor` behind the `SignalExtractor` protocol, with versioned prompts and deterministic fallback to `DefaultSignalExtractor`
- Prompt registry — prompts live in each runtime agent package under `app/agents/{agent}/prompts/{version}.txt`; loaded via `PromptRegistry` / `PromptSpec`
- Runtime config registry — versioned bundles in `app/runtime/configs/` (`runtime_{version}.json`) with flat agent settings (no per-agent keys); applied to discovered runtime agents (packages with a `prompts/` folder); loaded via `load_runtime_config`
- Agent layout — each agent lives in its own package under `app/agents/` (e.g. `signal_extraction/`, `profile_matching/`); deterministic logic lives in a sibling module (e.g. `deterministic.py`) with a thin `Default*` adapter in `__init__.py`; LLM-backed agents add `llm.py` (e.g. `LLMSignalExtractor`), versioned prompts under `prompts/`, and run through `BoundedAgentRuntime`; `wiring.py` selects deterministic vs. LLM wiring from the runtime config
- Execution provenance — LLM runtime metadata on each agent invocation (`AgentExecutionResult` on `SignalExtractorOutput.execution`, nested in workflow `AgentTrace`); captures config/prompt hashes, attempt count, retry/fallback outcome, and timing
- Observability — Logfire instruments FastAPI, Pydantic AI, and LangGraph (via LangSmith OTel); see [Observability](#observability)
- Signal extractor evaluation — golden dataset in `eval/dataset/` scored via Pydantic Evals (precision/recall/F1); `pytest -m llm` runs experiments (visible in Logfire when `LOGFIRE_TOKEN` is set); see [`eval/README.md`](eval/README.md)

## Run locally

```bash
poetry install
poetry run uvicorn app.api.main:app --reload
```

Local configuration lives in `.env` in this directory (gitignored). The app reads settings from that file only — no shell overrides.

| Variable | Default | When needed |
|----------|---------|-------------|
| `RUNTIME_CONFIG_VERSION` | `v1` | Optional. `v1` = deterministic; `v2` = LLM + prompt v1; `v3` = LLM + prompt v2 |
| `OPENAI_API_KEY` | — | LLM runtime (`v2`/`v3`) or live eval (`pytest -m llm`) |
| `LOGFIRE_TOKEN` | — | Optional. Write token for [Pydantic Logfire](https://logfire.pydantic.dev/); omit for local console / OTel-only |

Example `.env`:

```bash
RUNTIME_CONFIG_VERSION=v2
OPENAI_API_KEY=sk-...
# LOGFIRE_TOKEN=  # optional — leave unset for local-only traces
```

Tests:

```bash
poetry run pytest              # fast, no live OpenAI calls
poetry run pytest -m llm -s    # golden eval (needs OPENAI_API_KEY in .env)
```

## Observability

Pydantic Logfire (`app/observability.py`) adds full-stack OpenTelemetry tracing (latency, tokens, cost, model settings). It does not replace the structured domain audit on graph state:

| Need | Where to look |
|------|----------------|
| HTTP request → graph → agent → model spans; tokens, cost, latency, model settings | Logfire Live view (with `LOGFIRE_TOKEN`) or local console / any OTel backend |
| Plan vs execution, lifecycle events, HITL approve/revise, structured agent outputs | Thin audit on checkpointed `WorkflowGraphState` (`events`, `traces`, `human_review`) via `result.run` / `graph.get_state` |
| Config/prompt hashes, attempts, fallback | `AgentExecutionResult` nested on LLM agent output / `AgentTrace` |
| Golden-dataset precision / recall / F1 experiments | Pydantic Evals (`app/evaluation/`) → Logfire Evals UI when `LOGFIRE_TOKEN` is set |

`logfire.configure(send_to_logfire="if-token-present")` runs on app import. FastAPI is instrumented in `create_app()`; Pydantic AI + HTTPX are instrumented process-wide; LangGraph spans use LangSmith's OTel export (`LANGSMITH_OTEL_*`, set before `langgraph` import).

## API

- `GET /health` — liveness
- `POST /workflow/run` — `WorkflowInput` → graph-backed `WorkflowOutput`

## CI

GitHub Actions runs `poetry run pyright` then `poetry run pytest` on pushes and PRs to `main` (Python 3.14).

Workflow: [`.github/workflows/bounded-application-workflow.yml`](../../.github/workflows/bounded-application-workflow.yml)

## Documentation

- Project: [PRD](../../docs/PRD.md) · [ARCHITECTURE](../../docs/ARCHITECTURE.md) · [ROADMAP](../../docs/ROADMAP.md)
- Module: [runtime](app/runtime/README.md) · [agent guide](app/agents/README.md) · [evaluation](eval/README.md)
