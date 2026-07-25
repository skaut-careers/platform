# Bounded Application Workflow

Evaluates whether an opportunity is worth pursuing from user profile + job description. Decisions: `prepare` · `queue` · `skip` · `escalate`. No autonomous applications.

**Phase:** Milestones 1–5 complete — next: M6 Demo-ready application (local end-to-end demo), then M7 Public demo on Azure. See [ROADMAP](../../docs/ROADMAP.md).

## Implemented

- Evaluation — signal extraction · profile matching · decision policy · `POST /workflow/run` → `WorkflowOutput`
- Orchestration — LangGraph `StateGraph` + checkpointed `WorkflowGraphState`; HITL via `interrupt` / `Command`
- Agents — typed `Protocol` contracts; LLM path via Pydantic AI + `BoundedAgentRuntime` (retry / fallback / provenance)
- Observability — Logfire (OTel); thin domain audit on graph state (`events`, `human_review`)
- Evaluation — golden dataset via Pydantic Evals (`pytest -m llm`)

## Run locally

```bash
poetry install
poetry run uvicorn app.api.main:app --reload
```

Config in `.env` (gitignored):

| Variable | Default | When needed |
|----------|---------|-------------|
| `RUNTIME_CONFIG_VERSION` | `v1` | `v1` deterministic · `v2`/`v3` LLM |
| `OPENAI_API_KEY` | — | LLM (`v2`/`v3`) or `pytest -m llm` |
| `LOGFIRE_TOKEN` | — | optional; omit for local console / OTel |

```bash
poetry run pytest              # fast
poetry run pytest -m llm -s    # golden eval
```

## API

- `GET /health`
- `POST /workflow/run` — `WorkflowInput` → `WorkflowOutput`

## CI

`pyright` + `pytest` on pushes/PRs to `main` (Python 3.14). Workflow: [`.github/workflows/bounded-application-workflow.yml`](../../.github/workflows/bounded-application-workflow.yml)

## Documentation

- Project: [PRD](../../docs/PRD.md) · [ARCHITECTURE](../../docs/ARCHITECTURE.md) · [ROADMAP](../../docs/ROADMAP.md) · [ADR 0001](../../docs/adr/0001-adopt-modern-agent-stack.md)
- Module: [runtime](app/runtime/README.md) · [agents](app/agents/README.md) · [eval](eval/README.md)
