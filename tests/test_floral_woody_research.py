"""Floral expansion is source-bound, offline and not a campaign reconstruction."""

from __future__ import annotations

import hashlib
import json
import socket
from concurrent.futures import ThreadPoolExecutor

import pytest

from engine.formulation_intelligence import literature_knowledge as knowledge
from engine.formulation_intelligence import subtype_research as subtypes
from engine.formulation_intelligence.construction_library import load_construction_library
from engine.formulation_intelligence.source_review import assess_review_bundle

CASES = [
    ("lemony rose", "ROSE_LEMONY"),
    ("jammy rose", "ROSE_JAMMY"),
    ("honeyed rose", "ROSE_HONEY"),
    ("metallic rose", "ROSE_METALLIC"),
    ("rose patchouli", "ROSE_DARK_PATCH"),
    ("leathery jasmine", "JAS_LEATHER"),
    ("honeyed orange blossom", "ORANGE_HONEY"),
    ("indolic tuberose", "TUBEROSE_INDOLIC"),
    ("transparent tuberose", "TUBEROSE_TRANSPARENT"),
    ("creamy gardenia", "GARDENIA_CREAM"),
    ("ylang fractions", "YLANG_FRACTIONS"),
    ("tiare", "TROP_TIARE"),
    ("frangipani", "TROP_FRANGIPANI"),
    ("cyclamen", "MUGUET_CYCLAMEN"),
    ("muguet watery musk", "MUGUET_WATERY_MUSK"),
    ("dewy peony", "PEONY_DEWY"),
    ("rose adjacent peony", "PEONY_ROSE"),
    ("peppery freesia", "FREESIA_PEPPER"),
    ("creamy magnolia", "MAGNOLIA_CREAM"),
    ("narcissus absolute", "NARCISSUS_ABS"),
    ("salicylate lily", "LILY_SALICYLATE"),
    ("green lily", "LILY_GREEN"),
    ("pollen honey", "POLLEN_HONEY"),
    ("violet powder", "VIOLET_POWDER"),
    ("iris with violet leaf", "IRIS_VIOLET_LEAF"),
    ("classical bouquet", "BOUQUET_CLASSICAL"),
    ("floral aldehydic", "BOUQUET_ALDEHYDIC"),
    ("soft floral", "BOUQUET_SOFT"),
    ("pineapple woody", "PINEAPPLE_WOODY"),
    ("lavender apple", "LAV_APPLE"),
    ("lavender pineapple", "LAV_PINEAPPLE"),
    ("lavender spiced wood", "LAV_SPICED_WOOD"),
    ("floral fougere", "FOUGERE_FLORAL"),
    ("leathery fougere", "FOUGERE_LEATHER"),
    ("floral chypre", "CHYPRE_FLORAL"),
    ("green chypre", "CHYPRE_GREEN"),
    ("leathery chypre", "CHYPRE_LEATHER"),
    ("clean patchouli", "PATCH_CLEAN"),
    ("mineral woody amber", "WOOD_MINERAL"),
    ("ambergris musk", "AMBERGRIS_MUSK"),
]


def _ids(result):
    return {c["subtype_id"] for c in result["subtype_context"]["cards"]}


def test_floral_coverage_is_partial_and_exact_predecessor_is_unchanged():
    parent = load_construction_library()
    old = json.loads(subtypes.PREDECESSOR_PATH.read_bytes())
    current = subtypes._load_payload(subtypes.V2_PATH.read_bytes())
    assert hashlib.sha256(subtypes.PREDECESSOR_PATH.read_bytes()).hexdigest() == "2bbc6d9116fac0bcc033b3547c860a4f4033c517b76e11b016d8464b55a1f8f0"
    assert current["cards"][:26] == old["cards"]
    new = current["cards"][26:]
    assert len(new) == len(CASES) == 40
    assert sum(c["package_id"].startswith("FL_") for c in new) == 28
    planned_floral = {p["package_id"] for p in parent["packages"] if p["package_id"].startswith("FL_")}
    assert len(planned_floral) == 13
    assert {c["package_id"] for c in new if c["package_id"].startswith("FL_")} == planned_floral
    scoped = {(c["package_id"], c["planned_subtype"]) for c in current["cards"]}
    outstanding = {(p["package_id"], s) for p in parent["packages"]
                   if p["package_id"].startswith("FL_") for s in p["unreviewed_subtypes"]} - scoped
    assert outstanding == {("FL_TROPICAL", "cananga")}
    assert len(current["cards"]) == 66
    assert current["scope"] == "PARTIAL_SOURCE_BOUND_SUBTYPE_RESEARCH"


@pytest.mark.parametrize("prompt,expected", CASES)
def test_each_new_branch_has_complete_advisory_source_closure(prompt, expected):
    result = knowledge.retrieve_formulation_knowledge(prompt)
    assert expected in _ids(result)
    allowed = {r["source_id"] for r in result["source_reviews"] if r["allowed"]}
    sources = {r["source_id"] for r in result["sources"]}
    for card in result["subtype_context"]["cards"]:
        assert {b["source_id"] for b in card["source_bindings"]} <= allowed & sources
        assert card["status"] == "UNTESTED_SUBTYPE_HYPOTHESIS"
        assert card["comparison"]["change"] and card["comparison"]["question"]
        assert card["negative_space"] and card["identity_limits"]
        assert not any(card["authority"].values())
    assert result["subtype_context"]["coverage"]["floral_packages_deepened"] == 13
    assert result["subtype_context"]["coverage"]["empirically_validated_subtypes"] == 0
    assert result["pleasantness"] is result["personal_liking"] is None


@pytest.mark.parametrize("prompt", [
    "green lily of the valley", "salicylate lily of the valley", "green muguet",
])
def test_lilium_is_not_inferred_from_convallaria_or_muguet(prompt):
    assert not (_ids(knowledge.retrieve_formulation_knowledge(prompt)) & {"LILY_GREEN", "LILY_SALICYLATE"})


@pytest.mark.parametrize("prompt", [
    "rose, without honey", "jasmine, no leather", "no dewy peony",
    "lavender, avoid pineapple", "not mineral woody amber",
])
def test_negative_space_does_not_retrieve_the_negated_new_branch(prompt):
    assert not _ids(knowledge.retrieve_formulation_knowledge(prompt))


@pytest.mark.parametrize("name", ["CHIMIE LHOMME", "CHIMIE L'HOMME", "CHIMIE L’HOMME"])
def test_chimie_name_alone_never_becomes_an_aventus_formula(name):
    context = knowledge.retrieve_formulation_knowledge(name)["subtype_context"]
    assert context["cards"] == []
    hold, = context["campaign_identity_holds"]
    assert hold["state"] == "HOLD_EXACT_BRIEF_OR_FORMULA_REQUIRED"
    assert hold["inferred_package_ids"] == []
    assert not any(hold["authority"].values())


@pytest.mark.parametrize("name", ["Prada L'Homme", "La Nuit de L'Homme", "CHIMIE Femme"])
def test_unrelated_names_do_not_inherit_campaign_identity_hold(name):
    assert knowledge.retrieve_formulation_knowledge(name)["subtype_context"]["campaign_identity_holds"] == []


def test_explicit_descriptors_remain_usable_without_inventing_campaign_identity():
    result = knowledge.retrieve_formulation_knowledge("CHIMIE LHOMME, dewy peony")
    assert "PEONY_DEWY" in _ids(result)
    assert result["subtype_context"]["campaign_identity_holds"]
    assert knowledge.retrieve_formulation_knowledge(
        "CHIMIE LHOMME", avoid=("CHIMIE LHOMME",)
    )["subtype_context"]["campaign_identity_holds"] == []


@pytest.mark.parametrize("mutation", ["missing_predecessor", "predecessor_drift", "rewrite_history"])
def test_successor_cannot_silently_replace_its_predecessor(monkeypatch, tmp_path, mutation):
    if mutation == "rewrite_history":
        manifest = subtypes.load_subtype_research()
        manifest["cards"][0]["construction_hypothesis"] += " altered"
        path = tmp_path / "v2.json"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        monkeypatch.setattr(subtypes, "SUBTYPE_PATH", path)
    else:
        path = tmp_path / "v1.json"
        if mutation == "predecessor_drift":
            path.write_bytes(subtypes.PREDECESSOR_PATH.read_bytes() + b"\n")
        monkeypatch.setattr(subtypes, "PREDECESSOR_PATH", path)
    result = knowledge.retrieve_formulation_knowledge("dewy peony")
    assert result["subtype_context"]["state"] == "WITHHOLD_UNKNOWN"
    assert not result["subtype_context"]["cards"]
    assert result["claims"]  # independent source-bounded literature is retained


@pytest.mark.parametrize("change", [
    {"state": "IDENTITY_CONFIRMED"}, {"inferred_package_ids": ["FR_TROPICAL"]},
    {"names": [True]}, {"question": ""}, {"extra_formula": "pretend exact formula"},
    {"authority": {"compounding_authority": True}},
])
def test_campaign_hold_cannot_admit_a_guessed_identity(change):
    current = subtypes.load_subtype_research()
    current["campaign_identity_holds"][0].update(change)
    with pytest.raises(ValueError):
        subtypes.validate_subtype_research(current, load_construction_library())


def test_unavailable_new_source_withholds_only_its_dependents():
    result = subtypes.retrieve_subtype_research(
        "clean patchouli and dewy peony",
        sources=knowledge.load_knowledge_pack()["sources"],
        unavailable_source_ids=["dsm_clearwood_floral_v2"],
    )
    assert "PATCH_CLEAN" in result["withheld_subtype_ids"]
    assert "PEONY_DEWY" in {c["subtype_id"] for c in result["cards"]}
    assert "PATCH_CLEAN" not in {c["subtype_id"] for c in result["cards"]}


def test_new_sources_have_bounded_review_and_no_data_or_model_admission():
    pack = knowledge.load_knowledge_pack()
    new = [s for s in pack["sources"] if s["source_id"].endswith("_floral_v2")]
    assert len(new) == 21
    assert sum(s["evidence_class"] == "PRIMARY_RESEARCH" for s in new) == 8
    bundle = assess_review_bundle(pack["sources"], knowledge.SOURCE_REVIEWS_PATH.read_bytes())
    assert not ({s["source_id"] for s in new} & set(bundle["unavailable_source_ids"]))
    records = json.loads(knowledge.SOURCE_REVIEWS_PATH.read_bytes())["records"]
    reviews = [r for r in records if r["source_id"].endswith("_floral_v2")]
    assert all(r["empirical_data_rights"] == "NOT_ADMITTED" for r in reviews)
    assert all(r["review_scope"] in {"PRIMARY_ABSTRACT", "SELECTED_PRIMARY_SECTIONS"} for r in reviews)
    assert all(r["numeric_calibration_allowed"] is False for r in reviews)
    assert all(s["empirical_data_admission"] is False for s in new)
    assert len(pack["materials"]) == 25  # research descriptions do not create stock aliases
    assert knowledge.material_knowledge("Orris Liquid") is None


def test_new_branches_are_offline_bounded_and_parallel_deterministic(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("knowledge retrieval must not call the network")
    monkeypatch.setattr(socket, "create_connection", forbidden)
    prompts = [prompt for prompt, _ in CASES]
    serial = [knowledge.retrieve_formulation_knowledge(p) for p in prompts]
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert list(pool.map(knowledge.retrieve_formulation_knowledge, prompts)) == serial
    assert all(len(r["subtype_context"]["cards"]) <= 4 for r in serial)
    assert all(r["network_used"] is False for r in serial)
