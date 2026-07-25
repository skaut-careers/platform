# ADR 0001 — Adopt the 2026 Modern Agent Stack

- **Status:** Accepted
- **Date:** 2026-07-18
- **Deciders:** Ana Stanojevic

## Context

Milestones 1–4 built the bounded application workflow from primitives: a hand-written
state machine (`WorkflowStateMachine`), a bounded agent runtime with retry/validation/fallback
(`BoundedAgentRuntime`), versioned prompts/configs, custom execution tracing (`AgentTrace`,
`WorkflowRun`), and a custom evaluation harness (precision/recall/F1).

This is a production startup product, not a prototype. Maintaining bespoke equivalents of
capabilities that now exist as production-hardened libraries increases maintenance cost,
slows feature delivery, and makes it harder to integrate with the wider ecosystem
(standard tooling, model providers, deployment, observability). By 2026 the agent ecosystem
has consolidated around a small set of libraries that provide these capabilities directly.

### State of the art (July 2026)

- **Pydantic AI v2** (stable 2026-06-23) — type-safe agents, validated structured outputs,
  `capabilities`, dependency injection, `TestModel`/`FunctionModel` for LLM-free testing,
  model-agnostic providers, and native MCP support. Fits a Pydantic- and `Protocol`-first code base.
- **LangGraph 1.x** (GA 1.0 Oct 2025; 1.2.x mid-2026) — stateful graph orchestration with
  pluggable checkpointers, durable execution, and `interrupt`/`Command` for human-in-the-loop.
  Covers what `WorkflowStateMachine` + `WorkflowRun` + escalation do by hand, with production
  persistence and resumability.
- **Pydantic Logfire + Pydantic Evals** — OpenTelemetry-native observability (full-stack app +
  LLM tracing, token/cost/latency) and systematic evaluation, replacing the custom `AgentTrace`
  tracing and F1 harness. Chosen over LangSmith for full-stack OTel coverage and no vendor lock-in.

The industry-recommended composition is **LangGraph for orchestration + Pydantic AI as the
type-safe agent building block**, with Logfire/Evals for observability and evaluation.

## Decision

Migrate the backend onto this stack **before** building the user-facing product surface, so the
product ships and grows on maintained infrastructure rather than bespoke primitives:

- **Agents** → Pydantic AI v2 (signal extraction, profile matching), preserving deterministic
  fallback behaviour and the existing bounded decision policy/thresholds.
- **Orchestration & state** → LangGraph `StateGraph` with a checkpointer; escalation via
  `interrupt`/`Command` (human-in-the-loop stays first-class and bounded).
- **Observability & evaluation** → Pydantic Logfire (OTel) across FastAPI, LangGraph, and agents,
  with Pydantic Evals for the golden dataset and metrics.
- **Dependencies/tooling** → current stable versions, PEP 621 `pyproject`, CI matrix.

The migration must preserve **output parity** — the same decisions and scores as the current
workflow — since the decision policy is the product's core contract.

### Target product architecture (direction, not all in this milestone)

The migration is the backend foundation for the wider product stack:

| Layer | Direction |
| --- | --- |
| Frontend & UI | Next.js + CopilotKit (stream LangGraph agent state into the app UI) — local demo in M6; public Azure demo in M7 |
| Backend & API | FastAPI (Python) |
| Orchestration | LangGraph |
| Agents | Pydantic AI (model-agnostic; route a high-capability model for decisions and a cheaper model for subtasks) |
| Tool integration | MCP (Model Context Protocol) — introduced with retrieval & tooling |
| Data & memory | PostgreSQL + `pgvector` — introduced with memory & retrieval |
| Observability | Pydantic Logfire + Pydantic Evals (OpenTelemetry) |

Only the backend agent runtime, orchestration, and observability/eval land in this milestone;
the local demo UI (M6), Azure public demo (M7), tooling/MCP, and memory/pgvector arrive in
their own milestones.

## Consequences

**Positive**
- Production-grade durability, persistence, and human-in-the-loop out of the box.
- Less bespoke infrastructure to maintain; faster feature delivery.
- Later milestones (memory, retrieval/tooling, evaluation, multi-agent, observability) build on
  framework primitives and standards (MCP, OTel) instead of re-implementing them.
- Model-agnostic agent layer enables cost/quality routing across providers.

**Negative / risks**
- Non-trivial migration effort and temporary churn.
- Larger dependency footprint (LangGraph, LangChain core, agent/observability SDKs).
- `openai` v1 → v2 and other version bumps require a compatibility pass.
- Output parity with the current workflow must be verified before cut-over.

## Alternatives considered

- **Keep everything custom** — highest long-term maintenance cost and slowest integration with
  standard tooling/providers; rejected for a production product.
- **Adopt only Pydantic AI (keep custom orchestration)** — smallest change, but leaves the
  hand-written state machine, persistence, and human-in-the-loop to maintain; rejected because
  LangGraph is purpose-built for exactly this stateful, resumable, human-in-the-loop pattern.
- **CrewAI** — role-based autonomous multi-agent crews; rejected as the core because emergent,
  role-driven autonomy conflicts with this product's principles of bounded, auditable,
  policy-gated decisions with explicit state. LangGraph gives explicit control; may be revisited
  narrowly if a future milestone needs role-based collaboration.
- **Migrate after the product surface** — rejected: the frontend and later milestones would be
  built on the soon-to-be-replaced backend.

## Open questions

- **Model routing:** which providers/models for the decision path vs cheaper subtasks, and
  whether to route via a gateway.
