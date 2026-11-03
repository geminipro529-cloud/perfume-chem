"""A plant part in a label is not the material's name (engine bias audit, 2 Nov 2026).

The composer gives a query word five times its weight when it is one of the
material's name words.  The citrus layer's query word "peel" therefore matched
Orange Peel EO by its label, and it took the layer from Lemon FCF Oil Sicilian
in 18 of 44 briefs' unary rankings, although lemon, bergamot and grapefruit
oils are peel oils too.  Alone, a plant-part or preparation word (peel, leaf,
seed, root, flower, oil, absolute...) now earns only the vocabulary match any
material that carries it earns; "orange" and a phrase such as "orange peel"
still match the name.

These pin a scoring input; they make no sensory claim.
"""
from __future__ import annotations

import pytest

from engine.formulation_intelligence import formula_solver as fs
from engine.formulation_intelligence.formula_design_runtime import design_formula
from engine.formulation_intelligence.material_capability_index import (
    _term_score,
    build_material_capability_index,
)


@pytest.fixture(scope="module")
def caps():
    by_name = {}
    for cap in build_material_capability_index().capabilities:
        if cap.design_ready:
            by_name.setdefault(cap.identity_name, cap)
    return by_name


def test_a_plant_part_word_is_no_name_match(caps):
    orange_peel, lemon = caps["Orange Peel EO"], caps["Lemon FCF Oil Sicilian"]
    assert "peel" in orange_peel.identity_vocabulary  # kept: supports_descriptor_requirement reads it
    # A vocabulary match (3), not a name match (5): no more than the lemon peel oil earns.
    assert _term_score(orange_peel, ("peel",)) == pytest.approx(3.0)
    assert _term_score(orange_peel, ("peel",)) == _term_score(lemon, ("peel",))
    assert _term_score(caps["Carrot Seed EO"], ("seed",)) == pytest.approx(3.0)
    assert _term_score(caps["Violet Leaf Absolute"], ("leaf",)) == pytest.approx(3.0)


def test_the_material_word_and_a_phrase_still_match_the_name(caps):
    orange_peel = caps["Orange Peel EO"]
    assert _term_score(orange_peel, ("orange",)) == pytest.approx(5.0)
    assert _term_score(orange_peel, ("orange peel",)) == pytest.approx(5.0)
    assert _term_score(caps["Orange Flower Absolute"], ("orange flower",)) == pytest.approx(5.0)
    assert _term_score(caps["Violet Leaf Absolute"], ("violet leaf",)) == pytest.approx(5.0)


def test_the_citrus_layer_is_not_won_by_a_label_word(monkeypatch):
    # "a bright citrus cologne" names no orange: the label word "peel" alone
    # must not lift Orange Peel EO over the other sweet orange oil.
    ranked: dict[str, list] = {}
    original = fs._unary_rank_for_role

    def record(index, role, **kwargs):
        result = original(index, role, **kwargs)
        if kwargs.get("variant_index", 0) == 0:
            ranked.setdefault(role.role_id, result)
        return result

    monkeypatch.setattr(fs, "_unary_rank_for_role", record)
    design_formula(idea="a bright citrus cologne", design_mode="FAST_SKETCH")
    scores = {cap.identity_name: score for score, cap in ranked["facet_citrus_peel"]}
    assert ranked["facet_citrus_peel"][0][1].identity_name != "Orange Peel EO"
    assert scores["Orange Peel EO"] <= scores["Sweet Orange Essential Oil"] + 1e-6  # float sums
