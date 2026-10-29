"""Why the composer kept to the same stocks, and the three fixes (Kenny, 29 Oct 2026).

Asked "find out why the engine likes certain ingredients and doesn't use others, and fix
it". On the 34 duel and benchmark briefs (FAST) the composer used 132 owned stocks:

1. Old inventory.txt lines (design-only rows) carry the profile table's name, so they beat
   the owned bottle of the same material and the gate then held the formula (23 of 34).
2. Ten owned stock names missed a profile that exists under another spelling, so they got
   a category guess with no odour words.
3. Stocks with no profile at all ignored the material registry's own odour sentence, so
   they had no own-odour words and lost every unnamed layer.

These pin which stocks are eligible and what words they carry; they make no sensory claim.
"""
from __future__ import annotations

import pytest

from engine.formulation_intelligence.formula_design_runtime import design_formula
from engine.formulation_intelligence.material_capability_index import (
    _registry_odor_text,
    build_material_capability_index,
)
from engine.ingredient_intelligence import get_profile

LEGACY = "LEGACY_INVENTORY_TEXT_DESIGN_ONLY"


@pytest.fixture(scope="module")
def index():
    return build_material_capability_index()


@pytest.mark.parametrize(
    "idea",
    [
        "a soft woody amber with cedar and vetiver",
        "an aromatic fougere with rosemary and cedarwood",
        "a dark leather with labdanum",
    ],
)
def test_an_unnamed_role_never_takes_an_old_inventory_text_line(idea):
    rows = design_formula(idea=idea)["initial_formula"]["rows"]
    assert rows
    assert [row["material"] for row in rows if row.get("stock_authority") == LEGACY] == []


@pytest.mark.parametrize(
    ("stock", "profile"),
    [
        ("Cedarwood Virginia", "Cedarwood oil Virginia"),
        ("Cedarwood Himalayan EO", "Himalayan Cedarwood EO"),
        ("Coumarin Powder", "Coumarin"),
        ("Peppermint EO", "Peppermint Essential Oil"),
        ("Rosemary EO", "Rosemary EO (French Rosmarinus Officinalis leaf oil)"),
        ("Beta Damascone", "Damascone Beta"),
        ("Geranium Bourbon Essential Oil", "Geranium EO"),
        ("Olibanum Oil", "Frankincense EO"),
        ("Sweet Orange Essential Oil", "Orange Peel EO"),
        ("Black Pepper EO", "Black Pepper materials"),
    ],
)
def test_owned_stock_names_reach_their_profile(stock, profile):
    found = get_profile(stock)
    assert found is not None and found.name == profile


def test_owned_cedarwoods_have_own_odour_words(index):
    for name in ("Cedarwood Virginia", "Cedarwood Himalayan EO"):
        caps = [c for c in index.capabilities if c.identity_name == name]
        assert caps, name
        assert all(c.profile_source == "DECLARED_MATERIAL_PROFILE" for c in caps), name
        assert all("woody" in c.descriptor_vocabulary for c in caps), name


def test_a_stock_with_no_profile_takes_the_registry_odour_sentence(index):
    caps = [c for c in index.capabilities if c.identity_name == "Velvione"]
    assert caps
    for cap in caps:
        assert cap.profile_source == "HEURISTIC_CATEGORY_PROXY"
        assert cap.registry_descriptors
        assert {"musk", "powdery", "macrocyclic"} <= cap.descriptor_vocabulary


def test_a_stock_the_gate_cannot_score_gets_no_registry_words(index):
    # Red Saffron Infusion has a registry sentence but no own air threshold.
    caps = [c for c in index.capabilities if c.identity_name == "Red Saffron Infusion"]
    assert caps
    assert not any(c.registry_descriptors for c in caps)
    assert all(not c.descriptor_vocabulary for c in caps)


def test_registry_text_drops_where_a_material_is_used():
    # "the ingredient of choice in many musky or oriental colognes" names other
    # products' odours, not peppermint's.
    words = " ".join(_registry_odor_text("Peppermint EO")).casefold()
    assert "fresh" in words
    assert "musky" not in words
