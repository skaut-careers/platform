import json
from pathlib import Path

from app.domain.models import DecisionType, JobDescription, UserProfile, WorkflowInput

FIXTURES_DIR = Path(__file__).parent / "fixtures"

WORKFLOW_FIXTURES = (
    "strong_match.json",
    "weak_match.json",
    "ambiguous_match.json",
)

AI_ENGINEER_JOB_TEXT = """
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


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text())


def expected_decision(fixture_name: str) -> DecisionType:
    return DecisionType(load_fixture(fixture_name)["expected_decision"])


def workflow_input(fixture_name: str) -> WorkflowInput:
    data = load_fixture(fixture_name)
    return WorkflowInput(
        user_profile=UserProfile(**data["user_profile"]),
        job_description=JobDescription(**data["job_description"]),
    )
