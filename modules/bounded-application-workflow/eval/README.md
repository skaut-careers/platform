# Signal Extractor Evaluation

Golden dataset in [`dataset/`](dataset/) — human-curated `expected_signals` per job posting.

Each case JSON: `id`, `job_description`, `expected_signals` (+ optional `description`, `tags`).

Loaded as a [Pydantic Evals](https://pydantic.dev/docs/ai/evals/) `Dataset` with `SignalExtractionEvaluator` (set-based precision / recall / F1).

## Run

```bash
poetry run pytest tests/eval/           # dataset load + deterministic parity
poetry run pytest -m llm -s             # live LLM eval (OPENAI_API_KEY in .env)
```

Default `poetry run pytest` excludes `@pytest.mark.llm` tests.

With `LOGFIRE_TOKEN` in `.env`, experiments appear in the Logfire Evals UI.

## Layout

| Module | Role |
|--------|------|
| `app/evaluation/dataset.py` | JSON → `Case` / `Dataset` |
| `app/evaluation/metrics.py` | Field precision / recall / F1 |
| `app/evaluation/evaluators.py` | Pydantic Evals evaluator |
| `app/evaluation/runner.py` | `run_evaluation()` → `EvaluationReport` |

Runtime configs: `v1` deterministic · `v2` LLM+prompt v1 · `v3` LLM+prompt v2.
