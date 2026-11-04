"""Pairings for the literature-sourced profiles (Kenny 2 Nov 2026, "Add pairings to sourced profiles").

Stored as evidence only (Kenny's 4 Nov 2026 card): as matching words they made more
picks worse than they fixed.
"""

import json
from pathlib import Path

from engine.ingredient_intelligence import _PROFILES

ROOT = Path(__file__).resolve().parents[1]
DOC = json.loads((ROOT / "data/knowledge_graph/literature_synergies_20261102.json").read_text(encoding="utf-8"))


def test_most_sourced_profiles_carry_documented_partners_as_evidence_only():
    filled = [entry for entry in DOC["profiles"] if entry["synergies"]]
    assert len(DOC["profiles"]) == 121 and len(filled) >= 110
    for entry in filled:
        data = _PROFILES[entry["profile_key"]]
        assert 1 <= len(entry["synergies"]) <= 5
        quoted = {p["owned_stock_name"] or p["name"] for p in entry["partners"] if p.get("quote") and p.get("url")}
        assert set(entry["synergies"]) <= quoted, entry["profile_key"]
        evidence = data["evidence"]["literature_pairings"]
        assert evidence["status"] == "EVIDENCE_ONLY_NOT_APPLIED"
        assert evidence["partners"] == entry["synergies"]
        # Kenny's 4 Nov 2026 card: the composer's matching does not read them.
        assert entry["synergies"] != list(data.get("synergies") or ()), entry["profile_key"]


def test_no_ambrette_seed_and_no_banned_source():
    assert not any("ambrette seed" in s.casefold() for e in DOC["profiles"] for s in e["synergies"])
    text = json.dumps(DOC["profiles"]).casefold()
    assert not [w for w in ("scentree", "fragrantica", "wikipedia", "scent.vn", "scribd", "336871454") if w in text]
