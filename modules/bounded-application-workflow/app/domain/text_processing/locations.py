from __future__ import annotations

import re

from app.domain.text_processing.common import (
    _CONTACT_LINE,
    collapse_whitespace,
    dedupe_phrases,
    is_arrangement_only,
    text_tokens,
)

_PLACE_PART_SEPARATOR = re.compile(r"\s*(?:[|•·,;/]|[–—]|\s-\s)\s*")
_PARENTHESIZED_PART = re.compile(r"\s*[(\[]([^)\]]*)[)\]]")

_PLACE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"^\s*(?:location|city|based\s+in)\s*:\s*(.+)$",
        re.IGNORECASE | re.MULTILINE,
    ),
    re.compile(r"^\s*([^\n]*\|[^\n]*)\s*$", re.MULTILINE),
    re.compile(
        r"^\s*("
        r"[A-Z][a-zA-Z][\w'-]*(?:[\s-][A-Z][a-zA-Z][\w'-]*)?,\s*"
        r"[A-Z][a-zA-Z][\w'-]*(?:[\s-][A-Z][a-zA-Z][\w'-]*)?"
        r")\s*$",
        re.MULTILINE,
    ),
    re.compile(
        r"^\s*((?:remote|hybrid)\s+(?:Europe|EMEA|EU|worldwide|global))\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    re.compile(
        r"\b(?:based|located|living)\s+in\s+([A-Z][\w .'-]{1,40})",
        re.IGNORECASE,
    ),
)
_OFFICE_PLACE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(?:our|the)\s+([A-Z][\w .'-]{1,30}?)\s+office\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:headquartered|hq)\s+in\s+([A-Z][\w .'-]{1,40})",
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


def place_from_segment(segment: str) -> str:
    text = _PARENTHESIZED_PART.sub(
        lambda match: "" if is_arrangement_only(match.group(1)) else match.group(0),
        collapse_whitespace(segment),
    )
    for part in _PLACE_PART_SEPARATOR.split(text.strip(" ,;|/.-")):
        if part and not is_arrangement_only(part) and not _CONTACT_LINE.search(part):
            return part
    return ""


def places_from_text(text: str, *, include_office_cues: bool = True) -> list[str]:
    patterns = _PLACE_PATTERNS
    if include_office_cues:
        patterns = (*_PLACE_PATTERNS, *_OFFICE_PLACE_PATTERNS)
    places: list[str] = []
    for pattern in patterns:
        for match in pattern.finditer(text):
            place = place_from_segment(match.group(1))
            if place:
                places.append(place)
    return dedupe_phrases(places)


def locations_compatible(left_location: str, right_location: str) -> bool:
    if not left_location.strip() or not right_location.strip():
        return True
    left = left_location.casefold()
    right = right_location.casefold()
    if left in right or right in left:
        return True
    return bool(text_tokens(left_location) & text_tokens(right_location))
