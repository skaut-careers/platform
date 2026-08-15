from __future__ import annotations

from typing import Iterable

from app.domain.text_processing.common import text_tokens
from app.domain.text_processing.locations import locations_compatible
from app.domain.text_processing.seniority import canonicalize_seniority

_MATCH_QUALIFIERS = frozenset(
    {"background", "experience", "expertise", "knowledge", "proficiency", "skills"}
)
_CAPABILITY_MATCH_MIN = 0.67


def coverage_ratio(matched_count: int, total_count: int) -> float:
    if total_count == 0:
        return 1.0
    return matched_count / total_count


def text_matches_capability(evidence: str, requirement: str) -> bool:
    evidence_text = evidence.casefold().strip()
    requirement_text = requirement.casefold().strip()
    if requirement_text in evidence_text:
        return True
    meaningful_requirement = text_tokens(requirement_text) - _MATCH_QUALIFIERS
    if not meaningful_requirement:
        return True
    meaningful_overlap = meaningful_requirement & text_tokens(evidence_text)
    return (
        coverage_ratio(len(meaningful_overlap), len(meaningful_requirement))
        >= _CAPABILITY_MATCH_MIN
    )


def partition_text_matches(
    evidence_phrases: Iterable[str], requirements: Iterable[str]
) -> tuple[list[str], list[str]]:
    """Split job requirements into those covered by profile evidence and those not."""
    matched: list[str] = []
    missing: list[str] = []
    for requirement in requirements:
        if not requirement.strip():
            continue
        target = (
            matched
            if any(
                text_matches_capability(phrase, requirement)
                for phrase in evidence_phrases
            )
            else missing
        )
        target.append(requirement)
    return matched, missing


def work_arrangement_aligned(
    preferences: Iterable[str], job_modes: set[str]
) -> bool:
    prefs = set(preferences)
    if not job_modes or not prefs:
        return True
    return bool(prefs & job_modes)


def location_aligned(
    profile_location: str,
    job_modes: set[str],
    job_place: str,
) -> bool:
    profile_location = profile_location.strip()

    if "remote" in job_modes and "onsite" not in job_modes:
        return True
    if "onsite" in job_modes or (not job_modes and job_place):
        return locations_compatible(profile_location, job_place)
    if "hybrid" in job_modes:
        return locations_compatible(profile_location, job_place)
    return True


def seniority_labels_compatible(
    profile_seniority: str, job_seniority: str
) -> bool:
    profile_normalized = canonicalize_seniority(profile_seniority)
    job_normalized = canonicalize_seniority(job_seniority)
    return (
        profile_normalized in job_normalized
        or job_normalized in profile_normalized
    )
