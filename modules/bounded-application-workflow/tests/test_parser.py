import pytest

from app.parser import parse_job_description
from app.services.extractor import extract_job_signals

RAW_JOB_TEXT = """
AI Engineer

Company: Limen
Location: Zurich
Seniority: Mid
Employment Type: Full-time

- Python
- LLM Systems
- Evaluation

+ FastAPI
+ React
"""


def test_parse_job_description():
    job = parse_job_description(RAW_JOB_TEXT)

    assert job.title == "AI Engineer"
    assert job.company == "Limen"
    assert job.location == "Zurich"
    assert job.seniority == "Mid"
    assert job.employment_type == "Full-time"
    assert job.description == RAW_JOB_TEXT

    signals = extract_job_signals(job)
    assert signals.required_skills == ["Python", "LLM Systems", "Evaluation"]
    assert signals.preferred_skills == ["FastAPI", "React"]


def test_parse_job_description_rejects_empty_text():
    with pytest.raises(ValueError, match="cannot be empty"):
        parse_job_description("   \n  ")
