from app.domain.models import UserProfile, WorkflowInput
from app.parser import parse_job_description
from app.services.extractor import extract_job_signals
from app.services.policy import evaluate_workflow
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


def test_parse_and_evaluate_workflow_end_to_end():
    profile_data = load_fixture("strong_match.json")["user_profile"]
    profile = UserProfile(**profile_data)
    job = parse_job_description(RAW_JOB_TEXT)

    output = evaluate_workflow(
        WorkflowInput(user_profile=profile, job_description=job)
    )

    assert output.input_summary
    assert output.decision.score >= 0.0
    assert output.recommended_next_steps

    expected = extract_job_signals(job)
    assert output.job_signals == expected
    assert any(
        "Seniority meets job expectations" in reason
        for reason in output.decision.reasons
    )
