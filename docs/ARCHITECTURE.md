# Architecture — Bounded Application Workflow

Agent-oriented design: specialized bounded agents.

<p align="center">
  <img src="./images/runtime.png" width="500">
</p>

Priorities: bounded execution · explicit state transitions · observable decision chains · controllable autonomy · human oversight.

Agentic behavior is introduced incrementally and constrained by explicit policies.

---

## Current Phase — Milestone 3

Milestones 1–2 delivered the evaluation engine with structured signal extraction. Milestone 3 adds bounded orchestration on top.

### Workflow State Machine

```
intake → signal_extraction → profile_matching → policy_evaluation → [human_review] → decision
```

Each state has a defined entry condition, responsible agent, and output contract. Transitions are explicit and logged.

### Agent Boundaries

| Stage | Agent | Input | Output |
| ----- | ----- | ----- | ------ |
| signal_extraction | Signal Extractor | raw job description | `JobSignals` |
| profile_matching | Profile Matcher | `JobSignals` + `UserProfile` | `ProfileMatchResult` |
| policy_evaluation | Decision Policy | `ProfileMatchResult` | `WorkflowDecision` |
| human_review | Human Review Gate | escalated decision | approved or revised decision |
| orchestration | Workflow Orchestrator | workflow input | state-managed `WorkflowOutput` |

Planning (scope, signals, guardrails) is separated from execution (running agents, applying policy).

Later milestones (LLM runtime, retrieval, memory, eval, multi-agent, production platform): [ROADMAP.md](./ROADMAP.md).

---

## Principles

| Principle | Meaning |
| --------- | ------- |
| Bounded autonomy | Agents operate within explicit policy constraints |
| Human oversight | High-ambiguity decisions escalate for review |
| Observable reasoning | Decisions remain inspectable and debuggable |
| Modular agents | Composable components, not hidden monolithic prompts |
| Production orientation | Reliability and evaluation over unconstrained autonomy |
