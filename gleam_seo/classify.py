"""Track classification (Rule 2 of the Routine prompt).

Every query belongs to exactly one track, and the tracks are never averaged
together:

* ``brand``          — anything containing "gleam". Terms containing "gleam"
                       are brand *defence*, never conquest. "gleam alternative"
                       is brand; "rafflecopter alternative" is conquest and
                       therefore commercial.
* ``commercial``     — tool/software/platform/app/picker/generator/maker/
                       websites, plus the action phrasings run a / host a /
                       create a. Conquest ("<competitor> alternative") lands
                       here too.
* ``informational``  — ideas / examples / how to / rules / legal.
* ``other``          — matched none of the above signals.
* ``excluded``       — irrelevant intent; dropped from the report entirely.

Precedence is deliberate: exclusions first, then brand (so "gleam tool" is
brand, not commercial), then commercial, then informational.
"""

from __future__ import annotations

import re
from enum import Enum


class Track(str, Enum):
    BRAND = "brand"
    COMMERCIAL = "commercial"
    INFORMATIONAL = "informational"
    OTHER = "other"
    EXCLUDED = "excluded"


BRAND_TOKEN = "gleam"

# Irrelevant intent — dropped before anything else. None of these contain the
# brand token, so ordering against the brand check is unambiguous.
EXCLUSIONS: tuple[str, ...] = (
    "software giveaway",
    "software giveaways",
    "free software",
    "giveaway of the day",
    "steam key",
    "nft giveaway",
    "crypto giveaway",
)

# Single-word commercial signals. Matched on whole words, and also on their
# simple plural (tool -> tools) so "giveaway tools" still classifies.
_COMMERCIAL_WORDS: tuple[str, ...] = (
    "tool",
    "software",
    "platform",
    "app",
    "picker",
    "generator",
    "maker",
    "websites",
    "website",
    # Conquest: "<competitor> alternative" is commercial intent. "gleam
    # alternative" never reaches here — the brand check catches it first.
    "alternative",
    "competitor",
    "competitors",
)

# Multi-word commercial signals (action phrasings). Matched as substrings.
_COMMERCIAL_PHRASES: tuple[str, ...] = (
    "run a",
    "host a",
    "create a",
)

_INFORMATIONAL_WORDS: tuple[str, ...] = (
    "ideas",
    "examples",
    "example",
    "rules",
    "legal",
)

_INFORMATIONAL_PHRASES: tuple[str, ...] = (
    "how to",
)


def normalize(query: str) -> str:
    """Lower-case and collapse internal whitespace."""

    return " ".join(query.lower().split())


def _has_word(words: set[str], signal: str) -> bool:
    return signal in words or (signal + "s") in words


def is_excluded(query: str) -> bool:
    """True if the query is irrelevant intent and must be dropped entirely."""

    n = normalize(query)
    return any(phrase in n for phrase in EXCLUSIONS)


def classify(query: str) -> Track:
    """Return the :class:`Track` for a query."""

    n = normalize(query)

    if any(phrase in n for phrase in EXCLUSIONS):
        return Track.EXCLUDED

    # Rule 2: anything containing "gleam" is brand, full stop.
    if BRAND_TOKEN in n:
        return Track.BRAND

    words = set(re.findall(r"[a-z0-9.]+", n))

    # "how to ..." is research intent even when a commercial verb follows
    # ("how to run a giveaway"), so it is checked before the action phrasings.
    if any(phrase in n for phrase in _INFORMATIONAL_PHRASES):
        return Track.INFORMATIONAL

    if any(phrase in n for phrase in _COMMERCIAL_PHRASES):
        return Track.COMMERCIAL
    if any(_has_word(words, w) for w in _COMMERCIAL_WORDS):
        return Track.COMMERCIAL

    if any(_has_word(words, w) for w in _INFORMATIONAL_WORDS):
        return Track.INFORMATIONAL

    return Track.OTHER
