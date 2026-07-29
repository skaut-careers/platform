def collapse_whitespace(text: str) -> str:
    return " ".join(text.split())


def casefold_for_match(text: str) -> str:
    return collapse_whitespace(text).casefold()


# Arrangement / region tokens stripped when comparing or cleaning place strings.
LOCATION_NOISE_WORDS = frozenset(
    {
        "remote",
        "hybrid",
        "onsite",
        "on-site",
        "on",
        "site",
        "office",
        "first",
        "fully",
        "based",
        "work",
        "from",
        "home",
        "wfh",
        "anywhere",
        "europe",
        "emea",
        "eu",
        "worldwide",
        "global",
        "timezone",
        "preferred",
    }
)
