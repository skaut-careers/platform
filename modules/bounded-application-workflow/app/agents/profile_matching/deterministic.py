from app.domain.models import JobSignals, ProfileMatchResult, UserProfile
from app.domain.text_processing import (
    canonicalize_seniority,
    locations_compatible,
    partition_text_matches,
    seniority_rank,
)


def _profile_sources(profile: UserProfile) -> list[str]:
    return [
        *profile.skills,
        *profile.relevant_experience,
        *profile.work_preferences,
    ]


def _partition_skills(
    profile: UserProfile, skills: list[str]
) -> tuple[list[str], list[str]]:
    return partition_text_matches(_profile_sources(profile), skills)


def _coverage_ratio(matched_count: int, total_count: int) -> float:
    if total_count == 0:
        return 1.0
    return matched_count / total_count


# Score weights sum to 1.0.
_REQUIRED_WEIGHT = 0.62
_PREFERRED_WEIGHT = 0.10
_EXPERIENCE_WEIGHT = 0.08
_SENIORITY_WEIGHT = 0.10
_WORK_ARRANGEMENT_WEIGHT = 0.05
_LOCATION_WEIGHT = 0.05
_EXPERIENCE_RISK_MIN_MISSING = 2

def _primary_job_seniority(job_signals: JobSignals) -> str | None:
    for signal in job_signals.seniority_signals:
        if seniority_rank(signal) is not None:
            return signal
    return None


def _seniority_alignment_ratio(
    profile: UserProfile,
    job_signals: JobSignals,
) -> float:
    job_seniority = _primary_job_seniority(job_signals)
    if not job_seniority:
        return 1.0

    profile_rank = seniority_rank(profile.seniority)
    job_rank = seniority_rank(job_seniority)

    if profile_rank is not None and job_rank is not None:
        rank_gap = profile_rank - job_rank

        if rank_gap == 0:
            return 1.0
        return 0.0

    profile_normalized = canonicalize_seniority(profile.seniority)
    job_normalized = canonicalize_seniority(job_seniority)
    if profile_normalized in job_normalized or job_normalized in profile_normalized:
        return 1.0
    return 0.0


def _experience_alignment_ratio(
    job_signals: JobSignals,
    matched: list[str],
) -> float:
    if not job_signals.experience_requirements:
        return 1.0

    return _coverage_ratio(len(matched), len(job_signals.experience_requirements))


def _experience_gap_is_material(matched: list[str], missing: list[str]) -> bool:
    total = len(matched) + len(missing)
    if total == 0:
        return False

    if len(missing) >= _EXPERIENCE_RISK_MIN_MISSING:
        return True

    return len(missing) > total / 2


def _work_arrangement_aligned(
    profile: UserProfile, job_modes: set[str]
) -> bool:
    prefs = set(profile.work_preferences)
    if not job_modes or not prefs:
        return True
    return bool(prefs & job_modes)


def _location_aligned(
    profile: UserProfile,
    job_modes: set[str],
    job_place: str,
) -> bool:
    profile_location = profile.location.strip()

    if "remote" in job_modes and "onsite" not in job_modes:
        return True

    if "onsite" in job_modes or (not job_modes and job_place):
        return locations_compatible(profile_location, job_place)

    if "hybrid" in job_modes:
        return locations_compatible(profile_location, job_place)

    return True


def _assess_work_and_location_alignment(
    profile: UserProfile,
    job_modes: set[str],
    job_place: str,
    *,
    work_arrangement_aligned: bool,
    location_aligned: bool,
) -> tuple[list[str], list[str]]:
    reasons: list[str] = []
    risks: list[str] = []
    prefs = sorted(profile.work_preferences) or ["unspecified"]
    modes = sorted(job_modes) or ["unspecified"]
    profile_location = profile.location.strip() or "unspecified"
    job_location = job_place or "unspecified"

    if work_arrangement_aligned:
        reasons.append(
            "Work arrangement aligns "
            f"(profile prefs: {', '.join(prefs)}; job: {', '.join(modes)})."
        )
    else:
        risks.append(
            "Work arrangement mismatch "
            f"(profile prefs: {', '.join(prefs)}; job: {', '.join(modes)})."
        )

    if location_aligned:
        if "remote" in job_modes and "onsite" not in job_modes:
            reasons.append(
                "Job is remote-capable; candidate location is not a hard constraint "
                f"(profile: {profile_location}; job: {job_location})."
            )
        else:
            reasons.append(
                "Location aligns "
                f"(profile: {profile_location}; job: {job_location})."
            )
    else:
        severity = (
            "On-site role with incompatible locations"
            if "onsite" in job_modes
            else "Location mismatch"
        )
        risks.append(
            f"{severity} "
            f"(profile: {profile_location}; job: {job_location})."
        )
    return reasons, risks


def _assess_seniority_alignment(
    profile: UserProfile,
    job_signals: JobSignals,
) -> tuple[list[str], list[str], bool]:
    reasons: list[str] = []
    risks: list[str] = []
    severe_mismatch = False

    job_seniority = _primary_job_seniority(job_signals)
    if not job_seniority:
        return reasons, risks, severe_mismatch

    profile_rank = seniority_rank(profile.seniority)
    job_rank = seniority_rank(job_seniority)

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

    profile_normalized = canonicalize_seniority(profile.seniority)
    job_normalized = canonicalize_seniority(job_seniority)
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


def _partition_experience_requirements(
    profile: UserProfile, expectations: list[str]
) -> tuple[list[str], list[str]]:
    return partition_text_matches(profile.relevant_experience, expectations)


def _assess_experience_alignment(
    job_signals: JobSignals,
    matched: list[str],
    missing: list[str],
) -> tuple[list[str], list[str]]:
    if not job_signals.experience_requirements:
        return [], []

    reasons: list[str] = []
    risks: list[str] = []

    if matched:
        reasons.append(
            "Matched "
            f"{len(matched)} of {len(job_signals.experience_requirements)} "
            "experience requirements."
        )
    if missing and _experience_gap_is_material(matched, missing):
        risks.append(
            "Missing relevant experience for: "
            f"{', '.join(missing)}."
        )

    return reasons, risks


def match_profile_to_job(
    user_profile: UserProfile,
    job_signals: JobSignals,
) -> ProfileMatchResult:
    required_matched, required_missing = _partition_skills(
        user_profile, job_signals.required_skills
    )
    preferred_matched, _ = _partition_skills(
        user_profile, job_signals.preferred_skills
    )

    required_ratio = _coverage_ratio(
        len(required_matched), len(job_signals.required_skills)
    )
    preferred_ratio = _coverage_ratio(
        len(preferred_matched), len(job_signals.preferred_skills)
    )

    experience_matched, experience_missing = _partition_experience_requirements(
        user_profile, job_signals.experience_requirements
    )
    experience_ratio = _experience_alignment_ratio(job_signals, experience_matched)
    seniority_ratio = _seniority_alignment_ratio(user_profile, job_signals)
    job_modes = set(job_signals.work_arrangements)
    job_place = " ".join(job_signals.location_signals).strip()
    work_arrangement_aligned = _work_arrangement_aligned(user_profile, job_modes)
    location_aligned = _location_aligned(user_profile, job_modes, job_place)
    work_ratio = 1.0 if work_arrangement_aligned else 0.0
    location_ratio = 1.0 if location_aligned else 0.0

    score = min(
        1.0,
        _REQUIRED_WEIGHT * required_ratio
        + _PREFERRED_WEIGHT * preferred_ratio
        + _EXPERIENCE_WEIGHT * experience_ratio
        + _SENIORITY_WEIGHT * seniority_ratio
        + _WORK_ARRANGEMENT_WEIGHT * work_ratio
        + _LOCATION_WEIGHT * location_ratio,
    )

    reasons: list[str] = []
    risks: list[str] = []

    if required_matched:
        reasons.append(
            f"Matched {len(required_matched)} of {len(job_signals.required_skills)} required skills."
        )
    if preferred_matched:
        reasons.append(
            f"Matched {len(preferred_matched)} preferred skills."
        )

    if required_missing:
        risks.append(
            f"Missing required skills: {', '.join(required_missing)}."
        )

    seniority_reasons, seniority_risks, severe_seniority_mismatch = (
        _assess_seniority_alignment(user_profile, job_signals)
    )
    reasons.extend(seniority_reasons)
    risks.extend(seniority_risks)

    experience_reasons, experience_risks = _assess_experience_alignment(
        job_signals,
        experience_matched,
        experience_missing,
    )
    reasons.extend(experience_reasons)
    risks.extend(experience_risks)

    location_reasons, location_risks = _assess_work_and_location_alignment(
        user_profile,
        job_modes,
        job_place,
        work_arrangement_aligned=work_arrangement_aligned,
        location_aligned=location_aligned,
    )
    reasons.extend(location_reasons)
    risks.extend(location_risks)

    for indicator in job_signals.risk_indicators:
        risks.append(f"Job posting risk: {indicator}")

    return ProfileMatchResult(
        score=round(score, 2),
        required_skills_matched=required_matched,
        required_skills_missing=required_missing,
        preferred_skills_matched=preferred_matched,
        experience_requirements_matched=experience_matched,
        experience_requirements_missing=experience_missing,
        work_arrangement_aligned=work_arrangement_aligned,
        location_aligned=location_aligned,
        severe_seniority_mismatch=severe_seniority_mismatch,
        reasons=reasons,
        risks=risks,
    )
