import pytest
from pydantic_ai.exceptions import ModelHTTPError

from app.agents.decision_rules.rules import (
    build_workflow_decision,
    decision_from_score,
    decision_from_signals,
)
from app.agents.profile_extraction.deterministic import extract_user_profile
from app.agents.profile_matching.deterministic import match_profile_to_job
from app.agents.signal_extraction import LLMSignalExtractor
from app.agents.signal_extraction.deterministic import extract_job_signals
from app.domain.job_signals import JobSignals
from app.domain.models import (
    DecisionType,
    JobDescription,
    ProfileMatchResult,
    UserProfile,
)
from app.runtime import ExecutionStatus, RuntimeConfig
from tests.conftest import (
    PROFILE_EXTRACTION_FIXTURES,
    SIGNAL_EXTRACTION_FIXTURES,
    SIGNAL_FIELDS,
    RecordingSignalModel,
    load_profile_fixture,
    load_signal_fixture,
    sample_signal_extractor_input,
    signals_test_model,
    fixture_entities,
)


def _match(fixture_name: str):
    case = fixture_entities(fixture_name)
    return match_profile_to_job(
        case.user_profile,
        case.job_description,
        extract_job_signals(case.job_description),
    )


@pytest.mark.parametrize(
    "fixture_name,min_score,max_score,role_aligned",
    [
        ("strong_match.json", 0.5, 1.0, True),
        ("weak_match.json", 0.0, 0.35, False),
        ("ambiguous_match.json", 0.35, 0.75, True),
    ],
)
def test_profile_match_fixtures(fixture_name, min_score, max_score, role_aligned):
    result = _match(fixture_name)
    assert min_score <= result.score <= max_score
    assert result.role_aligned is role_aligned


def test_severe_seniority_mismatch():
    result = match_profile_to_job(
        UserProfile(seniority="staff"),
        JobDescription(
            title="Engineer",
            description="Build features.\n\n- Python",
            seniority="junior",
        ),
        JobSignals(required_skills=["Python"], seniority_signals=["junior"]),
    )
    assert result.severe_seniority_mismatch


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
            target_roles=["Backend Engineer"],
            skills=["Python"],
            location=location,
            work_preferences=prefs,
        ),
        JobDescription(
            title="Backend Engineer",
            description="Backend role.\n\nRequirements:\n• Python",
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
    signals = JobSignals(
        required_skills=["Python"],
        work_arrangements=["onsite"],
        location_signals=["Berlin"],
    )
    job = JobDescription(
        title="Backend Engineer",
        description="On-site role.\n\nRequirements:\n• Python",
    )
    aligned = match_profile_to_job(
        UserProfile(
            target_roles=["Backend Engineer"],
            skills=["Python"],
            location="Berlin",
            work_preferences=["onsite"],
        ),
        job,
        signals,
    )
    mismatched = match_profile_to_job(
        UserProfile(
            target_roles=["Backend Engineer"],
            skills=["Python"],
            location="Lisbon",
            work_preferences=["onsite"],
        ),
        job,
        signals,
    )
    assert mismatched.score < aligned.score
    assert any("On-site role with incompatible locations" in r for r in mismatched.risks)


@pytest.mark.parametrize("fixture_name", SIGNAL_EXTRACTION_FIXTURES)
def test_extract_signals_from_fixture(fixture_name):
    case = load_signal_fixture(fixture_name)
    signals = extract_job_signals(JobDescription(**case["job_description"]))
    expected = case["expected_signals"]
    for field in SIGNAL_FIELDS:
        assert getattr(signals, field) == expected[field]


def test_extract_skills_normalization_and_prose():
    normalized = extract_job_signals(
        JobDescription(
            title="AI Engineer",
            description=(
                "Requirements:\n• Python\n• python\n• LLMs\n\n"
                "Nice to have:\n• FastAPI\n• fastapi\n• Python"
            ),
        )
    )
    assert normalized.required_skills == ["Python", "LLMs"]
    assert normalized.preferred_skills == ["FastAPI"]

    prose = extract_job_signals(
        JobDescription(
            title="Frontend Developer",
            description=(
                "We're looking for someone with strong React and TypeScript skills. "
                "Experience with Next.js would be a plus."
            ),
        )
    )
    assert prose.required_skills == ["React", "TypeScript"]
    assert prose.preferred_skills == ["Next.js"]


@pytest.mark.parametrize(
    "location,description,expect_work,expect_places",
    [
        (None, "Fully remote Python role.\n\n- Python", ["remote"], []),
        (None, "On-site role in our Berlin office.\n\n- Python", ["onsite"], ["Berlin"]),
        ("Berlin · On-site", "Python services.\n\n- Python", ["onsite"], ["Berlin"]),
    ],
)
def test_extract_work_and_location(location, description, expect_work, expect_places):
    signals = extract_job_signals(
        JobDescription(title="Backend Engineer", location=location, description=description)
    )
    assert signals.work_arrangements == expect_work
    assert signals.location_signals == expect_places


@pytest.mark.parametrize(
    "score,expected",
    [
        (0.34, DecisionType.SKIP),
        (0.35, DecisionType.ESCALATE),
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
    assert decision_from_signals(0.9, risky_but_usable) == DecisionType.ESCALATE
    assert (
        decision_from_signals(0.9, risky_but_usable, severe_seniority_mismatch=True)
        == DecisionType.SKIP
    )


def test_decision_unusable_posting_is_hard_pass():
    assert (
        decision_from_signals(
            0.9,
            JobSignals(risk_indicators=["gibberish description"]),
        )
        == DecisionType.SKIP
    )
    assert (
        decision_from_signals(
            0.9,
            JobSignals(
                missing_signals=["seniority level", "salary range", "team size"],
            ),
        )
        == DecisionType.SKIP
    )
    # Invented skills must not rescue a hollow posting.
    assert (
        decision_from_signals(
            0.9,
            JobSignals(
                required_skills=["communication"],
                risk_indicators=[
                    "gibberish description",
                    "no responsibilities listed",
                    "unclear hiring intent",
                ],
                missing_signals=["seniority level", "salary range", "team size"],
            ),
        )
        == DecisionType.SKIP
    )
    # Real job with ordinary risk flags must not hard-pass (e.g. Google SWE).
    assert (
        decision_from_signals(
            0.9,
            JobSignals(
                required_skills=["Python", "ML infrastructure"],
                risk_indicators=[
                    "research + production hybrid role",
                    "very broad technical scope",
                    "high ownership expectation",
                ],
                missing_signals=["salary range", "team size", "employment type"],
            ),
        )
        == DecisionType.ESCALATE
    )


def test_build_workflow_decision():
    decision = build_workflow_decision(
        ProfileMatchResult(
            score=0.82,
            reasons=["Matched 1 of 2 required skills."],
            risks=["Missing required skills: Kubernetes."],
        ),
        JobSignals(
            required_skills=["Python"],
            risk_indicators=["ambiguous scope"],
            missing_signals=["salary range"],
        ),
    )
    assert decision.decision == DecisionType.ESCALATE
    assert decision.missing_information == ["Job posting missing signal: salary range"]


def test_build_workflow_decision_hard_passes_unusable_posting():
    decision = build_workflow_decision(
        ProfileMatchResult(score=0.86, reasons=["full coverage"], risks=[]),
        JobSignals(
            risk_indicators=["gibberish description"],
            missing_signals=["salary range", "team size", "seniority level"],
        ),
    )
    assert decision.decision == DecisionType.SKIP
    assert decision.score == 0.0
    assert "hard pass" in decision.reasons[0].casefold()


@pytest.mark.parametrize("fixture_name", PROFILE_EXTRACTION_FIXTURES)
def test_extract_profile_from_fixture(fixture_name):
    case = load_profile_fixture(fixture_name)
    assert extract_user_profile(case["raw_text"]) == UserProfile(**case["expected_profile"])


def test_extract_profile_rejects_empty_text():
    with pytest.raises(ValueError, match="cannot be empty"):
        extract_user_profile("   ")


def test_llm_signal_extractor_success_and_fallback():
    ok = LLMSignalExtractor(
        model=signals_test_model(required_skills=["Python"], preferred_skills=["FastAPI"]),
    ).run(sample_signal_extractor_input())
    assert ok.signals.required_skills == ["Python"]
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
