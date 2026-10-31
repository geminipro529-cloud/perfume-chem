"""Sourced character and note for owned stocks that had only odour prose (31 Oct 2026)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.ingredient_intelligence import DIMENSIONS, get_profile

DATA = Path(__file__).resolve().parents[1] / "data" / "knowledge_graph" / "literature_character_profiles_20261031.json"
DOCUMENT = json.loads(DATA.read_text(encoding="utf-8"))
ENTRIES = DOCUMENT["profiles"]
BANNED = ("scentree", "fragrantica", "wikipedia", "scent.vn", "scribd")


def test_fifty_materials_are_loaded() -> None:
    assert len(ENTRIES) == 50
    assert len({entry["profile_key"] for entry in ENTRIES}) == 50


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
    assert profile.odor_description  # the intake prose is kept, not replaced


def test_role_and_prose_are_unchanged() -> None:
    cypress = get_profile("cypress eo")
    assert cypress.role == "modifier"
    assert cypress.odor_description == "dry conifer-woody-aromatic natural"
    assert get_profile("Acetoin").role == "unassigned"
    assert get_profile("Acetoin").odor_description.startswith("Acetoin is intensely sweet caramel")


def test_identity_cas_fixes() -> None:
    assert get_profile("Fructone B").cas == "6290-17-1"
    assert get_profile("Methyl Diantilis").cas == "5595-79-9"


def test_no_excluded_sources() -> None:
    text = json.dumps(DOCUMENT).casefold()
    assert not any(name in text for name in BANNED)
