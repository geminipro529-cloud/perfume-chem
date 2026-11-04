"""Good Scents odour descriptions for hand-written profiles (Kenny's 4 Nov 2026 card)."""

from __future__ import annotations

import json
from copy import deepcopy

import engine.ingredient_intelligence as ii

# Proprietary bases with no Good Scents page: the maker's own page is the source.
_MAKER_PAGE_ONLY = {"Lilyreal ND", "Tonkarome"}
_BANNED = ("scentree", "fragrantica", "wikipedia", "scent.vn", "scribd", "336871454")


def _document():
    return json.loads(ii._HAND_ODOUR_DESCRIPTIONS.read_text(encoding="utf-8"))


def test_every_entry_names_a_profile_and_carries_a_sourced_quote():
    for entry in _document()["profiles"]:
        assert entry["profile_key"] in ii._PROFILES, entry["profile_key"]
        if entry["odor_description"] is None:
            continue
        assert entry["odor_description"].endswith("."), entry["profile_key"]
        assert entry["sources"] and all(row["url"] and row["quote"] for row in entry["sources"]), entry["profile_key"]
        if entry["profile_key"] not in _MAKER_PAGE_ONLY:
            assert any("thegoodscentscompany.com" in row["url"] for row in entry["sources"]), entry["profile_key"]


def test_no_banned_source_is_cited():
    text = json.dumps(_document()["profiles"]).casefold()
    assert not any(word in text for word in _BANNED)


def test_only_empty_odour_text_is_filled_and_nothing_else_changes(monkeypatch):
    before = deepcopy(ii._PROFILES)
    for entry in _document()["profiles"]:
        before[entry["profile_key"]].pop("odor_description", None)
        before[entry["profile_key"]].get("evidence", {}).pop("odor_description", None)
    profiles = deepcopy(before)
    keep = next(iter(profiles))
    profiles[keep]["odor_description"] = "Kept."
    monkeypatch.setattr(ii, "_PROFILES", profiles)
    ii._apply_hand_odour_descriptions()
    filled = {e["profile_key"]: e for e in _document()["profiles"] if e["odor_description"]}
    for key, data in profiles.items():
        if key == keep:
            assert data["odor_description"] == "Kept."
            continue
        for field in ("character", "note", "synergies"):
            assert data.get(field) == before[key].get(field), (key, field)
        if key in filled:
            assert data["odor_description"] == filled[key]["odor_description"]
            assert data["evidence"]["odor_description"]["status"] == "TGSC_ODOUR_DESCRIPTION_20261104"
        else:
            assert data.get("odor_description") == before[key].get("odor_description"), key
