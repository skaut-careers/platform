from app.domain.models import UserProfile
from app.domain.text_processing import (
    location_from_profile,
    relevant_experience_from_profile,
    seniority_from_profile,
    skills_from_profile,
    work_preferences_from_profile,
)


def extract_user_profile(profile_text: str) -> UserProfile:
    if not profile_text.strip():
        raise ValueError("Profile text cannot be empty.")

    return UserProfile(
        skills=skills_from_profile(profile_text),
        location=location_from_profile(profile_text),
        seniority=seniority_from_profile(profile_text),
        relevant_experience=relevant_experience_from_profile(profile_text),
        work_preferences=work_preferences_from_profile(profile_text),
    )
