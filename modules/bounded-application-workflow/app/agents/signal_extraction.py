import re
from typing import Iterable

from app.domain.job_signals import JobSignals
from app.domain.models import JobDescription

PatternLabel = tuple[re.Pattern[str], str | None]

_YEARS_EXPERIENCE_PATTERN = re.compile(
    r"\b(\d+\s*-\s*\d+|\d+\+?)\s*(?:years?|yrs?)"
    r"(?:\s+of\s+(?:[\w-]+\s+)*experience)?\b",
    re.IGNORECASE,
)
_SENIORITY_LEVEL_PATTERN = re.compile(
    r"\b("
    r"junior|mid[- ]level|mid[- ]senior|senior|staff|principal|"
    r"(?:team\s+)?lead|director"
    r")\b",
    re.IGNORECASE,
)
_OWNERSHIP_PATTERNS: list[PatternLabel] = [
    (re.compile(r"\bproduct ownership\b", re.IGNORECASE), "product ownership"),
    (
        re.compile(r"\bend[- ]to[- ]end ownership\b", re.IGNORECASE),
        "end-to-end ownership",
    ),
    (re.compile(r"\btechnical ownership\b", re.IGNORECASE), "technical ownership"),
    (
        re.compile(
            r"\b(?:own|drive|lead)\s+(?:and\s+)?(?:[\w-]+\s+){0,4}"
            r"(?:product|workflows?|systems?|initiatives?|roadmap|delivery)\b",
            re.IGNORECASE,
        ),
        None,
    ),
]
_PRODUCTION_PATTERNS: list[PatternLabel] = [
    (re.compile(r"\bon[- ]call(?:\s+rotation)?\b", re.IGNORECASE), "on-call rotation"),
    (
        re.compile(r"\blarge[- ]scale(?:\s+[\w-]+)?\b", re.IGNORECASE),
        None,
    ),
    (re.compile(r"\bproduction[- ]ready\b", re.IGNORECASE), "production readiness"),
    (
        re.compile(
            r"\b(?:deploy(?:ment)?|operating|running)\s+in\s+production\b",
            re.IGNORECASE,
        ),
        "production deployment",
    ),
    (
        re.compile(
            r"\b(?:monitoring|observability|reliability|incident response|sla)\b",
            re.IGNORECASE,
        ),
        None,
    ),
]
_RISK_PATTERNS: list[PatternLabel] = [
    (
        re.compile(
            r"\b(?:unclear|ambiguous|vague|TBD|to be determined)\b",
            re.IGNORECASE,
        ),
        "ambiguous scope",
    ),
    (
        re.compile(
            r"\b(?:10x|rockstar|ninja|unicorn)\s+(?:engineer|developer|hire)\b",
            re.IGNORECASE,
        ),
        "unrealistic expectations",
    ),
    (
        re.compile(r"\bwear many hats\b", re.IGNORECASE),
        "broad unfocused role",
    ),
    (
        re.compile(r"\bhigh(?:\s+[\w-]+){0,2}\s+ownership\b", re.IGNORECASE),
        "high ownership expectations",
    )
]
_MISSING_PATTERNS: list[PatternLabel] = [
    (
        re.compile(r"\bno explicit remote policy\b", re.IGNORECASE),
        "remote policy",
    ),
    (
        re.compile(r"\bseniority(?: level)? unclear\b", re.IGNORECASE),
        "seniority level",
    ),
    (
        re.compile(
            r"\b(?:salary|compensation) (?:not listed|unclear|unlisted)\b",
            re.IGNORECASE,
        ),
        "salary range",
    ),
    (
        re.compile(
            r"\b(?:team size|team structure) (?:not mentioned|unclear|unspecified)\b",
            re.IGNORECASE,
        ),
        "team size",
    ),
]
_SALARY_PATTERN = re.compile(
    r"\b(?:salary|compensation|pay range|pay band|£|\$|€|USD|EUR|CHF|\d+k)\b",
    re.IGNORECASE,
)
_TEAM_SIZE_PATTERN = re.compile(
    r"\b(?:team size|team of \d+|\d+[- ]person team|\d+\s+engineers|\d+\s+people)\b",
    re.IGNORECASE,
)
_REMOTE_POLICY_PATTERN = re.compile(
    r"\b(?:remote[- ]first|fully remote|remote|hybrid|on[- ]site|office[- ]first|work from home|WFH)\b",
    re.IGNORECASE,
)
_EMPLOYMENT_TYPE_PATTERN = re.compile(
    r"\b(?:full[- ]time|part[- ]time|contract|freelance|permanent|employment type)\b",
    re.IGNORECASE,
)


def _normalize_skill(skill: str) -> str:
    return " ".join(skill.split())


def _dedupe_skills(skills: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []

    for skill in skills:
        normalized = _normalize_skill(skill)
        if not normalized:
            continue

        key = normalized.casefold()
        if key in seen:
            continue

        seen.add(key)
        result.append(normalized)

    return result


def _skills_from_description(description: str) -> tuple[list[str], list[str]]:
    required: list[str] = []
    preferred: list[str] = []

    for line in description.splitlines():
        stripped = line.strip()
        if stripped.startswith("-"):
            required.append(stripped.lstrip("- ").strip())
        elif stripped.startswith("+"):
            preferred.append(stripped.lstrip("+ ").strip())

    return required, preferred


def _job_corpus(job: JobDescription) -> str:
    return "\n".join(part for part in [job.title, job.description] if part)


def _signals_from_labeled_patterns(
    corpus: str, patterns: list[PatternLabel]
) -> list[str]:
    signals: list[str] = []

    for pattern, label in patterns:
        for match in pattern.finditer(corpus):
            signals.append(label or _normalize_skill(match.group(0)))

    return signals


def _seniority_signals_from_job(job: JobDescription) -> list[str]:
    signals: list[str] = []

    if job.seniority:
        signals.append(job.seniority)

    corpus = _job_corpus(job)
    for match in _YEARS_EXPERIENCE_PATTERN.finditer(corpus):
        signals.append(_normalize_skill(match.group(0)))

    for match in _SENIORITY_LEVEL_PATTERN.finditer(corpus):
        signals.append(_normalize_skill(match.group(0)))

    description_required, description_preferred = _skills_from_description(job.description)
    for skill in [*description_required, *description_preferred]:
        if "ownership" in skill.casefold():
            signals.append(skill)

    signals.extend(_signals_from_labeled_patterns(corpus, _OWNERSHIP_PATTERNS))

    return _dedupe_skills(signals)


def _production_expectations_from_job(job: JobDescription) -> list[str]:
    return _dedupe_skills(
        _signals_from_labeled_patterns(_job_corpus(job), _PRODUCTION_PATTERNS)
    )


def _risk_indicators_from_job(job: JobDescription) -> list[str]:
    return _dedupe_skills(
        _signals_from_labeled_patterns(_job_corpus(job), _RISK_PATTERNS)
    )


def _has_remote_policy(job: JobDescription, corpus: str) -> bool:
    if _REMOTE_POLICY_PATTERN.search(corpus):
        return True
    return bool(job.location and _REMOTE_POLICY_PATTERN.search(job.location))


def _missing_signals_from_job(job: JobDescription) -> list[str]:
    missing: list[str] = []
    corpus = _job_corpus(job)

    missing.extend(_signals_from_labeled_patterns(corpus, _MISSING_PATTERNS))

    if (
        not job.seniority
        and not _SENIORITY_LEVEL_PATTERN.search(corpus)
        and not _YEARS_EXPERIENCE_PATTERN.search(corpus)
    ):
        missing.append("seniority level")

    if not _has_remote_policy(job, corpus):
        missing.append("remote policy")

    if not _SALARY_PATTERN.search(corpus):
        missing.append("salary range")

    if not _TEAM_SIZE_PATTERN.search(corpus):
        missing.append("team size")

    if not job.employment_type and not _EMPLOYMENT_TYPE_PATTERN.search(corpus):
        missing.append("employment type")

    return _dedupe_skills(missing)


def _normalize_job_signals(signals: JobSignals) -> JobSignals:
    """Deduplicate parsed signals from regex/heuristic extraction."""
    required_skills = _dedupe_skills(signals.required_skills)
    required_keys = {skill.casefold() for skill in required_skills}
    preferred_skills = [
        skill
        for skill in _dedupe_skills(signals.preferred_skills)
        if skill.casefold() not in required_keys
    ]

    return JobSignals(
        required_skills=required_skills,
        preferred_skills=preferred_skills,
        seniority_signals=_dedupe_skills(signals.seniority_signals),
        production_expectations=_dedupe_skills(signals.production_expectations),
        risk_indicators=_dedupe_skills(signals.risk_indicators),
        missing_signals=_dedupe_skills(signals.missing_signals),
    )


def extract_job_signals(job: JobDescription) -> JobSignals:
    description_required, description_preferred = _skills_from_description(
        job.description
    )

    return _normalize_job_signals(
        JobSignals(
            required_skills=description_required,
            preferred_skills=description_preferred,
            seniority_signals=_seniority_signals_from_job(job),
            production_expectations=_production_expectations_from_job(job),
            risk_indicators=_risk_indicators_from_job(job),
            missing_signals=_missing_signals_from_job(job),
        )
    )
