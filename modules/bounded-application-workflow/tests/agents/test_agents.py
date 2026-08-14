import pytest
from pydantic_ai.exceptions import ModelHTTPError

from app.agents.decision_rules.deterministic import (
    build_workflow_decision,
    decision_from_score,
    decision_from_signals,
)
from app.agents.profile_extraction.deterministic import extract_user_profile
from app.agents.profile_matching.deterministic import match_profile_to_job
from app.agents.signal_extraction import LLMSignalExtractor
from app.agents.signal_extraction.deterministic import extract_job_signals
from app.domain.models import (
    DecisionType,
    JobSignals,
    ProfileMatchResult,
    UserProfile,
    WorkflowDecision,
)
from app.runtime import ExecutionStatus, RuntimeConfig
from tests.conftest import (
    DECISION_FIXTURES,
    MATCH_FIXTURES,
    PROFILE_EXTRACTION_FIXTURES,
    SIGNAL_EXTRACTION_FIXTURES,
    SIGNAL_FIELDS,
    RecordingSignalModel,
    load_decision_fixture,
    load_match_fixture,
    load_profile_fixture,
    load_signal_fixture,
    sample_signal_extractor_input,
    signals_test_model,
)


@pytest.mark.parametrize("fixture_name", MATCH_FIXTURES)
def test_match_profile_from_fixture(fixture_name):
    case = load_match_fixture(fixture_name)
    result = match_profile_to_job(
        UserProfile(**case["user_profile"]),
        JobSignals(**case["job_signals"]),
    )
    assert result == ProfileMatchResult(**case["expected_match"])


@pytest.mark.parametrize(
    "prefs,arrangements,location,places,expect_work,expect_location",
    [
        (["remote"], ["remote"], "Lisbon", [], True, True),
        (["remote"], ["onsite"], "Lisbon", ["Berlin"], False, False),
        (["onsite"], ["onsite"], "Berlin", ["Berlin"], True, True),
    ],
)
def test_work_and_location_alignment(
    prefs, arrangements, location, places, expect_work, expect_location
):
    result = match_profile_to_job(
        UserProfile(
            skills=["Python"],
            location=location,
            work_preferences=prefs,
        ),
        JobSignals(
            required_skills=["Python"],
            work_arrangements=arrangements,
            location_signals=places,
        ),
    )
    assert result.work_arrangement_aligned is expect_work
    assert result.location_aligned is expect_location


def test_onsite_location_mismatch_lowers_score():
    job_signals = JobSignals(
        required_skills=["Python"],
        work_arrangements=["onsite"],
        location_signals=["Berlin"],
    )
    aligned = match_profile_to_job(
        UserProfile(
            skills=["Python"],
            location="Berlin",
            work_preferences=["onsite"],
        ),
        job_signals,
    )
    mismatched = match_profile_to_job(
        UserProfile(
            skills=["Python"],
            location="Lisbon",
            work_preferences=["onsite"],
        ),
        job_signals,
    )
    assert mismatched.score < aligned.score
    assert any("On-site role with incompatible locations" in r for r in mismatched.risks)


@pytest.mark.parametrize("fixture_name", SIGNAL_EXTRACTION_FIXTURES)
def test_extract_signals_from_fixture(fixture_name):
    case = load_signal_fixture(fixture_name)
    job_signals = extract_job_signals(case["job_description_text"])
    expected = case["expected_signals"]
    for field in SIGNAL_FIELDS:
        assert getattr(job_signals, field) == expected[field]


def test_extract_skills_normalization_and_prose():
    normalized = extract_job_signals(
        "Requirements:\n• Python\n• python\n• LLMs\n\n"
        "Nice to have:\n• FastAPI\n• fastapi\n• Python"
    )
    assert normalized.required_skills == ["Python", "LLMs"]
    assert normalized.preferred_skills == ["FastAPI"]

    prose = extract_job_signals(
        "We're looking for someone with strong React and TypeScript skills. "
        "Experience with Next.js would be a plus."
    )
    assert prose.required_skills == ["React", "TypeScript"]
    assert prose.preferred_skills == ["Next.js"]


@pytest.mark.parametrize(
    "description,expect_work,expect_places",
    [
        ("Fully remote Python role.\n\n- Python", ["remote"], []),
        ("On-site role in our Berlin office.\n\n- Python", ["onsite"], ["Berlin"]),
    ],
)
def test_extract_work_and_location(description, expect_work, expect_places):
    job_signals = extract_job_signals(description)
    assert job_signals.work_arrangements == expect_work
    assert job_signals.location_signals == expect_places


@pytest.mark.parametrize(
    "score,expected",
    [
        (0.54, DecisionType.SKIP),
        (0.55, DecisionType.QUEUE),
        (0.75, DecisionType.PREPARE),
    ],
)
def test_decision_thresholds(score, expected):
    assert decision_from_score(score) == expected


def test_decision_risk_and_seniority_overrides():
    risky_but_usable = JobSignals(
        required_skills=["Python"],
        risk_indicators=["ambiguous scope"],
    )
    assert decision_from_signals(0.9, risky_but_usable) == DecisionType.PREPARE
    assert (
        decision_from_signals(0.9, risky_but_usable, severe_seniority_mismatch=True)
        == DecisionType.SKIP
    )


@pytest.mark.parametrize("fixture_name", DECISION_FIXTURES)
def test_build_workflow_decision_from_fixture(fixture_name):
    case = load_decision_fixture(fixture_name)
    decision = build_workflow_decision(
        ProfileMatchResult(**case["match"]),
        JobSignals(**case["job_signals"]),
    )
    assert decision == WorkflowDecision(**case["expected_decision"])


@pytest.mark.parametrize("fixture_name", PROFILE_EXTRACTION_FIXTURES)
def test_extract_profile_from_fixture(fixture_name):
    case = load_profile_fixture(fixture_name)
    assert extract_user_profile(case["profile_text"]) == UserProfile(
        **case["expected_profile"]
    )


def test_extract_profile_rejects_empty_text():
    with pytest.raises(ValueError, match="cannot be empty"):
        extract_user_profile("   ")


def test_extract_profile_still_reads_labeled_lines():
    profile = extract_user_profile(
        "seniority: mid\nlocation: Amsterdam\nskills: Python, SQL, Airflow\n"
        "work_preferences: remote"
    )
    assert profile == UserProfile(
        skills=["Python", "SQL", "Airflow"],
        location="Amsterdam",
        seniority="mid",
        work_preferences=["remote"],
    )


def test_extract_profile_reads_non_tech_skills_section():
    profile = extract_user_profile(
        "Mid-level Teacher\nLisbon\n\nCompetencies\n"
        "classroom management, curriculum design"
    )
    assert profile.skills == ["classroom management", "curriculum design"]
    assert profile.location == "Lisbon"
    assert profile.seniority == "mid"


def test_extract_profile_supports_credentials_and_non_tech_experience():
    profile = extract_user_profile(
        "Jordan Lee\nSenior Registered Nurse\nBoston, MA\n\n"
        "Licenses & Certifications\nRN, BLS\n\n"
        "Competencies\npatient care, medication administration, de-escalation\n\n"
        "Clinical Experience: patient care, medication administration\n"
        "work_preferences: onsite"
    )

    assert profile.skills == [
        "RN",
        "BLS",
        "patient care",
        "medication administration",
        "de-escalation",
    ]
    assert profile.location == "Boston"
    assert profile.seniority == "senior"
    assert profile.relevant_experience == [
        "patient care",
        "medication administration",
    ]
    assert profile.work_preferences == ["onsite"]


def test_extract_and_match_non_tech_job_requirements():
    signals = extract_job_signals(
        "Senior Registered Nurse\nOn-site in our Boston office.\n"
        "Requirements:\n• RN\n• BLS\n• patient communication\n"
        "The role includes patient care and weekend shifts."
    )
    assert signals.required_skills == ["RN", "BLS", "patient communication"]
    assert signals.experience_requirements == ["weekend shifts", "patient care"]

    result = match_profile_to_job(
        UserProfile(
            skills=["RN", "BLS", "patient communication"],
            location="Boston",
            seniority="senior",
            relevant_experience=["patient care", "weekend shifts"],
            work_preferences=["onsite"],
        ),
        signals,
    )
    assert result.required_skills_missing == []
    assert result.experience_requirements_missing == []
    assert result.location_aligned
    assert result.score == 1.0


def test_llm_signal_extractor_success_and_fallback():
    ok = LLMSignalExtractor(
        model=signals_test_model(required_skills=["Python"], preferred_skills=["FastAPI"]),
    ).run(sample_signal_extractor_input())
    assert ok.job_signals.required_skills == ["Python"]
    assert ok.execution and not ok.execution.used_fallback

    failed = LLMSignalExtractor(
        model=RecordingSignalModel(
            ModelHTTPError(status_code=503, model_name="test", body="down")
        ).as_model(),
        runtime_config=RuntimeConfig.build(max_attempts=1),
    ).run(sample_signal_extractor_input())
    assert failed.execution
    assert failed.execution.used_fallback
    assert failed.execution.status == ExecutionStatus.SUCCESS
    assert (failed.execution.error or "").startswith("SignalExtractionLLMError")

