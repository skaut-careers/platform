# Roadmap

## Milestone 1 — MVP — completed

Executable evaluation workflow: I/O contract, job parsing, profile matching, decision policy, API, tests, CI.

## Milestone 2 — Signal Extraction — completed

Structured signals from job descriptions and profiles: skills, seniority, production expectations, ambiguity/risk, missing signals. Matcher and extractor covered by tests.

## Milestone 3 — Agentic Workflow Layer — completed

Bounded orchestration: agent contracts, planning/execution separation, explicit states, human review, auditable transitions.

## Milestone 4 — LLM-Backed Agent Runtime — completed

LLM agents behind Protocol contracts with typed fallbacks, versioned prompts/configs, eval set, and auditable execution.

## Milestone 5 — Framework Migration — completed

Migrate onto LangGraph · Pydantic AI · Logfire · Pydantic Evals behind existing contracts. See [ADR 0001](adr/0001-adopt-modern-agent-stack.md). Output parity preserved.

| Before | After |
|--------|-------|
| `BoundedAgentRuntime` (LLM calls) | Pydantic AI (+ thin `BoundedAgentRuntime` for retry / fallback / provenance) |
| `WorkflowStateMachine` / `WorkflowRun` | LangGraph |
| `AgentTrace` | Logfire |
| Custom eval harness | Pydantic Evals |

## Milestone 6 — Minimal product

Local end-to-end product: paste profile/CV + job description → evaluate → show decision, missing signals, risks, reasoning. Next.js + CopilotKit over the FastAPI / LangGraph backend.

## Milestone 7 — Retrieval & Tooling

Tool registry, contracts, retriever abstraction, vector search, tool selection, schema-validated invocation via Pydantic AI tools / MCP. Runs on the local product from M6 (shared vector store with M8).

## Milestone 8 — Agent Memory & Context

Short-term/working memory, artifacts, context windows, persistence, pruning — via LangGraph checkpointers and state reducers, backed by PostgreSQL + `pgvector` (local first; same store later wired on Azure in M10).

## Milestone 9 — Early Reliability Baseline

Schema validation, execution tracing, prompt versioning, benchmark fixtures — built on Logfire traces and Pydantic Evals. Continues in Milestone 11.

**Done when:** all outputs Pydantic-validated; runs inspectable via Logfire/LangGraph checkpoints; versioned configs; starter benchmark set.

## Milestone 10 — Public launch on Azure

Deploy the product (M6 + M7/M8 capabilities as ready) to Azure: managed app hosting, public HTTPS, secure config, repeatable deploy, and the Postgres/`pgvector` store introduced in M8.

## Milestone 11 — Evaluation & Reliability

Golden datasets, agent/workflow evals, regression tests, confidence scoring, fallback policies, failure analysis, cost tracking — on Pydantic Evals + Logfire.

**Done when:** changes measured against benchmarks; prompts have regression suite; failures classified and actionable.

## Milestone 12 — Multi-Agent Collaboration

Planner, executor, critic, review agents under orchestrator control with handoffs and shared artifacts — as LangGraph subgraphs.

## Milestone 13 — Learning & Policy Adaptation

Outcome tracking, threshold adaptation, feedback loops, decision calibration.

## Milestone 14 — Production AI Platform

Observability dashboards, cost/latency monitoring, trace explorer, run replay, versioned workflows/prompts, A/B testing — on Logfire.

**Done when:** any run reproducible, explainable from trace data, and comparable across model/prompt experiments.
