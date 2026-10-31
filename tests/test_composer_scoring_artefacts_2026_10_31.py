"""More scoring artefacts that made some stocks win or lose every role (Kenny, 31 Oct 2026).

Kenny asked to "find other problems similar to" the Clearwood/Linalool ones:

1. 34 owned profiles carried note "unassigned", so every role scored them as a
   wrong-note material (-0.8 where a match earns +1.25). #169 filled them; a
   profile still without one now takes the registry's vapour-pressure tier.
2. The owned Bergamot FCF Oil Sicilian profile was tagged heart (the generic
   Bergamot FCF and Bergamot EO profiles are top), so it lost every opening.
3. A stock with no character data took full marks on every negative weight
   ("low sweetness"), since a missing value read as 0 (51 stocks before #169).
4. The composer looked odour thresholds up by exact name, so 9 stocks with a
   bulk air ODT the gate uses (suffixed labels, registry or profile thresholds)
   paid the unscorable penalty on every unnamed role.

These pin the scoring inputs; they make no sensory claim.
"""
from __future__ import annotations

import pytest

from engine.formulation_intelligence.material_capability_index import (
    _registry_note,
    build_material_capability_index,
    capability_role_score,
)


@pytest.fixture(scope="module")
def caps():
    by_name = {}
    for cap in build_material_capability_index().capabilities:
        by_name.setdefault(cap.identity_name, cap)
    return by_name


@pytest.mark.parametrize(
    ("name", "note"),
    [("Helvetolide", "base"), ("Cis-3 Hexenyl Acetate", "top"), ("Buccoxime", "heart")],
)
def test_the_registry_vapour_pressure_gives_a_note_tier(name, note):
    # #169 filled these profiles' notes; the fallback stays for the next stock
    # that arrives with none.
    assert _registry_note(name) == note


def test_a_stock_with_no_vapour_pressure_gets_no_tier():
    assert _registry_note("Rose Otto Bulgarian") == ""


def test_every_owned_stock_has_a_note_tier(caps):
    assert not [n for n, c in caps.items() if c.design_ready and c.note not in {"top", "heart", "base"}]


def test_the_owned_bergamot_is_a_top_note(caps):
    assert caps["Bergamot FCF Oil Sicilian"].note == "top"


def test_no_character_data_earns_nothing_on_a_negative_weight(caps):
    blank = next(cap for cap in caps.values() if not cap.character_map and cap.design_ready)

    def score(weights):
        return capability_role_score(
            blank, query_terms=(), character_weights=weights, note="heart",
            function="character", exact_material=None,
        )

    assert score((("sweetness", -1.0),)) == score(())
    annotated = caps["Bergamot FCF Oil Sicilian"]
    assert capability_role_score(
        annotated, query_terms=(), character_weights=(("sweetness", -1.0),), note="top",
        function="character", exact_material=None,
    ) > capability_role_score(
        annotated, query_terms=(), character_weights=(), note="top",
        function="character", exact_material=None,
    )


@pytest.mark.parametrize(
    "name",
    ["Vetiver EO (Haiti)", "Allyl Amyl Glycolate (AAG)", "Coumarin Powder", "Dimethyl Benzyl Carbinyl Acetate"],
)
def test_a_stock_the_gate_scores_is_not_unscorable_to_the_composer(name):
    # 4. The composer looked thresholds up by exact name, so these paid the
    # unscorable penalty on every unnamed role although the gate scores them.
    from engine.formulation_intelligence.formula_solver import _has_own_threshold

    assert _has_own_threshold(name)


@pytest.mark.parametrize("name", ["Red Saffron Infusion", "Oman Frankincense Ethanol Tincture"])
def test_a_stock_with_no_bulk_threshold_stays_unscorable(name):
    # The tincture is modelled only through its constituents (Kenny chose the
    # scorable Olibanum Resinoid over it, 15 Oct 2026).
    from engine.formulation_intelligence.formula_solver import _has_own_threshold

    assert not _has_own_threshold(name)
