# Agent Evaluation

Human-curated golden datasets, one directory per LLM-backed agent:

| Dataset | Directory | Case JSON | Metric |
|---------|-----------|-----------|--------|
| Signal extractor | [`signal_extraction/`](signal_extraction/) | `job_description`, `expected_signals` | set-based P/R/F1 per signal field + macro F1 |
| Profile extractor | [`profile_extraction/`](profile_extraction/) | `raw_text`, `expected_profile` | set-based F1 per profile field + macro F1 |
| Profile matcher | [`profile_matching/`](profile_matching/) | `user_profile`, `job_description`, `signals`, `expected` | score band + role/work/location/seniority flags + required/preferred/production set F1 |
| Decision policy | [`decision_rules/`](decision_rules/) | `match`, `signals`, `expected` | exact decision + score band + reasons/risks/missing_information set F1 |

Each agent has exactly **seven** golden cases.

Signal goldens are intentionally hard for regex baselines: prose/numbered skills, soft remote/hybrid cues, PagerDuty→on-call, risk without the word “vague”, and decade-tenure seniority. Prefer empty lists when evidence is weak.

Matching goldens stress semantic bridges the deterministic matcher misses: skill aliases (`k8s`/`GCP`/`ML`), Frontend↔UI role titles, NYC↔New York place aliasing, `wfh`↔remote preferences, plus one severe seniority negative.

Decision goldens cover score thresholds (`prepare` / `queue` / `escalate` / `skip`) plus guardrails: risk indicators escalate a prepare-band match, severe seniority hard-skips, and unusable/gibberish postings hard-pass at score `0.0`.

Each case also carries optional `id`, `description`, `tags`. Datasets load as
[Pydantic Evals](https://pydantic.dev/docs/ai/evals/) `Dataset`s with a matching evaluator.

## Run

```bash
poetry run pytest tests/eval/           # golden datasets (v1 deterministic agents)
poetry run pytest -m llm -s             # live LLM; prints Rich report + macro_f1 (-s recommended)
```

Default `poetry run pytest` excludes `@pytest.mark.llm` tests.

With `LOGFIRE_TOKEN` in `.env`, experiments appear in the Logfire Evals UI.

## Layout

| Module | Role |
|--------|------|
| `app/evaluation/dataset.py` | JSON → `Case` / `Dataset` for every agent |
| `app/evaluation/metrics.py` | set precision / recall / F1 (`score_field`, `score_signals`, `score_profile`) |
| `app/evaluation/evaluators.py` | Pydantic Evals evaluators |
| `app/evaluation/runner.py` | `run_*_evaluation()` → `EvaluationReport` |
| `app/evaluation/report.py` | shared harness + report helpers |

Runtime configs: `v1` deterministic · `v2` LLM+prompt v1 · `v3` LLM+prompt v2.
