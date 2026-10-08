"""Every new scope remains partial, source-bound and non-authoritative."""

from __future__ import annotations

import copy
import hashlib
import json
import socket
from concurrent.futures import ThreadPoolExecutor

import pytest

from engine.formulation_intelligence import literature_knowledge as knowledge
from engine.formulation_intelligence import subtype_research as subtypes
from engine.formulation_intelligence.construction_library import load_construction_library
from engine.formulation_intelligence.source_review import assess_review_bundle, source_record_hash
from engine.research.subtype_benchmark import audit_answer, compare_answers

MANIFEST = json.loads(subtypes.V3_PATH.read_bytes())
NEW_CARDS = MANIFEST["cards"][66:]


def test_all_frozen_gaps_have_partial_cards_without_rewriting_history():
    old = json.loads(subtypes.V2_PATH.read_bytes())
    assert hashlib.sha256(subtypes.V2_PATH.read_bytes()).hexdigest() == "6a7da23c4dbc7f205390cc2502f2b4d451025741eb3aa2cc1b60d89eb9e4d6c2"
    current = subtypes._load_payload(subtypes.V3_PATH.read_bytes())
    assert current["cards"][:66] == old["cards"]
    assert current["campaign_identity_holds"] == old["campaign_identity_holds"]
    parent = load_construction_library()
    gaps = {(p["package_id"], s) for p in parent["packages"] for s in p["unreviewed_subtypes"]}
    added = {(r["package_id"], r["planned_subtype"]) for r in current["taxonomy_additions"]}
    scoped = {(c["package_id"], c["planned_subtype"]) for c in current["cards"]}
    assert len(gaps) == 155 and len(added) == 5 and not gaps & added
    assert scoped == gaps | added
    assert len(NEW_CARDS) == 94 and len(current["cards"]) == 160
    assert len({c["package_id"] for c in current["cards"]}) == 49
    assert current["numeric_calibrations_admitted"] == []
    assert all(c["status"] == "UNTESTED_SUBTYPE_HYPOTHESIS" for c in current["cards"])


@pytest.mark.parametrize("card", NEW_CARDS, ids=[c["subtype_id"] for c in NEW_CARDS])
def test_every_added_scope_retrieves_exact_supported_comparison(card):
    prompt = " ".join(g[0] for g in card["match_groups"])
    result = knowledge.retrieve_formulation_knowledge(prompt)
    found = {c["subtype_id"]: c for c in result["subtype_context"]["cards"]}
    assert card["subtype_id"] in found
    allowed = {r["source_id"] for r in result["source_reviews"] if r["allowed"]}
    sources = {r["source_id"]: r for r in result["sources"]}
    for binding in found[card["subtype_id"]]["source_bindings"]:
        assert binding["source_id"] in allowed
        assert source_record_hash(sources[binding["source_id"]]) == binding["source_record_sha256"]
    assert not any(found[card["subtype_id"]]["authority"].values())
    assert all(found[card["subtype_id"]]["comparison"].values())
    assert result["numeric_calibrations_admitted"] == []
    assert result["pleasantness"] is result["personal_liking"] is None


@pytest.mark.parametrize("mutation", [
    "duplicate_scope", "rewrite_frozen_scope", "unknown_package", "orphan_addition",
    "botanical_bool", "addition_authority", "addendum_target", "addendum_missing_source",
    "addendum_authority", "duplicate_addendum", "unknown_addendum_field",
])
def test_expansion_and_addenda_fail_closed(mutation):
    value = copy.deepcopy(MANIFEST)
    addition = value["taxonomy_additions"][0]
    addendum = value["review_addenda"][0]
    if mutation == "duplicate_scope":
        value["taxonomy_additions"].append(copy.deepcopy(addition))
    elif mutation == "rewrite_frozen_scope":
        addition.update(package_id="FL_TROPICAL", planned_subtype="cananga")
    elif mutation == "unknown_package":
        addition["package_id"] = "INVENTED"
    elif mutation == "orphan_addition":
        value["cards"] = [c for c in value["cards"] if c["subtype_id"] != "LIGHT_LILAC"]
    elif mutation == "botanical_bool":
        addition["botanical_identity"] = True
    elif mutation == "addition_authority":
        addition["authority"]["safety_authority"] = True
    elif mutation == "addendum_target":
        addendum["target_card_sha256"] = "0" * 64
    elif mutation == "addendum_missing_source":
        addendum["source_bindings"] = []
    elif mutation == "addendum_authority":
        addendum["authority"]["compounding_authority"] = True
    elif mutation == "duplicate_addendum":
        value["review_addenda"].append(copy.deepcopy(addendum))
    else:
        addendum["dose"] = "invented"
    with pytest.raises(ValueError):
        subtypes.validate_subtype_research(value, load_construction_library())


@pytest.mark.parametrize("mutation", ["missing_v2", "changed_v2", "campaign_rewrite"])
def test_v3_needs_exact_predecessor_and_preserved_campaign(monkeypatch, tmp_path, mutation):
    path = tmp_path / "manifest.json"
    if mutation == "campaign_rewrite":
        value = copy.deepcopy(MANIFEST)
        value["campaign_identity_holds"][0]["reason"] = "Pretend recovered"
        path.write_text(json.dumps(value), encoding="utf-8")
        monkeypatch.setattr(subtypes, "SUBTYPE_PATH", path)
    else:
        if mutation == "changed_v2":
            path.write_bytes(subtypes.V2_PATH.read_bytes() + b"\n")
        monkeypatch.setattr(subtypes, "V2_PATH", path)
    result = knowledge.retrieve_formulation_knowledge("lilac flowers")
    assert result["subtype_context"]["state"] == "WITHHOLD_UNKNOWN"
    assert result["subtype_context"]["cards"] == []


def test_addendum_has_independent_source_closure_and_does_not_erase_old_card():
    result = subtypes.retrieve_subtype_research(
        "dewy peony", sources=knowledge.load_knowledge_pack()["sources"],
        unavailable_source_ids=["peony_methods_finish"],
    )
    card = next(c for c in result["cards"] if c["subtype_id"] == "PEONY_DEWY")
    assert "review_addenda" not in card
    assert result["withheld_addendum_ids"] == ["PEONY_DEWY"]
    current = knowledge.retrieve_formulation_knowledge("dewy peony")
    card = next(c for c in current["subtype_context"]["cards"] if c["subtype_id"] == "PEONY_DEWY")
    assert card["review_addenda"]
    assert "peony_methods_finish" in {s["source_id"] for s in current["sources"]}


@pytest.mark.parametrize("prompt,excluded", [
    ("Fresh floral perfume", "LIGHT_LILAC"),
    ("Cananga odorata ylang oil", "TROP_CANANGA"),
    ("Pink pepper", "SPICE_PEPPER"),
    ("green fruit, without mango", "TROP_MANGO"),
    ("floral, avoid honeysuckle", "LIGHT_HONEYSUCKLE"),
    ("CHIMIE L'HOMME", "PINEAPPLE_WOODY"),
])
def test_no_false_botanical_or_campaign_identity(prompt, excluded):
    cards = knowledge.retrieve_formulation_knowledge(prompt)["subtype_context"]["cards"]
    assert excluded not in {c["subtype_id"] for c in cards}


def test_new_sources_are_bounded_and_not_new_numeric_materials():
    pack = knowledge.load_knowledge_pack()
    new = [s for s in pack["sources"] if s["source_id"].endswith("_finish")]
    assert len(new) == 58
    # The closure wave is immutable; the active knowledge pack may grow.
    assert len([s for s in pack["sources"] if not s["source_id"].endswith("_depth")]) == 212
    assert len([c for c in pack["claims"] if not c["claim_id"].endswith("_depth")]) == 205
    assert len(pack["materials"]) == 25 and len(pack["profiles"]) == 43
    bundle = assess_review_bundle(pack["sources"], knowledge.SOURCE_REVIEWS_PATH.read_bytes())
    assert bundle["unavailable_source_ids"] == ["iff_lime_conflict_subtypes"]
    assert all(not s["empirical_data_admission"] for s in new)
    # These are deeper method reviews of existing papers, not independent studies.
    revisits = {
        "ylang_methods_finish": ("ylang_fractions_floral_v2", "YLANG_FRACTIONS"),
        "peony_methods_finish": ("peony_cultivars_floral_v2", "PEONY_DEWY"),
        "freesia_methods_finish": ("freesia_cultivars_floral_v2", "FREESIA_PEPPER"),
    }
    sources = {s["source_id"]: s for s in pack["sources"]}
    for name, (prior_id, card_id) in revisits.items():
        # Some older metadata has no DOI: do not manufacture or rewrite it.
        assert sources[name]["doi"]
        if sources[prior_id]["doi"]:
            assert sources[prior_id]["doi"] == sources[name]["doi"]
        card = next(c for c in MANIFEST["cards"] if c["subtype_id"] == card_id)
        addendum = next(r for r in MANIFEST["review_addenda"] if r["subtype_id"] == card_id)
        assert prior_id in {b["source_id"] for b in card["source_bindings"]}
        assert name in {b["source_id"] for b in addendum["source_bindings"]}


def test_closure_retrieval_offline_parallel_and_defensive(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("runtime network forbidden")
    monkeypatch.setattr(socket, "create_connection", forbidden)
    prompts = [" ".join(g[0] for g in c["match_groups"]) for c in NEW_CARDS]
    serial = [knowledge.retrieve_formulation_knowledge(p) for p in prompts]
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert list(pool.map(knowledge.retrieve_formulation_knowledge, prompts)) == serial
    assert all(len(r["subtype_context"]["cards"]) <= 4 for r in serial)
    serial[0]["subtype_context"]["cards"].clear()
    assert knowledge.retrieve_formulation_knowledge(prompts[0])["subtype_context"]["cards"]


def test_benchmark_does_not_relabel_extra_advice_as_formula_improvement():
    base = {"optimized_formula": {"rows": []}, "composition_plan": {},
            "formulation_knowledge": {}, "request_interpretation": {"must_avoid": ["vanilla"]}}
    before = audit_answer(base, ["vanilla"])
    after = copy.deepcopy(before)
    after.update(advice_sha256="different", subtype_ids=["NEW_CLUE"])
    comparison = compare_answers(before, after)
    assert comparison["advice_changed"]
    assert comparison["complete_formula_changed"] is False
    assert comparison["physical_rows_changed"] is False
    assert comparison["role_assignment_changed"] is False
    assert comparison["sensory_improvement"] == "NOT_TESTED"
    assert before["authority_safe"] is False  # absent authority is not false authority
    assert audit_answer(base, ["mango"])["explicit_avoids_preserved"] is False
