from __future__ import annotations

import copy
import json
import socket
from concurrent.futures import ThreadPoolExecutor

import pytest

from engine.formulation_intelligence import construction_library as library
from engine.formulation_intelligence import literature_knowledge as knowledge


def _plan():
    return json.loads(library.PLAN_PATH.read_bytes())


def test_frozen_49_package_scope_and_cross_domain_questions_close():
    data = library.load_construction_library()
    library.validate_construction_library(data, _plan())
    assert len(data["packages"]) == 49
    assert sum(len(row["subtype_scope"]) for row in data["packages"]) == 275
    for package in data["packages"]:
        assert package["state"] == "ADVISORY_CONSTRUCTION_DOSSIER"
        assert len(package["architectures"]) == 2
        assert package["unreviewed_subtypes"]  # initial coverage is not exhaustive
        assert all(value is False for value in package["authority"].values())
    assert {key: len(rows) for key, rows in data["cross_domain"].items()} == {
        "scientific_fronts": 14, "market_segments": 8,
        "product_formats": 13, "commercial_panel_tracks": 14,
    }


def test_every_package_retrieves_through_public_knowledge_context():
    for package in library.load_construction_library()["packages"]:
        result = knowledge.retrieve_formulation_knowledge(package["anchors"][0])
        context = result["construction_context"]
        assert package["package_id"] in {row["package_id"] for row in context["dossiers"]}, package["package_id"]
        assert context["coverage"]["initial_package_dossiers"] == 49
        assert context["coverage"]["empirically_validated_packages"] == 0
        assert context["numeric_calibrations_admitted"] == []
        assert result["pleasantness"] is result["personal_liking"] is None
        returned_sources = {row["source_id"] for row in result["sources"]}
        reviews = {row["source_id"] for row in result["source_reviews"]}
        for dossier in context["dossiers"]:
            assert {row["source_id"] for row in dossier["source_bindings"]} <= returned_sources & reviews


@pytest.mark.parametrize("prompt,forbidden", [
    ("lavender, no ambrox", "AM_AMBERGRIS"),
    ("non-Ambroxan lavender", "AM_AMBERGRIS"),
    ("iris, avoid gardenia", "FL_GARDENIA"),
    ("pear, no rose", "FL_ROSE"),
    ("sandalwood, without tobacco", "TO_HAY"),
    ("tea, no marine", "WA_AQUATIC"),
    ("smooth and rich", "HY_HYBRIDS"),
])
def test_negated_recognizers_or_generic_adjectives_do_not_activate(prompt, forbidden):
    assert forbidden not in {row["package_id"] for row in knowledge.retrieve_formulation_knowledge(prompt)["construction_context"]["dossiers"]}


@pytest.mark.parametrize("mutation", [
    "authority", "numeric", "missing_package", "duplicate_package", "source_hash",
    "orphan_role", "quantitative_role", "measured_edge", "duplicate_architecture",
    "invented_dose", "silent_subtype_promotion", "missing_cross_domain",
    "empty_function", "empty_intent", "duplicate_architecture_name",
    "invented_protected_floor",
])
def test_invalid_or_escalating_construction_contract_fails_closed(mutation):
    data = library.load_construction_library()
    package = data["packages"][0]
    if mutation == "authority":
        package["authority"]["compounding_authority"] = True
    elif mutation == "numeric":
        data["numeric_calibrations_admitted"] = ["imaginary curve"]
    elif mutation == "missing_package":
        data["packages"].pop()
    elif mutation == "duplicate_package":
        data["packages"][1] = copy.deepcopy(package)
    elif mutation == "source_hash":
        package["source_bindings"][0]["source_record_sha256"] = "missing"
    elif mutation == "orphan_role":
        package["functional_graph"]["nodes"][0]["source_ids"] = ["no-such-source"]
    elif mutation == "quantitative_role":
        package["functional_graph"]["nodes"][0]["time_scope"] = "MEASURED_4_HOURS"
    elif mutation == "measured_edge":
        package["functional_graph"]["edges"][0]["support"] = "MEASURED_SYNERGY"
    elif mutation == "duplicate_architecture":
        package["architectures"][1] = copy.deepcopy(package["architectures"][0])
    elif mutation == "invented_dose":
        package["architectures"][0]["dose_ul"] = 10
    elif mutation == "silent_subtype_promotion":
        package["unreviewed_subtypes"] = []
    elif mutation == "missing_cross_domain":
        data["cross_domain"]["product_formats"].pop()
    elif mutation == "empty_function":
        package["functional_graph"]["nodes"][0]["function"] = ""
    elif mutation == "empty_intent":
        package["architectures"][0]["intent"] = ""
    elif mutation == "duplicate_architecture_name":
        package["architectures"][1]["name"] = package["architectures"][0]["name"]
    elif mutation == "invented_protected_floor":
        package["functional_graph"]["nodes"][0]["protection_scope"] = "MANDATORY_LIBRARY_FLOOR"
    with pytest.raises(ValueError):
        library.validate_construction_library(data, _plan())


def test_source_drift_withholds_only_dependent_dossiers():
    pack = knowledge.load_knowledge_pack()
    sources = pack["sources"]
    changed = copy.deepcopy(sources)
    next(row for row in changed if row["source_id"] == "iff_orivone")["title"] += " drift"
    result = library.retrieve_construction_dossiers("iris lavender", sources=changed, unavailable_source_ids=[])
    assert "FL_IRIS" in result["withheld_package_ids"]
    assert "AR_LAVENDER" in {row["package_id"] for row in result["dossiers"]}
    unavailable = library.retrieve_construction_dossiers("iris lavender", sources=sources, unavailable_source_ids=["iff_orivone"])
    assert "FL_IRIS" in unavailable["withheld_package_ids"]


@pytest.mark.parametrize("contents", [None, "{bad", "{}", "[]"])
def test_library_failure_does_not_remove_independent_literature(monkeypatch, tmp_path, contents):
    path = tmp_path / "library.json"
    if contents is not None:
        path.write_text(contents, encoding="utf-8")
    monkeypatch.setattr(library, "LIBRARY_PATH", path)
    result = knowledge.retrieve_formulation_knowledge("iris")
    assert result["construction_context"]["state"] == "WITHHOLD_UNKNOWN"
    assert result["construction_library_sha256"] is None
    assert result["claims"]


def test_plan_hash_drift_withholds_construction(monkeypatch, tmp_path):
    path = tmp_path / "plan.json"
    path.write_bytes(library.PLAN_PATH.read_bytes() + b"\n")
    monkeypatch.setattr(library, "PLAN_PATH", path)
    context = knowledge.retrieve_formulation_knowledge("lavender")["construction_context"]
    assert context["state"] == "WITHHOLD_UNKNOWN"
    assert context["dossiers"] == []


def test_retrieval_is_bounded_defensive_offline_and_parallel_deterministic(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("runtime research must be offline")
    monkeypatch.setattr(socket, "create_connection", forbidden)
    prompt = "lavender rose pear apple iris tea musk vanilla leather"
    before = knowledge.retrieve_formulation_knowledge(prompt)
    assert len(before["construction_context"]["dossiers"]) <= 4
    changed = copy.deepcopy(before)
    changed["construction_context"]["dossiers"].clear()
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(knowledge.retrieve_formulation_knowledge, [prompt] * 8))
    assert all(result == before for result in results)


def test_source_snapshots_are_not_inventory_aliases_or_receptor_maps():
    for package in library.load_construction_library()["packages"]:
        for node in package["functional_graph"]["nodes"]:
            assert node["identity_scope"] == "EXACT_SOURCE_ENTITIES_NOT_STOCK_BINDINGS"
            assert node["support"] == "SOURCE_DESCRIPTOR_TO_FUNCTION_HYPOTHESIS"
            assert node["protection_scope"] == "LOCKED_REQUEST_ONLY_NOT_LIBRARY_POLICY"
        for edge in package["functional_graph"]["edges"]:
            assert edge["support"] == "UNMEASURED_INTERACTION_HYPOTHESIS"
    assert knowledge.material_knowledge("Orris Liquid") is None


def test_formula_studio_and_goal_analysis_return_advisory_construction():
    from engine.formulation_intelligence.formula_design_runtime import design_formula
    from engine.research.goal_analysis import (
        GoalAnalysisRequestV1,
        GoalFormulaRowV1,
        analyze_formula_for_goal,
    )

    design = design_formula(idea="A lavender perfume without Ambroxan", max_materials=12)
    context = design["formulation_knowledge"]["construction_context"]
    assert "AR_LAVENDER" in {row["package_id"] for row in context["dossiers"]}
    assert "AM_AMBERGRIS" not in {row["package_id"] for row in context["dossiers"]}
    assert design["semantic_brief"]["knowledge_context"] == design["formulation_knowledge"]
    assert design["beauty_score"] is None
    report = analyze_formula_for_goal(GoalAnalysisRequestV1(
        formula_id="construction-check", formula_name="Lavender Study",
        rows=(GoalFormulaRowV1("lavender", "Lavender EO Bontoux", "500", "uL"),),
        goals=("Make lavender clearer",), observations=("The current bottle is too sweet",),
    ))
    clue = next(row for row in report["clues"] if row["clue_id"] == "construction-AR_LAVENDER")
    assert clue["evidence_class"] == "UNTESTED_ARCHITECTURE_HYPOTHESIS"
    assert clue["action_authority"] is False
    assert report["default_user_view"]["strongest_clue"] == "The current bottle is too sweet"
    assert report["formula_modified"] is False
    assert report["compounding_authority"] is False


def test_construction_byte_drift_changes_design_request_identity(monkeypatch, tmp_path):
    from engine.formulation_intelligence.formula_design_runtime import design_formula

    before = design_formula(idea="Transparent iris with pale wood", max_materials=12)
    changed = tmp_path / "library.json"
    changed.write_bytes(library.LIBRARY_PATH.read_bytes() + b"\n")
    monkeypatch.setattr(library, "LIBRARY_PATH", changed)
    after = design_formula(idea="Transparent iris with pale wood", max_materials=12)
    assert before["request_sha256"] != after["request_sha256"]
    assert before["formulation_knowledge"]["construction_library_sha256"] != after["formulation_knowledge"]["construction_library_sha256"]
    assert before["optimized_formula"] == after["optimized_formula"]
