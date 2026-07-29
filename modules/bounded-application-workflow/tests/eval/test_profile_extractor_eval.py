import pytest

from app.evaluation import (
    fallback_rate,
    load_profile_cases,
    macro_f1,
    run_profile_extraction_evaluation,
)


def test_deterministic_eval():
    report = run_profile_extraction_evaluation(runtime_version="v1", progress=False)
    assert len(report.cases) == len(load_profile_cases()) == 7
    assert fallback_rate(report) == 0.0
    assert 0.0 <= macro_f1(report) <= 1.0


@pytest.mark.llm
def test_llm_v3():
    print("\n[profile_extraction] LLM v3 eval — 7 cases", flush=True)
    report = run_profile_extraction_evaluation(runtime_version="v3", progress=True)
    report.print()
    print(
        f"[profile_extraction] macro_f1={macro_f1(report):.3f} "
        f"fallback_rate={fallback_rate(report):.3f}",
        flush=True,
    )
    assert fallback_rate(report) == 0.0
    assert macro_f1(report) >= 0.8
