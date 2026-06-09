# Roadmap

## Milestone 1 — MVP — completed

Executable evaluation workflow: I/O contract, job parsing, profile matching, decision policy, API, tests, CI.

## Milestone 2 — Signal Extraction — completed

Structured signals from job descriptions and profiles: skills, seniority, production expectations, ambiguity/risk, missing signals. Matcher and extractor covered by tests.

## Milestone 3 — Agentic Workflow Layer — in progress

Bounded agentic orchestration: planning/execution separation, agent contracts, explicit workflow states, human review on escalation, auditable transitions.

**Done when:** state machine is explicit; each agent has I/O contract; escalation routes to human review; transitions and outputs are logged and inspectable.

## Milestone 4 — LLM-Backed Agent Runtime

LLM implementations behind existing Protocol contracts with typed fallbacks and auditable execution.

**Focus:** structured extraction · versioned prompts/configs · tool-ready interface · fallback/retry · Pydantic validation · eval set · tracing.

**Done when:** ≥1 LLM-backed agent with schema validation, deterministic fallback, versioned configs, eval set, and full traceability.

## Milestone 5 — User-Facing Demo

Paste job description → evaluate → show score, decision, missing signals, risks, reasoning.

## Milestone 6 — Early Reliability Baseline

Schema validation, execution tracing, prompt versioning, benchmark fixtures. Continues in Milestone 9.

**Done when:** all outputs Pydantic-validated; runs inspectable via `WorkflowRun`; versioned configs; starter benchmark set.

## Milestone 7 — Retrieval & Tooling

Tool registry, contracts, retriever abstraction, vector search, tool selection, schema-validated invocation.

## Milestone 8 — Agent Memory & Context

Short-term/working memory, artifacts, context windows, persistence, pruning. Reconstructable from `WorkflowRun`.

## Milestone 9 — Evaluation & Reliability

Golden datasets, agent/workflow evals, regression tests, confidence scoring, fallback policies, failure analysis, cost tracking.

**Done when:** changes measured against benchmarks; prompts have regression suite; failures classified and actionable.

## Milestone 10 — Multi-Agent Collaboration

Planner, executor, critic, review agents under orchestrator control with handoffs and shared artifacts.

## Milestone 11 — Learning & Policy Adaptation

Outcome tracking, threshold adaptation, feedback loops, decision calibration.

## Milestone 12 — Production AI Platform

Observability dashboards, cost/latency monitoring, trace explorer, run replay, versioned workflows/prompts, A/B testing.

**Done when:** any run reproducible, explainable from trace data, and comparable across model/prompt experiments.
