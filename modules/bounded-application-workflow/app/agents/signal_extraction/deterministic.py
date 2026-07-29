import re
from typing import Iterable

from app.domain.job_signals import JobSignals
from app.domain.models import JobDescription
from app.domain.signal_text import (
    LOCATION_NOISE_WORDS,
    casefold_for_match,
    collapse_whitespace,
)

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
_SALARY_PATTERN = re.compile(
    r"\b(?:salary|compensation|pay range|pay band|£|\$|€|USD|EUR|CHF|\d+k)\b",
    re.IGNORECASE,
)
_TEAM_SIZE_PATTERN = re.compile(
    r"\b(?:team size|team of \d+|\d+[- ]person(?:\s+\w+)?\s+team|"
    r"\d+[- ]engineers?|\d+\s+engineers|\d+\s+people)\b",
    re.IGNORECASE,
)
_REMOTE_POLICY_PATTERN = re.compile(
    r"\b(?:remote[- ]first|fully remote|remote|hybrid|on[- ]site|office[- ]first|work from home|WFH|work from anywhere)\b",
    re.IGNORECASE,
)
_EMPLOYMENT_TYPE_PATTERN = re.compile(
    r"\b(?:full[- ]time|part[- ]time|contract|freelance|permanent|employment type)\b",
    re.IGNORECASE,
)
_REMOTE_ARRANGEMENT_IN_LOCATION = re.compile(
    r"\b(?:remote[- ]first|fully remote|remote|work from home|wfh|work from anywhere)\b",
    re.IGNORECASE,
)
_REMOTE_ARRANGEMENT_IN_DESCRIPTION = re.compile(
    r"\b(?:remote[- ]first|fully remote|work from home|wfh|work from anywhere)\b",
    re.IGNORECASE,
)
_BARE_REMOTE_IN_DESCRIPTION = re.compile(r"\bremote\b", re.IGNORECASE)
_NEGATED_REMOTE_IN_DESCRIPTION = re.compile(
    r"\b(?:no|not|without|lack(?:ing)?)\s+(?:an?\s+)?(?:explicit\s+)?remote\b",
    re.IGNORECASE,
)
_HYBRID_ARRANGEMENT_PATTERN = re.compile(r"\bhybrid\b", re.IGNORECASE)
_ONSITE_ARRANGEMENT_PATTERN = re.compile(
    r"\b(?:on[- ]?site|office[- ]first|in[- ]office)\b",
    re.IGNORECASE,
)
_PLACE_FROM_DESCRIPTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(?:based|located|headquartered|hq)\s+in\s+([A-Z][\w .'-]{1,40})",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:our|the)\s+([A-Z][\w .'-]{1,30}?)\s+office\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\boffice\s+in\s+([A-Z][\w .'-]{1,40})",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bon[- ]?site\s+in\s+([A-Z][\w .'-]{1,40})",
        re.IGNORECASE,
    ),
)


def _dedupe_skills(skills: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []

    for skill in skills:
        normalized = collapse_whitespace(skill)
        if not normalized:
            continue

        key = casefold_for_match(normalized)
        if key in seen:
            continue

        seen.add(key)
        result.append(normalized)

    return result


_BULLET_LINE = re.compile(r"^[\-•*]\s+(.+)$")
_REQUIRED_SECTION = re.compile(
    r"^(?:requirements?|required(?:\s+skills)?|must[- ]haves?|"
    r"what (?:you.?ll|we) need|our requirements)\s*:?\s*$",
    re.IGNORECASE,
)
_PREFERRED_SECTION = re.compile(
    r"^(?:nice to haves?|preferred(?:\s+skills)?|plus|bonus|optional)\s*:?\s*$",
    re.IGNORECASE,
)
_PREFERRED_CUE = re.compile(
    r"\b(?:ideally|ideal|preferably|preferred|nice to have|a plus|bonus)\b",
    re.IGNORECASE,
)
_IDEALLY_CLAUSE = re.compile(
    r",?\s*\b(?:ideally|preferably)\s+(?:with\s+)?(.+)$",
    re.IGNORECASE,
)
_SKILL_LIST_CUES: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(?:experience with|knowledge of)\s+(.+)$",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:strong|solid)\s+(.+?)\s+(?:skills|background)\b",
        re.IGNORECASE,
    ),
)
_MUST_HAVE_PROSE = re.compile(
    r"\b(?:must (?:have|know)|required:)\s*(.+?)(?:\.|$)",
    re.IGNORECASE,
)
_STRONG_SKILLS_PROSE = re.compile(
    r"\b(?:strong|solid)\s+(.+?)\s+skills\b",
    re.IGNORECASE,
)
_PLUS_PROSE = re.compile(
    r"(?:experience with\s+)?(.+?)\s+(?:would be|is)\s+a plus\b",
    re.IGNORECASE,
)


def _skill_phrases_from_list_text(text: str) -> list[str]:
    """Split 'Python and TensorFlow' / 'Linux, Kubernetes, Terraform' into phrases."""
    cleaned = collapse_whitespace(text)
    if not cleaned:
        return []
    cleaned = re.sub(
        r"^(?:with|in|relevant)\s+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    parts = re.split(r"\s*(?:,|;|\band\b)\s*", cleaned, flags=re.IGNORECASE)
    phrases: list[str] = []
    for part in parts:
        phrase = part.strip(" .")
        if not phrase or len(phrase.split()) > 6:
            continue
        phrases.append(phrase)
    return phrases


def _is_short_skill_label(text: str) -> bool:
    """True for bare skill bullets like 'Python' / 'LLM applications'."""
    if re.search(r"[.!?]", text):
        return False
    return 1 <= len(text.split()) <= 5


def _skills_from_bullet(
    item: str, *, section: str | None
) -> tuple[list[str], list[str]]:
    """Pull skills from a bullet label or from skills embedded in a sentence."""
    required: list[str] = []
    preferred: list[str] = []

    ideally = _IDEALLY_CLAUSE.search(item)
    head = item
    if ideally:
        preferred.extend(_skill_phrases_from_list_text(ideally.group(1)))
        head = item[: ideally.start()].rstrip(" ,;")

    extracted = False
    for pattern in _SKILL_LIST_CUES:
        for match in pattern.finditer(head):
            required.extend(_skill_phrases_from_list_text(match.group(1)))
            extracted = True

    if not extracted and _is_short_skill_label(head):
        required.append(head)

    if section == "preferred":
        return [], _dedupe_skills([*required, *preferred])
    return required, preferred


def _skills_from_description(description: str) -> tuple[list[str], list[str]]:
    required: list[str] = []
    preferred: list[str] = []
    section: str | None = None

    for raw_line in description.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue

        if _REQUIRED_SECTION.match(stripped):
            section = "required"
            continue
        if _PREFERRED_SECTION.match(stripped):
            section = "preferred"
            continue

        bullet = _BULLET_LINE.match(stripped)
        if bullet:
            item = collapse_whitespace(bullet.group(1))
            if not item:
                continue
            bullet_required, bullet_preferred = _skills_from_bullet(
                item, section=section
            )
            required.extend(bullet_required)
            preferred.extend(bullet_preferred)
            continue

        for sentence in re.split(r"(?<=[.!?])\s+", stripped):
            for match in _MUST_HAVE_PROSE.finditer(sentence):
                required.extend(_skill_phrases_from_list_text(match.group(1)))
            for match in _STRONG_SKILLS_PROSE.finditer(sentence):
                required.extend(_skill_phrases_from_list_text(match.group(1)))
            for match in _PLUS_PROSE.finditer(sentence):
                preferred.extend(_skill_phrases_from_list_text(match.group(1)))

    return required, preferred


def _job_corpus(job: JobDescription) -> str:
    return "\n".join(part for part in [job.title, job.description] if part)


def _signals_from_labeled_patterns(
    corpus: str, patterns: list[PatternLabel]
) -> list[str]:
    signals: list[str] = []

    for pattern, label in patterns:
        for match in pattern.finditer(corpus):
            signals.append(label or collapse_whitespace(match.group(0)))

    return signals


def _seniority_signals_from_job(job: JobDescription) -> list[str]:
    signals: list[str] = []

    if job.seniority:
        signals.append(job.seniority)

    corpus = _job_corpus(job)
    for match in _YEARS_EXPERIENCE_PATTERN.finditer(corpus):
        signals.append(collapse_whitespace(match.group(0)))

    for match in _SENIORITY_LEVEL_PATTERN.finditer(corpus):
        signals.append(collapse_whitespace(match.group(0)))

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


def work_arrangements_from_job(job: JobDescription) -> list[str]:
    location = job.location or ""
    description = job.description
    modes: list[str] = []

    location_has_arrangement = bool(
        _REMOTE_ARRANGEMENT_IN_LOCATION.search(location)
        or _HYBRID_ARRANGEMENT_PATTERN.search(location)
        or _ONSITE_ARRANGEMENT_PATTERN.search(location)
    )

    if _REMOTE_ARRANGEMENT_IN_LOCATION.search(location):
        modes.append("remote")
    if _HYBRID_ARRANGEMENT_PATTERN.search(location):
        modes.append("hybrid")
    if _ONSITE_ARRANGEMENT_PATTERN.search(location):
        modes.append("onsite")

    if not location_has_arrangement:
        if _REMOTE_ARRANGEMENT_IN_DESCRIPTION.search(description) or (
            _BARE_REMOTE_IN_DESCRIPTION.search(description)
            and not _NEGATED_REMOTE_IN_DESCRIPTION.search(description)
        ):
            modes.append("remote")
        if _HYBRID_ARRANGEMENT_PATTERN.search(description):
            modes.append("hybrid")
        if _ONSITE_ARRANGEMENT_PATTERN.search(description):
            modes.append("onsite")
    else:
        # Metadata already set arrangements; still pick up description-only extras.
        if "hybrid" not in modes and _HYBRID_ARRANGEMENT_PATTERN.search(description):
            modes.append("hybrid")
        if "onsite" not in modes and _ONSITE_ARRANGEMENT_PATTERN.search(description):
            modes.append("onsite")
        if "remote" not in modes and _REMOTE_ARRANGEMENT_IN_DESCRIPTION.search(
            description
        ):
            modes.append("remote")

    return _dedupe_skills(modes)


def _clean_place(value: str) -> str:
    normalized = (
        value.replace("·", " ").replace("/", " ").replace("|", " ").replace("-", " ")
    )
    parts: list[str] = []
    for raw in normalized.split():
        part = raw.strip("()[]{},.")
        if not part:
            continue
        if part.casefold() in LOCATION_NOISE_WORDS:
            continue
        parts.append(part)
    return collapse_whitespace(" ".join(parts))


def location_signals_from_job(job: JobDescription) -> list[str]:
    """Places from Location metadata, or from description when metadata is empty."""
    if job.location and job.location.strip():
        cleaned = _clean_place(job.location)
        return [cleaned] if cleaned else []

    places: list[str] = []
    for pattern in _PLACE_FROM_DESCRIPTION_PATTERNS:
        for match in pattern.finditer(job.description):
            cleaned = _clean_place(match.group(1))
            if cleaned:
                places.append(cleaned)
    return _dedupe_skills(places)


def _missing_signals_from_job(
    job: JobDescription, *, work_arrangements: list[str]
) -> list[str]:
    missing: list[str] = []
    corpus = _job_corpus(job)

    if (
        not job.seniority
        and not _SENIORITY_LEVEL_PATTERN.search(corpus)
        and not _YEARS_EXPERIENCE_PATTERN.search(corpus)
    ):
        missing.append("seniority level")

    if not work_arrangements and not _has_remote_policy(job, corpus):
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
    required_keys = {casefold_for_match(skill) for skill in required_skills}
    preferred_skills = [
        skill
        for skill in _dedupe_skills(signals.preferred_skills)
        if casefold_for_match(skill) not in required_keys
    ]

    return JobSignals(
        required_skills=required_skills,
        preferred_skills=preferred_skills,
        seniority_signals=_dedupe_skills(signals.seniority_signals),
        production_expectations=_dedupe_skills(signals.production_expectations),
        work_arrangements=_dedupe_skills(signals.work_arrangements),
        location_signals=_dedupe_skills(signals.location_signals),
        risk_indicators=_dedupe_skills(signals.risk_indicators),
        missing_signals=_dedupe_skills(signals.missing_signals),
    )


def extract_job_signals(job: JobDescription) -> JobSignals:
    description_required, description_preferred = _skills_from_description(
        job.description
    )
    work_arrangements = work_arrangements_from_job(job)

    return _normalize_job_signals(
        JobSignals(
            required_skills=description_required,
            preferred_skills=description_preferred,
            seniority_signals=_seniority_signals_from_job(job),
            production_expectations=_production_expectations_from_job(job),
            work_arrangements=work_arrangements,
            location_signals=location_signals_from_job(job),
            risk_indicators=_risk_indicators_from_job(job),
            missing_signals=_missing_signals_from_job(
                job, work_arrangements=work_arrangements
            ),
        )
    )
