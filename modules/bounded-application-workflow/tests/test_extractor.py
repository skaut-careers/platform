from app.domain.job_signals import JobSignals
from app.domain.models import JobDescription
from app.parser import parse_job_description
from app.services.extractor import extract_job_signals
from tests.fixture_helpers import load_fixture

RAW_JOB_TEXT = """
AI Engineer

Company: Frontier AI Startup
Location: Remote Europe
Seniority: mid-senior
Employment Type: full-time

- Python
- LLM applications
- evaluation pipelines
- agentic workflows
- product ownership

+ research background
+ startup experience

Build and own LLM-based product workflows.
"""


def test_extract_job_signals_from_fixture():
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


def test_extract_job_signals_from_parsed_description():
    job = parse_job_description(RAW_JOB_TEXT)

    signals = extract_job_signals(job)

    assert signals.required_skills == [
        "Python",
        "LLM applications",
        "evaluation pipelines",
        "agentic workflows",
        "product ownership",
    ]
    assert signals.preferred_skills == [
        "research background",
        "startup experience",
    ]
    assert signals.seniority_signals == [
        "mid-senior",
        "product ownership",
        "own LLM-based product workflows",
    ]
    assert signals.production_expectations == []
    assert signals.risk_indicators == []
    assert signals.missing_signals == ["salary range", "team size"]


def test_extract_job_signals_deduplicates_skills():
    job = JobDescription(
        title="AI Engineer",
        description="""
- Python
- python
-  Python

+ FastAPI
+ fastapi
+ React
""",
        required_skills=["Python", "LLMs"],
        nice_to_have_skills=["FastAPI", "React"],
    )

    signals = extract_job_signals(job)

    assert signals.required_skills == ["Python", "LLMs"]
    assert signals.preferred_skills == ["FastAPI", "React"]


def test_extract_job_signals_prefers_required_over_preferred():
    job = JobDescription(
        title="AI Engineer",
        description="""
- Python
+ Python
+ FastAPI
""",
        required_skills=[],
        nice_to_have_skills=["Python", "FastAPI"],
    )

    signals = extract_job_signals(job)

    assert signals.required_skills == ["Python"]
    assert signals.preferred_skills == ["FastAPI"]


def test_extract_job_signals_returns_job_signals_model():
    job = JobDescription(
        title="AI Engineer",
        description="Build LLM workflows.",
        required_skills=["Python"],
        nice_to_have_skills=["FastAPI"],
    )

    signals = extract_job_signals(job)

    assert isinstance(signals, JobSignals)
    assert signals.seniority_signals == []
    assert signals.production_expectations == []
    assert signals.risk_indicators == []
    assert signals.missing_signals == [
        "seniority level",
        "remote policy",
        "salary range",
        "team size",
        "employment type",
    ]


def test_extract_job_signals_detects_years_of_experience():
    job = JobDescription(
        title="Senior AI Engineer",
        description="Looking for 5+ years of experience building ML systems.",
        required_skills=[],
        nice_to_have_skills=[],
        seniority=None,
    )

    signals = extract_job_signals(job)

    assert signals.seniority_signals == ["5+ years of experience", "Senior"]


def test_extract_job_signals_detects_production_expectations():
    job = JobDescription(
        title="Platform Engineer",
        description=(
            "Operate large-scale inference systems with on-call rotation "
            "and production-ready deployment practices."
        ),
        required_skills=[],
        nice_to_have_skills=[],
    )

    signals = extract_job_signals(job)

    assert signals.production_expectations == [
        "on-call rotation",
        "large-scale inference",
        "production readiness",
    ]


def test_extract_job_signals_deduplicates_seniority_signals():
    job = JobDescription(
        title="Senior Engineer",
        description="Senior engineer with 3-5 years experience. Senior team lead.",
        required_skills=[],
        nice_to_have_skills=[],
        seniority="senior",
    )

    signals = extract_job_signals(job)

    assert signals.seniority_signals == ["senior", "3-5 years", "team lead"]


def test_extract_job_signals_from_risk_fixture():
    fixture = load_fixture("risk_extraction.json")
    job = JobDescription(**fixture["job_description"])
    expected = fixture["expected_signals"]

    signals = extract_job_signals(job)

    assert signals.risk_indicators == expected["risk_indicators"]
    assert signals.missing_signals == expected["missing_signals"]


def test_extract_job_signals_detects_risk_indicators():
    job = JobDescription(
        title="Full Stack Unicorn Engineer",
        description=(
            "Ambiguous scope with high infrastructure ownership. "
            "We need a 10x engineer who can wear many hats."
        ),
        required_skills=[],
        nice_to_have_skills=[],
    )

    signals = extract_job_signals(job)

    assert signals.risk_indicators == [
        "ambiguous scope",
        "unrealistic expectations",
        "broad unfocused role",
        "high infrastructure ownership",
    ]


def test_extract_job_signals_detects_explicit_missing_signals():
    job = JobDescription(
        title="ML Engineer",
        description=(
            "Build ML models. No explicit remote policy. "
            "Seniority level unclear. Compensation not listed."
        ),
        required_skills=["Python"],
        seniority=None,
    )

    signals = extract_job_signals(job)

    assert "remote policy" in signals.missing_signals
    assert "seniority level" in signals.missing_signals
    assert "salary range" in signals.missing_signals
