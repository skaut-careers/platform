# PRD — Bounded Application Workflow

## Overview

Evaluates whether a professional opportunity is worth pursuing from structured signals in a user profile and job description.

Supports deliberate, high-quality career decisions — not application volume or autonomous actions. First executable Skaut Careers module.

**Phase:** Milestones 1–5 complete — next: Milestone 6 (minimal product), then Milestone 7 (retrieval & tooling) and Milestone 8 (memory). Public Azure launch is Milestone 10.

---

## Problem

Job search is noisy and cognitively expensive. Existing tools optimize volume, speed, and keyword matching — not whether an opportunity is aligned, attainable, or worth the investment.

**Target users:** technical professionals, researchers entering industry, multidisciplinary candidates with non-linear careers. Users who value quality, strategic applications, and bounded automation.

---

## Core Engine (Milestones 1–2 — delivered)

1. Accept user profile + job description
2. Extract structured opportunity signals
3. Score profile alignment
4. Apply bounded decision policy
5. Return structured recommendation via API

The module **evaluates** (prepare, queue, skip, escalate). It does **not** apply to jobs, send emails, automate browsers, optimize resumes, or scrape platforms at scale.

---

## Milestone 3 — Agentic Workflow Layer (delivered)

Bounded orchestration: typed agent contracts, explicit states, auditable transitions.

**Non-goals:** unconstrained multi-agent autonomy; LLM overrides without policy bounds.

---

## Milestone 4 — LLM-Backed Agent Runtime (delivered)

LLM agents behind the same `Protocol` contracts: schema-validated outputs, deterministic fallback, bounded retry, versioned prompts/configs, execution provenance, evaluation dataset.

**Non-goals:** autonomous actions; unbounded retries; LLM output accepted without validation or fallback.

---

## Milestone 5 — Framework Migration (delivered)

Migrated onto LangGraph · Pydantic AI · Logfire · Pydantic Evals per [ADR 0001](./adr/0001-adopt-modern-agent-stack.md). Contracts and decision policy unchanged; **output parity** preserved.

**Non-goals:** changing decision policy; user-facing product UI (Milestone 6+).

---

## Milestone 6 — Minimal product (planned)

Local end-to-end product on the migrated stack: Next.js + CopilotKit UI over the FastAPI / LangGraph backend. Paste profile/CV + job description, run evaluation, and see decision, missing signals, risks, and reasoning — with UX states, verification, and setup docs.

**Non-goals:** Azure / cloud deployment (Milestone 10); retrieval/memory (Milestones 7–8); autonomous actions.

---

## Milestone 7 — Retrieval & Tooling (planned)

Tool registry, retriever abstraction, vector search, and schema-validated tool invocation (Pydantic AI tools / MCP) so evaluation can use more than a single pasted JD.

**Non-goals:** Azure deploy; multi-agent sprawl; unbounded tool use outside contracts.

---

## Milestone 8 — Agent Memory & Context (planned)

LangGraph checkpointer-backed memory and context (artifacts, pruning) on PostgreSQL + `pgvector`, first locally so profile/history and concurrent runs can persist.

**Non-goals:** Azure hosting of that database (Milestone 10 wires the same store); adaptive policy learning (Milestone 13).

---

## Milestone 9 — Early Reliability Baseline (planned)

Schema validation, execution tracing, prompt versioning, and starter benchmark fixtures on Logfire / Pydantic Evals. Continues in Milestone 11.

**Non-goals:** full regression platform (Milestone 11); Azure launch.

---

## Milestone 10 — Public launch on Azure (planned)

Deploy the product to Azure after M7/M8 exist locally: managed app hosting, public HTTPS, secure configuration, repeatable deploy, and the Postgres/`pgvector` store from Milestone 8.

**Non-goals:** Kubernetes, complex networking, or inventing a second persistence stack.

---

## Inputs

**User profile** — experience, skills, research/production background, domains, location, seniority.

**Job description** — raw posting text. System extracts required/preferred skills, domain alignment, seniority, execution signals, production requirements, ambiguity/risk indicators.

---

## Outputs

Structured evaluation object:

```json
{
  "score": 0.82,
  "decision": "prepare",
  "missing_signals": ["large-scale production inference"],
  "risks": ["high infrastructure ownership expectations"],
  "reasoning_summary": "Strong AI systems alignment with partial production gaps."
}
```

### Decision categories

| Decision | Meaning |
| -------- | ------- |
| prepare | High alignment — pursue actively |
| queue | Potential fit, not current priority |
| escalate | Ambiguity or conflicting signals — inspect personally |
| skip | Low alignment or poor strategic fit |

### Policy thresholds

| Score | Decision |
| ----- | -------- |
| ≥ 0.75 | prepare |
| ≥ 0.55 | queue |
| ≥ 0.35 | escalate |
| < 0.35 | skip |

Deterministic and simple. Risk-based escalation via workflow plan and decision rules. Future: confidence, uncertainty, weighted signals, user preferences, memory.

---

## Technical Scope

Python · FastAPI · LangGraph · Pydantic AI · Logfire · Pydantic Evals · typed agent contracts · bounded runtime (retry / fallback / provenance) · versioned prompts and configs · modular domain layer · tests · CI. Planned product surface: Next.js + CopilotKit (M6 local); retrieval/memory (M7–M8); public Azure launch (M10).

Implementation details: [module README](../modules/bounded-application-workflow/README.md).

---

## Success Criteria

**Milestones 1–2:** core evaluation engine shipped.

**Milestone 3:** explicit states · typed agent contracts · inspectable transitions.

**Milestone 4:** ≥1 LLM-backed agent · schema validation · deterministic fallback · versioned prompts/configs · provenance · eval dataset.

**Milestone 5:** LangGraph orchestration · Pydantic AI agents · Logfire traces · Pydantic Evals · output parity · see [ARCHITECTURE](./ARCHITECTURE.md).

**Milestone 6:** main user journey works locally · frontend connected to real backend · loading/empty/validation/success/error states · verification · local docs.

**Milestone 7:** tools/retrieval behind contracts · vector search usable from the workflow · schema-validated invocation.

**Milestone 8:** Postgres/`pgvector` + checkpointer memory locally · concurrent runs isolated · context/pruning defined.

**Milestone 9:** outputs validated · runs inspectable · versioned configs · starter benchmarks.

**Milestone 10:** public HTTPS product on Azure · secure env/secrets · M8 store wired · repeatable deploy · basic logging/health/cost/troubleshooting docs.

---

## Open Questions

- How should uncertainty and user preferences influence scoring?
- Which signals deserve highest weighting?
- What explainability should future versions expose?
- Should policies remain bounded or become adaptive?
