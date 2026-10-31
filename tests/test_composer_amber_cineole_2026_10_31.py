"""Amber layer, small crystal rows and the cardamom stack (Kenny, engine audit, 31 Oct 2026).

Kenny picked fixes 4 and 5 of the engine audit
(/mnt/project-files/engine-audit-20261031/ENGINE_AUDIT.md):

4. An amber layer counted ambergris's own facets (animalic, musky, powdery) as
   off-brief, so Ambrox Super paid 4 points and Amber Xtreme took 10 of 12
   amber layers.  A rule-weighed Ambrox Super crystal row under 100 mg (20 mg
   in the marine brief) now pours his Ambrox Super 25% instead: his scale
   cannot weigh tens of mg.
5. Cardamom beside another cineole or camphor oil reads medicinal: he poured
   out Cardamom, Rosemary, Lavender and Clary Sage on 25 Oct.  The composer
   now avoids that pair.

These pin the scoring inputs; they make no sensory claim.
"""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from engine.formulation_intelligence import formula_solver as fs
from engine.formulation_intelligence.formula_design_runtime import design_formula
from engine.formulation_intelligence.material_capability_index import (
    build_material_capability_index,
)


def _amber_layer():
    return SimpleNamespace(
        role_id="base_amber_layer", note="base", provenance="LAYERED_BASE_ARCHITECTURE",
        query_terms=("amber",), character_weights=(), exact_material=None, descriptor_requirement="base_amber",
    )


def _cap(*descriptors):
    return SimpleNamespace(note="base", character_map={}, descriptor_vocabulary=frozenset(descriptors))


def test_ambergris_facets_are_not_off_brief_in_an_amber_layer():
    assert fs._off_brief_penalty(_cap("ambergris", "animalic", "musky", "powdery"), _amber_layer(), frozenset()) == 0.0
    # A material without the amber family still pays for those facets.
    assert fs._off_brief_penalty(_cap("woody", "animalic"), _amber_layer(), frozenset()) > 0.0


def _duel(brief_id):
    duel = json.loads(Path("data/benchmarks/opus_duel_v1.json").read_text(encoding="utf-8"))["duel"]
    return next(entry for entry in duel if entry["id"] == brief_id)


def _rows(idea, **kwargs):
    result = design_formula(idea=idea, design_mode="FAST_SKETCH", **kwargs)
    return result["optimized_formula"]["rows"]


def test_no_rule_weighed_crystal_row_is_too_small_to_weigh():
    for idea in ("A marine ozonic with a mineral ambergris trail", "A soft woody amber"):
        for row in _rows(idea, liquid_concentrate_ul_decimal="6000"):
            if row.get("mass_basis") == "AMBROX_CRYSTAL_AS_25PCT_SOLUTION_ACTIVE":
                assert Decimal(row["amount_decimal"]) >= 100, row


def test_a_small_crystal_dose_pours_the_owned_solution():
    # This brief's amber facet rule-doses the crystals under 100 mg.
    brief = _duel("baie-rose-homme-r3")
    rows = [row for row in _rows(
        brief["idea"], formula_name=brief["name"], liquid_concentrate_ul_decimal=str(brief["concentrate_ul"]),
    ) if row["identity_name"] == "Ambrox Super"]
    assert rows
    for row in rows:
        assert (row["amount_unit"], row["operation"]) == ("uL", "DIRECT_ADD"), row
        assert row["stock_label"].startswith("25%"), row["stock_label"]


def test_cardamom_is_not_stacked_with_another_cineole_oil():
    caps = {c.identity_name: c for c in build_material_capability_index().capabilities if c.design_ready}
    assert fs._cineole_stack(caps["Cardamom EO"], caps["Rosemary EO"])
    assert not fs._cineole_stack(caps["Rosemary EO"], caps["Spike Lavender EO"])
    assert not fs._cineole_stack(caps["Cardamom EO"], caps["Lavender EO (BONTAUX SAS)"])
    brief = _duel("lavande-r7")
    names = {row["identity_name"] for row in _rows(
        brief["idea"], formula_name=brief["name"], liquid_concentrate_ul_decimal=str(brief["concentrate_ul"]),
    )}
    # The aromatic family asks for both rosemary and cardamom: one goes.
    stacked = [n for n in names if n != "Cardamom EO" and fs._cineole_camphor_fraction(n) >= .10]
    assert not ("Cardamom EO" in names and stacked), sorted(names)
