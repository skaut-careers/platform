# Bounded Application Workflow

First executable Limen module. Evaluates whether an opportunity is worth pursuing based on user profile, job description, and a bounded decision policy.

Decisions: `prepare` · `queue` · `skip` · `escalate` (human review). Does not submit applications or take autonomous actions.

**Phase:** Milestone 4 — LLM-Backed Agent Runtime (Milestones 1–3 complete). See [ROADMAP](../../docs/ROADMAP.md).

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

## In progress — Milestone 4

- Agent runtime — bounded, observable execution path for LLM-backed agents behind the existing contracts (`AgentRuntime`, `BoundedAgentRuntime`, `RuntimeConfig`, `AgentExecutionResult`)
- LLM signal extractor — `LLMSignalExtractor` behind the `SignalExtractor` protocol, with versioned prompts, Pydantic schema validation, runtime retries, and deterministic fallback to `DefaultSignalExtractor`

## Run locally

```bash
poetry install
poetry run uvicorn app.api.main:app --reload
poetry run pytest
```

Set `SIGNAL_EXTRACTOR=llm` to use the LLM-backed signal extractor (falls back to deterministic rules when the provider is unavailable). Optional: `LLM_SIGNAL_MODEL` (default `gpt-5-mini`), `OPENAI_API_KEY` for live OpenAI Responses API calls. Install the OpenAI extra with `poetry install -E openai`.

## API

- `GET /health` — liveness
- `POST /workflow/run` — evaluate `WorkflowInput` → `WorkflowOutput`

## CI

GitHub Actions runs `poetry run pytest` on pushes/PRs to `main` when this module changes (Python 3.11–3.13).

Workflow: [`.github/workflows/bounded-application-workflow.yml`](../../.github/workflows/bounded-application-workflow.yml)

## Documentation

- [PRD](../../docs/PRD.md) · [ARCHITECTURE](../../docs/ARCHITECTURE.md) · [ROADMAP](../../docs/ROADMAP.md)
