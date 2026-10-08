"""Exact botanical/product distinctions stay advisory through the v4 chain."""

from __future__ import annotations

import copy
import hashlib
import json
import socket
from concurrent.futures import ThreadPoolExecutor

import pytest

from engine.formulation_intelligence import literature_knowledge as knowledge
from engine.formulation_intelligence import subtype_research as subtypes
from engine.formulation_intelligence.source_review import assess_review_bundle, source_record_hash

MANIFEST = json.loads(subtypes.SUBTYPE_PATH.read_bytes())
NEW_CARDS = MANIFEST["cards"][160:]


def test_v4_preserves_all_prior_objects_and_has_exact_counts():
    prior_bytes = subtypes.V3_PATH.read_bytes()
    prior = json.loads(prior_bytes)
    current = subtypes.load_subtype_research()
    assert hashlib.sha256(prior_bytes).hexdigest() == "e70ddbfcb56b026003dc91785441e2da58c9292584112d2ae3afa66f86499f22"
    assert current["predecessor_manifest_sha256"] == hashlib.sha256(prior_bytes).hexdigest()
    assert current["schema_version"] == "formulation-subtype-research-v4"
    for field in ("cards", "taxonomy_additions", "review_addenda"):
        assert current[field][:len(prior[field])] == prior[field]
    assert current["campaign_identity_holds"] == prior["campaign_identity_holds"]
    assert len(current["cards"]) == 179 and len(NEW_CARDS) == 19
    assert len(current["taxonomy_additions"]) == 24
    assert len(current["review_addenda"]) == 8
    assert subtypes._load_payload(prior_bytes) == prior


@pytest.mark.parametrize("card", NEW_CARDS, ids=[c["subtype_id"] for c in NEW_CARDS])
def test_each_new_card_retrieves_bound_evidence_and_a_real_comparison(card):
    prompt = " ".join(g[0] for g in card["match_groups"])
    result = knowledge.retrieve_formulation_knowledge(prompt)
    cards = {c["subtype_id"]: c for c in result["subtype_context"]["cards"]}
    assert card["subtype_id"] in cards
    assert all(cards[card["subtype_id"]]["comparison"].values())
    sources = {s["source_id"]: s for s in result["sources"]}
    allowed = {s["source_id"] for s in result["source_reviews"] if s["allowed"]}
    for binding in card["source_bindings"]:
        assert binding["source_id"] in allowed
        assert source_record_hash(sources[binding["source_id"]]) == binding["source_record_sha256"]
    assert result["numeric_calibrations_admitted"] == []
    assert result["pleasantness"] is result["personal_liking"] is None
    assert all(flag is False for flag in card["authority"].values())
    assert result["network_used"] is False


@pytest.mark.parametrize("card", NEW_CARDS, ids=[c["subtype_id"] for c in NEW_CARDS])
def test_explicit_avoid_never_activates_the_new_target(card):
    prompt = "A soft floral perfume, without " + card["match_groups"][0][0]
    result = knowledge.retrieve_formulation_knowledge(prompt)
    assert card["subtype_id"] not in {c["subtype_id"] for c in result["subtype_context"]["cards"]}


@pytest.mark.parametrize("prompt,excluded", [
    ("water lily", "AQUATIC_NELUMBO"),
    ("Nymphaea lotus", "AQUATIC_NELUMBO"),
    ("sacred lotus", "AQUATIC_NYMPHAEA_PROLIFERA"),
    ("orchid", "ORCHID_PHALAENOPSIS"),
    ("Phalaenopsis violacea", "ORCHID_CYMBIDIUM_SUNNY"),
    ("Cytisus scoparius broom absolute", "POLLEN_SPARTIUM_BROOM"),
    ("Boronia leaf absolute", "GREEN_BORONIA_ABSOLUTE"),
    ("fig latex", "GREEN_FIG_LEAF"),
    ("fig leaf", "ORCHARD_FIG_FRUIT"),
    ("Pseudocydonia sinensis quince", "ORCHARD_QUINCE_CYDONIA"),
    ("natural Tolu absolute", "RESIN_TOLU_RECONSTRUCTIONS"),
    ("treemoss", "CHYPRE_OAKMOSS_PRODUCT"),
])
def test_botanical_organs_and_products_do_not_auto_alias(prompt, excluded):
    result = knowledge.retrieve_formulation_knowledge(prompt)
    assert excluded not in {c["subtype_id"] for c in result["subtype_context"]["cards"]}


@pytest.mark.parametrize("field", ["cards", "taxonomy_additions", "review_addenda", "campaign_identity_holds"])
def test_successor_cannot_rewrite_any_inherited_object(field):
    bad = copy.deepcopy(MANIFEST)
    bad[field] = bad[field][1:]
    with pytest.raises(ValueError):
        subtypes._load_payload(json.dumps(bad).encode())


@pytest.mark.parametrize("path_name", ["PREDECESSOR_PATH", "V2_PATH", "V3_PATH"])
def test_any_ancestor_drift_withholds_current_context(monkeypatch, tmp_path, path_name):
    path = tmp_path / "ancestor.json"
    path.write_bytes(getattr(subtypes, path_name).read_bytes() + b"\n")
    monkeypatch.setattr(subtypes, path_name, path)
    result = knowledge.retrieve_formulation_knowledge("lychee")
    assert result["subtype_context"]["state"] == "WITHHOLD_UNKNOWN"
    assert result["subtype_context"]["cards"] == []


def test_correction_is_a_required_runtime_dependency():
    pack = knowledge.load_knowledge_pack()
    result = subtypes.retrieve_subtype_research(
        "tilia", sources=pack["sources"], unavailable_source_ids=["tilia_correction_depth"],
    )
    assert "POLLEN_TILIA_STAGES" in result["withheld_subtype_ids"]
    assert not result["cards"]
    card = next(c for c in NEW_CARDS if c["subtype_id"] == "POLLEN_TILIA_STAGES")
    assert {s["source_id"] for s in card["source_bindings"]} == {"tilia_stages_depth", "tilia_correction_depth"}


def test_new_reviews_are_partial_and_never_numeric_admission():
    pack = knowledge.load_knowledge_pack()
    assert (len(pack["sources"]), len(pack["claims"])) == (233, 226)
    assert (len(pack["materials"]), len(pack["profiles"])) == (25, 43)
    new = [s for s in pack["sources"] if s["source_id"].endswith("_depth")]
    assert len(new) == 21
    reviewed = assess_review_bundle(pack["sources"], knowledge.SOURCE_REVIEWS_PATH.read_bytes())
    assert reviewed["unavailable_source_ids"] == ["iff_lime_conflict_subtypes"]
    records = {r["source_id"]: r for r in reviewed["assessments"]}
    for source in new:
        r = records[source["source_id"]]
        assert r["allowed"] and not r["numeric_calibration_allowed"]
        assert r["review_scope"] in {"PRIMARY_ABSTRACT", "SELECTED_PRIMARY_SECTIONS"}
    assert records["tilia_correction_depth"]["correction_retraction_state"] == "CORRECTION_REVIEWED"


def test_new_context_is_offline_deterministic_and_defensively_copied(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("network is forbidden in runtime research retrieval")
    monkeypatch.setattr(socket, "create_connection", forbidden)
    prompts = [c["match_groups"][0][0] for c in NEW_CARDS]
    serial = [knowledge.retrieve_formulation_knowledge(p) for p in prompts]
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert list(pool.map(knowledge.retrieve_formulation_knowledge, prompts)) == serial
    serial[0]["subtype_context"]["cards"].clear()
    assert knowledge.retrieve_formulation_knowledge(prompts[0])["subtype_context"]["cards"]
