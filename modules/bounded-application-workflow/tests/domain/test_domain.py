import pytest
from pydantic import ValidationError

from app.domain.models import DecisionType, UserProfile, WorkflowDecision
from app.domain.text_processing import place_from_segment


@pytest.mark.parametrize(
    ("segment", "expected_place"),
    [
        ("Berlin, Germany | remote", "Berlin"),
        ("remote | Berlin, Germany", "Berlin"),
        ("Berlin, Germany | tel: +49 30 123456", "Berlin"),
        ("tel: +49 30 123456 | Berlin, Germany", "Berlin"),
        ("jane@example.com | Berlin, Germany", "Berlin"),
        ("Tel Aviv, Israel", "Tel Aviv"),
        ("Remote, Berlin", "Berlin"),
        ("Remote - Berlin", "Berlin"),
        ("Remote/Berlin", "Berlin"),
        ("Berlin (remote)", "Berlin"),
        ("Berlin", "Berlin"),
        ("San Francisco Bay Area", "San Francisco Bay Area"),
        ("remote", ""),
    ],
)
def test_place_from_segment_ignores_arrangement_and_contact_parts(
    segment, expected_place
):
    assert place_from_segment(segment) == expected_place


def test_user_profile_rejects_null_list_fields():
    with pytest.raises(ValidationError):
        UserProfile(skills=None)


def test_workflow_decision_rejects_invalid_score():
    with pytest.raises(ValidationError):
        WorkflowDecision(decision=DecisionType.SKIP, score=1.5)
