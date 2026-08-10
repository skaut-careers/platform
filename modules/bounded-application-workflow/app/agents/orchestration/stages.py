"""Canonical LangGraph node / stage ids for the product workflow."""

PROFILE_EXTRACTION = "profile_extraction"
SIGNAL_EXTRACTION = "signal_extraction"
PROFILE_MATCHING = "profile_matching"
POLICY_APPLICATION = "policy_application"
DECISION = "decision"

CANONICAL_STAGES = (
    PROFILE_EXTRACTION,
    SIGNAL_EXTRACTION,
    PROFILE_MATCHING,
    POLICY_APPLICATION,
    DECISION,
)

__all__ = [
    "CANONICAL_STAGES",
    "DECISION",
    "POLICY_APPLICATION",
    "PROFILE_EXTRACTION",
    "PROFILE_MATCHING",
    "SIGNAL_EXTRACTION",
]
