"""A named stock takes the size the brief's words give it (engine bias audit, 2 Nov 2026).

Every stock the brief names became an explicit anchor role with the same share
(.12), whatever the brief said about it, so the planner split those stocks
equally.  In the Acqua di Gio Luxe brief ("a large Hedione jasmine
transparency ... a little incense and labdanum") Hedione and Labdanum were both
354 uL of 8000 (4.4%).  An anchor now reads the words before each place the
brief names it, as a facet does: "a large Hedione" takes 2.5 times the default
share, a stock every mention calls a nuance ("a little labdanum", "a little
incense and labdanum") takes the nuance share facets use, and any other
mention keeps .12.

These pin a share the planner scales from; they make no sensory claim.
"""
from __future__ import annotations

import pytest

from engine.formulation_intelligence.formula_design_runtime import design_formula
from engine.formulation_intelligence.semantic_brief_adapter import (
    _ANCHOR_EMPHASIS,
    _ANCHOR_SHARE,
    _NUANCE_SHARE,
    compile_semantic_brief,
)


def _anchor_shares(text: str, explicit: tuple[str, ...]) -> dict[str, float]:
    brief = compile_semantic_brief(
        formula_name="Anchor share trial",
        request=text,
        interpretation={"must_avoid": (), "must_preserve": (), "explicit_materials": explicit},
        max_materials=18,
    )
    return {
        role.exact_material: role.share
        for role in brief.roles
        if role.provenance == "EXPLICIT_REQUEST_MATERIAL"
    }


def test_the_default_and_emphasis_shares() -> None:
    assert _ANCHOR_SHARE == pytest.approx(.12)
    assert _ANCHOR_SHARE * _ANCHOR_EMPHASIS == pytest.approx(.30)
    assert _NUANCE_SHARE == pytest.approx(.035)


def test_a_large_hedione_gets_the_emphasis_share() -> None:
    shares = _anchor_shares("a fresh cologne built on a large Hedione transparency", ("hedione",))
    assert shares["hedione"] == pytest.approx(.30)


def test_a_little_labdanum_gets_the_nuance_share() -> None:
    shares = _anchor_shares("a fresh cologne with a little labdanum", ("labdanum",))
    assert shares["labdanum"] == pytest.approx(.035)


def test_a_nuance_reaches_the_second_of_two_named_notes() -> None:
    shares = _anchor_shares("an aquatic aromatic with a little incense and labdanum", ("labdanum",))
    assert shares["labdanum"] == pytest.approx(.035)


def test_a_plain_mention_keeps_the_default_share() -> None:
    shares = _anchor_shares("a citrus cologne with Hedione and labdanum", ("labdanum", "hedione"))
    assert shares == {"labdanum": pytest.approx(.12), "hedione": pytest.approx(.12)}


def test_a_stock_named_once_plainly_is_not_a_nuance() -> None:
    shares = _anchor_shares("a little labdanum on top and a labdanum base", ("labdanum",))
    assert shares["labdanum"] == pytest.approx(.12)


def test_a_material_named_by_its_alias_reads_the_alias() -> None:
    # "cedar" names Cedarwood Virginia (request_interpretation._MATERIAL_ALIASES).
    shares = _anchor_shares("a citrus cologne with a touch of cedar", ("Cedarwood Virginia",))
    assert shares["Cedarwood Virginia"] == pytest.approx(.035)


def test_adg_luxe_doses_hedione_large_and_labdanum_small() -> None:
    result = design_formula(
        idea=(
            "A luxurious aquatic aromatic in the style of Acqua di Gio: a large Hedione jasmine "
            "transparency, Calone sea air and ozone, bergamot and lemon citrus, neroli, rosemary, "
            "lavender and clary sage, a little incense and labdanum, geranium and violet leaf, "
            "cedar, patchouli and vetiver, an ambergris trail and clean musks. Not gourmand."
        ),
        formula_name="Acqua di Gio Luxe",
        liquid_concentrate_ul_decimal="8000",
        design_mode="FAST_SKETCH",
    )
    rows = (result.get("optimized_formula") or result.get("initial_formula") or {}).get("rows", ())
    # Active material: stock volume times the stock's own fraction (a 10% dilution counts a tenth).
    active = {
        str(row.get("identity_name")): float(row.get("amount_decimal")) * float(row.get("stock_fraction_decimal"))
        for row in rows
    }
    hedione, labdanum = active["Hedione"], active["Labdanum Absolute"]
    # Before: both 354 uL of neat stock, the same as every other named stock.
    assert hedione == max(active.values())
    assert labdanum < 150 < hedione / 4
