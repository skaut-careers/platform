import pytest

from app.evaluation import (
    fallback_rate,
    load_signal_cases,
    macro_f1,
    run_signal_evaluation,
)


def test_deterministic_eval():
    report = run_signal_evaluation(runtime_version="v1", progress=False)
    assert len(report.cases) == len(load_signal_cases()) == 7
    assert fallback_rate(report) == 0.0
    # Harder goldens intentionally leave headroom vs regex baselines.
    assert 0.5 <= macro_f1(report) < 0.85


@pytest.mark.llm
def test_llm_v3():
    print("\n[signal_extraction] LLM v3 eval — 7 cases", flush=True)
    report = run_signal_evaluation(runtime_version="v3", progress=True)
    report.print()
    print(
        f"[signal_extraction] macro_f1={macro_f1(report):.3f} "
        f"fallback_rate={fallback_rate(report):.3f}",
        flush=True,
    )
    assert fallback_rate(report) == 0.0
    assert macro_f1(report) >= 0.7
