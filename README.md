# Liman

> Navigate your professional life with clarity.

Liman is a career platform designed to support people throughout their professional lives — across opportunities, applications, learning, growth, transitions, and long-term direction.

---

## Current Module

# Bounded Application Workflow

A workflow for evaluating opportunities, preparing tailored applications, and keeping the human in control of final application decisions.

The workflow prioritizes high-value opportunities while keeping execution bounded, reviewable, and human-controlled.

---

## Core Principles

- bounded autonomy
- human-in-the-loop execution
- expected-value decision making
- policy-gated actions
- reviewable runtime behavior
- uncertainty-aware orchestration

---

## Architecture

intake
  → ranking
  → bounded decision runtime
  → execution
  → human submission

Decision loop:

research
  → prepare
  → queue
  → skip
  → escalate

Learning loop:

outcomes
  → ranking updates
  → threshold adaptation
  → retry policy tuning

---

## Example Runtime Flow

120 jobs
→ 18 filtered
→ 6 shortlisted
→ 2 prepared
→ 1 escalated
→ 1 submitted

---

## Real Execution Pipeline

Input:

- CV
- job description
- preferences

Output:

```
{
  "score": 0.82,
  "decision": "prepare",
  "missing_signals": [
    "production inference",
    "LLM evaluation"
  ],
  "risks": [
    "domain mismatch"
  ],
  "suggested_angle": "AI systems + product ownership"
}
```

---

## Repository Structure

```txt
docs/ 
modules/  
  bounded-application-workflow/
```

---

## Milestone 1 — Bounded Application Workflow MVP

Goal:

Evaluate opportunities against a user profile and decide whether the system should:

- prepare
- queue
- skip
- escalate

Current implementation focus:

1. input/output contract
2. job description parsing
3. profile matching
4. decision policy
5. runtime API
6. tests and CI

---

## Long-Term Direction

Liman is being designed as a modular career platform.

The Bounded Application Workflow is the first system module inside a broader professional decision and execution environment.
