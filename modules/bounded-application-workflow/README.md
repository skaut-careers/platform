# Bounded Application Workflow

First executable Skaut Careers module. Evaluates whether an opportunity is worth pursuing based on user profile, job description, and a bounded decision policy.

Decisions: `prepare` · `queue` · `skip` · `escalate` (human review). Does not submit applications or take autonomous actions.

**Phase:** Milestones 1–4 complete — LLM-Backed Agent Runtime delivered. See [ROADMAP](../../docs/ROADMAP.md).

## Implemented

Evaluation engine:

- Signal extraction — structured signals from a job description (`JobSignals`)
- Profile matching — alignment scoring of profile against extracted signals (`ProfileMatchResult`)
- Decision policy — bounded thresholds and escalation rules (`WorkflowDecision`)
- API — evaluate `WorkflowInput` → `WorkflowOutput`

Agentic workflow:

- Workflow state machine — explicit states and validated transitions (`WorkflowStateMachine`)
- Workflow run model — every run recorded and reconstructable (`WorkflowRun`)
- Planning layer — stages selected before execution, plan vs. execution compared (`WorkflowPlan`)
- Agent contracts — typed input/output Protocol per agent
- Orchestrator — state-managed execution of the agent pipeline
- Human review path — escalated decisions approved or revised (`HumanReviewRecord`)
- Audit trail — timestamped events and per-agent traces (`WorkflowEvent`, `AgentTrace`)

Agent runtime:

- Runtime — bounded, observable execution path for LLM-backed agents behind the existing contracts (`AgentRuntime`, `BoundedAgentRuntime`, `RuntimeConfig`, `AgentExecutionResult`), with runtime-level validation, retry, and fallback policies (`PydanticOutputValidator`, `RetryPolicy`)
- LLM signal extractor — `LLMSignalExtractor` behind the `SignalExtractor` protocol, with versioned prompts and deterministic fallback to `DefaultSignalExtractor`
- Prompt registry — prompts live in each runtime agent package under `app/agents/{agent}/prompts/{version}.txt`; loaded via `PromptRegistry` / `PromptSpec`
- Runtime config registry — versioned bundles in `app/runtime/configs/` (`runtime_{version}.json`) with flat agent settings (no per-agent keys); applied to discovered runtime agents (packages with a `prompts/` folder); loaded via `load_runtime_config`
- Agent layout — each agent lives in its own package under `app/agents/` (e.g. `signal_extraction/`, `profile_matching/`); deterministic logic lives in a sibling module (e.g. `deterministic.py`) with a thin `Default*` adapter in `__init__.py`; LLM-backed agents add `llm.py` (e.g. `LLMSignalExtractor`), versioned prompts under `prompts/`, and run through `BoundedAgentRuntime`; `wiring.py` selects deterministic vs. LLM wiring from the runtime config
- Execution tracing — LLM runtime metadata on each agent invocation (`AgentExecutionResult` on `SignalExtractorOutput.execution`, nested in workflow `AgentTrace`); captures config/prompt hashes, attempt count, retry/fallback outcome, and timing
- Signal extractor evaluation — golden dataset in `eval/dataset/` (LLM eval), see [`eval/README.md`](eval/README.md)

## Run locally

```bash
poetry install
poetry run uvicorn app.api.main:app --reload
```

Local configuration lives in `.env` in this directory (gitignored). The app reads settings from that file only — no shell overrides.

| Variable | Default | When needed |
|----------|---------|-------------|
| `RUNTIME_CONFIG_VERSION` | `v1` | Optional. `v1` = deterministic extractor; `v2`/`v3` = LLM-backed extractor (see `runtime_v*.json`) |
| `OPENAI_API_KEY` | — | LLM runtime (`v2`/`v3`) or live eval (`pytest -m llm`) |

Example `.env`:

```bash
RUNTIME_CONFIG_VERSION=v2
OPENAI_API_KEY=sk-...
```

Tests:

```bash
poetry run pytest              # fast, no live OpenAI calls
poetry run pytest -m llm -s    # golden eval (needs OPENAI_API_KEY in .env)
```

## API

- `GET /health` — liveness
- `POST /workflow/run` — evaluate `WorkflowInput` → `WorkflowOutput`

## CI

GitHub Actions runs `poetry run pytest` on pushes and PRs to `main` (Python 3.14).

Workflow: [`.github/workflows/bounded-application-workflow.yml`](../../.github/workflows/bounded-application-workflow.yml)

## Documentation

- Project: [PRD](../../docs/PRD.md) · [ARCHITECTURE](../../docs/ARCHITECTURE.md) · [ROADMAP](../../docs/ROADMAP.md)
- Module: [runtime](app/runtime/README.md) · [agent guide](app/agents/README.md) · [evaluation](eval/README.md)
