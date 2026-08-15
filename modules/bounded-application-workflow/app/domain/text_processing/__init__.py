"""Public API for deterministic text extraction and matching."""

from __future__ import annotations

from app.domain.text_processing.common import (
    collapse_whitespace,
    dedupe_phrases,
    is_arrangement_only,
    is_short_skill_label,
    normalize_for_match,
    phrases_from_list,
    strip_fillers,
    text_tokens,
)
from app.domain.text_processing.jobs import (
    experience_requirements_from_job,
    normalize_job_signals,
    seniority_signals_from_job,
    skills_from_job_text,
)
from app.domain.text_processing.locations import (
    locations_compatible,
    place_from_segment,
    places_from_text,
)
from app.domain.text_processing.matching import (
    coverage_ratio,
    location_aligned,
    partition_text_matches,
    seniority_labels_compatible,
    text_matches_capability,
    work_arrangement_aligned,
)
from app.domain.text_processing.profile import (
    location_from_profile,
    relevant_experience_from_profile,
    seniority_from_profile,
    skills_from_profile,
    work_preferences_from_profile,
)
from app.domain.text_processing.seniority import (
    canonicalize_seniority,
    highest_ranked_seniority,
    seniority_from_text,
    seniority_rank,
    seniority_tokens_from_text,
)
from app.domain.text_processing.work_arrangements import work_arrangements_from_text

__all__ = [
    "canonicalize_seniority",
    "collapse_whitespace",
    "coverage_ratio",
    "dedupe_phrases",
    "experience_requirements_from_job",
    "highest_ranked_seniority",
    "is_arrangement_only",
    "is_short_skill_label",
    "location_aligned",
    "location_from_profile",
    "locations_compatible",
    "normalize_for_match",
    "normalize_job_signals",
    "partition_text_matches",
    "place_from_segment",
    "places_from_text",
    "phrases_from_list",
    "relevant_experience_from_profile",
    "seniority_from_profile",
    "seniority_from_text",
    "seniority_labels_compatible",
    "seniority_rank",
    "seniority_signals_from_job",
    "seniority_tokens_from_text",
    "skills_from_job_text",
    "skills_from_profile",
    "strip_fillers",
    "text_matches_capability",
    "text_tokens",
    "work_arrangement_aligned",
    "work_arrangements_from_text",
    "work_preferences_from_profile",
]
