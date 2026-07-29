import pytest

from app.evaluation import (
    fallback_rate,
    load_match_cases,
    run_profile_matching_evaluation,
    score_average,
)


def test_deterministic_eval():
    report = run_profile_matching_evaluation(runtime_version="v1", progress=False)
    assert len(report.cases) == len(load_match_cases()) == 7
    assert fallback_rate(report) == 0.0
    assert 0.0 <= score_average(report, "macro_f1") <= 1.0


@pytest.mark.llm
def test_llm_v3():
    print("\n[profile_matching] LLM v3 eval — 7 cases", flush=True)
    report = run_profile_matching_evaluation(runtime_version="v3", progress=True)
    report.print()
    print(
        f"[profile_matching] macro_f1={score_average(report, 'macro_f1'):.3f} "
        f"required_skills_matched_f1="
        f"{score_average(report, 'required_skills_matched_f1'):.3f} "
        f"fallback_rate={fallback_rate(report):.3f}",
        flush=True,
    )
    assert fallback_rate(report) == 0.0
    assert score_average(report, "macro_f1") >= 0.8
    assert score_average(report, "required_skills_matched_f1") >= 0.7
