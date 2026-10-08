"""Partial subtype research cannot become a dose, stock alias or authority."""

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

CASES = [
    ("citrus lavender cologne", "LAV_COLOGNE"),
    ("green barbershop lavender", "LAV_BARBERSHOP"),
    ("lavender vanilla resin", "LAV_VANILLIC"),
    ("soft musky lavender", "LAV_SOFT_MUSK"),
    ("lavender orange blossom", "LAV_ORANGE"),
    ("iris lavender", "LAV_IRIS"),
    ("incense lavender without Ambroxan", "LAV_INCENSE"),
    ("lavender licorice", "LAV_LICORICE"),
    ("green mandarin", "CIT_MANDARIN_GREEN"),
    ("grapefruit peel and juice", "CIT_GRAPEFRUIT"),
    ("yuzu citrus", "CIT_YUZU"),
    ("galbanum green", "GREEN_GALBANUM"),
    ("watery violet leaf", "GREEN_VIOLET_LEAF"),
    ("fresh neroli", "ORANGE_NEROLI"),
    ("bitter petitgrain", "ORANGE_PETITGRAIN"),
    ("grandiflorum jasmine", "JAS_GRANDIFLORUM"),
    ("jasmine green tea", "JAS_TEA_GREEN"),
    ("soft muguet", "MUGUET_SOFT"),
    ("ripe apple", "ORCHARD_RIPE_APPLE"),
    ("persistent pear musk", "ORCHARD_PEAR_MUSK"),
    ("pear freesia heart", "ORCHARD_HEART"),
    ("blackcurrant bud", "BERRY_CASSIS"),
    ("raspberry floral fruit", "BERRY_RASPBERRY"),
    ("floral green tea", "TEA_GREEN"),
    ("sun dried black tea", "TEA_BLACK"),
    ("roasted Dong Ding oolong", "TEA_OOLONG"),
]


def _ids(result):
    return {row["subtype_id"] for row in result["subtype_context"]["cards"]}


def test_exact_parent_and_partial_scope_are_preserved():
    manifest = subtypes.load_subtype_research()
    parent = load_construction_library()
    subtypes.validate_subtype_research(manifest, parent)
    predecessor = json.loads(subtypes.PREDECESSOR_PATH.read_bytes())
    subtypes.validate_subtype_research(predecessor, parent)
    assert len(predecessor["cards"]) == len(CASES) == 26
    assert len({c["package_id"] for c in predecessor["cards"]}) == 9
    assert manifest["cards"][:26] == predecessor["cards"]
    assert len(manifest["cards"]) == 179
    assert len({c["package_id"] for c in manifest["cards"]}) == 49
    assert hashlib.sha256(subtypes.LIBRARY_PATH.read_bytes()).hexdigest() == "cba922283537998fa1dcc57dccd896b070cc7f1545c6209040d3d76b1f3652c7"
    assert sum(len(p["unreviewed_subtypes"]) for p in parent["packages"]) == 155
    assert manifest["scope"] == "PARTIAL_SOURCE_BOUND_SUBTYPE_RESEARCH"
    assert manifest["numeric_calibrations_admitted"] == []


@pytest.mark.parametrize("prompt,expected", CASES)
def test_every_reviewed_example_has_source_and_review_closure(prompt, expected):
    result = knowledge.retrieve_formulation_knowledge(prompt)
    assert expected in _ids(result)
    sources = {r["source_id"] for r in result["sources"]}
    reviews = {r["source_id"] for r in result["source_reviews"] if r["allowed"]}
    for card in result["subtype_context"]["cards"]:
        assert {b["source_id"] for b in card["source_bindings"]} <= sources & reviews
        assert all(flag is False for flag in card["authority"].values())
        assert card["status"] == "UNTESTED_SUBTYPE_HYPOTHESIS"
        assert card["comparison"]["question"]
    assert result["pleasantness"] is result["personal_liking"] is None
    assert result["network_used"] is False


@pytest.mark.parametrize("prompt", [
    "lavender", "violet petals", "tea", "fresh and rich", "not yuzu",
    "lavender, without incense", "pear, avoid musk and freesia",
    "lavender, no vanilla, no musk, no iris", "raspberryish",
])
def test_broad_negated_and_substring_requests_do_not_expand(prompt):
    assert _ids(knowledge.retrieve_formulation_knowledge(prompt)) == set()


def test_explicit_avoid_overrides_subtype_matching():
    result = knowledge.retrieve_formulation_knowledge("lavender incense", avoid=("incense",))
    assert "LAV_INCENSE" not in _ids(result)


@pytest.mark.parametrize("mutation", [
    "authority", "numeric", "duplicate", "duplicate_scope", "unknown_scope",
    "missing_evidence", "invalid_hash", "empty_question", "empty_functions",
    "dose", "unknown_state", "match_shape", "boolean_match", "invalid_date",
])
def test_invalid_and_authoritative_cards_are_rejected(mutation):
    manifest = subtypes.load_subtype_research()
    card = manifest["cards"][0]
    if mutation == "authority":
        card["authority"]["compounding_authority"] = True
    elif mutation == "numeric":
        manifest["numeric_calibrations_admitted"] = ["pretend dose curve"]
    elif mutation == "duplicate":
        manifest["cards"].append(copy.deepcopy(card))
    elif mutation == "duplicate_scope":
        manifest["cards"][1]["planned_subtype"] = card["planned_subtype"]
    elif mutation == "unknown_scope":
        card["planned_subtype"] = "fabricated family"
    elif mutation == "missing_evidence":
        card["source_bindings"] = []
    elif mutation == "invalid_hash":
        card["source_bindings"][0]["source_record_sha256"] = "not a hash"
    elif mutation == "empty_question":
        card["comparison"]["question"] = ""
    elif mutation == "empty_functions":
        card["function_map"] = []
    elif mutation == "dose":
        card["dose_ul"] = "100"
    elif mutation == "unknown_state":
        card["status"] = "EMPIRICALLY_PROVEN"
    elif mutation == "match_shape":
        card["match_groups"] = "lavender"
    elif mutation == "boolean_match":
        card["match_groups"] = [[True]]
    elif mutation == "invalid_date":
        manifest["review_date"] = "not a date"
    with pytest.raises(ValueError):
        subtypes.validate_subtype_research(manifest, load_construction_library())


@pytest.mark.parametrize("change", ["source_bytes", "source_hold", "missing_source"])
def test_source_failure_withholds_only_dependent_cards(change):
    sources = knowledge.load_knowledge_pack()["sources"]
    missing = []
    source_id = "iff_violet_leaf_subtypes"
    if change == "source_bytes":
        next(r for r in sources if r["source_id"] == source_id)["title"] += " changed"
    elif change == "source_hold":
        missing = [source_id]
    else:
        sources = [r for r in sources if r["source_id"] != source_id]
    result = subtypes.retrieve_subtype_research(
        "violet leaf and oolong", sources=sources, unavailable_source_ids=missing,
    )
    assert result["withheld_subtype_ids"] == ["GREEN_VIOLET_LEAF"]
    assert [c["subtype_id"] for c in result["cards"]] == ["TEA_OOLONG"]


@pytest.mark.parametrize("corruption", ["missing", "malformed", "parent_drift", "plan_drift"])
def test_unavailable_extension_does_not_erase_independent_literature(monkeypatch, tmp_path, corruption):
    path = tmp_path / "broken.json"
    if corruption == "malformed":
        path.write_text('{"broken":', encoding="utf-8")
    if corruption in {"missing", "malformed"}:
        monkeypatch.setattr(subtypes, "SUBTYPE_PATH", path)
    else:
        original = subtypes.LIBRARY_PATH if corruption == "parent_drift" else subtypes.PLAN_PATH
        path.write_bytes(original.read_bytes() + b"\n")
        monkeypatch.setattr(subtypes, "LIBRARY_PATH" if corruption == "parent_drift" else "PLAN_PATH", path)
    result = knowledge.retrieve_formulation_knowledge("lavender incense")
    assert result["subtype_context"]["state"] == "WITHHOLD_UNKNOWN"
    assert result["subtype_context"]["cards"] == []
    assert result["claims"]


def test_conflicting_lime_source_is_not_selectable():
    result = knowledge.retrieve_formulation_knowledge("distilled lime")
    assert "iff_lime_conflict_subtypes" in result["unavailable_source_ids"]
    assert all(s["source_id"] != "iff_lime_conflict_subtypes" for s in result["sources"])
    assert knowledge.material_knowledge("Orris Liquid") is None
    assert knowledge.material_knowledge("Fructone B") is None


def test_offline_bounded_defensive_parallel_retrieval(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("subtype research must remain offline")
    monkeypatch.setattr(socket, "create_connection", forbidden)
    prompts = [p for p, _ in CASES]
    serial = [knowledge.retrieve_formulation_knowledge(p) for p in prompts]
    with ThreadPoolExecutor(max_workers=4) as pool:
        parallel = list(pool.map(knowledge.retrieve_formulation_knowledge, prompts))
    assert serial == parallel
    serial[0]["subtype_context"]["cards"].clear()
    assert "LAV_COLOGNE" in _ids(knowledge.retrieve_formulation_knowledge(prompts[0]))
    crowded = knowledge.retrieve_formulation_knowledge("lavender vanilla musk iris incense cologne orange blossom licorice")
    assert len(crowded["subtype_context"]["cards"]) == 4
    assert crowded["subtype_context"]["matched_subtype_count"] > 4


def test_goal_clue_preserves_direct_observation_precedence():
    from engine.research.goal_analysis import (
        GoalAnalysisRequestV1,
        GoalFormulaRowV1,
        analyze_formula_for_goal,
    )
    result = analyze_formula_for_goal(GoalAnalysisRequestV1(
        formula_id="synthetic-subtype-check", formula_name="Lavender Incense",
        rows=(GoalFormulaRowV1("lav", "Lavender EO Bontoux", "500", "uL"),),
        goals=("Make lavender incense clearer",), observations=("The incense is too smoky",),
    ))
    clue = next(c for c in result["clues"] if c["clue_id"] == "subtype-LAV_INCENSE")
    assert clue["evidence_class"] == "UNTESTED_SUBTYPE_HYPOTHESIS"
    assert clue["action_authority"] is False
    assert result["default_user_view"]["strongest_clue"] == "The incense is too smoky"
    assert result["formula_modified"] is result["compounding_authority"] is False


def test_manifest_byte_drift_changes_design_identity_not_composition(monkeypatch, tmp_path):
    from engine.formulation_intelligence.formula_design_runtime import design_formula
    before = design_formula(idea="Lavender incense without Ambroxan", max_materials=12)
    path = tmp_path / "subtypes.json"
    path.write_bytes(subtypes.SUBTYPE_PATH.read_bytes() + b"\n")
    monkeypatch.setattr(subtypes, "SUBTYPE_PATH", path)
    after = design_formula(idea="Lavender incense without Ambroxan", max_materials=12)
    assert before["request_sha256"] != after["request_sha256"]
    assert before["optimized_formula"] == after["optimized_formula"]
    assert "LAV_INCENSE" in _ids(after["formulation_knowledge"])
    assert after["beauty_score"] is None


def test_new_source_counts_and_review_states_close():
    pack = knowledge.load_knowledge_pack()
    reviews = json.loads(knowledge.SOURCE_REVIEWS_PATH.read_bytes())
    new = [r for r in reviews["records"] if r["source_id"].endswith("_subtypes")]
    assert len(new) == 18
    assert sum(r["review_state"] == "REVIEWED_ADVISORY" for r in new) == 17
    assert sum(r["review_state"] == "HOLD" for r in new) == 1
    assert sum(s["evidence_class"] == "PRIMARY_RESEARCH" for s in pack["sources"] if s["source_id"].endswith("_subtypes")) == 8
