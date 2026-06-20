import pytest

from app.agents import (
    build_workflow_decision,
    create_workflow_plan,
    decision_from_score,
    decision_from_signals,
    extract_job_signals,
    match_profile_to_job,
)
from app.agents.llm_signal_extraction import LLMSignalExtractor, job_signals_schema, load_system_prompt
from app.domain.job_signals import JobSignals
from app.domain.models import (
    DecisionType,
    JobDescription,
    ProfileMatchResult,
    UserProfile,
    WorkflowInput,
)
from app.domain.workflow_state import WorkflowState
from app.llm.client import LLMClientError
from app.runtime import ExecutionStatus, SignalExtractorRuntimeConfig
from tests.conftest import (
    escalating_workflow_input,
    load_fixture,
    mock_llm_client,
    sample_signal_extractor_input,
    signals_payload,
    workflow_input,
)


# --- profile_matching.py ---


def _match(fixture_name: str):
    workflow = workflow_input(fixture_name)
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
def test_profile_match_fixtures(
    fixture_name: str, min_score: float, max_score: float, role_aligned: bool
):
    result = _match(fixture_name)

    assert min_score <= result.score <= max_score
    assert result.role_aligned is role_aligned


@pytest.mark.parametrize(
    "profile_seniority,job_seniority",
    [("staff", "junior"), ("junior", "principal")],
)
def test_severe_seniority_mismatch(profile_seniority: str, job_seniority: str):
    result = match_profile_to_job(
        UserProfile(name="Ana", seniority=profile_seniority),
        JobDescription(
            title="Engineer",
            description="Build features.\n\n- Python",
            seniority=job_seniority,
        ),
        JobSignals(required_skills=["Python"], seniority_signals=[job_seniority]),
    )

    assert result.severe_seniority_mismatch


# --- signal_extraction.py ---


def test_extract_from_fixture():
    fixture = load_fixture("skill_extraction.json")
    job = JobDescription(**fixture["job_description"])
    expected = fixture["expected_signals"]

    signals = extract_job_signals(job)

    assert signals.required_skills == expected["required_skills"]
    assert signals.preferred_skills == expected["preferred_skills"]
    assert signals.seniority_signals == expected["seniority_signals"]
    assert signals.production_expectations == expected["production_expectations"]
    assert signals.risk_indicators == expected["risk_indicators"]
    assert signals.missing_signals == expected["missing_signals"]


def test_extract_risk_and_missing_signals():
    fixture = load_fixture("risk_extraction.json")
    signals = extract_job_signals(JobDescription(**fixture["job_description"]))
    expected = fixture["expected_signals"]

    assert signals.risk_indicators == expected["risk_indicators"]
    assert signals.missing_signals == expected["missing_signals"]


def test_extract_normalizes_skill_lists():
    job = JobDescription(
        title="AI Engineer",
        description="""
- Python
- python
- LLMs
+ FastAPI
+ fastapi
+ Python
""",
    )

    signals = extract_job_signals(job)

    assert signals.required_skills == ["Python", "LLMs"]
    assert signals.preferred_skills == ["FastAPI"]


# --- decision_rules.py ---


@pytest.mark.parametrize(
    "score,expected",
    [
        (0.34, DecisionType.SKIP),
        (0.35, DecisionType.ESCALATE),
        (0.54, DecisionType.ESCALATE),
        (0.55, DecisionType.QUEUE),
        (0.74, DecisionType.QUEUE),
        (0.75, DecisionType.PREPARE),
    ],
)
def test_decision_thresholds(score: float, expected: DecisionType):
    assert decision_from_score(score) == expected


def test_decision_escalates_on_risk():
    signals = JobSignals(risk_indicators=["ambiguous scope"])
    assert decision_from_signals(0.9, signals) == DecisionType.ESCALATE


def test_decision_skips_on_severe_seniority_mismatch():
    signals = JobSignals(risk_indicators=["ambiguous scope"])
    assert (
        decision_from_signals(0.9, signals, severe_seniority_mismatch=True)
        == DecisionType.SKIP
    )


def test_build_workflow_decision():
    match = ProfileMatchResult(
        score=0.82,
        reasons=["Matched 1 of 2 required skills."],
        risks=["Missing required skills: Kubernetes."],
    )
    signals = JobSignals(
        risk_indicators=["ambiguous scope"],
        missing_signals=["salary range"],
    )

    decision = build_workflow_decision(match, signals)

    assert decision.decision == DecisionType.ESCALATE
    assert decision.score == match.score
    assert decision.missing_information == ["Job posting missing signal: salary range"]


# --- workflow_planning.py ---


def test_plan_for_clean_posting_omits_human_review():
    plan = create_workflow_plan(workflow_input("strong_match.json"))

    assert plan.stages == [
        WorkflowState.INTAKE,
        WorkflowState.SIGNAL_EXTRACTION,
        WorkflowState.PROFILE_MATCHING,
        WorkflowState.POLICY_EVALUATION,
        WorkflowState.DECISION,
    ]


def test_plan_for_risky_posting_includes_human_review():
    plan = create_workflow_plan(escalating_workflow_input())

    assert WorkflowState.HUMAN_REVIEW in plan.stages
    assert plan.stages[-1] == WorkflowState.DECISION


# --- llm_signal_extraction.py ---


def test_prompt_and_schema():
    assert "required_skills" in load_system_prompt("v1")
    assert set(job_signals_schema()["properties"]) == set(signals_payload())


def test_llm_extractor_success():
    client = mock_llm_client(signals_payload(required_skills=["Python"], preferred_skills=["FastAPI"]))
    output = LLMSignalExtractor(client=client).run(sample_signal_extractor_input())

    assert output.signals.required_skills == ["Python"]
    assert output.signals.preferred_skills == ["FastAPI"]
    assert output.metadata and not output.metadata.used_fallback


@pytest.mark.parametrize(
    "responses, used_fallback, attempts, error_prefix",
    [
        ([LLMClientError("down")], True, 1, "SignalExtractionLLMError"),
        ([signals_payload(required_skills="Python")], True, 1, "SignalExtractionSchemaError"),
        (
            [LLMClientError("retry"), signals_payload(required_skills=["Python"])],
            False,
            2,
            None,
        ),
    ],
)
def test_llm_extractor_runtime_paths(responses, used_fallback, attempts, error_prefix):
    client = mock_llm_client(*responses)
    output = LLMSignalExtractor(
        client=client,
        config=SignalExtractorRuntimeConfig(max_attempts=attempts),
    ).run(sample_signal_extractor_input())

    assert output.metadata
    assert output.metadata.used_fallback is used_fallback
    assert output.metadata.attempts == attempts
    if used_fallback:
        assert output.metadata.status == ExecutionStatus.FAILED
        assert output.metadata.error.startswith(error_prefix)
