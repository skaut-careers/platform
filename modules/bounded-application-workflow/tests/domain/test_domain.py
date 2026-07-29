import pytest
from pydantic import ValidationError

from app.domain.models import DecisionType, UserProfile, WorkflowDecision


def test_user_profile_rejects_null_list_fields():
    with pytest.raises(ValidationError):
        UserProfile(skills=None)


def test_workflow_decision_rejects_invalid_score():
    with pytest.raises(ValidationError):
        WorkflowDecision(decision=DecisionType.SKIP, score=1.5)
