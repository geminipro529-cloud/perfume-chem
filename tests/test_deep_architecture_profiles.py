"""Profile-coverage tests for the Deep Architecture capability (Phase 1)."""
from __future__ import annotations

import json
from pathlib import Path

from engine.knowledge.deep_architecture import (
    DIMENSIONS,
    PROFILES_PATH,
    resolve_profile,
)
from engine.knowledge.perfume_taxonomy import FAMILY_SUBFAMILY_MAP, PerfumeFamily


def test_all_thirteen_families_have_profiles():
    for family in PerfumeFamily:
        profile = resolve_profile(family.value)
        assert profile.level == "family", family
        assert set(profile.targets) == set(DIMENSIONS)


def test_every_subfamily_resolves_to_its_family():
    for family, subfamilies in FAMILY_SUBFAMILY_MAP.items():
        for subfamily in subfamilies:
            profile = resolve_profile(getattr(subfamily, "value", subfamily))
            assert profile.family == getattr(family, "value", family)
            assert profile.level == "subfamily"


def test_archetype_overrides_resolve_with_family():
    payload = json.loads(Path(PROFILES_PATH).read_text(encoding="utf-8"))
    for key, override in payload["archetype_overrides"].items():
        profile = resolve_profile(key)
        assert profile.level == "archetype", key
        assert profile.family == override["family"], key


def test_tolerant_ranges_are_ordered_and_bounded():
    payload = json.loads(Path(PROFILES_PATH).read_text(encoding="utf-8"))
    for key in [f.value for f in PerfumeFamily] + list(payload["archetype_overrides"]):
        profile = resolve_profile(key)
        for dim in DIMENSIONS:
            spec = profile.targets[dim]
            assert 0 <= spec.minimum <= spec.target <= spec.maximum <= 100, (key, dim)


def test_unknown_key_falls_back_to_generic():
    profile = resolve_profile("__nonexistent_profile__")
    assert profile.level == "generic"
    assert set(profile.targets) == set(DIMENSIONS)
