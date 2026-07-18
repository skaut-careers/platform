import pytest

from app.evaluation import (
    compare_runs,
    format_comparison_report,
    format_report,
    load_eval_cases,
    run_evaluation,
)
from app.local_env import get_local_env

# Floor for a live OpenAI run. Target: beat deterministic (~0.69 macro-F1).
MIN_LLM_MACRO_F1 = 0.7


@pytest.fixture
def openai_api_key():
    key = get_local_env("OPENAI_API_KEY")
    if not key:
        pytest.skip("OPENAI_API_KEY not set in .env")
    return key


def test_golden_dataset_loads():
    cases = load_eval_cases()
    assert len(cases) >= 7
    assert all(case.id and case.job_description.title for case in cases)


def _assert_llm_backed(run) -> None:
    assert run.aggregate.fallback_count == 0, (
        f"LLM eval used deterministic fallback on "
        f"{run.aggregate.fallback_count}/{run.aggregate.case_count} cases:\n"
        f"{format_report(run)}"
    )
    assert all(not result.used_fallback for result in run.case_results)


@pytest.mark.llm
def test_llm_signal_extractor_v4_against_golden_dataset(openai_api_key):
    run = run_evaluation(runtime_version="v4", progress=True)
    report = format_report(run)
    print(f"\n{report}")
    _assert_llm_backed(run)
    assert run.aggregate.macro_f1 >= MIN_LLM_MACRO_F1, report


@pytest.mark.llm
def test_llm_prompt_v3_vs_v2_comparison(openai_api_key):
    baseline = run_evaluation(label="prompt_v2", runtime_version="v3", progress=True)
    candidate = run_evaluation(label="prompt_v3", runtime_version="v4", progress=True)
    comparison = compare_runs(baseline, candidate)
    report = format_comparison_report(baseline, candidate, comparison)
    print(f"\n{report}")
    _assert_llm_backed(baseline)
    _assert_llm_backed(candidate)
    assert candidate.aggregate.macro_f1 >= MIN_LLM_MACRO_F1, report
