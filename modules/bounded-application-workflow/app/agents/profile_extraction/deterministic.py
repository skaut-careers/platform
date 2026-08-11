import re
from typing import Any

from app.domain.models import UserProfile

_LIST_SEPARATOR = re.compile(r"[,;]")

_LIST_FIELDS = {
    "target roles": "target_roles",
    "target_roles": "target_roles",
    "roles": "target_roles",
    "skills": "skills",
    "production experience": "production_experience",
    "production_experience": "production_experience",
    "work preferences": "work_preferences",
    "work_preferences": "work_preferences",
    "preferences": "work_preferences",
}
_TEXT_FIELDS = {
    "location": "location",
    "seniority": "seniority",
    "experience": "experience_summary",
    "experience summary": "experience_summary",
    "experience_summary": "experience_summary",
    "summary": "experience_summary",
    "recent wins": "experience_summary",
}


def _split_list(value: str) -> list[str]:
    return [item.strip() for item in _LIST_SEPARATOR.split(value) if item.strip()]


def extract_user_profile(raw_text: str) -> UserProfile:
    if not raw_text.strip():
        raise ValueError("Profile text cannot be empty.")

    fields: dict[str, Any] = {}
    for line in raw_text.splitlines():
        label, separator, value = line.partition(":")
        if not separator:
            continue
        key = label.strip().casefold()
        value = value.strip()
        if key in _LIST_FIELDS:
            fields[_LIST_FIELDS[key]] = _split_list(value)
        elif key in _TEXT_FIELDS:
            fields[_TEXT_FIELDS[key]] = value

    return UserProfile(**fields)
