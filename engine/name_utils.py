"""Shared material-name normalisation across all engine modules.

Centralises the canonical form so that cross-module lookups
(ODT, VP, profiles, SAR, psychophysics, synergy graph, etc.)
never fail due to Title Case vs lowercase vs trailing whitespace.

Usage:
    from engine.name_utils import normalize_name, names_match

    key = normalize_name("Iso E Super")   # -> "iso e super"
    if names_match(user_input, profile_key):
        ...
"""

from __future__ import annotations

import re

# Canonical aliases – map common spelling variants to a single form.
# All keys **must** already be lowercase-stripped.
_ALIASES: dict[str, str] = {
    "d-limonene": "limonene",
    "ambrox": "ambrox super",
    "ambrox dl": "ambrox super",
    "iso-e-super": "iso e super",
    "isoesuper": "iso e super",
    "benz salicylate": "benzyl salicylate",
    "benz sal": "benzyl salicylate",
    "hex sal": "hexyl salicylate",
    "hexsal": "hexyl salicylate",
    "eb": "ethylene brassylate",
    "hedione hc": "hedione",
}


def normalize_name(name: str) -> str:
    """Return the canonical lowercase key for *name*.

    Steps:
        1. Strip leading/trailing whitespace.
        2. Collapse internal whitespace to a single space.
        3. Lower-case the result.
        4. Resolve known aliases.
    """
    if not name:
        return ""
    n = re.sub(r"\s+", " ", name.strip()).lower()
    return _ALIASES.get(n, n)


def names_match(a: str, b: str) -> bool:
    """Return True when *a* and *b* resolve to the same canonical name."""
    return normalize_name(a) == normalize_name(b)
