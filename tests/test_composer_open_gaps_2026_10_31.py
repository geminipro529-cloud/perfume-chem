"""Three gaps left after the 31 Oct scoring fixes (Kenny: "Fix those", 31 Oct 2026).

1. Powders.  No unnamed role could take a solid but the Ambrox Super crystals.
   Oranger Crystals 10% in DPG and the resin tinctures ("dissolved-solids
   fraction") read as solids by name although they are poured.  DMBCA is
   melted in the closed bottle and pipetted (Kenny, 30 Oct: his scale cannot
   weigh it).  Any other owned neat powder with no owned solution is now
   weighed as the active a 10% solution would carry; a dose under 100 mg is
   held for a 10% solution first.
2. Fuller descriptions paid more.  The off-brief penalty was 8 per family a
   material's description named, so Jasmine Absolute (floral, green, animalic)
   paid 16 where Jasmine Sambac (floral) paid 0.  Any number of off-brief
   families now costs one family's worth, half when the material also
   carries the brief.
3. A threshold entry with no air value (Diethyl Malonate's only records the
   receipt) counted as a threshold, so such a stock dodged the unscorable
   penalty and led the pear note of a brief the gate could not check.
4. Found on the way: a note's own word had to be one of a material's
   descriptors, so Frangipani Absolute, Jasmine Sambac Absolute and Rose Otto
   could not lead their own notes, and Benzyl Salicylate led frangipani.

These pin the scoring and dosing inputs; they make no sensory claim.
"""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from engine.formulation_intelligence import formula_solver as fs
from engine.formulation_intelligence.formula_design_runtime import design_formula
from engine.formulation_intelligence.material_capability_index import (
    build_material_capability_index,
    supports_descriptor_requirement,
)
from engine.formulation_intelligence.semantic_brief_adapter import compile_semantic_brief
from engine.research.composition_planner import WEIGHABLE_POWDER_MIN_MG


@pytest.fixture(scope="module")
def caps():
    by_name = {}
    for cap in build_material_capability_index().capabilities:
        if cap.design_ready:
            by_name.setdefault(cap.identity_name, cap)
    return by_name


def test_a_solution_is_poured_whatever_its_name_says(caps):
    assert not caps["Oranger Crystals"].candidate.solid


def test_dmbca_is_pipetted_melted_not_weighed():
    result = design_formula(idea="A dewy green lily of the valley with dimethyl benzyl carbinyl acetate",
                            liquid_concentrate_ul_decimal="6000", design_mode="FAST_SKETCH")
    rows = [row for row in result["optimized_formula"]["rows"]
            if row["identity_name"] == "Dimethyl Benzyl Carbinyl Acetate"]
    assert rows
    for row in rows:
        assert (row["amount_unit"], row["operation"]) == ("uL", "DIRECT_ADD")
        assert row["handling"] == "MELT_CLOSED_BOTTLE_IN_WARM_WATER_THEN_PIPETTE"


def _role(request, role_id):
    brief = compile_semantic_brief(
        formula_name="Probe", request=request,
        interpretation={"must_preserve": [], "must_avoid": [], "explicit_materials": [],
                        "material_count_constraints": []},
        max_materials=15,
    )
    return next(role for role in brief.roles if role.role_id == role_id)


def _ranked(role):
    index = build_material_capability_index()
    return [cap for _score, cap in fs._unary_rank_for_role(
        index, role, avoid=(), previous_stock_ids=frozenset(), prior_variant_stock_ids=frozenset(),
        variant_index=0,
    )]


def test_an_owned_powder_without_a_solution_can_fill_an_unnamed_role():
    ranked = _ranked(_role("A powdery heliotrope almond with soft vanilla", "facet_powder"))
    assert [cap.candidate.solid for cap in ranked if cap.identity_name == "Heliotropin"] == [True]


def test_a_powder_gives_way_to_its_owned_solution():
    # Kenny's scale cannot weigh small doses: Coumarin 10% takes coumarin's roles.
    ranked = _ranked(_role("A warm tonka and coumarin hay", "facet_tobacco_hay"))
    coumarins = [cap for cap in ranked if cap.identity_name.startswith("Coumarin")]
    assert coumarins
    assert not [cap.identity_name for cap in coumarins if cap.candidate.solid]


def test_a_weighed_powder_carries_the_active_of_its_ten_percent_solution():
    result = design_formula(idea="A powdery heliotrope almond with soft vanilla",
                            liquid_concentrate_ul_decimal="6000", design_mode="FAST_SKETCH")
    rows = [row for row in result["optimized_formula"]["rows"] if row["identity_name"] == "Heliotropin"]
    assert rows
    for row in rows:
        assert (row["amount_unit"], row["operation"]) == ("mg", "MASS_ADD")
        assert row["mass_basis"] == "POWDER_AS_10PCT_SOLUTION_ACTIVE"
        weighable = Decimal(row["amount_decimal"]) >= WEIGHABLE_POWDER_MIN_MG
        assert row["execution_ready"] is weighable
        if not weighable:
            assert row["execution_hold_reason"] == "MAKE_10PCT_SOLUTION_BELOW_WEIGHABLE_MASS"


def _layer():
    return SimpleNamespace(
        role_id="heart_floral_layer", note="heart", provenance="LAYERED_HEART_ARCHITECTURE",
        query_terms=("jasmine", "floral"), character_weights=(("floral", .8),),
        exact_material=None, descriptor_requirement=None,
    )


def _cap(*descriptors):
    return SimpleNamespace(note="heart", character_map={}, descriptor_vocabulary=frozenset(descriptors))


def test_a_fuller_description_does_not_pay_more():
    if _layer().provenance not in fs.LAYER_PROVENANCE.values():
        pytest.skip("layer provenance renamed")
    penalty = fs._OFF_BRIEF_FAMILY_PENALTY
    # floral, green, animalic: two families off-brief cost what one does.
    assert fs._off_brief_penalty(_cap("floral", "green", "animalic"), _layer(), frozenset()) == penalty / 2
    assert fs._off_brief_penalty(_cap("floral", "green"), _layer(), frozenset()) == penalty / 2
    assert fs._off_brief_penalty(_cap("floral"), _layer(), frozenset()) == 0.0
    # Wholly off-brief pays one family's worth, however many it names.
    assert fs._off_brief_penalty(_cap("green", "animalic"), _layer(), frozenset()) == penalty
    assert fs._off_brief_penalty(_cap("green"), _layer(), frozenset()) == penalty


def test_a_threshold_entry_without_an_air_value_is_unscorable():
    assert not fs._has_own_threshold("Diethyl Malonate")
    assert fs._has_own_threshold("Hexyl Acetate")


def test_the_pear_lead_is_a_stock_the_gate_can_score():
    duel = json.loads(Path("data/benchmarks/opus_duel_v1.json").read_text(encoding="utf-8"))["duel"]
    brief = next(entry for entry in duel if entry["id"] == "chimie-femme-r8-1")
    result = design_formula(idea=brief["idea"], formula_name=brief["name"],
                            liquid_concentrate_ul_decimal=str(brief["concentrate_ul"]),
                            design_mode="FAST_SKETCH")
    (lead,) = [row for row in result["optimized_formula"]["rows"] if row["slot"] == "facet_fruit"]
    assert fs._has_own_threshold(lead["identity_name"]), lead["identity_name"]


@pytest.mark.parametrize(
    ("name", "requirement"),
    [("Frangipani Absolute", "frangipani"), ("Jasmine Sambac Absolute", "jasmine"), ("Rose Otto Bulgarian", "rose")],
)
def test_a_natural_named_for_a_note_can_lead_it(caps, name, requirement):
    assert supports_descriptor_requirement(caps[name], requirement)


def test_guard_a_name_proves_no_layer_family_or_multi_word_facet(caps):
    # Orange Flower Absolute is not a citrus layer; a myrrh tincture's "resin"
    # is not a bitter green resin.
    assert not supports_descriptor_requirement(caps["Orange Flower Absolute"], "top_citrus")
    assert not supports_descriptor_requirement(caps["Kenyan Myrrh Ethanol Tincture"], "bitter_resin_green")
    # A product name that is not a natural proves nothing.
    assert not supports_descriptor_requirement(caps["Rose Oxide"], "jasmine")


def test_the_frangipani_note_is_led_by_frangipani_absolute():
    result = design_formula(
        idea=("Fresh frangipani on skin, creamy and a little apricot, then a modern ambery trail of "
              "ambergris, Iso E Super, benzoin and vanilla. Easy to wear."),
        formula_name="Frangipani Ambre R4", liquid_concentrate_ul_decimal="6000", design_mode="FAST_SKETCH",
    )
    (lead,) = [row for row in result["optimized_formula"]["rows"] if row["slot"] == "facet_frangipani"]
    assert lead["identity_name"] == "Frangipani Absolute"
