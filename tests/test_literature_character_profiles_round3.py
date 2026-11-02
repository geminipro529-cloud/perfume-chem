"""Sourced profiles for the 15 owned stocks the pickability audit ranked below #169 (31 Oct 2026)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.ingredient_intelligence import DIMENSIONS, get_profile
from engine.research import composition_planner as cp

ROOT = Path(__file__).resolve().parents[1] / "data" / "knowledge_graph"
ROUND3 = json.loads((ROOT / "literature_character_profiles_20261031_round3.json").read_text(encoding="utf-8"))
ENTRIES = ROUND3["profiles"]
BANNED = ("scentree", "fragrantica", "wikipedia", "scent.vn", "scribd", "336871454")


def test_counts_and_unique_keys() -> None:
    assert len(ENTRIES) == 15
    keys = [entry["profile_key"].casefold() for entry in ENTRIES]
    assert len(set(keys)) == len(keys)


@pytest.mark.parametrize("entry", ENTRIES, ids=lambda entry: entry["identity"])
def test_profile_takes_the_sourced_character_and_note(entry: dict) -> None:
    profile = get_profile(entry["profile_key"])
    assert profile is not None
    assert profile.character == entry["character"]
    assert set(profile.character) <= set(DIMENSIONS)
    assert all(0.0 < value <= 10.0 for value in profile.character.values())
    assert profile.note == entry["note"] in {"top", "heart", "base"}
    assert profile.evidence["character"]["status"] == "LITERATURE_DESCRIPTOR_RUBRIC_NOT_SENSORY_MEASUREMENT"
    assert profile.evidence["note"]["status"] == "LITERATURE_VOLATILITY_RULE"
    if entry.get("odor_description"):
        assert profile.odor_description == entry["odor_description"]


def test_every_profile_reaches_an_owned_composer_candidate() -> None:
    candidates, _, _ = cp._load_candidates([])
    declared = {
        candidate.profile.name.casefold()
        for candidate in candidates
        if candidate.profile_source == "DECLARED_MATERIAL_PROFILE"
    }
    assert [entry["profile_key"] for entry in ENTRIES if entry["profile_key"].casefold() not in declared] == []


def test_round3_overrides_keep_existing_entries() -> None:
    assert get_profile("Spike Lavender EO").note == "heart"
    assert get_profile("Damascenone").note == "base"
    assert get_profile("cis-3-Hexenol").note == "top"
    assert len(get_profile("Damascenone").character) >= 2


def test_no_excluded_sources_in_any_profile() -> None:
    for entry in ENTRIES:
        text = json.dumps(entry).casefold()
        assert not any(name in text for name in BANNED), entry["identity"]
