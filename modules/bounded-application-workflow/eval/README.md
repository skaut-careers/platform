# Agent Evaluation

Human-curated golden datasets, one directory per LLM-backed agent:

| Dataset | Directory | Case JSON | Metric |
|---------|-----------|-----------|--------|
| Job signal extractor | [`job_signal_extraction/`](job_signal_extraction/) | `job_description_text`, `expected_signals` | set-based P/R/F1 per signal field + macro F1 |
| Profile extractor | [`profile_extraction/`](profile_extraction/) | `profile_text`, `expected_profile` | set-based F1 per profile field + macro F1 |
| Match decision | [`match_decision/`](match_decision/) | `user_profile`, `job_signals`, `expected` | decision accuracy + score band + work/location/seniority flags + required/preferred/experience/missing_information set F1 |

Input keys match the `WorkflowInput` field names so a golden case reads the same as a product request.

Each agent has exactly **eight** golden cases.

Signal goldens are intentionally hard for regex baselines: prose/numbered skills, soft remote/hybrid cues, PagerDuty→on-call, risk without the word “vague”, and decade-tenure seniority. Prefer empty lists when evidence is weak.

Profile goldens are pasted CVs, not labelled form fields. Structured Skills sections are the regex baseline; harder cases bury skills in prose, filler words (`some Postgres`), slash-separated stacks, and production cues in experience bullets.

Matching goldens stress semantic bridges the deterministic matcher misses: skill aliases (`k8s`/`GCP`/`ML`), NYC↔New York place aliasing, `wfh`↔remote preferences, plus one severe seniority negative.

Each case also carries optional `id`, `description`, `tags`. Datasets load as
[Pydantic Evals](https://pydantic.dev/docs/ai/evals/) `Dataset`s with a matching evaluator.

## Run

```bash
poetry run pytest eval/                 # golden datasets (v1 deterministic agents)
poetry run pytest -m llm -s             # live LLM; prints Rich report + macro_f1 (-s recommended)
```

Default `poetry run pytest` excludes `@pytest.mark.llm` tests.

With `LOGFIRE_TOKEN` in `.env`, experiments appear in the Logfire Evals UI.

## Layout

| Module | Role |
|--------|------|
| `app/evaluation/dataset.py` | JSON → `Case` / `Dataset` for every agent |
| `app/evaluation/metrics.py` | set precision / recall / F1 (`score_field`, `score_job_signals`, `score_profile`, `score_match_decision`) |
| `app/evaluation/evaluators.py` | Pydantic Evals evaluators |
| `app/evaluation/runner.py` | `run_*_evaluation()` → `EvaluationReport` |
| `app/evaluation/report.py` | shared harness + report helpers |

Runtime configs: `v1` deterministic · `v2` LLM+prompt v1.
