"""Round 4 of the literature profiles (Kenny 2 Nov 2026 09:19 UTC, card answer "Sources only").

The 186 hand-written profiles get their sources, CAS flags, literature note tiers and the Dior Homme
Intense reparse odour records as evidence. Nothing that scores a formula may change.
"""

import copy
import json
from pathlib import Path

from engine import ingredient_intelligence
from engine.ingredient_intelligence import _PROFILES

ROOT = Path(__file__).resolve().parents[1]
DOC = json.loads((ROOT / "data/knowledge_graph/literature_sources_round4_20261102.json").read_text(encoding="utf-8"))


def test_every_round4_profile_exists_and_carries_its_sources():
    keys = {entry["profile_key"] for entry in DOC["profiles"]}
    assert len(DOC["profiles"]) == 193 and len(keys) == 186
    for key in keys:
        literature = _PROFILES[key]["evidence"]["literature_sources"]
        assert literature["status"] == "EVIDENCE_ONLY_NOT_APPLIED"
        assert literature["records"] and all(record["sources"] for record in literature["records"])


def test_attaching_the_sources_changes_nothing_but_that_evidence(monkeypatch):
    before = copy.deepcopy(_PROFILES)
    for data in before.values():
        data.get("evidence", {}).pop("literature_sources", None)
    after = copy.deepcopy(before)
    monkeypatch.setattr(ingredient_intelligence, "_PROFILES", after)
    ingredient_intelligence._attach_literature_sources_evidence()
    for data in after.values():
        data.get("evidence", {}).pop("literature_sources", None)
    assert after == before


def test_the_agreed_note_tiers_are_recorded_not_applied():
    moved = {
        entry["profile_key"]: entry["note_evidence"]
        for entry in DOC["profiles"]
        if entry["note_evidence"]["status"] == "TGSC_AND_VP_AGREE_ON_A_DIFFERENT_TIER"
    }
    assert set(moved) == {
        "Adoxal", "Allyl Amyl Glycolate", "Benzyl Acetate", "Cashmeran", "Ebanol", "Ethyl Maltol",
        "Farnesol", "Isobutyl Quinoline", "Nerol", "Peonile", "Terpinyl Acetate",
    }
    for key, note in moved.items():
        assert _PROFILES[key]["note"] == note["engine_note"] != note["sourced_note"], key


def test_no_banned_source_is_cited():
    banned = ("scentree", "fragrantica", "wikipedia", "scent.vn", "scribd", "336871454")
    text = json.dumps(DOC["profiles"]).casefold()
    assert not [word for word in banned if word in text]
