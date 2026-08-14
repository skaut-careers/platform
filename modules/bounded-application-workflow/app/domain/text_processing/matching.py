from __future__ import annotations

from typing import Iterable

from app.domain.text_processing.common import text_tokens

# Soft words that inflate overlap without proving a real match
# ("Python experience" vs "Java experience" should not match on "experience").
_MATCH_QUALIFIERS = frozenset(
    {"background", "experience", "expertise", "knowledge", "proficiency", "skills"}
)


def text_matches_capability(evidence: str, requirement: str) -> bool:
    evidence_text = evidence.casefold().strip()
    requirement_text = requirement.casefold().strip()
    if requirement_text in evidence_text:
        return True
    meaningful_requirement = text_tokens(requirement_text) - _MATCH_QUALIFIERS
    if not meaningful_requirement:
        return True
    meaningful_overlap = meaningful_requirement & text_tokens(evidence_text)
    return len(meaningful_overlap) / len(meaningful_requirement) >= 0.67


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
