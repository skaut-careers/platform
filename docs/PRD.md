# PRD — Bounded Application Workflow

## Overview

Evaluates whether a professional opportunity is worth pursuing from structured signals in a user profile and job description.

Supports deliberate, high-quality career decisions — not application volume or autonomous actions. First executable Limen module.

**Phase:** Milestone 3 — Agentic Workflow Layer (Milestones 1–2 complete). See [ARCHITECTURE.md](./ARCHITECTURE.md) for workflow states and agent boundaries.

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

## Milestone 3 — Agentic Workflow Layer (current)

Evolve the engine into bounded agentic orchestration with explicit states, specialized agents, and human oversight.

**Requirements:**

- planning and execution are separate stages
- each agent has a defined input/output contract
- workflow state is explicit and persisted
- escalation routes to human review before final decision
- state transitions and agent outputs are logged and inspectable

**Non-goals:** unconstrained multi-agent autonomy; LLM overrides without policy bounds.

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

Python · FastAPI · deterministic policy and extraction · bounded agentic orchestration · modular domain layer · tests · CI.

LLM-backed agents: Milestone 4. Implementation details: [module README](../modules/bounded-application-workflow/README.md).

---

## Success Criteria

**Milestones 1–2:** core evaluation engine shipped.

**Milestone 3:** explicit logged states · planning/execution separation · human review on escalation · inspectable transitions · foundation for user-facing demo (Milestone 5).

---

## Open Questions

- How should uncertainty and user preferences influence scoring?
- Which signals deserve highest weighting?
- What explainability should future versions expose?
- Should policies remain bounded or become adaptive?
