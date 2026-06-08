import pytest

from app.domain.job_signals import JobSignals
from app.domain.models import JobDescription, UserProfile
from app.agents import extract_job_signals, match_profile_to_job
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
def test_match_fixture_score_and_role_alignment(
    fixture_name: str, min_score: float, max_score: float, role_aligned: bool
):
    result = _match(fixture_name)

    assert min_score <= result.score <= max_score
    assert result.role_aligned is role_aligned


def test_weak_match_partitions_required_skills():
    result = _match("weak_match.json")

    assert result.required_skills_matched == []
    assert set(result.required_skills_missing) == {
        "React",
        "TypeScript",
        "CSS",
        "frontend architecture",
        "design systems",
    }


def test_ambiguous_match_has_partial_skill_coverage():
    result = _match("ambiguous_match.json")

    assert result.required_skills_matched
    assert result.required_skills_missing


def test_role_misalignment_without_target_roles():
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


def test_weak_match_flags_one_level_seniority_gap():
    result = _match("weak_match.json")

    assert any("Job expects senior" in risk for risk in result.risks)


def test_severe_seniority_mismatch_when_overqualified():
    profile = UserProfile(name="Ana", seniority="staff")
    job = JobDescription(
        title="Junior Engineer",
        description="Build features.\n\n- Python",
        seniority="junior",
    )
    signals = JobSignals(required_skills=["Python"], seniority_signals=["junior"])

    result = match_profile_to_job(profile, job, signals)

    assert result.severe_seniority_mismatch


def test_severe_seniority_mismatch_when_underqualified():
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


def test_production_expectations_partition():
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


def test_production_gap_surfaces_risk_when_material():
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

    assert any(
        "Missing production experience for:" in risk for risk in result.risks
    )


def test_production_alignment_affects_score():
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


def test_seniority_alignment_affects_score():
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


def test_production_expectations_ignored_when_absent():
    profile = UserProfile(name="Ana", production_experience=["on-call rotation"])
    signals = JobSignals(required_skills=["Python"])

    result = match_profile_to_job(
        profile,
        JobDescription(title="Engineer", description="- Python"),
        signals,
    )

    assert result.production_expectations_matched == []
    assert result.production_expectations_missing == []
