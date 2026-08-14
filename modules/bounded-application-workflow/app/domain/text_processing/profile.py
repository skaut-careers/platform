from __future__ import annotations

import re

from app.domain.text_processing.common import (
    _BULLET_LINE,
    collapse_whitespace,
    dedupe_phrases,
    is_short_skill_label,
    phrases_from_list,
)
from app.domain.text_processing.locations import places_from_text
from app.domain.text_processing.seniority import seniority_from_text
from app.domain.text_processing.work_arrangements import work_arrangements_from_text

_EXPERIENCE_CUES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\b(?:on[- ]call|pagerduty|pager duty)\b", re.IGNORECASE), "on-call"),
    (re.compile(r"\bmonitoring\b", re.IGNORECASE), "monitoring"),
    (re.compile(r"\bobservability\b", re.IGNORECASE), "observability"),
    (re.compile(r"\breliability\b", re.IGNORECASE), "reliability"),
    (re.compile(r"\b(?:large[- ]scale|at scale)\b", re.IGNORECASE), "scale"),
    (re.compile(r"\bincident response\b", re.IGNORECASE), "incident response"),
    (re.compile(r"\bpatient care\b", re.IGNORECASE), "patient care"),
    (re.compile(r"\bmedication administration\b", re.IGNORECASE), "medication administration"),
    (re.compile(r"\bclassroom management\b", re.IGNORECASE), "classroom management"),
    (re.compile(r"\bcurriculum (?:design|development)\b", re.IGNORECASE), "curriculum design"),
    (re.compile(r"\bcase(?:load| management)\b", re.IGNORECASE), "case management"),
    (re.compile(r"\b(?:workplace |food |patient )?safety\b", re.IGNORECASE), "safety"),
    (re.compile(r"\bregulatory compliance\b", re.IGNORECASE), "regulatory compliance"),
    (re.compile(r"\bcustomer service\b", re.IGNORECASE), "customer service"),
    (re.compile(r"\binventory management\b", re.IGNORECASE), "inventory management"),
    (re.compile(r"\bbudget management\b", re.IGNORECASE), "budget management"),
    (re.compile(r"\bquality (?:assurance|control)\b", re.IGNORECASE), "quality assurance"),
    (re.compile(r"\bproject management\b", re.IGNORECASE), "project management"),
)

# Matches both a bare section header ('Skills', 'Skills:') and a labeled list
# ('Skills: Python, Java'); the inline list, when present, is in group 1.
_PROFILE_SKILLS_SECTION = re.compile(
    r"^(?:(?:core|key|technical|professional)\s+)?"
    r"(?:skills?|competenc(?:y|ies)|expertise|"
    r"qualifications?|licenses?(?:\s*(?:&|and)\s*certifications?)?|"
    r"certifications?|education|methods?|"
    r"tech(?:nical)?\s+stack|technologies|tools)"
    r"\s*(?::\s*(.*))?$",
    re.IGNORECASE,
)
_PROFILE_OTHER_SECTION = re.compile(
    r"^(?:summary|profile|about|experience|work experience|employment|"
    r"clinical experience|teaching experience|projects|languages|contact|"
    r"work preferences)\s*:?\s*$",
    re.IGNORECASE,
)


def _experience_cues_from_text(text: str) -> list[str]:
    found: list[str] = []
    for pattern, label in _EXPERIENCE_CUES:
        if pattern.search(text):
            found.append(label)
    return dedupe_phrases(found)


def _skills_from_sections(profile_text: str) -> list[str]:
    skills: list[str] = []
    in_skills = False
    bullets_only = False
    has_skill_content = False
    for raw_line in profile_text.splitlines():
        line = collapse_whitespace(raw_line)
        if not line:
            if in_skills and has_skill_content:
                in_skills = False
            continue
        skills_section = _PROFILE_SKILLS_SECTION.match(line)
        if skills_section or _PROFILE_OTHER_SECTION.match(line):
            in_skills = bool(skills_section)
            has_skill_content = False
            bullets_only = False
            inline_list = skills_section.group(1) if skills_section else ""
            if inline_list:
                skills.extend(phrases_from_list(inline_list))
                has_skill_content = True
                bullets_only = True
            continue
        if not in_skills:
            continue
        bullet = _BULLET_LINE.match(line)
        if bullets_only and not bullet:
            in_skills = False
            continue
        item = bullet.group(1) if bullet else line
        phrases = phrases_from_list(item)
        if phrases:
            skills.extend(phrases)
            has_skill_content = True
        elif is_short_skill_label(item):
            skills.append(item)
            has_skill_content = True
    return skills


def skills_from_profile(profile_text: str) -> list[str]:
    return dedupe_phrases(_skills_from_sections(profile_text))


def location_from_profile(profile_text: str) -> str:
    places = places_from_text(profile_text, include_office_cues=False)
    return places[0] if places else ""


def seniority_from_profile(profile_text: str) -> str:
    return seniority_from_text(profile_text)


def relevant_experience_from_profile(profile_text: str) -> list[str]:
    return _experience_cues_from_text(profile_text)


def work_preferences_from_profile(profile_text: str) -> list[str]:
    return work_arrangements_from_text(profile_text)
