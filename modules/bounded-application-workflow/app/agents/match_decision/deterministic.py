from app.domain.models import (
    DecisionType,
    JobSignals,
    MatchDecision,
    UserProfile,
)
from app.domain.text_processing import (
    coverage_ratio,
    highest_ranked_seniority,
    location_aligned,
    partition_text_matches,
    seniority_labels_compatible,
    seniority_rank,
    work_arrangement_aligned,
)

# Soft score weights sum to 1.0. Work/location are hard gates in decision_from_match.
_REQUIRED_WEIGHT = 0.70
_PREFERRED_WEIGHT = 0.15
_EXPERIENCE_WEIGHT = 0.15
_EXPERIENCE_RISK_MIN_MISSING = 3

# MVP thresholds — docs/PRD.md
_STRONG_MIN = 0.90
_PREPARE_MIN = 0.75
_QUEUE_MIN = 0.55


def _profile_sources(profile: UserProfile) -> list[str]:
    return [
        *profile.skills,
        *profile.relevant_experience,
        *profile.work_preferences,
    ]





def _assess_work_and_location_alignment(
    profile: UserProfile,
    job_signals: JobSignals,
) -> tuple[list[str], list[str], bool, bool]:
    reasons: list[str] = []
    risks: list[str] = []
    job_modes = set(job_signals.work_arrangements)
    job_place = " ".join(job_signals.location_signals).strip()
    work_ok = work_arrangement_aligned(profile.work_preferences, job_modes)
    location_ok = location_aligned(profile.location, job_modes, job_place)
    prefs = sorted(profile.work_preferences) or ["No preference"]
    modes = sorted(job_modes) or ["No preference"]
    profile_location = profile.location.strip() or "No location"
    job_location = job_place or "No location"

    if work_ok:
        reasons.append(
            "Work arrangement aligns "
            f"(profile prefs: {', '.join(prefs)}; job: {', '.join(modes)})."
        )
    else:
        risks.append(
            "Work arrangement mismatch "
            f"(profile prefs: {', '.join(prefs)}; job: {', '.join(modes)})."
        )

    if location_ok:
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
        if "onsite" in job_modes:
            severity = (
                "On-site role is missing a job location"
                if not job_place
                else "On-site role with incompatible locations"
            )
        elif "hybrid" in job_modes:
            severity = (
                "Hybrid role is missing a job location"
                if not job_place
                else "Hybrid role with incompatible locations"
            )
        else:
            severity = "Location mismatch"
        risks.append(
            f"{severity} "
            f"(profile: {profile_location}; job: {job_location})."
        )
    return reasons, risks, work_ok, location_ok


def _assess_seniority_alignment(
    profile: UserProfile,
    job_signals: JobSignals,
) -> tuple[list[str], list[str], bool]:
    reasons: list[str] = []
    risks: list[str] = []
    severe_mismatch = False

    job_seniority = highest_ranked_seniority(job_signals.seniority_signals)
    if not job_seniority:
        return reasons, risks, severe_mismatch

    profile_rank = seniority_rank(profile.seniority)
    job_rank = seniority_rank(job_seniority)
    rank_gap = (
        None
        if profile_rank is None or job_rank is None
        else profile_rank - job_rank
    )
    if rank_gap is not None:
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

    if seniority_labels_compatible(profile.seniority, job_seniority):
        reasons.append(
            "Seniority meets job expectations "
            f"(job: {job_seniority}, profile: {profile.seniority})."
        )
    else:
        risks.append(
            f"Job expects {job_seniority}; profile indicates {profile.seniority}."
        )
    return reasons, risks, severe_mismatch


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
    if missing:
        risks.append(
            "Missing relevant experience for: "
            f"{', '.join(missing)}."
        )
    return reasons, risks


def match_and_decide(
    user_profile: UserProfile,
    job_signals: JobSignals,
) -> MatchDecision:
    required_matched, required_missing = partition_text_matches(
        _profile_sources(user_profile), job_signals.required_skills
    )
    preferred_matched, _ = partition_text_matches(
        _profile_sources(user_profile), job_signals.preferred_skills
    )
    experience_matched, experience_missing = partition_text_matches(
        user_profile.relevant_experience, job_signals.experience_requirements
    )

    score = min(
        1.0,
        _REQUIRED_WEIGHT
        * coverage_ratio(len(required_matched), len(job_signals.required_skills))
        + _PREFERRED_WEIGHT
        * coverage_ratio(len(preferred_matched), len(job_signals.preferred_skills))
        + _EXPERIENCE_WEIGHT
        * coverage_ratio(
            len(experience_matched), len(job_signals.experience_requirements)
        )
    )

    reasons: list[str] = []
    risks: list[str] = []
    if required_matched:
        reasons.append(
            f"Matched {len(required_matched)} of "
            f"{len(job_signals.required_skills)} required skills."
        )
    if preferred_matched:
        reasons.append(f"Matched {len(preferred_matched)} preferred skills.")
    if required_missing:
        risks.append(f"Missing required skills: {', '.join(required_missing)}.")

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

    location_reasons, location_risks, work_ok, location_ok = (
        _assess_work_and_location_alignment(user_profile, job_signals)
    )
    reasons.extend(location_reasons)
    risks.extend(location_risks)

    rounded_score = round(score, 2)
    return MatchDecision(
        decision=decision_from_match(
            rounded_score,
            severe_seniority_mismatch=severe_seniority_mismatch,
            work_arrangement_aligned=work_ok,
            location_aligned=location_ok,
        ),
        score=rounded_score,
        required_skills_matched=required_matched,
        required_skills_missing=required_missing,
        preferred_skills_matched=preferred_matched,
        experience_requirements_matched=experience_matched,
        experience_requirements_missing=experience_missing,
        work_arrangement_aligned=work_ok,
        location_aligned=location_ok,
        severe_seniority_mismatch=severe_seniority_mismatch,
        reasons=reasons,
        risks=risks,
    )


def decision_from_score(score: float) -> DecisionType:
    if score >= _STRONG_MIN:
        return DecisionType.STRONG
    if score >= _PREPARE_MIN:
        return DecisionType.PREPARE
    if score >= _QUEUE_MIN:
        return DecisionType.QUEUE
    return DecisionType.SKIP


def decision_from_match(
    score: float,
    *,
    severe_seniority_mismatch: bool = False,
    work_arrangement_aligned: bool = True,
    location_aligned: bool = True,
) -> DecisionType:
    if severe_seniority_mismatch or not work_arrangement_aligned:
        return DecisionType.SKIP
    decision = decision_from_score(score)
    if not location_aligned and decision in {DecisionType.STRONG, DecisionType.PREPARE}:
        return DecisionType.QUEUE
    return decision
