import pytest

from app.domain.job_signals import JobSignals
from app.domain.models import JobDescription, ProfileMatchResult, UserProfile
from app.services.extractor import extract_job_signals
from app.services.matcher import match_profile_to_job
from tests.fixture_helpers import workflow_input as load_workflow_input


def _match(fixture_name: str):
    workflow = load_workflow_input(fixture_name)
    signals = extract_job_signals(workflow.job_description)
    return match_profile_to_job(
        workflow.user_profile, workflow.job_description, signals
    )


@pytest.mark.parametrize(
    "fixture_name,min_score,max_score,role_aligned",
    [
        ("strong_match.json", 0.5, 1.0, True),
        ("weak_match.json", 0.0, 0.35, False),
        ("ambiguous_match.json", 0.35, 0.75, True),
    ],
)
def test_match_profile_to_job_fixture_ranges(
    fixture_name: str, min_score: float, max_score: float, role_aligned: bool
):
    result = _match(fixture_name)

    assert min_score <= result.score <= max_score
    assert result.role_aligned is role_aligned


def test_strong_match_covers_core_required_skills():
    result = _match("strong_match.json")

    assert "Python" in result.required_skills_matched
    assert "LLM applications" in result.required_skills_matched
    assert len(result.required_skills_missing) <= 3


def test_weak_match_misses_frontend_stack():
    workflow = load_workflow_input("weak_match.json")
    signals = extract_job_signals(workflow.job_description)
    result = match_profile_to_job(
        workflow.user_profile, workflow.job_description, signals
    )

    assert result.required_skills_matched == []
    assert len(result.required_skills_missing) == len(signals.required_skills)
    assert "React" in result.required_skills_missing


def test_ambiguous_match_is_partial_not_empty():
    result = _match("ambiguous_match.json")

    assert result.required_skills_matched
    assert result.required_skills_missing
    assert result.reasons
    assert result.risks


def test_strong_match_seniority_aligns_with_job():
    result = _match("strong_match.json")

    assert any(
        "Seniority meets job expectations" in reason for reason in result.reasons
    )


def test_weak_match_flags_seniority_gap():
    result = _match("weak_match.json")

    assert any(
        "Job expects senior" in risk for risk in result.risks
    )


def test_overqualified_profile_flags_poor_seniority_fit():
    profile = UserProfile(name="Ana", seniority="staff")
    job = JobDescription(
        title="Junior Engineer",
        description="Build features.\n\n- Python",
        seniority="junior",
    )
    signals = JobSignals(required_skills=["Python"], seniority_signals=["junior"])

    result = match_profile_to_job(profile, job, signals)

    assert not any(
        "Seniority meets job expectations" in reason for reason in result.reasons
    )
    assert any(
        "exceeds job expectations by more than one level" in risk
        for risk in result.risks
    )
