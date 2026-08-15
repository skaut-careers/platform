import pytest
from pydantic_evals.reporting import EvaluationReport

from app.domain.models import SIGNAL_FIELDS
from app.evaluation import (
    MATCH_DECISION_LIST_FIELDS,
    PROFILE_SCORED_FIELDS,
    fallback_rate,
    load_match_cases,
    load_profile_cases,
    load_signal_cases,
    run_profile_extraction_evaluation,
    run_match_decision_evaluation,
    run_job_signal_evaluation,
    score_average,
)

JOB_SIGNAL_SCORE_KEYS = (
    "macro_f1",
    *(f"{field}_f1" for field in SIGNAL_FIELDS),
)
PROFILE_SCORE_KEYS = (
    "macro_f1",
    *(f"{field}_f1" for field in PROFILE_SCORED_FIELDS),
)
MATCH_DECISION_SCORE_KEYS = (
    "macro_f1",
    "decision_accuracy",
    "score_in_range",
    "work_arrangement_aligned_correct",
    "location_aligned_correct",
    "severe_seniority_mismatch_correct",
    *(f"{field}_f1" for field in MATCH_DECISION_LIST_FIELDS),
)


def _assert_scores_in_unit(report: EvaluationReport, keys: tuple[str, ...]) -> None:
    for key in keys:
        assert 0.0 <= score_average(report, key) <= 1.0, key


def _format_scores(report: EvaluationReport, keys: tuple[str, ...]) -> str:
    return " ".join(f"{key}={score_average(report, key):.3f}" for key in keys)


def test_job_signal_extraction_deterministic():
    report = run_job_signal_evaluation(runtime_version="v1", progress=False)
    assert len(report.cases) == len(load_signal_cases()) == 8
    assert fallback_rate(report) == 0.0
    _assert_scores_in_unit(report, JOB_SIGNAL_SCORE_KEYS)


def test_profile_extraction_deterministic():
    report = run_profile_extraction_evaluation(runtime_version="v1", progress=False)
    assert len(report.cases) == len(load_profile_cases()) == 8
    assert fallback_rate(report) == 0.0
    _assert_scores_in_unit(report, PROFILE_SCORE_KEYS)


def test_match_decision_deterministic():
    report = run_match_decision_evaluation(runtime_version="v1", progress=False)
    assert len(report.cases) == len(load_match_cases()) == 8
    assert fallback_rate(report) == 0.0
    _assert_scores_in_unit(report, MATCH_DECISION_SCORE_KEYS)


@pytest.mark.llm
def test_job_signal_extraction_llm_v2():
    print("\n[job_signal_extraction] LLM v2 eval — 8 cases", flush=True)
    report = run_job_signal_evaluation(runtime_version="v2", progress=True)
    report.print()
    print(
        f"[job_signal_extraction] {_format_scores(report, JOB_SIGNAL_SCORE_KEYS)} "
        f"fallback_rate={fallback_rate(report):.3f}",
        flush=True,
    )
    assert fallback_rate(report) == 0.0
    _assert_scores_in_unit(report, JOB_SIGNAL_SCORE_KEYS)
    assert score_average(report, "macro_f1") >= 0.7


@pytest.mark.llm
def test_profile_extraction_llm_v2():
    print("\n[profile_extraction] LLM v2 eval — 8 cases", flush=True)
    report = run_profile_extraction_evaluation(runtime_version="v2", progress=True)
    report.print()
    print(
        f"[profile_extraction] {_format_scores(report, PROFILE_SCORE_KEYS)} "
        f"fallback_rate={fallback_rate(report):.3f}",
        flush=True,
    )
    assert fallback_rate(report) == 0.0
    _assert_scores_in_unit(report, PROFILE_SCORE_KEYS)
    assert score_average(report, "macro_f1") >= 0.8


@pytest.mark.llm
def test_match_decision_llm_v2():
    print("\n[match_decision] LLM v2 eval — 8 cases", flush=True)
    report = run_match_decision_evaluation(runtime_version="v2", progress=True)
    report.print()
    print(
        f"[match_decision] {_format_scores(report, MATCH_DECISION_SCORE_KEYS)} "
        f"fallback_rate={fallback_rate(report):.3f}",
        flush=True,
    )
    assert fallback_rate(report) == 0.0
    _assert_scores_in_unit(report, MATCH_DECISION_SCORE_KEYS)
    assert score_average(report, "decision_accuracy") >= 0.85
    assert score_average(report, "macro_f1") >= 0.8
    assert score_average(report, "required_skills_matched_f1") >= 0.7
