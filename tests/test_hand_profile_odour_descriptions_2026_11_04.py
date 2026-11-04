"""Good Scents odour descriptions for hand-written profiles (Kenny's 4 Nov 2026 cards).

Stored as evidence only: as matching words they let broad descriptions win roles.
"""

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


def test_the_descriptions_are_evidence_and_change_no_scoring_field(monkeypatch):
    before = deepcopy(ii._PROFILES)
    for data in before.values():
        data.get("evidence", {}).pop("tgsc_odour_description", None)
    profiles = deepcopy(before)
    monkeypatch.setattr(ii, "_PROFILES", profiles)
    ii._attach_hand_odour_descriptions_evidence()
    filled = {e["profile_key"]: e for e in _document()["profiles"] if e["odor_description"]}
    assert len(filled) >= 190
    for key, data in profiles.items():
        for field in ("character", "note", "synergies", "odor_description"):
            assert data.get(field) == before[key].get(field), (key, field)
        if key in filled:
            evidence = data["evidence"]["tgsc_odour_description"]
            assert evidence["status"] == "EVIDENCE_ONLY_NOT_APPLIED"
            assert evidence["text"] == filled[key]["odor_description"]
