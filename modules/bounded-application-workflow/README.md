# Bounded Application Workflow

Decides whether an opportunity is worth pursuing from user profile + job description. Decisions: `prepare` · `queue` · `skip` · `escalate`. No autonomous applications.

**Phase:** Milestones 1–5 complete — next: M6 Minimal product, then M7 Retrieval & Tooling and M8 Agent Memory (local Postgres). Public Azure launch is M10. See [ROADMAP](../../docs/ROADMAP.md).

## Implemented

- Workflow — profile extraction · signal extraction · profile matching · decision policy · `POST /workflow/run` → `WorkflowOutput`
- Orchestration — LangGraph `StateGraph` + checkpointed `WorkflowGraphState`; 
- Agents — typed `Protocol` contracts; LLM path via Pydantic AI + `BoundedAgentRuntime` (retry / fallback / provenance)
- Product surface — Next.js UI + CopilotKit AG-UI on FastAPI (`/copilotkit`) over the same workflow run path
- Observability — Logfire (OTel); thin domain audit on graph state (`events`)
- Evaluation — golden dataset via Pydantic Evals (`make test-llm`)

## Run locally

```bash
make install
make dev
```

- UI: http://127.0.0.1:3000  
- API: http://127.0.0.1:8000  

Optional config in module `.env` (gitignored):

| Variable | Default | When needed |
|----------|---------|-------------|
| `RUNTIME_CONFIG_VERSION` | `v1` | `v1` deterministic · `v2`/`v3` LLM |
| `OPENAI_API_KEY` | — | LLM (`v2`/`v3`) or `make test-llm` |
| `LOGFIRE_TOKEN` | — | optional; omit for local console / OTel |
| `CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | only if Next runs on another origin |

```bash
make test        # fast suite
make test-llm    # golden eval (needs OPENAI_API_KEY)
make check       # types + tests + frontend lint
```

## API

- `GET /health`
- `POST /workflow/run` — raw `profile_text` + raw `job_description_text` → `WorkflowOutput`
- `POST /copilotkit` — streaming bridge for the Next.js UI (same run path as `/workflow/run`)

## CI

`make check` on pushes/PRs to `main` (Python 3.14 + Node 24). Workflow: [`.github/workflows/bounded-application-workflow.yml`](../../.github/workflows/bounded-application-workflow.yml)

## Documentation

- Project: [PRD](../../docs/PRD.md) · [ARCHITECTURE](../../docs/ARCHITECTURE.md) · [ROADMAP](../../docs/ROADMAP.md) · [ADR 0001](../../docs/adr/0001-adopt-modern-agent-stack.md)
- Module: [runtime](app/runtime/README.md) · [agents](app/agents/README.md) · [eval](eval/README.md) · [web](web/README.md)
