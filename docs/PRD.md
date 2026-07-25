# PRD — Bounded Application Workflow

## Overview

Evaluates whether a professional opportunity is worth pursuing from structured signals in a user profile and job description.

Supports deliberate, high-quality career decisions — not application volume or autonomous actions. First executable Skaut Careers module.

**Phase:** Milestones 1–5 complete — next: Milestone 6 (local demo-ready application), then Milestone 7 (public demo on Azure).

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

Bounded orchestration: planning/execution separation, typed agent contracts, explicit states, human review on escalation, auditable transitions.

**Non-goals:** unconstrained multi-agent autonomy; LLM overrides without policy bounds.

---

## Milestone 4 — LLM-Backed Agent Runtime (delivered)

LLM agents behind the same `Protocol` contracts: schema-validated outputs, deterministic fallback, bounded retry, versioned prompts/configs, execution provenance, evaluation dataset.

**Non-goals:** autonomous actions; unbounded retries; LLM output accepted without validation or fallback.

---

## Milestone 5 — Framework Migration (delivered)

Migrated onto LangGraph · Pydantic AI · Logfire · Pydantic Evals per [ADR 0001](./adr/0001-adopt-modern-agent-stack.md). Contracts and decision policy unchanged; **output parity** preserved.

**Non-goals:** changing decision policy; user-facing demo (Milestones 6–7).

---

## Milestone 6 — Demo-ready application (planned)

Local end-to-end demo on the migrated stack: Next.js + CopilotKit UI over the FastAPI / LangGraph backend. Paste or load a job description, run evaluation, and see score, decision, missing signals, risks, and reasoning — with seed data, UX states, verification, and setup docs.

**Non-goals:** Azure / cloud deployment (Milestone 7); new evaluation logic; autonomous actions.

---

## Milestone 7 — Public demo on Azure (planned)

Deploy the M6 demo to Azure with a minimal managed architecture, public HTTPS access, secure configuration, repeatable deploy (GitHub Actions or documented process), and basic ops docs (logging, health, cost, troubleshooting, cleanup).

**Non-goals:** Kubernetes, complex networking, production multi-tenant hardening, or introducing Postgres/`pgvector` memory (later milestones).

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
| escalate | Ambiguity or conflicting signals — human review |
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

Python · FastAPI · LangGraph · Pydantic AI · Logfire · Pydantic Evals · typed agent contracts · bounded runtime (retry / fallback / provenance) · versioned prompts and configs · modular domain layer · tests · CI. Planned product surface: Next.js + CopilotKit (M6 local demo; M7 Azure).

Implementation details: [module README](../modules/bounded-application-workflow/README.md).

---

## Success Criteria

**Milestones 1–2:** core evaluation engine shipped.

**Milestone 3:** explicit states · planning/execution separation · human review · inspectable transitions.

**Milestone 4:** ≥1 LLM-backed agent · schema validation · deterministic fallback · versioned prompts/configs · provenance · eval dataset.

**Milestone 5:** LangGraph orchestration · Pydantic AI agents · Logfire traces · Pydantic Evals · output parity · see [ARCHITECTURE](./ARCHITECTURE.md).

**Milestone 6:** main demo journey works locally · frontend connected to real backend · loading/empty/validation/success/error states · seed data · verification · local docs · deploy-ready but not cloud-deployed.

**Milestone 7:** public HTTPS demo on Azure · secure env/secrets · required persistence decided · repeatable deploy · basic logging/health/cost/troubleshooting docs.

---

## Open Questions

- How should uncertainty and user preferences influence scoring?
- Which signals deserve highest weighting?
- What explainability should future versions expose?
- Should policies remain bounded or become adaptive?
