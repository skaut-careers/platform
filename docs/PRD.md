# PRD — Bounded Application Workflow

## Overview

The Bounded Application Workflow module evaluates whether a professional opportunity is worth pursuing based on structured signals from a user's background and a job description.

The goal of the module is not to automate applications at scale, but to support deliberate, high-quality career decisions through bounded evaluation and human review.

This module represents the first executable component of the broader Limen platform.

---

# Problem

Modern job searching is noisy, fragmented, and cognitively expensive.

Most existing systems optimize for:

- application volume,
- automation speed,
- engagement metrics,
- keyword matching.

They rarely help users answer more important questions:

- Is this opportunity actually aligned with my background?
- What signals are missing?
- Is this role realistically attainable?
- Is it worth investing time and emotional energy into?
- Should this opportunity be pursued now, later, or not at all?

The result is decision fatigue, low-quality applications, and poor alignment between people and opportunities.

---

# Target User

Initial target users:

- technical professionals,
- AI engineers,
- researchers transitioning into industry,
- multidisciplinary candidates with non-linear careers.

The system is designed for users who value:

- quality over quantity,
- strategic applications,
- deliberate career navigation,
- bounded automation.

---

# MVP Goal

Build a working evaluation engine that:

1. accepts a user profile and job description,
2. extracts relevant opportunity signals,
3. scores profile alignment,
4. applies a bounded decision policy,
5. returns a structured recommendation.

The MVP focuses on evaluation only.

It does not:

- apply to jobs,
- send emails,
- automate browser workflows,
- optimize resumes,
- perform autonomous actions.

## Architectural Direction

The broader Limen system is designed toward bounded agentic workflows rather than isolated prompt-response interactions.

The MVP intentionally starts with deterministic evaluation policies and explicit system boundaries before introducing more advanced orchestration, memory, and tool-using agents in future iterations.

---

# Inputs

## User Profile

Structured or semi-structured profile information.

Example fields:

- experience summary,
- technical skills,
- research background,
- production experience,
- preferred domains,
- location constraints,
- seniority indicators.

## Job Description

Raw job posting text.

The system extracts:

- required skills,
- preferred skills,
- domain alignment,
- seniority expectations,
- execution signals,
- production requirements,
- ambiguity or risk indicators.

---

# Outputs

The module returns a structured evaluation object.

Example:

```
json {   
    "score": 0.82,   
    "decision": "prepare",   
    "missing_signals": [ "large-scale production inference"],
    "risks": ["high infrastructure ownership expectations"],   
    "reasoning_summary": "Strong AI systems alignment with partial production gaps."
    } 
```

---

# Decision Categories

## prepare

High alignment. Recommended for active pursuit.

## queue

Potential fit, but not currently a priority.

## escalate

Requires human review due to ambiguity or conflicting signals.

## skip

Low alignment or poor strategic fit.

---

# Decision Policy

Initial MVP thresholds:


| Score Range | Decision |
| ----------- | -------- |
| >= 0.75     | prepare  |
| >= 0.55     | queue    |
| >= 0.35     | escalate |
| < 0.35      | skip     |


The policy is intentionally simple in V1.

Future versions incorporate:

- confidence estimation,
- uncertainty handling,
- weighted signals,
- user-specific preferences,
- memory systems.

---

# Non-Goals

The MVP does not attempt to:

- replace human judgment,
- maximize application count,
- fully automate career decisions,
- autonomously submit applications,
- scrape job platforms at scale,
- simulate a general autonomous agent.

---

# Technical Scope

Initial implementation includes:

- Python backend,
- FastAPI service,
- deterministic decision policy,
- modular domain layer,
- test coverage,
- CI pipeline,
- example inputs and outputs.

LLM integration is optional and not required for V1.

---

# Success Criteria

The MVP is successful if it:

- produces deterministic structured evaluations,
- exposes a working API endpoint,
- passes automated tests,
- can be run locally by external reviewers,
- demonstrates clear system boundaries,
- serves as a foundation for future modules.

---

# Open Questions

- How should uncertainty be represented?
- How should user preferences influence scoring?
- Which signals deserve the highest weighting?
- What level of explainability should future versions expose?
- Should future policies become adaptive or remain bounded?

---

