import pytest

from app.agents.contracts import SignalExtractorInput
from app.agents.signal_extraction import DefaultSignalExtractor
from app.domain.job_signals import SIGNAL_FIELDS
from app.evaluation import (
    fallback_rate,
    load_cases,
    load_dataset,
    macro_f1,
    run_evaluation,
    score_signals,
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
    cases = load_cases()
    dataset = load_dataset(cases=cases)
    assert len(cases) >= 7
    assert dataset.name == "signal_extractor_golden"
    assert len(dataset.evaluators) == 1
    assert all(
        case.name and case.inputs.title and case.expected_output is not None
        for case in cases
    )


def test_score_signals_set_metrics():
    case = load_cases()[0]
    assert case.expected_output is not None
    predicted = DefaultSignalExtractor().run(
        SignalExtractorInput(job_description=case.inputs)
    ).signals
    scored = score_signals(case.expected_output, predicted)
    assert 0.0 <= scored.macro_f1 <= 1.0
    assert scored.fields


def test_deterministic_eval_via_pydantic_evals():
    report = run_evaluation(runtime_version="v1", progress=False)
    assert len(report.cases) >= 7
    assert fallback_rate(report) == 0.0
    assert 0.65 <= macro_f1(report) <= 0.75


def _assert_llm_backed(report) -> None:
    rate = fallback_rate(report)
    assert rate == 0.0, f"LLM eval used deterministic fallback on {rate:.0%} of cases"
    assert all(not case.attributes.get("used_fallback") for case in report.cases)


def _field_f1(report, field: str) -> float:
    averages = report.averages()
    if averages is None:
        return 0.0
    return float(averages.scores.get(f"{field}_f1", 0.0))


def _print_comparison(baseline, candidate) -> None:
    base_macro = macro_f1(baseline)
    cand_macro = macro_f1(candidate)
    print(
        f"\nprompt_v1 macro_f1={base_macro:.3f} -> "
        f"prompt_v2 macro_f1={cand_macro:.3f} "
        f"(delta {cand_macro - base_macro:+.3f})"
    )
    print("field F1 (prompt_v1 -> prompt_v2):")
    for field in SIGNAL_FIELDS:
        base = _field_f1(baseline, field)
        cand = _field_f1(candidate, field)
        print(f"  {field:<24} {base:.3f} -> {cand:.3f} (delta {cand - base:+.3f})")


@pytest.mark.llm
def test_llm_signal_extractor_v3_against_golden_dataset(openai_api_key):
    report = run_evaluation(runtime_version="v3", progress=True)
    report.print()
    _assert_llm_backed(report)
    assert macro_f1(report) >= MIN_LLM_MACRO_F1


@pytest.mark.llm
def test_llm_prompt_v2_vs_v1_comparison(openai_api_key):
    baseline = run_evaluation(label="prompt_v1", runtime_version="v2", progress=True)
    candidate = run_evaluation(label="prompt_v2", runtime_version="v3", progress=True)
    baseline.print()
    candidate.print()
    _assert_llm_backed(baseline)
    _assert_llm_backed(candidate)
    _print_comparison(baseline, candidate)
    assert macro_f1(candidate) >= MIN_LLM_MACRO_F1
