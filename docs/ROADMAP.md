# Roadmap

## Milestone 1 — Bounded Application Workflow MVP — completed

Goal: build the first executable workflow inside Limen.

The module evaluates opportunities against a user profile and decides whether the system should:

- prepare
- queue
- skip
- escalate

Implementation focus:

1. input/output contract
2. job description parsing
3. profile matching
4. decision policy
5. runtime API
6. tests and CI

Done when:

- the module can be run locally
- an opportunity can be evaluated through an API endpoint
- the decision policy is covered by tests
- CI validates the implementation

## Milestone 2 — Signal Extraction — completed

Improve structured extraction from job descriptions and user profiles.

Focus:

- required skills
- preferred skills
- seniority signals
- production expectations
- ambiguity and risk indicators
- missing signals

Done when:

- job descriptions yield structured signal categories
- user profiles expose seniority and production experience fields
- matcher incorporates signal-level alignment and risk detection
- extraction and matching are covered by tests and fixtures

## Milestone 3 — Agentic Workflow Layer — in progress

Introduce bounded agentic orchestration.

Focus:

- separate planning from execution
- define agent responsibilities
- add explicit workflow states
- introduce human review points
- keep decisions observable and auditable

Done when:

- workflow states are explicit and transition through a defined state machine
- planning and execution are separate stages with clear boundaries
- each agent has a defined responsibility and input/output contract
- human review points are wired into escalation paths
- state transitions and decisions are logged and inspectable

## Milestone 4 — LLM-Backed Agent Runtime

Introduce LLM-backed implementations for selected workflow agents while preserving typed contracts, deterministic fallbacks, and auditable execution.

Focus:

- LLM structured output for job signal extraction
- prompt/versioned agent configurations
- tool-ready agent interface
- model fallback and retry policy
- validation of LLM outputs against Pydantic schemas
- evaluation set for extraction and decision quality
- tracing of prompts, outputs, errors, and decisions

Done when:

- at least one workflow agent has an LLM-backed implementation behind the existing Protocol contract
- LLM outputs are validated against Pydantic schemas before entering the workflow
- deterministic fallback is used when the model fails or output is invalid
- agent prompts and model configs are versioned and selectable at runtime
- extraction and decision quality can be measured against a fixed evaluation set
- prompts, outputs, errors, and final decisions are traced for inspection

## Milestone 5 — User-Facing Demo

Expose the workflow through a simple interface.

Focus:

- paste job description
- evaluate opportunity
- show score, decision, missing signals, risks, and reasoning summary

## Milestone 6 — Evaluation & Reliability

Build confidence that workflow decisions are consistent, observable, and measurable.

## Goal

Move from a working prototype to an engineering-grade AI system.

The system should not only produce decisions, but also provide evidence that those decisions are reliable.

## Focus

### Evaluation Dataset

Create a benchmark set of job opportunities with expected outcomes.

Examples:

- strong fit → PREPARE
- uncertain fit → ESCALATE
- weak fit → SKIP
- later opportunity → QUEUE

### Automated Evaluation

Measure decision quality against benchmark data.

Track:

- decision accuracy
- false positives
- false negatives
- escalation rate

### Structured Outputs

Ensure all AI-generated outputs follow validated schemas.

Examples:

- extracted signals
- risk indicators
- opportunity summaries
- workflow decisions

### Prompt Versioning

Treat prompts as production assets.

Track:

- prompt versions
- changes
- evaluation results per version

### Observability

Make workflow execution transparent.

Capture:

- execution traces
- workflow state transitions
- model responses
- decision rationale
- failure events

### Reliability Testing

Evaluate behavior under difficult conditions.

Examples:

- incomplete job descriptions
- contradictory requirements
- missing user information
- malformed inputs

### Benchmark Reports

Generate evaluation reports after major changes.

Report:

- benchmark results
- decision distribution
- regression detection
- notable failures

## Done When

- benchmark dataset exists
- evaluation can run automatically
- all outputs are schema validated
- workflow execution is observable
- prompt changes are measurable
- regressions are detectable before deployment

