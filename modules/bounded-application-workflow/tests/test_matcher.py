import pytest

from app.services.matcher import match_profile_to_job
from tests.fixture_helpers import workflow_input as load_workflow_input


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
    workflow = load_workflow_input(fixture_name)
    result = match_profile_to_job(workflow.user_profile, workflow.job_description)

    assert min_score <= result.score <= max_score
    assert result.role_aligned is role_aligned


def test_strong_match_covers_core_required_skills():
    workflow = load_workflow_input("strong_match.json")
    result = match_profile_to_job(workflow.user_profile, workflow.job_description)

    assert "Python" in result.required_skills_matched
    assert "LLM applications" in result.required_skills_matched
    assert len(result.required_skills_missing) <= 3


def test_weak_match_misses_frontend_stack():
    workflow = load_workflow_input("weak_match.json")
    result = match_profile_to_job(workflow.user_profile, workflow.job_description)

    assert result.required_skills_matched == []
    assert len(result.required_skills_missing) == len(
        workflow.job_description.required_skills
    )
    assert "React" in result.required_skills_missing


def test_ambiguous_match_is_partial_not_empty():
    workflow = load_workflow_input("ambiguous_match.json")
    result = match_profile_to_job(workflow.user_profile, workflow.job_description)

    assert result.required_skills_matched
    assert result.required_skills_missing
    assert result.reasons
    assert result.risks
