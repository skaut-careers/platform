# Architecture — Bounded Application Workflow

Bounded agents behind typed contracts. Priorities: bounded execution · explicit state transitions · observable decisions.

Stack: **LangGraph** (orchestration) · **Pydantic AI** (agents) · **Logfire** (observability) · **Pydantic Evals** (evaluation). 

## Orchestration

```mermaid
stateDiagram-v2
    [*] --> profile_extraction
    profile_extraction --> signal_extraction
    signal_extraction --> workflow_planning
    workflow_planning --> profile_matching
    profile_matching --> policy_application
    policy_application --> decision
    decision --> [*]
```

LangGraph `StateGraph` nodes: `profile_extraction` → `UserProfile` → `signal_extraction` → `JobDescription` + `JobSignals` → `workflow_planning` → `WorkflowPlan` → `profile_matching` → `ProfileMatchResult` → `policy_application` → `WorkflowDecision` → terminal `decision` (`prepare` / `queue` / `escalate` / `skip`). Checkpointed `WorkflowGraphState` holds data plus thin audit (`events`); plan vs execution via `WorkflowPlan` / `PlanExecutionReport`.

## Agents

Each stage is a typed `Protocol`. LLM agents (e.g. `LLMSignalExtractor`) use Pydantic AI for structured outputs; `BoundedAgentRuntime` bounds attempts, deterministic fallback, and `AgentExecutionResult` provenance. Prompts and runtime settings are versioned (`RUNTIME_CONFIG_VERSION`).

```mermaid
flowchart TD
    op["Pydantic AI operation"] --> attempts{"attempts left?"}
    attempts -- yes --> run["run + validate"]
    run -- ok --> success["SUCCESS"]
    run -- error --> retry{"retryable?"}
    retry -- yes --> attempts
    retry -- no --> fb{"fallback?"}
    attempts -- no --> fb
    fb -- yes --> det["deterministic fallback"] --> success
    fb -- no --> failed["FAILED (contained)"]
```

## Observability & evaluation

- **Logfire** — OTel spans across FastAPI, LangGraph, and Pydantic AI (`app/observability.py`). Optional `LOGFIRE_TOKEN`.
- **Evals** — golden dataset via Pydantic Evals (precision / recall / F1); `pytest -m llm`.

Details: [module README](../modules/bounded-application-workflow/README.md) · [runtime](../modules/bounded-application-workflow/app/runtime/README.md) · [agents](../modules/bounded-application-workflow/app/agents/README.md) · [eval](../modules/bounded-application-workflow/eval/README.md).


## Influences

- [OpenClaw](https://github.com/openclaw/openclaw)
- [LangGraph](https://github.com/langchain-ai/langgraph)
- [Pydantic AI](https://ai.pydantic.dev/)
