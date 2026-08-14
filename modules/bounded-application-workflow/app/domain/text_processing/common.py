from __future__ import annotations

import re
from typing import Iterable


def collapse_whitespace(value: str) -> str:
    return " ".join(value.split())


def normalize_for_match(value: str) -> str:
    return collapse_whitespace(value).casefold()


def dedupe_phrases(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = collapse_whitespace(value)
        if not normalized:
            continue
        key = normalize_for_match(normalized)
        if key in seen:
            continue
        seen.add(key)
        result.append(normalized)
    return result


_LIST_SEPARATOR = re.compile(
    r"\s*(?:,|;|\s/\s|\band\b|\bor\b)\s*",
    re.IGNORECASE,
)
_FILLER_PREFIX = re.compile(
    r"^(?:some|plus(?:\s+some)?|including|relevant|strong|solid|"
    r"with|in|etc\.?)\s+",
    re.IGNORECASE,
)
_CONTACT_LINE = re.compile(
    r"@|https?://|linkedin|github|\b[\d+().\s-]{8,}\b",
    re.IGNORECASE,
)
_BULLET_LINE = re.compile(r"^[\-•*]\s+(.+)$")
_TOKEN = re.compile(r"[a-z0-9]+")
_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "as",
        "at",
        "be",
        "by",
        "for",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "the",
        "to",
        "with",
    }
)
# A segment that only states an arrangement carries no place name.
_ARRANGEMENT_ONLY = frozenset(
    {
        "remote",
        "remote-first",
        "fully remote",
        "hybrid",
        "onsite",
        "on-site",
        "on site",
        "office-first",
        "wfh",
    }
)
# Cross-occupation career levels. Domain-specific titles are deliberately not ranked:
# "associate", for example, means very different things in law, medicine, and retail.
_SENIORITY_TOKEN_PATTERN = re.compile(
    r"\b("
    r"vice president|entry[- ]level|mid[- ]senior|mid[- ]level|"
    r"apprentice|trainee|intern|junior|intermediate|journeyman|senior|"
    r"supervisor|staff|principal|(?:team\s+)?lead|manager|head|director|"
    r"executive|mid"
    r")\b",
    re.IGNORECASE,
)


def strip_fillers(phrase: str) -> str:
    cleaned = collapse_whitespace(phrase).strip(" .")
    while True:
        stripped = _FILLER_PREFIX.sub("", cleaned, count=1).strip(" .")
        if stripped == cleaned:
            return stripped
        cleaned = stripped


def phrases_from_list(list_text: str) -> list[str]:
    """Split a delimited list of capabilities or qualifications into phrases."""
    cleaned = strip_fillers(list_text)
    if not cleaned:
        return []
    phrases: list[str] = []
    for part in _LIST_SEPARATOR.split(cleaned):
        phrase = strip_fillers(part)
        if not phrase or len(phrase.split()) > 6:
            continue
        if _CONTACT_LINE.search(phrase):
            continue
        phrases.append(phrase)
    return phrases


def is_short_skill_label(skill_label: str) -> bool:
    if re.search(r"[.!?]", skill_label):
        return False
    return 1 <= len(skill_label.split()) <= 6


def text_tokens(value: str) -> set[str]:
    return {
        token
        for token in _TOKEN.findall(value.casefold())
        if token not in _STOPWORDS
    }


def is_arrangement_only(segment: str) -> bool:
    return normalize_for_match(segment) in _ARRANGEMENT_ONLY
