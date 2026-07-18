import pytest

from app.agents.decision_rules.rules import (
    build_workflow_decision,
    decision_from_score,
    decision_from_signals,
)
from app.agents.profile_matching.matching import match_profile_to_job
from app.agents.signal_extraction import LLMSignalExtractor
from app.agents.signal_extraction.deterministic import extract_job_signals
from app.agents.signal_extraction.llm import job_signals_schema
from app.agents.workflow_planning.planning import create_workflow_plan
from app.domain.job_signals import JobSignals
from app.domain.models import (
    DecisionType,
    JobDescription,
    ProfileMatchResult,
    UserProfile,
)
from app.domain.workflow_state import WorkflowState
from pydantic_ai.exceptions import ModelHTTPError
from app.runtime import ExecutionStatus, RuntimeConfig, default_prompt_registry
from tests.conftest import (
    SIGNAL_EXTRACTION_FIXTURES,
    SIGNAL_FIELDS,
    RecordingSignalModel,
    escalating_workflow_input,
    load_signal_fixture,
    load_fixture,
    sample_signal_extractor_input,
    signals_payload,
    signals_test_model,
    workflow_input,
)


def _match(fixture_name: str):
    workflow = workflow_input(fixture_name)
    return match_profile_to_job(
        workflow.user_profile,
        workflow.job_description,
        extract_job_signals(workflow.job_description),
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


@pytest.mark.parametrize(
    "profile_seniority,job_seniority",
    [("staff", "junior"), ("junior", "principal")],
)
def test_severe_seniority_mismatch(profile_seniority, job_seniority):
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


@pytest.mark.parametrize("fixture_name", SIGNAL_EXTRACTION_FIXTURES)
def test_extract_from_fixture(fixture_name):
    case = load_signal_fixture(fixture_name)
    signals = extract_job_signals(JobDescription(**case["job_description"]))
    expected = case["expected_signals"]
    for field in SIGNAL_FIELDS:
        assert getattr(signals, field) == expected[field]


def test_extract_normalizes_skill_lists():
    signals = extract_job_signals(
        JobDescription(
            title="AI Engineer",
            description="- Python\n- python\n- LLMs\n+ FastAPI\n+ fastapi\n+ Python",
        )
    )
    assert signals.required_skills == ["Python", "LLMs"]
    assert signals.preferred_skills == ["FastAPI"]


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
def test_decision_thresholds(score, expected):
    assert decision_from_score(score) == expected


def test_decision_escalates_on_risk():
    assert (
        decision_from_signals(0.9, JobSignals(risk_indicators=["ambiguous scope"]))
        == DecisionType.ESCALATE
    )


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


@pytest.mark.parametrize(
    "workflow,includes_review",
    [
        (workflow_input("strong_match.json"), False),
        (escalating_workflow_input(), True),
    ],
)
def test_workflow_plan_stages(workflow, includes_review):
    stages = create_workflow_plan(workflow).stages
    assert stages[-1] == WorkflowState.DECISION
    assert (WorkflowState.HUMAN_REVIEW in stages) is includes_review


def test_prompt_and_schema():
    prompt = default_prompt_registry().get_for(LLMSignalExtractor, "v1")
    assert "required_skills" in prompt.content
    schema = job_signals_schema()
    properties = set(schema["properties"])
    assert properties == set(signals_payload())
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == properties


def test_llm_extractor_success():
    output = LLMSignalExtractor(
        model=signals_test_model(required_skills=["Python"], preferred_skills=["FastAPI"]),
    ).run(sample_signal_extractor_input())

    assert output.signals.required_skills == ["Python"]
    assert output.execution
    assert not output.execution.used_fallback
    assert output.execution.prompt_hash


def _provider_error() -> ModelHTTPError:
    return ModelHTTPError(status_code=503, model_name="test", body="down")


@pytest.mark.parametrize(
    "responses, used_fallback, attempts, error_prefix",
    [
        ([_provider_error()], True, 1, "SignalExtractionLLMError"),
        (
            [_provider_error(), signals_payload(required_skills=["Python"])],
            False,
            2,
            None,
        ),
    ],
)
def test_llm_extractor_runtime_paths(responses, used_fallback, attempts, error_prefix):
    output = LLMSignalExtractor(
        model=RecordingSignalModel(*responses).as_model(),
        runtime_config=RuntimeConfig.build(max_attempts=attempts),
    ).run(sample_signal_extractor_input())

    assert output.execution
    assert output.execution.used_fallback is used_fallback
    assert output.execution.attempts == attempts
    if used_fallback:
        assert output.execution.status == ExecutionStatus.SUCCESS
        assert (output.execution.error or "").startswith(error_prefix)
