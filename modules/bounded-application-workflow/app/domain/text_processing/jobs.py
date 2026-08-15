from __future__ import annotations

import re

from app.domain.models import JobSignals
from app.domain.text_processing.common import (
    _BULLET_LINE,
    collapse_whitespace,
    dedupe_phrases,
    is_short_skill_label,
    normalize_for_match,
    phrases_from_list,
)
from app.domain.text_processing.seniority import seniority_tokens_from_text

_PatternLabel = tuple[re.Pattern[str], str | None]

_JOB_YEARS_EXPERIENCE = re.compile(
    r"\b(\d+\s*-\s*\d+|\d+\+?)\s*(?:years?|yrs?)"
    r"(?:\s+of\s+(?:[\w-]+\s+)*experience)?\b",
    re.IGNORECASE,
)
_JOB_OWNERSHIP_PATTERNS: tuple[_PatternLabel, ...] = (
    (
        re.compile(r"\bend[- ]to[- ]end ownership\b", re.IGNORECASE),
        "end-to-end ownership",
    ),
    (
        re.compile(
            r"\b(?:own|drive|lead|manage|oversee)\s+(?:and\s+)?"
            r"(?:[\w-]+\s+){0,5}(?:work|team|cases?|classroom|shift|"
            r"operations?|projects?|programs?|initiatives?|delivery|"
            r"products?|workflows?|services?|portfolio|accounts?)\b",
            re.IGNORECASE,
        ),
        None,
    ),
)
_JOB_EXPERIENCE_PATTERNS: tuple[_PatternLabel, ...] = (
    (re.compile(r"\bon[- ]call(?:\s+rotation)?\b", re.IGNORECASE), "on-call rotation"),
    (re.compile(r"\b(?:night|evening|weekend) shifts?\b", re.IGNORECASE), None),
    (re.compile(r"\blarge[- ]scale(?:\s+[\w-]+)?\b", re.IGNORECASE), None),
    (re.compile(r"\bproduction[- ]ready\b", re.IGNORECASE), "production readiness"),
    (re.compile(r"\bpatient care\b", re.IGNORECASE), "patient care"),
    (
        re.compile(r"\bmedication administration\b", re.IGNORECASE),
        "medication administration",
    ),
    (
        re.compile(r"\bclassroom management\b", re.IGNORECASE),
        "classroom management",
    ),
    (re.compile(r"\bcase(?:load| management)\b", re.IGNORECASE), "case management"),
    (
        re.compile(r"\b(?:workplace |food |patient )?safety\b", re.IGNORECASE),
        "safety",
    ),
    (
        re.compile(r"\bregulatory compliance\b", re.IGNORECASE),
        "regulatory compliance",
    ),
    (re.compile(r"\bcustomer service\b", re.IGNORECASE), "customer service"),
    (
        re.compile(r"\binventory management\b", re.IGNORECASE),
        "inventory management",
    ),
    (re.compile(r"\bbudget management\b", re.IGNORECASE), "budget management"),
    (
        re.compile(r"\bquality (?:assurance|control)\b", re.IGNORECASE),
        "quality assurance",
    ),
    (re.compile(r"\bproject management\b", re.IGNORECASE), "project management"),
    (re.compile(r"\bincident response\b", re.IGNORECASE), "incident response"),
    (
        re.compile(r"\b(?:monitoring|observability|reliability)\b", re.IGNORECASE),
        None,
    ),
    (
        re.compile(
            r"\b(?:deploy(?:ment)?|operating|running)\s+in\s+production\b",
            re.IGNORECASE,
        ),
        "production deployment",
    ),
)
_JOB_REQUIRED_SECTION = re.compile(
    r"^(?:requirements?|required(?:\s+skills)?|must[- ]haves?|"
    r"qualifications?|licenses?(?:\s+and\s+certifications?)?|certifications?|"
    r"what (?:you.?ll|we) need|our requirements)\s*:?\s*$",
    re.IGNORECASE,
)
_JOB_PREFERRED_SECTION = re.compile(
    r"^(?:nice to haves?|preferred(?:\s+(?:skills|qualifications))?|"
    r"desired qualifications?|plus|bonus|optional)\s*:?\s*$",
    re.IGNORECASE,
)
_JOB_IDEALLY_CLAUSE = re.compile(
    r",?\s*\b(?:ideally|preferably)\s+(?:with\s+)?(.+)$",
    re.IGNORECASE,
)
_JOB_SKILL_LIST_CUES: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(?:experience with|knowledge of)\s+(.+)$", re.IGNORECASE),
    re.compile(
        r"\b(?:strong|solid)\s+(.+?)\s+(?:skills|background)\b",
        re.IGNORECASE,
    ),
)
_JOB_MUST_HAVE_PROSE = re.compile(
    r"\b(?:must (?:have|know)|required:)\s*(.+?)(?:\.|$)",
    re.IGNORECASE,
)
_JOB_PLUS_CLAUSE = re.compile(
    r"(?:experience with\s+)?(.+?)\s+(?:would be|is)\s+a plus\b",
    re.IGNORECASE,
)


def _skills_from_clause(
    clause: str,
    *,
    is_bullet: bool,
    target: list[str],
    required: list[str],
    preferred: list[str],
) -> None:
    for optional_tail in (_JOB_IDEALLY_CLAUSE, _JOB_PLUS_CLAUSE):
        tail = optional_tail.search(clause)
        if tail:
            preferred.extend(phrases_from_list(tail.group(1)))
            clause = clause[: tail.start()].rstrip(" ,;")

    extracted = False
    for match in _JOB_MUST_HAVE_PROSE.finditer(clause):
        required.extend(phrases_from_list(match.group(1)))
        extracted = True
    for pattern in _JOB_SKILL_LIST_CUES:
        for match in pattern.finditer(clause):
            target.extend(phrases_from_list(match.group(1)))
            extracted = True

    if is_bullet and not extracted and is_short_skill_label(clause):
        target.append(clause)


def skills_from_job_text(job_text: str) -> tuple[list[str], list[str]]:
    required: list[str] = []
    preferred: list[str] = []
    section: str | None = None

    for raw_line in job_text.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        if _JOB_REQUIRED_SECTION.match(stripped):
            section = "required"
            continue
        if _JOB_PREFERRED_SECTION.match(stripped):
            section = "preferred"
            continue

        target = preferred if section == "preferred" else required

        bullet = _BULLET_LINE.match(stripped)
        if bullet:
            _skills_from_clause(
                collapse_whitespace(bullet.group(1)),
                is_bullet=True,
                target=target,
                required=required,
                preferred=preferred,
            )
            continue

        for sentence in re.split(r"(?<=[.!?])\s+", stripped):
            _skills_from_clause(
                sentence,
                is_bullet=False,
                target=target,
                required=required,
                preferred=preferred,
            )

    return required, preferred


def _signals_from_patterns(
    text: str, patterns: tuple[_PatternLabel, ...]
) -> list[str]:
    signals: list[str] = []
    for pattern, label in patterns:
        for match in pattern.finditer(text):
            signals.append(label or collapse_whitespace(match.group(0)))
    return signals


def seniority_signals_from_job(job_text: str) -> list[str]:
    signals = [
        collapse_whitespace(match.group(0))
        for match in _JOB_YEARS_EXPERIENCE.finditer(job_text)
    ]
    signals.extend(seniority_tokens_from_text(job_text))

    required, preferred = skills_from_job_text(job_text)
    signals.extend(
        skill for skill in [*required, *preferred] if "ownership" in skill.casefold()
    )
    signals.extend(_signals_from_patterns(job_text, _JOB_OWNERSHIP_PATTERNS))
    return dedupe_phrases(signals)


def experience_requirements_from_job(job_text: str) -> list[str]:
    return dedupe_phrases(
        _signals_from_patterns(job_text, _JOB_EXPERIENCE_PATTERNS)
    )


def normalize_job_signals(job_signals: JobSignals) -> JobSignals:
    # Required dominates preferred: a skill listed in both stays only as required.
    required_skills = dedupe_phrases(job_signals.required_skills)
    required_keys = {normalize_for_match(skill) for skill in required_skills}
    preferred_skills = [
        skill
        for skill in dedupe_phrases(job_signals.preferred_skills)
        if normalize_for_match(skill) not in required_keys
    ]
    return JobSignals(
        required_skills=required_skills,
        preferred_skills=preferred_skills,
        seniority_signals=dedupe_phrases(job_signals.seniority_signals),
        experience_requirements=dedupe_phrases(job_signals.experience_requirements),
        work_arrangements=dedupe_phrases(job_signals.work_arrangements),
        location_signals=dedupe_phrases(job_signals.location_signals),
    )
