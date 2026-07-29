import pytest

from app.parser import parse_job_description

RAW_JOB_TEXT = """
AI Engineer

Company: Skaut Careers
Location: Zurich
Seniority: Mid
Employment Type: Full-time

Build and own LLM-based product workflows.

Requirements:
• Python
• LLM Systems
• Evaluation

Nice to have:
• FastAPI
• React
"""


def test_parse_job_description():
    job = parse_job_description(RAW_JOB_TEXT)

    assert job.title == "AI Engineer"
    assert job.company == "Skaut Careers"
    assert job.location == "Zurich"
    assert job.seniority == "Mid"
    assert job.employment_type == "Full-time"
    assert job.description == RAW_JOB_TEXT


def test_parse_job_description_rejects_empty_text():
    with pytest.raises(ValueError, match="cannot be empty"):
        parse_job_description("   \n  ")
