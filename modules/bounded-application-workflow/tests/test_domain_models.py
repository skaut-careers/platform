import pytest
from pydantic import ValidationError

from app.domain.models import (
    DecisionType,
    JobDescription,
    UserProfile,
    WorkflowDecision,
    WorkflowInput,
    WorkflowOutput,
)
from app.domain.job_signals import JobSignals


def test_workflow_input_can_be_created():
    user_profile = UserProfile(
        name="Ana",
        target_roles=["AI Engineer", "Product Engineer"],
        skills=["Python", "FastAPI", "LLM systems"],
        experience_summary="Research background with applied AI product work.",
        location="Zurich",
        work_preferences=["remote", "hybrid"],
    )

    job_description = JobDescription(
        title="AI Engineer",
        company="Example AI",
        location="Remote",
        description=(
            "Build and evaluate LLM-based product workflows.\n\n"
            "- Python\n- LLMs\n- APIs\n\n+ FastAPI\n+ Evaluation"
        ),
        seniority="mid-senior",
        employment_type="full-time",
    )

    workflow_input = WorkflowInput(
        user_profile=user_profile,
        job_description=job_description,
    )

    assert workflow_input.user_profile.name == "Ana"
    assert workflow_input.job_description.title == "AI Engineer"
    assert "Python" in workflow_input.user_profile.skills


def test_workflow_decision_accepts_valid_decision_type():
    decision = WorkflowDecision(
        decision=DecisionType.PREPARE,
        score=0.82,
        reasons=["Strong skill overlap"],
        risks=["Seniority expectations unclear"],
        missing_information=["Salary range"],
    )

    assert decision.decision == DecisionType.PREPARE
    assert decision.score == 0.82
    assert decision.reasons == ["Strong skill overlap"]


def test_workflow_decision_rejects_invalid_score():
    with pytest.raises(ValidationError):
        WorkflowDecision(
            decision=DecisionType.SKIP,
            score=1.5,
            reasons=["Invalid score should fail"],
        )


def test_workflow_output_can_be_created():
    decision = WorkflowDecision(
        decision=DecisionType.QUEUE,
        score=0.63,
        reasons=["Partial match"],
        risks=["Missing some required skills"],
        missing_information=[],
    )

    output = WorkflowOutput(
        input_summary="Ana is being evaluated for an AI Engineer role.",
        decision=decision,
        job_signals=JobSignals(),
        recommended_next_steps=[
            "Review job requirements manually",
            "Improve CV alignment before applying",
        ],
    )

    assert output.decision.decision == DecisionType.QUEUE
    assert output.recommended_next_steps
    