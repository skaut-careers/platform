# Bounded Application Workflow

First executable Limen module. Evaluates whether an opportunity is worth pursuing based on user profile, job description, and a bounded decision policy.

Decisions: `prepare` · `queue` · `skip` · `escalate` (human review). Does not submit applications or take autonomous actions.

**Phase:** Milestone 3 — Agentic Workflow Layer. See [ROADMAP](../../docs/ROADMAP.md).

## Run locally

```bash
poetry install
poetry run uvicorn app.api.main:app --reload
poetry run pytest
```

## API

- `GET /health` — liveness
- `POST /workflow/run` — evaluate `WorkflowInput` → `WorkflowOutput`

## CI

GitHub Actions runs `poetry run pytest` on pushes/PRs to `main` when this module changes (Python 3.11–3.13).

Workflow: [`.github/workflows/bounded-application-workflow.yml`](../../.github/workflows/bounded-application-workflow.yml)

## Documentation

- [PRD](../../docs/PRD.md) · [ARCHITECTURE](../../docs/ARCHITECTURE.md) · [ROADMAP](../../docs/ROADMAP.md)
