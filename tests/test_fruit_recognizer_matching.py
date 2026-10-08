"""Named fruit intent is not a botanical name or a measured scent result."""

from dataclasses import replace
from functools import lru_cache

import pytest

from engine.formulation_intelligence import material_capability_index as capabilities
from engine.formulation_intelligence.material_capability_index import (
    build_material_capability_index,
    supports_descriptor_requirement,
)
from engine.formulation_intelligence.semantic_brief_adapter import compile_semantic_brief


def _brief(text, avoid=()):
    return compile_semantic_brief(
        formula_name="Recognizer regression", request=text, max_materials=12,
        interpretation={"explicit_materials": [], "must_avoid": list(avoid),
                        "must_preserve": [], "material_count_constraints": []},
    )


@lru_cache(maxsize=1)
def _index():
    return build_material_capability_index()


def test_lychee_intent_reaches_material_selection_without_unrequested_fruits():
    brief = _brief("A juicy lychee fruit perfume")
    role = next(r for r in brief.roles if r.role_id == "facet_fruit")
    assert "lychee" in role.query_terms
    assert "berry" not in role.query_terms
    assert "lychee" in brief.protected_recognizers


def test_juniper_identity_cannot_supply_fruit_descriptor_evidence():
    from engine.formulation_intelligence.formula_solver import _unary_rank_for_role

    role = next(r for r in _brief("A fruit perfume").roles if r.role_id == "facet_fruit")
    ranked = _unary_rank_for_role(
        _index(), role, avoid=(), previous_stock_ids=frozenset(),
        prior_variant_stock_ids=frozenset(), variant_index=0,
    )
    assert ranked
    assert all("juniper" not in c.identity_name.casefold() for _, c in ranked)


@pytest.mark.parametrize("text,expected", [
    ("A lychee perfume", ("lychee",)), ("A litchi perfume", ("lychee",)),
    ("An apple and pear perfume", ("pear", "apple")),
    ("Pear with lychee fruit", ("pear", "lychee")),
    ("Juniper Berry EO", ()),
])
def test_requested_fruit_identity_is_retained_as_intent_not_a_stock_alias(text, expected):
    brief = _brief(text)
    assert brief.requested_fruits == expected
    assert set(expected) <= set(brief.protected_recognizers)


def test_avoided_fruit_does_not_delete_an_independent_requested_fruit():
    brief = _brief("An apple perfume without pear", avoid=("pear",))
    assert brief.requested_fruits == ("apple",)
    role = next(r for r in brief.roles if r.role_id == "facet_fruit")
    assert role.query_terms == ("apple", "fruit", "fruity")


def test_avoid_apple_does_not_remove_pineapple():
    assert _brief("A pineapple perfume without apple", avoid=("apple",)).requested_fruits == ("pineapple",)


@pytest.mark.parametrize("positive,negative", [("litchi", "lychee"), ("lychee", "litchi")])
def test_positive_and_negative_fruit_aliases_use_same_vocabulary(positive, negative):
    brief = _brief(f"A {positive} perfume without {negative}", avoid=(negative,))
    assert not brief.requested_fruits
    assert not any(r.role_id == "facet_fruit" for r in brief.roles)


@pytest.mark.parametrize("contamination", ["name", "category", "synergy", "comment", "fresh_sweet", "ester"])
def test_context_or_chemical_class_cannot_fabricate_own_fruit_evidence(monkeypatch, contamination):
    juniper = next(c for c in _index().capabilities if c.identity_name == "Juniper Berry EO")
    candidate = juniper.candidate
    profile = replace(candidate.profile, odor_description="woody conifer",
                      texture="dry", or_family="woody", formulation_roles=[],
                      synergies=[], character={"freshness": 8, "sweetness": 3})
    stock = candidate.stock
    if contamination == "synergy":
        profile = replace(profile, synergies=["lychee pear fruit"])
    elif contamination == "category":
        stock = replace(stock, category="fruit")
    elif contamination == "comment":
        stock = replace(stock, raw_name=stock.raw_name + " # pairs with lychee fruit")
    elif contamination == "ester":
        profile = replace(profile, odor_description="ester")
    monkeypatch.setattr(capabilities, "material_knowledge", lambda name: None)
    capability = capabilities._capability(replace(candidate, stock=stock, profile=profile,
                                                profile_source="LOCAL_ANNOTATED_PROFILE"))
    assert not supports_descriptor_requirement(capability, "fruit")


def test_own_fruity_annotation_qualifies_without_inventing_measured_recognition():
    material = next(c for c in _index().capabilities if c.identity_name == "Paradisamide")
    assert supports_descriptor_requirement(material, "fruit")
    assert {"fruit", "fruity"} <= material.descriptor_vocabulary
    assert not supports_descriptor_requirement(material, "unknown")


def test_explicit_juniper_anchor_is_still_available_independently_of_fruit():
    from engine.formulation_intelligence.formula_solver import _unary_rank_for_role

    brief = compile_semantic_brief(
        formula_name="Exact anchor", request="Use Juniper Berry EO with fruit", max_materials=12,
        interpretation={"explicit_materials": ["Juniper Berry EO"], "must_avoid": []},
    )
    role = next(r for r in brief.roles if r.exact_material)
    ranked = _unary_rank_for_role(_index(), role, avoid=(), previous_stock_ids=frozenset(),
                                 prior_variant_stock_ids=frozenset(), variant_index=0)
    assert ranked and all(c.identity_name == "Juniper Berry EO" for _, c in ranked)


def test_live_fruit_proposal_reports_unverified_recognition_without_blocking_research():
    from engine.research.formula_design import design_inventory_formula

    result = design_inventory_formula(idea="A juicy lychee perfume", design_mode="DEEP_COMPOSE", max_materials=12)
    assert result["design_variants"]
    for variant in result["design_variants"]:
        assert "NAMED_FRUIT_RECOGNITION_UNVERIFIED:lychee" in variant["critic"]["limitations"]
        assert variant["formula"]["request_alignment_basis"] == "STRUCTURAL_ROLE_COVERAGE_ONLY_NOT_SENSORY_ACCURACY"
        assert variant["solver"]["named_fruit_recognition"] == {"lychee": "NOT_SENSORY_VALIDATED"}
        assert variant["critic"]["state"] != "WITHHELD"
    assert result["pleasantness"] is result["beauty_score"] is None
