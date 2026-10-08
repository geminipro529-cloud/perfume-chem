"""V3 expansion preserves both predecessors and makes subtype specificity explicit."""

import copy
import hashlib
import json

import pytest

from engine.formulation_intelligence import architecture_bridge as bridge
from engine.formulation_intelligence.semantic_brief_adapter import compile_semantic_brief
from engine.research.subtype_benchmark import architecture_protocol


def _plan(text, *, avoid=(), preserve=()):
    interpretation = {"must_avoid": list(avoid), "must_preserve": list(preserve)}
    control = compile_semantic_brief(
        formula_name="V3 contract", request=text,
        interpretation=interpretation, max_materials=12,
    )
    return bridge.derive_architecture_briefs(
        control=control, interpretation=interpretation, max_materials=12,
    )


def test_historical_protocols_do_not_follow_active_adapter_path(monkeypatch, tmp_path):
    monkeypatch.setattr(bridge, "ADAPTER_PATH", tmp_path / "unrelated.json")
    for version in (1, 2, 3):
        corpus, adapter, schema, count = architecture_protocol(version)
        assert adapter == getattr(bridge, f"V{version}_PATH")
        assert schema == f"source-bound-architecture-adapters-v{version}"
        assert len(json.loads(corpus.read_bytes())["cases"]) == count
    assert hashlib.sha256(architecture_protocol(1)[0].read_bytes()).hexdigest() == (
        "5c952b513dc87cc9156a6f805b9e1f4d1f9430b946ffeadfc73f60c0c594c035"
    )
    assert hashlib.sha256(architecture_protocol(2)[0].read_bytes()).hexdigest() == (
        "df29990670f6981f4b9c048198e8bd1c5246510d65be3821330ec79c6e8e3d54"
    )


@pytest.mark.parametrize("version", [0, 6, True, "3", None])
def test_protocol_registry_is_closed(version):
    with pytest.raises(ValueError):
        architecture_protocol(version)


def test_v3_corpus_keeps_all_v2_cases_and_frozen_expansion():
    v2 = json.loads(architecture_protocol(2)[0].read_bytes())
    v3 = json.loads(architecture_protocol(3)[0].read_bytes())
    assert v3["cases"][:30] == v2["cases"]
    assert v3["frozen_before_execution"] is True
    manifest = json.loads(bridge.V3_PATH.read_bytes())
    new_ids = {a["subtype_id"] for a in manifest["adapters"][22:]}
    assert len(new_ids) == 22
    assert {c["expected_subtype"] for c in v3["cases"][30:52]} == new_ids


@pytest.mark.parametrize("version", [1, 2])
def test_active_v3_cannot_load_an_older_contract_as_current(monkeypatch, version):
    monkeypatch.setattr(bridge, "ADAPTER_PATH", getattr(bridge, f"V{version}_PATH"))
    plan = _plan("A dewy peony perfume")
    assert len(plan.briefs) == 1
    assert plan.receipt["state"] == "WITHHOLD_UNKNOWN"


def test_expected_schema_is_external_not_inferred_from_payload():
    predecessor = json.loads(bridge.V1_PATH.read_bytes())
    with pytest.raises(ValueError):
        bridge.validate_adapter_manifest(predecessor)
    bridge.validate_adapter_manifest(
        predecessor, expected_schema="source-bound-architecture-adapters-v1",
    )


def test_qualified_muguet_precedes_umbrella_only_in_v3(monkeypatch):
    plan = _plan("A muguet perfume with watery musk")
    assert {b.architecture_plan["subtype_id"] for b in plan.briefs[1:]} == {"MUGUET_WATERY_MUSK"}
    monkeypatch.setattr(bridge, "ADAPTER_PATH", bridge.V2_PATH)
    monkeypatch.setattr(bridge, "ADAPTER_SCHEMA", "source-bound-architecture-adapters-v2")
    previous = _plan("A muguet perfume with watery musk")
    assert {b.architecture_plan["subtype_id"] for b in previous.briefs[1:]} == {"MUGUET_SOFT"}


@pytest.mark.parametrize("text,avoid,remaining", [
    ("A metallic rose perfume", ("green", "spice"), set()),
    ("A honeyed orange blossom perfume", ("indole", "indolic"), {"honey_flower"}),
    ("A dewy peony perfume", ("rose", "geranium"), {"dewy_lift"}),
])
def test_negative_space_controls_each_new_option(text, avoid, remaining):
    plan = _plan(text, avoid=avoid)
    assert {b.architecture_plan["option_id"] for b in plan.briefs[1:]} == remaining
    assert any(x["reason"] == "EXPLICIT_AVOID_CONFLICT" for x in plan.receipt["withheld_options"])


def test_exact_grade_questions_are_not_faked_with_generic_role_options():
    manifest = json.loads(bridge.V3_PATH.read_bytes())
    ids = {a["subtype_id"] for a in manifest["adapters"]}
    assert ids.isdisjoint({
        "YLANG_FRACTIONS", "TROP_TIARE", "TROP_FRANGIPANI",
        "HERB_ROSEMARY", "VETIVER_HEART", "AMBERGRIS_STEREO", "MAGNOLIA_CREAM",
    })


def test_v3_new_dependency_failure_does_not_disable_independent_cards():
    from dataclasses import replace

    interpretation = {"must_avoid": [], "must_preserve": []}
    control = compile_semantic_brief(
        formula_name="V3 isolation", request="Lemony rose with jasmine grandiflorum",
        interpretation=interpretation, max_materials=12,
    )
    context = copy.deepcopy(control.knowledge_context)
    next(r for r in context["source_reviews"] if r["source_id"] == "iff_rose_completion")["allowed"] = False
    plan = bridge.derive_architecture_briefs(
        control=replace(control, knowledge_context=context),
        interpretation=interpretation, max_materials=12,
    )
    assert {b.architecture_plan["subtype_id"] for b in plan.briefs[1:]} == {"JAS_GRANDIFLORUM"}
    assert any(x["reason"] == "SOURCE_REVIEW_UNAVAILABLE" for x in plan.receipt["withheld_options"])


@pytest.mark.parametrize("collection", ["sources", "source_reviews"])
def test_duplicate_source_identity_withholds_only_dependent_options(collection):
    from dataclasses import replace

    interpretation = {"must_avoid": [], "must_preserve": []}
    control = compile_semantic_brief(
        formula_name="V3 ambiguity", request="Lemony rose with jasmine grandiflorum",
        interpretation=interpretation, max_materials=12,
    )
    context = copy.deepcopy(control.knowledge_context)
    duplicate = copy.deepcopy(next(r for r in context[collection] if r["source_id"] == "iff_rose_completion"))
    if collection == "source_reviews":
        duplicate["allowed"] = False
    context[collection].append(duplicate)
    plan = bridge.derive_architecture_briefs(
        control=replace(control, knowledge_context=context),
        interpretation=interpretation, max_materials=12,
    )
    assert {b.architecture_plan["subtype_id"] for b in plan.briefs[1:]} == {"JAS_GRANDIFLORUM"}
    assert any(x["reason"] == "AMBIGUOUS_SOURCE_OR_REVIEW_IDENTITY" for x in plan.receipt["withheld_options"])


@pytest.mark.parametrize("version", [1, 2, 3])
def test_historical_protocol_rejects_changed_manifest_before_execution(monkeypatch, tmp_path, version):
    from engine.research import subtype_benchmark

    original = getattr(bridge, f"V{version}_PATH")
    replacement = tmp_path / original.name
    replacement.write_bytes(original.read_bytes() + b"\n")
    monkeypatch.setattr(bridge, f"V{version}_PATH", replacement)
    monkeypatch.setattr(subtype_benchmark, "design_formula", lambda **kwargs: pytest.fail("drift reached execution"))
    with pytest.raises(ValueError, match="historical architecture manifest bytes drifted"):
        subtype_benchmark.run_architecture_comparison(version=version)
