import pytest
from pydantic_ai.exceptions import ModelHTTPError

from app.agents.contracts import MatchDeciderInput
from app.agents.match_decision.deterministic import (
    decision_from_match,
    decision_from_score,
    match_and_decide,
)
from app.agents.profile_extraction.deterministic import extract_user_profile
from app.agents.match_decision import LLMMatchDecider
from app.agents.job_signal_extraction import LLMJobSignalExtractor
from app.agents.job_signal_extraction.deterministic import extract_job_signals
from app.domain.models import (
    DecisionType,
    JobSignals,
    UserProfile,
)
from app.runtime import ExecutionStatus, RuntimeConfig
from tests.conftest import (
    MATCH_FIXTURES,
    PROFILE_EXTRACTION_FIXTURES,
    JOB_SIGNAL_EXTRACTION_FIXTURES,
    SIGNAL_FIELDS,
    RecordingSignalModel,
    load_match_fixture,
    load_profile_fixture,
    load_signal_fixture,
    sample_job_signal_extractor_input,
    signals_test_model,
)


@pytest.mark.parametrize("fixture_name", MATCH_FIXTURES)
def test_match_profile_from_fixture(fixture_name):
    case = load_match_fixture(fixture_name)
    result = match_and_decide(
        UserProfile(**case["user_profile"]),
        JobSignals(**case["job_signals"]),
    )
    for field, expected in case["expected_match"].items():
        assert getattr(result, field) == expected


@pytest.mark.parametrize(
    "prefs,arrangements,location,places,expect_work,expect_location",
    [
        (["remote"], ["remote"], "Lisbon", [], True, True),
        (["remote"], ["onsite"], "Lisbon", ["Berlin"], False, False),
        (["onsite"], ["onsite"], "Berlin", ["Berlin"], True, True),
        (["onsite"], ["onsite"], "Berlin", [], True, False),
        (["onsite"], ["hybrid"], "Berlin", [], False, False),
    ],
)
def test_work_and_location_alignment(
    prefs, arrangements, location, places, expect_work, expect_location
):
    result = match_and_decide(
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


def test_onsite_location_mismatch_queues_without_changing_score():
    job_signals = JobSignals(
        required_skills=["Python"],
        work_arrangements=["onsite"],
        location_signals=["Berlin"],
    )
    aligned = match_and_decide(
        UserProfile(
            skills=["Python"],
            location="Berlin",
            work_preferences=["onsite"],
        ),
        job_signals,
    )
    mismatched = match_and_decide(
        UserProfile(
            skills=["Python"],
            location="Lisbon",
            work_preferences=["onsite"],
        ),
        job_signals,
    )
    assert mismatched.score == aligned.score
    assert mismatched.decision == DecisionType.QUEUE
    assert aligned.decision == DecisionType.STRONG
    assert any("On-site role with incompatible locations" in r for r in mismatched.risks)


@pytest.mark.parametrize("fixture_name", JOB_SIGNAL_EXTRACTION_FIXTURES)
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
        (0.90, DecisionType.STRONG),
    ],
)
def test_decision_thresholds(score, expected):
    assert decision_from_score(score) == expected


def test_decision_alignment_overrides():
    assert decision_from_match(0.95) == DecisionType.STRONG
    assert (
        decision_from_match(0.95, severe_seniority_mismatch=True)
        == DecisionType.SKIP
    )
    assert (
        decision_from_match(0.95, work_arrangement_aligned=False)
        == DecisionType.SKIP
    )
    assert (
        decision_from_match(0.95, location_aligned=False)
        == DecisionType.QUEUE
    )
    assert (
        decision_from_match(0.60, location_aligned=False)
        == DecisionType.QUEUE
    )
    assert (
        decision_from_match(0.40, location_aligned=False)
        == DecisionType.SKIP
    )
    assert (
        decision_from_match(
            0.95,
            work_arrangement_aligned=False,
            location_aligned=False,
        )
        == DecisionType.SKIP
    )


@pytest.mark.parametrize("fixture_name", PROFILE_EXTRACTION_FIXTURES)
def test_extract_profile_from_fixture(fixture_name):
    case = load_profile_fixture(fixture_name)
    assert extract_user_profile(case["profile_text"]) == UserProfile(
        **case["expected_profile"]
    )


def test_extract_profile_rejects_empty_text():
    with pytest.raises(ValueError, match="cannot be empty"):
        extract_user_profile("   ")


def test_extract_profile_reads_fields_from_label_style_resume():
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


@pytest.mark.parametrize(
    "header_line",
    ["Berlin, Germany | remote", "remote | Berlin, Germany", "wfh | Berlin"],
)
def test_extract_profile_reads_place_regardless_of_segment_order(header_line):
    profile = extract_user_profile(f"Jane Doe\nSenior Engineer\n{header_line}")
    assert profile.location == "Berlin"


def test_extract_profile_keeps_place_named_like_a_contact_label():
    profile = extract_user_profile("Jane Doe\nSenior Engineer\nTel Aviv, Israel")
    assert profile.location == "Tel Aviv"


def test_extract_profile_reads_non_tech_skills_section():
    profile = extract_user_profile(
        "Mid-level Teacher\nLisbon, Portugal\n\nCompetencies\n"
        "classroom management, curriculum design"
    )
    assert profile.skills == ["classroom management", "curriculum design"]
    assert profile.location == "Lisbon"
    assert profile.seniority == "mid"


def test_extract_profile_stops_skills_at_paragraph_boundary():
    profile = extract_user_profile(
        "Skills:\n\nPython\n\nAwards\nEmployee of the Year"
    )
    assert profile.skills == ["Python"]


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

    result = match_and_decide(
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


def test_llm_job_signal_extractor_success_and_fallback():
    ok = LLMJobSignalExtractor(
        model=signals_test_model(required_skills=["Python"], preferred_skills=["FastAPI"]),
        runtime_config=RuntimeConfig.build(config_version="v2"),
    ).run(sample_job_signal_extractor_input())
    assert ok.job_signals.required_skills == ["Python"]
    assert ok.execution and not ok.execution.used_fallback

    failed = LLMJobSignalExtractor(
        model=RecordingSignalModel(
            ModelHTTPError(status_code=503, model_name="test", body="down")
        ).as_model(),
        runtime_config=RuntimeConfig.build(config_version="v2", max_attempts=1),
    ).run(sample_job_signal_extractor_input())
    assert failed.execution
    assert failed.execution.used_fallback
    assert failed.execution.status == ExecutionStatus.SUCCESS
    assert (failed.execution.error or "").startswith("JobSignalExtractionLLMError")


def test_llm_match_decider_returns_match_and_decision_in_one_call():
    payload = {
        "decision": "strong",
        "score": 0.95,
        "required_skills_matched": ["Python"],
        "required_skills_missing": [],
        "preferred_skills_matched": [],
        "experience_requirements_matched": [],
        "experience_requirements_missing": [],
        "work_arrangement_aligned": True,
        "location_aligned": True,
        "severe_seniority_mismatch": False,
        "reasons": ["Required skill matches."],
        "risks": [],
        "missing_information": [],
    }
    model = RecordingSignalModel(payload)
    output = LLMMatchDecider(
        model=model.as_model(),
        runtime_config=RuntimeConfig.build(config_version="v2"),
    ).run(
        MatchDeciderInput(
            user_profile=UserProfile(skills=["Python"]),
            job_signals=JobSignals(required_skills=["Python"]),
        )
    )

    assert model.call_count == 1
    assert output.result.score == 0.95
    assert output.result.decision == DecisionType.STRONG

