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
    result = _match("weak_match.json")

    assert result.required_skills_matched == []
    assert set(result.required_skills_missing) == {
        "React",
        "TypeScript",
        "CSS",
        "frontend architecture",
        "design systems",
    }


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


def test_match_without_target_roles_skips_role_alignment_risk():
    profile = UserProfile(name="Ana", skills=["Python"], seniority="senior")
    job = JobDescription(
        title="Platform Engineer",
        description="Build backend services.\n\n- Python\n- Kubernetes",
        seniority="senior",
    )
    signals = JobSignals(
        required_skills=["Python", "Kubernetes"],
        seniority_signals=["senior"],
    )

    result = match_profile_to_job(profile, job, signals)

    assert not result.role_aligned
    assert not any("target role" in risk.lower() for risk in result.risks)
    assert not any("target role" in reason.lower() for reason in result.reasons)


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

    assert result.severe_seniority_mismatch
    assert not any(
        "Seniority meets job expectations" in reason for reason in result.reasons
    )
    assert any(
        "exceeds job expectations by more than one level" in risk
        for risk in result.risks
    )


def test_underqualified_profile_flags_severe_seniority_gap():
    profile = UserProfile(name="Ana", seniority="junior")
    job = JobDescription(
        title="Principal Engineer",
        description="Lead platform architecture.\n\n- Python",
        seniority="principal",
    )
    signals = JobSignals(
        required_skills=["Python"],
        seniority_signals=["principal"],
    )

    result = match_profile_to_job(profile, job, signals)

    assert result.severe_seniority_mismatch
    assert any(
        "more than one level below job expectations" in risk for risk in result.risks
    )


def test_production_expectations_align_when_profile_documents_experience():
    profile = UserProfile(
        name="Ana",
        production_experience=["on-call rotation", "incident response"],
    )
    signals = JobSignals(
        production_expectations=["on-call rotation", "observability"],
    )

    result = match_profile_to_job(
        profile,
        JobDescription(title="Platform Engineer", description="Operate services."),
        signals,
    )

    assert result.production_expectations_matched == ["on-call rotation"]
    assert result.production_expectations_missing == ["observability"]
    assert any(
        "Matched 1 of 2 production expectations" in reason
        for reason in result.reasons
    )
    assert not any(
        "Missing production experience for:" in risk for risk in result.risks
    )


def test_production_expectations_flags_missing_experience():
    profile = UserProfile(
        name="Ana",
        seniority="senior",
        production_experience=["incident response"],
    )
    signals = JobSignals(production_expectations=["on-call rotation"])

    result = match_profile_to_job(
        profile,
        JobDescription(title="Platform Engineer", description="Operate services."),
        signals,
    )

    assert result.production_expectations_matched == []
    assert result.production_expectations_missing == ["on-call rotation"]
    assert any(
        "Missing production experience for: on-call rotation" in risk
        for risk in result.risks
    )


def test_production_gap_risk_when_majority_missing():
    profile = UserProfile(
        name="Ana",
        production_experience=["on-call rotation"],
    )
    signals = JobSignals(
        production_expectations=[
            "on-call rotation",
            "observability",
            "incident response",
        ],
    )

    result = match_profile_to_job(
        profile,
        JobDescription(title="Platform Engineer", description="Operate services."),
        signals,
    )

    assert len(result.production_expectations_missing) == 2
    assert any(
        "Missing production experience for:" in risk for risk in result.risks
    )


def test_production_gap_lowers_score():
    job = JobDescription(title="Platform Engineer", description="Operate services.")
    aligned = UserProfile(
        name="Ana",
        skills=["Python"],
        production_experience=["on-call rotation", "observability"],
    )
    partial = UserProfile(
        name="Ana",
        skills=["Python"],
        production_experience=["on-call rotation"],
    )
    signals = JobSignals(
        required_skills=["Python"],
        production_expectations=["on-call rotation", "observability"],
    )

    aligned_result = match_profile_to_job(aligned, job, signals)
    partial_result = match_profile_to_job(partial, job, signals)

    assert aligned_result.score > partial_result.score


def test_seniority_gap_lowers_score():
    job = JobDescription(
        title="Senior Engineer",
        description="Build features.\n\n- Python",
        seniority="senior",
    )
    signals = JobSignals(required_skills=["Python"], seniority_signals=["senior"])
    aligned = UserProfile(name="Ana", skills=["Python"], seniority="senior")
    gap = UserProfile(name="Ana", skills=["Python"], seniority="mid-level")

    aligned_result = match_profile_to_job(aligned, job, signals)
    gap_result = match_profile_to_job(gap, job, signals)

    assert aligned_result.score > gap_result.score


def test_production_expectations_skipped_when_job_has_none():
    profile = UserProfile(name="Ana", production_experience=["on-call rotation"])
    signals = JobSignals(required_skills=["Python"])

    result = match_profile_to_job(
        profile,
        JobDescription(title="Engineer", description="- Python"),
        signals,
    )

    assert result.production_expectations_matched == []
    assert result.production_expectations_missing == []
    assert not any("production" in reason.lower() for reason in result.reasons)
    assert not any("production" in risk.lower() for risk in result.risks)
