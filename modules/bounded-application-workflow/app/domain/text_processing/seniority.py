from __future__ import annotations

from typing import Iterable

from app.domain.text_processing.common import (
    _SENIORITY_TOKEN_PATTERN,
    collapse_whitespace,
)

_SENIORITY_ALIASES = {
    "entry-level": "entry",
    "entry level": "entry",
    "mid-level": "mid",
    "mid level": "mid",
    "team lead": "lead",
    "vice president": "executive",
}
_SENIORITY_RANKS: tuple[tuple[str, int], ...] = (
    ("mid-senior", 3),
    ("apprentice", 1),
    ("trainee", 1),
    ("intern", 1),
    ("entry", 1),
    ("junior", 1),
    ("intermediate", 2),
    ("journeyman", 3),
    ("supervisor", 4),
    ("staff", 5),
    ("principal", 5),
    ("manager", 5),
    ("head", 5),
    ("director", 6),
    ("executive", 7),
    ("senior", 4),
    ("lead", 4),
    ("mid", 2),
)


def canonicalize_seniority(value: str) -> str:
    normalized = collapse_whitespace(value).casefold()
    return _SENIORITY_ALIASES.get(normalized, normalized)


def seniority_rank(value: str) -> int | None:
    normalized = canonicalize_seniority(value)
    for label, rank in _SENIORITY_RANKS:
        if label in normalized:
            return rank
    return None


def seniority_tokens_from_text(text: str) -> list[str]:
    return [
        collapse_whitespace(match.group(1))
        for match in _SENIORITY_TOKEN_PATTERN.finditer(text)
    ]


def highest_ranked_seniority(values: Iterable[str]) -> str | None:
    """Pick the highest-ranked value, ignoring the ones without a known rank."""
    best: tuple[int, str] | None = None
    for value in values:
        rank = seniority_rank(value)
        if rank is None:
            continue
        if best is None or rank > best[0]:
            best = (rank, value)
    return best[1] if best else None


def seniority_from_text(text: str) -> str:
    """Pick the highest-ranked seniority level mentioned in the text."""
    highest = highest_ranked_seniority(seniority_tokens_from_text(text))
    return canonicalize_seniority(highest) if highest else ""
