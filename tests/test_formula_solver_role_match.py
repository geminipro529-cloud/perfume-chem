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
OUD_ROSE = "a dark oud rose for evening, no vanilla"
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
    # Coverage roles are steered off the shadow family only (not off wood).
    assert fs._off_brief_penalty(agarwood, coverage, frozenset()) == fs._OFF_BRIEF_FAMILY_PENALTY
    assert fs._off_brief_penalty(_cap("woody", "floral", "green"), coverage, frozenset()) == 0.0
    assert fs._off_brief_penalty(agarwood, _role(), frozenset()) == 0.0


def test_layer_without_own_odor_annotation_is_not_free():
    layer = _role(role_id="top_green_layer", provenance="LAYERED_TOP_ARCHITECTURE",
                  query_terms=("green",), descriptor_requirement="top_green")
    unannotated = _cap()
    assert fs._off_brief_penalty(unannotated, layer, frozenset()) == fs._OFF_BRIEF_FAMILY_PENALTY
    assert fs._off_brief_penalty(unannotated, _role(), frozenset()) == 0.0


def test_a_layer_takes_a_material_from_its_own_note_tier_or_lighter():
    citrus = _role(role_id="top_citrus_layer", note="top", provenance="LAYERED_TOP_ARCHITECTURE",
                   query_terms=("citrus",), descriptor_requirement="top_citrus")
    assert fs._note_tier_penalty(_cap("citrus", note="heart"), citrus) == fs._OFF_BRIEF_FAMILY_PENALTY
    assert fs._note_tier_penalty(_cap("citrus", note="base"), citrus) == fs._OFF_BRIEF_FAMILY_PENALTY
    assert fs._note_tier_penalty(_cap("citrus", note="top"), citrus) == 0.0
    assert fs._note_tier_penalty(_cap("citrus", note="unassigned"), citrus) == 0.0
    powder = _role(role_id="heart_powder_layer", note="heart", provenance="LAYERED_HEART_ARCHITECTURE")
    assert fs._note_tier_penalty(_cap("powdery", note="top"), powder) == 0.0
    assert fs._note_tier_penalty(_cap("powdery", note="base"), powder) == fs._OFF_BRIEF_FAMILY_PENALTY


def test_a_coverage_link_may_borrow_from_the_next_tier_but_not_skip_one():
    opening = _role(role_id="opening_articulation", note="top", provenance="FUNCTIONAL_COVERAGE")
    assert fs._note_tier_penalty(_cap("floral", note="heart"), opening) == 0.0
    assert fs._note_tier_penalty(_cap("powdery", note="base"), opening) == fs._OFF_BRIEF_FAMILY_PENALTY
    link = _role(role_id="heart_to_base_link", note="base", provenance="FUNCTIONAL_COVERAGE")
    assert fs._note_tier_penalty(_cap("woody", note="heart"), link) == 0.0
    assert fs._note_tier_penalty(_cap("citrus", note="top"), link) == fs._OFF_BRIEF_FAMILY_PENALTY
    # Accord supports and named stocks keep their own rules.
    assert fs._note_tier_penalty(_cap("musk", note="top"), _role()) == 0.0
    named = _role(role_id="top_citrus_layer", note="top", provenance="LAYERED_TOP_ARCHITECTURE",
                  exact_material="Hedione")
    assert fs._note_tier_penalty(_cap("citrus", note="heart"), named) == 0.0


def test_asking_for_oud_asks_for_the_shadow_family():
    brief = SimpleNamespace(normalized_request="a dark oud rose for evening", roles=())
    assert "base_shadow" in fs._asked_families(brief)
    assert "base_shadow" not in fs._asked_families(
        SimpleNamespace(normalized_request="a bright citrus cologne", roles=()))


def test_a_base_in_a_product_name_is_not_the_base_note():
    from engine.formulation_intelligence.material_capability_index import (
        build_material_capability_index,
    )

    names = {cap.identity_name: cap for cap in build_material_capability_index().capabilities}
    cassis = names["Cassis Base 345B"]
    assert "cassis" in cassis.identity_vocabulary
    assert "base" not in cassis.identity_vocabulary


def _rows(idea):
    result = design_formula(idea=idea)
    return (result["optimized_formula"] or result["initial_formula"])["rows"]


@pytest.fixture(scope="module")
def designs():
    return {idea: _rows(idea) for idea in (AMBER, COLOGNE, CHYPRE, OUD_ROSE)}


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


def test_coverage_fills_keep_annotated_materials(designs):
    # A family penalty on coverage roles once handed every opening to an
    # unannotated or family-free material (Juniper Berry EO, then Benzaldehyde).
    openings = {
        next(row["identity_name"] for row in rows if row["slot"] == "opening_articulation")
        for rows in designs.values()
    }
    assert not openings & {"Juniper Berry EO", "Benzaldehyde"}


def test_neroli_role_is_led_by_a_neroli_material(designs):
    lead = next(row["identity_name"] for row in designs[COLOGNE] if row["slot"] == "facet_white_floral")
    assert lead in {"Neroli EO", "Nerolin Bromelia", "Petitgrain EO Paraguay", "Oranger Crystals"}


def test_no_violet_leaf_background_fill(designs):
    for rows in designs.values():
        assert not any(row["identity_name"] == "Violet Leaf Absolute" for row in rows)


def test_top_citrus_layers_hold_citrus_not_hedione(designs):
    # #69's family penalty once handed the rose briefs' top citrus layer to
    # Hedione, a heart material that carries a citrus descriptor.
    for idea in (CHYPRE, OUD_ROSE):
        layer = next(row for row in designs[idea] if row["slot"] == "top_citrus_layer")
        assert "hedione" not in layer["identity_name"].casefold(), (idea, layer["identity_name"])


def test_oud_rose_links_are_not_picked_by_a_product_name(designs):
    link = next(row for row in designs[OUD_ROSE] if row["slot"] == "heart_to_base_link")
    assert not link["identity_name"].endswith(("Base", "Base 345B", "Base 3X")), link["identity_name"]
