"""Own odor evidence, not stock names or generic freshness, qualifies a role."""

from dataclasses import replace
from functools import lru_cache

import pytest

from engine.formulation_intelligence import formula_solver as solver
from engine.formulation_intelligence import material_capability_index as capabilities
from engine.formulation_intelligence.semantic_brief_adapter import SemanticRole


@lru_cache(maxsize=1)
def _index():
    return capabilities.build_material_capability_index()


def _candidate():
    return next(c.candidate for c in _index().capabilities if c.identity_name == "Hedione")


@pytest.mark.parametrize("name,fruit,jasmine", [
    ("Fructone B", True, False),
    ("Berry Hexanoate (BerryFlor)", True, True),
    ("Hedione", False, True),
])
def test_reviewed_supplier_odor_is_separate_from_applications(name, fruit, jasmine):
    material = next(c for c in _index().capabilities if c.identity_name == name)
    assert capabilities.supports_descriptor_requirement(material, "fruit") is fruit
    assert capabilities.supports_descriptor_requirement(material, "jasmine") is jasmine


def _capability(monkeypatch, description="", *, reviewed=None, source="LOCAL_ANNOTATED_PROFILE"):
    candidate = _candidate()
    profile = replace(candidate.profile, odor_description=description, texture="",
                      or_family=None, formulation_roles=(), synergies=(), character={})
    monkeypatch.setattr(capabilities, "material_knowledge", lambda name: reviewed)
    return capabilities._capability(replace(candidate, profile=profile, profile_source=source))


@pytest.mark.parametrize("requirement,description", [
    ("fruit", "juicy pear"),
    ("rose", "rose petal"), ("rose", "rosy"),
    ("jasmine", "jasmine"), ("jasmine", "jasminic"),
    ("bitter_resin_green", "bitter green resin"),
    ("bitter_resin_green", "green resinous bitter"),
    ("watery_leaf", "watery leafy"), ("watery_leaf", "aquatic leaf"),
    ("citrus_leaf_floral", "floral citrus leaf"),
])
def test_closed_requirements_accept_own_descriptive_evidence(monkeypatch, requirement, description):
    material = _capability(monkeypatch, description)
    assert capabilities.supports_descriptor_requirement(material, requirement)


@pytest.mark.parametrize("requirement,description", [
    ("rose", "tuberose"), ("rose", "floral petal"),
    ("jasmine", "indolic floral"), ("jasmine", "fresh transparent floral"),
    ("bitter_resin_green", "green resin"),
    ("bitter_resin_green", "bitter green"),
    ("bitter_resin_green", "bitter resin"),
    ("watery_leaf", "aquatic green"), ("watery_leaf", "leaf green"),
    ("citrus_leaf_floral", "citrus green floral"),
    ("citrus_leaf_floral", "leaf green floral"),
    ("citrus_leaf_floral", "citrus leaf green"),
])
def test_each_required_conjunct_and_whole_token_must_be_present(monkeypatch, requirement, description):
    material = _capability(monkeypatch, description)
    assert not capabilities.supports_descriptor_requirement(material, requirement)


@pytest.mark.parametrize("requirement,description", [
    ("fruit", "Supplier-labelled Apple Pear; detailed odor profile not reviewed in this stock intake."),
    ("rose", "Supplier-labelled Rose Otto Bulgarian; detailed odor profile not reviewed in this stock intake."),
    ("jasmine", "Supplier labeled Jasmine"),
    ("watery_leaf", "Watery Leaf: detailed odour profile not reviewed."),
])
def test_unreviewed_placeholder_prose_cannot_be_odor_evidence(monkeypatch, requirement, description):
    material = _capability(monkeypatch, description)
    assert not material.descriptor_vocabulary
    assert not capabilities.supports_descriptor_requirement(material, requirement)


def test_placeholder_withholding_preserves_independently_reviewed_vocabulary(monkeypatch):
    material = _capability(
        monkeypatch, "Supplier-labelled Jasmine; detailed odor profile not reviewed.",
        reviewed={"vocabulary": ["rose"], "claim_ids": ["independent_review"], "role_slots": []},
    )
    assert material.descriptor_vocabulary == {"rose"}
    assert material.knowledge_claim_ids == ("independent_review",)
    assert capabilities.supports_descriptor_requirement(material, "rose")
    assert not capabilities.supports_descriptor_requirement(material, "jasmine")


def test_placeholder_withholding_preserves_other_independent_profile_fields(monkeypatch):
    candidate = _candidate()
    profile = replace(candidate.profile, odor_description="Supplier-labelled Apple Pear",
                      texture="watery", or_family=None, formulation_roles=("leaf",),
                      character={}, synergies=())
    monkeypatch.setattr(capabilities, "material_knowledge", lambda name: None)
    material = capabilities._capability(replace(candidate, profile=profile))
    assert material.descriptor_vocabulary == {"watery", "leaf"}
    assert capabilities.supports_descriptor_requirement(material, "watery_leaf")
    assert not capabilities.supports_descriptor_requirement(material, "fruit")


@pytest.mark.parametrize("contamination", ["identity", "label", "category", "comment", "synergy", "category_proxy"])
@pytest.mark.parametrize("requirement", ["rose", "jasmine", "bitter_resin_green", "watery_leaf", "citrus_leaf_floral"])
def test_context_cannot_manufacture_role_evidence(monkeypatch, contamination, requirement):
    candidate = _candidate()
    words = "rose jasmine bitter resin green watery leaf citrus floral"
    profile = replace(candidate.profile, odor_description="", texture="", or_family=None,
                      formulation_roles=(), character={}, synergies=())
    stock = candidate.stock
    source = "LOCAL_ANNOTATED_PROFILE"
    if contamination == "identity":
        stock = replace(stock, identity_name=words)
    elif contamination == "label":
        stock = replace(stock, name=words, raw_name=words)
    elif contamination == "category":
        stock = replace(stock, category=words)
    elif contamination == "comment":
        stock = replace(stock, raw_name=stock.raw_name + " # " + words)
    elif contamination == "synergy":
        profile = replace(profile, synergies=(words,))
    else:
        profile = replace(profile, odor_description=words, character={"rose": 5})
        source = "HEURISTIC_CATEGORY_PROXY"
    monkeypatch.setattr(capabilities, "material_knowledge", lambda name: None)
    material = capabilities._capability(replace(candidate, stock=stock, profile=profile, profile_source=source))
    assert not capabilities.supports_descriptor_requirement(material, requirement)


@pytest.mark.parametrize("requirement", ["unknown", "", "Rose", "floral", "leaf", "green"])
def test_unknown_or_loose_requirements_remain_ineligible(monkeypatch, requirement):
    material = _capability(monkeypatch, "rose jasmine bitter green resin watery leaf floral citrus")
    assert not capabilities.supports_descriptor_requirement(material, requirement)
    assert capabilities.supports_descriptor_requirement(material, None)


@pytest.mark.parametrize("requirement,description", [
    ("rose", "rose"), ("jasmine", "jasmine"),
    ("bitter_resin_green", "bitter green resin"),
    ("watery_leaf", "watery leaf"),
    ("citrus_leaf_floral", "citrus leaf floral"),
])
def test_both_solver_paths_enforce_evidence_before_generic_scores(monkeypatch, requirement, description):
    qualified = _capability(monkeypatch, description)
    contaminant = replace(qualified, stock_id="unqualified", descriptor_vocabulary=frozenset())
    index = replace(_index(), capabilities=(contaminant, qualified))
    role = SemanticRole("research_probe", "Bounded probe", "heart", "bridge", (description,),
                        (), .05, provenance="SOURCE_BOUND_ARCHITECTURE_HEURISTIC",
                        descriptor_requirement=requirement)
    monkeypatch.setattr(solver, "capability_role_score", lambda capability, **kwargs: 10000.0)
    ranked = solver._unary_rank_for_role(
        index, role, avoid=(), previous_stock_ids=frozenset(),
        prior_variant_stock_ids=frozenset(), variant_index=0,
    )
    assert [c.stock_id for _, c in ranked] == [qualified.stock_id]
    state = solver._BeamState((), frozenset(), (), 0.0)
    assert solver._allowed(qualified, role, state, avoid=(), allow_multiple_musks=False)
    assert not solver._allowed(contaminant, role, state, avoid=(), allow_multiple_musks=False)
    exact = replace(role, descriptor_requirement=None, exact_material=qualified.identity_name)
    assert solver._allowed(contaminant, exact, state, avoid=(), allow_multiple_musks=False)


def test_live_placeholder_and_aquatic_context_do_not_gain_exact_facet_eligibility():
    index = _index()
    placeholder = next(c for c in index.capabilities if c.identity_name == "Rose Otto Bulgarian")
    assert not capabilities.supports_descriptor_requirement(placeholder, "rose")
    for name in ("Calone", "Helional"):
        materials = index.exact_matches(name)
        assert materials
        assert all(not capabilities.supports_descriptor_requirement(c, "watery_leaf") for c in materials)


def test_descriptor_queries_do_not_switch_adapter_authority(monkeypatch):
    from engine.formulation_intelligence import architecture_bridge

    original = (architecture_bridge.ADAPTER_PATH, architecture_bridge.ADAPTER_SCHEMA)
    material = _capability(monkeypatch, "rose jasmine bitter green resin watery leaf floral citrus")
    for requirement in ("rose", "jasmine", "bitter_resin_green", "watery_leaf", "citrus_leaf_floral"):
        assert capabilities.supports_descriptor_requirement(material, requirement)
    assert (architecture_bridge.ADAPTER_PATH, architecture_bridge.ADAPTER_SCHEMA) == original
