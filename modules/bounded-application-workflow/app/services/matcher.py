import re
from typing import Iterable

from app.domain.job_signals import JobSignals
from app.domain.models import JobDescription, ProfileMatchResult, UserProfile

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
_STOPWORDS = frozenset({"and", "the", "for", "with", "or"})
_GENERIC_TOKENS = frozenset(
    {
        "engineer",
        "engineering",
        "developer",
        "development",
        "systems",
        "system",
        "senior",
        "junior",
        "lead",
        "staff",
        "manager",
        "experience",
        "product",
        "role",
        "roles",
    }
)


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in _TOKEN_PATTERN.findall(text.lower())
        if len(token) > 2 and token not in _STOPWORDS
    }


def _profile_corpus(profile: UserProfile) -> str:
    parts = [
        *profile.skills,
        *profile.target_roles,
        *profile.work_preferences,
        profile.experience_summary or "",
    ]
    return " ".join(parts).lower()


def _profile_sources(profile: UserProfile) -> list[str]:
    return [
        *profile.skills,
        *profile.target_roles,
        *profile.work_preferences,
        profile.experience_summary or "",
    ]


def _specific_tokens(tokens: set[str]) -> set[str]:
    return tokens - _GENERIC_TOKENS


def _skill_matches_in_text(text: str, skill: str) -> bool:
    normalized_text = text.lower().strip()
    normalized_skill = skill.lower().strip()
    if not normalized_skill:
        return False

    if normalized_skill in normalized_text:
        return True

    skill_tokens = _tokens(normalized_skill)
    if not skill_tokens:
        return False

    text_tokens = _tokens(normalized_text)
    overlap = skill_tokens & text_tokens
    if not overlap:
        return False

    if len(skill_tokens) == 1:
        return True

    specific_skill = _specific_tokens(skill_tokens)
    specific_overlap = _specific_tokens(overlap)
    if specific_skill:
        return len(specific_overlap) / len(specific_skill) >= 0.5

    return len(overlap) == len(skill_tokens)


def _skill_matches(profile: UserProfile, skill: str) -> bool:
    for source in _profile_sources(profile):
        if source and _skill_matches_in_text(source, skill):
            return True
    #return _skill_matches_in_text(_profile_corpus(profile), skill)


def _partition_skills(
    profile: UserProfile, skills: Iterable[str]
) -> tuple[list[str], list[str]]:
    matched: list[str] = []
    missing: list[str] = []

    for skill in skills:
        if _skill_matches(profile, skill):
            matched.append(skill)
        else:
            missing.append(skill)

    return matched, missing


def _role_aligned(profile: UserProfile, job: JobDescription) -> bool:
    job_text = f"{job.title} {job.description}".lower()
    job_title_tokens = _specific_tokens(_tokens(job.title))

    for role in profile.target_roles:
        role_lower = role.lower().strip()
        if not role_lower:
            continue

        if role_lower in job_text:
            return True

        role_tokens = _specific_tokens(_tokens(role_lower))
        if role_tokens and role_tokens & job_title_tokens:
            return True

    profile_tokens = _specific_tokens(_tokens(_profile_corpus(profile)))
    shared_title_tokens = profile_tokens & job_title_tokens
    return len(shared_title_tokens) >= 2


def _coverage_ratio(matched_count: int, total_count: int) -> float:
    if total_count == 0:
        return 1.0
    return matched_count / total_count


# Score weights sum to 1.0 — production and seniority are lighter than required skills.
_REQUIRED_WEIGHT = 0.57
_PREFERRED_WEIGHT = 0.10
_ROLE_WEIGHT = 0.15
_PRODUCTION_WEIGHT = 0.08
_SENIORITY_WEIGHT = 0.10
_PRODUCTION_RISK_MIN_MISSING = 2


_SENIORITY_RANKS: list[tuple[str, int]] = [
    ("mid-senior", 3),
    ("mid-level", 2),
    ("junior", 1),
    ("staff", 5),
    ("principal", 5),
    ("director", 6),
    ("senior", 4),
    ("lead", 4),
    ("mid", 2),
]


def _normalize_seniority(value: str) -> str:
    return " ".join(value.lower().split())


def _seniority_rank(value: str) -> int | None:
    normalized = _normalize_seniority(value)
    for label, rank in _SENIORITY_RANKS:
        if label in normalized:
            return rank
    return None


def _primary_job_seniority(
    job: JobDescription, signals: JobSignals
) -> str | None:
    if job.seniority:
        return job.seniority

    for signal in signals.seniority_signals:
        if _seniority_rank(signal) is not None:
            return signal

    return None


def _seniority_alignment_ratio(
    profile: UserProfile,
    job: JobDescription,
    signals: JobSignals,
) -> float:
    job_seniority = _primary_job_seniority(job, signals)
    if not job_seniority:
        return 1.0

    profile_rank = _seniority_rank(profile.seniority)
    job_rank = _seniority_rank(job_seniority)

    if profile_rank is not None and job_rank is not None:
        rank_gap = profile_rank - job_rank

        if rank_gap == 0:
            return 1.0
        return 0.0

    profile_normalized = _normalize_seniority(profile.seniority)
    job_normalized = _normalize_seniority(job_seniority)
    if profile_normalized in job_normalized or job_normalized in profile_normalized:
        return 1.0
    return 0.0


def _production_alignment_ratio(
    signals: JobSignals,
    matched: list[str],
) -> float:
    if not signals.production_expectations:
        return 1.0

    return _coverage_ratio(len(matched), len(signals.production_expectations))


def _production_gap_is_material(matched: list[str], missing: list[str]) -> bool:
    total = len(matched) + len(missing)
    if total == 0:
        return False

    if len(missing) >= _PRODUCTION_RISK_MIN_MISSING:
        return True

    return len(missing) > total / 2


def _assess_seniority_alignment(
    profile: UserProfile,
    job: JobDescription,
    signals: JobSignals,
) -> tuple[list[str], list[str], bool]:
    reasons: list[str] = []
    risks: list[str] = []
    severe_mismatch = False

    job_seniority = _primary_job_seniority(job, signals)
    if not job_seniority:
        return reasons, risks, severe_mismatch

    profile_rank = _seniority_rank(profile.seniority)
    job_rank = _seniority_rank(job_seniority)

    if profile_rank is not None and job_rank is not None:
        rank_gap = profile_rank - job_rank

        if rank_gap <= -2:
            severe_mismatch = True
            risks.append(
                "Profile seniority is more than one level below job expectations "
                f"(job: {job_seniority}, profile: {profile.seniority}); "
                "this role is not a realistic fit."
            )
        elif rank_gap == -1:
            risks.append(
                f"Job expects {job_seniority}; profile indicates {profile.seniority}."
            )
        elif rank_gap >= 2:
            severe_mismatch = True
            risks.append(
                "Profile seniority exceeds job expectations by more than one level "
                f"(job: {job_seniority}, profile: {profile.seniority}); "
                "this role is not a realistic fit."
            )
        else:
            reasons.append(
                "Seniority meets job expectations "
                f"(job: {job_seniority}, profile: {profile.seniority})."
            )
        return reasons, risks, severe_mismatch

    profile_normalized = _normalize_seniority(profile.seniority)
    job_normalized = _normalize_seniority(job_seniority)
    if profile_normalized in job_normalized or job_normalized in profile_normalized:
        reasons.append(
            "Seniority meets job expectations "
            f"(job: {job_seniority}, profile: {profile.seniority})."
        )
    else:
        risks.append(
            f"Job expects {job_seniority}; profile indicates {profile.seniority}."
        )

    return reasons, risks, severe_mismatch


def _production_expectation_matches(profile: UserProfile, expectation: str) -> bool:
    for item in profile.production_experience:
        if item and _skill_matches_in_text(item, expectation):
            return True
    return False


def _partition_production_expectations(
    profile: UserProfile, expectations: Iterable[str]
) -> tuple[list[str], list[str]]:
    matched: list[str] = []
    missing: list[str] = []

    for expectation in expectations:
        if _production_expectation_matches(profile, expectation):
            matched.append(expectation)
        else:
            missing.append(expectation)

    return matched, missing


def _assess_production_alignment(
    profile: UserProfile,
    signals: JobSignals,
    matched: list[str],
    missing: list[str],
) -> tuple[list[str], list[str]]:
    if not signals.production_expectations:
        return [], []

    reasons: list[str] = []
    risks: list[str] = []

    if matched:
        reasons.append(
            "Matched "
            f"{len(matched)} of {len(signals.production_expectations)} "
            "production expectations."
        )
    if missing and _production_gap_is_material(matched, missing):
        risks.append(
            "Missing production experience for: "
            f"{', '.join(missing)}."
        )

    return reasons, risks


def match_profile_to_job(
    user_profile: UserProfile,
    job_description: JobDescription,
    signals: JobSignals,
) -> ProfileMatchResult:
    required_matched, required_missing = _partition_skills(
        user_profile, signals.required_skills
    )
    preferred_matched, _ = _partition_skills(
        user_profile, signals.preferred_skills
    )

    required_ratio = _coverage_ratio(
        len(required_matched), len(signals.required_skills)
    )
    preferred_ratio = _coverage_ratio(
        len(preferred_matched), len(signals.preferred_skills)
    )
    has_target_roles = bool(user_profile.target_roles)
    role_aligned = (
        _role_aligned(user_profile, job_description) if has_target_roles else False
    )
    role_ratio = 1.0 if role_aligned else 0.0

    production_matched, production_missing = _partition_production_expectations(
        user_profile, signals.production_expectations
    )
    production_ratio = _production_alignment_ratio(signals, production_matched)
    seniority_ratio = _seniority_alignment_ratio(
        user_profile, job_description, signals
    )

    score = min(
        1.0,
        _REQUIRED_WEIGHT * required_ratio
        + _PREFERRED_WEIGHT * preferred_ratio
        + _ROLE_WEIGHT * role_ratio
        + _PRODUCTION_WEIGHT * production_ratio
        + _SENIORITY_WEIGHT * seniority_ratio,
    )

    reasons: list[str] = []
    risks: list[str] = []

    if required_matched:
        reasons.append(
            f"Matched {len(required_matched)} of {len(signals.required_skills)} required skills."
        )
    if preferred_matched:
        reasons.append(
            f"Matched {len(preferred_matched)} preferred skills."
        )
    if has_target_roles:
        if role_aligned:
            reasons.append("Job aligns with target role.")
        else:
            risks.append(
                "Job title or description does not clearly align with target roles."
            )

    if required_missing:
        risks.append(
            f"Missing required skills: {', '.join(required_missing)}."
        )

    seniority_reasons, seniority_risks, severe_seniority_mismatch = (
        _assess_seniority_alignment(user_profile, job_description, signals)
    )
    reasons.extend(seniority_reasons)
    risks.extend(seniority_risks)

    (
        production_reasons,
        production_risks,
    ) = _assess_production_alignment(
        user_profile,
        signals,
        production_matched,
        production_missing,
    )
    reasons.extend(production_reasons)
    risks.extend(production_risks)

    for indicator in signals.risk_indicators:
        risks.append(f"Job posting risk: {indicator}")

    return ProfileMatchResult(
        score=round(score, 2),
        required_skills_matched=required_matched,
        required_skills_missing=required_missing,
        preferred_skills_matched=preferred_matched,
        production_expectations_matched=production_matched,
        production_expectations_missing=production_missing,
        role_aligned=role_aligned,
        severe_seniority_mismatch=severe_seniority_mismatch,
        reasons=reasons,
        risks=risks,
    )
