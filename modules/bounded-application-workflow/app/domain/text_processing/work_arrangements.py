from __future__ import annotations

import re

from app.domain.text_processing.common import dedupe_phrases

_REMOTE_EXPLICIT = re.compile(
    r"\b(?:remote[- ]first|fully remote|work from home|wfh|work from anywhere)\b",
    re.IGNORECASE,
)
_BARE_REMOTE = re.compile(r"\bremote\b", re.IGNORECASE)
_NEGATED_REMOTE = re.compile(
    r"\b(?:no|not|without|lack(?:ing)?)\s+(?:an?\s+)?(?:explicit\s+)?remote\b",
    re.IGNORECASE,
)
_HYBRID = re.compile(r"\bhybrid\b", re.IGNORECASE)
_ONSITE = re.compile(
    r"\b(?:on[- ]?site|office[- ]first|in[- ]office)\b",
    re.IGNORECASE,
)


def work_arrangements_from_text(text: str) -> list[str]:
    modes: list[str] = []
    if _REMOTE_EXPLICIT.search(text) or (
        _BARE_REMOTE.search(text) and not _NEGATED_REMOTE.search(text)
    ):
        modes.append("remote")
    if _HYBRID.search(text):
        modes.append("hybrid")
    if _ONSITE.search(text):
        modes.append("onsite")
    return dedupe_phrases(modes)
