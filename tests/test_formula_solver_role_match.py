"""Composer role matching: accord supports stay below and beside their lead,
and background fills avoid odor families the brief never asked for."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from engine.formulation_intelligence import formula_solver as fs
from engine.formulation_intelligence.formula_design_runtime import design_formula

AMBER = "warm amber with an iris heart and a smoky shadow"
COLOGNE = "fresh citrus cologne with neroli and a soft musk"
CHYPRE = "rose chypre with patchouli and oakmoss depth"
MUSKS = ("galaxolide", "habanolide", "zenolide", "romandolide", "exaltolide",
         "ambrettolide", "helvetolide", "ethylene brassylate")


def _role(**overrides):
    values = dict(
        role_id="facet_skin_musk__accord_1", note="base", provenance="ACCORD_SUPPORT",
        query_terms=("musk", "soft", "skin"), character_weights=(), exact_material=None,
        descriptor_requirement=None,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def _cap(*descriptors, note="base"):
    return SimpleNamespace(note=note, character_map={}, descriptor_vocabulary=frozenset(descriptors))


def test_musk_accord_support_needs_own_musk_descriptor():
    role = _role()
    lead = _cap("musk", "animalic", "sweet")
    assert fs._supports_accord(_cap("musky", "powdery"), role, lead)
    assert not fs._supports_accord(_cap("woody", "sandalwood", "creamy"), role, lead)
    assert not fs._supports_accord(_cap("suede", "leather"), role, lead)


def test_accord_support_without_descriptor_group_in_query_is_unchanged():
    role = _role(query_terms=("soft", "skin"))
    assert fs._supports_accord(_cap("woody"), role, _cap("musk"))


def test_off_brief_penalty_applies_to_layers_and_coverage_only():
    asked = frozenset({"base_amber", "heart_powder", "base_shadow"})
    pinene = _cap("green", "pine", "woody")
    layer = _role(role_id="top_green_layer", provenance="LAYERED_TOP_ARCHITECTURE",
                  query_terms=("green",), descriptor_requirement="top_green")
    assert fs._off_brief_penalty(pinene, layer, asked) == fs._OFF_BRIEF_FAMILY_PENALTY
    assert fs._off_brief_penalty(_cap("green", "leafy"), layer, asked) == 0.0
    coverage = _role(role_id="heart_to_base_link", provenance="FUNCTIONAL_COVERAGE",
                     query_terms=("amber", "heart", "base"))
    agarwood = _cap("smoky", "animalic", "woody", "amber")
    assert fs._off_brief_penalty(agarwood, coverage, frozenset()) == 2 * fs._OFF_BRIEF_FAMILY_PENALTY
    assert fs._off_brief_penalty(agarwood, _role(), frozenset()) == 0.0


def _rows(idea):
    result = design_formula(idea=idea)
    return (result["optimized_formula"] or result["initial_formula"])["rows"]


@pytest.fixture(scope="module")
def designs():
    return {idea: _rows(idea) for idea in (AMBER, COLOGNE, CHYPRE)}


def test_iris_lead_is_an_iris_material(designs):
    rows = designs[AMBER]
    lead = next(row for row in rows if row["slot"] == "facet_iris_violet")
    name = lead["identity_name"].casefold()
    assert any(marker in name for marker in ("orris", "iris", "irone", "methyl ionone"))
    assert not any(row["identity_name"] == "Beta-Pinene" for row in rows)


def test_musk_accord_rows_are_musks(designs):
    rows = designs[COLOGNE]
    musk_rows = [row for row in rows if row["slot"].startswith("facet_skin_musk")]
    assert musk_rows
    for row in musk_rows:
        assert any(musk in row["identity_name"].casefold() for musk in MUSKS), row
    assert not any("Black Agarwood" in row["identity_name"] for row in rows)


def test_no_violet_leaf_background_fill(designs):
    for rows in designs.values():
        assert not any(row["identity_name"] == "Violet Leaf Absolute" for row in rows)
