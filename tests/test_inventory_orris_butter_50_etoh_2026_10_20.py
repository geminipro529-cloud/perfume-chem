"""Orris Butter 50% w/w in ethanol (v26 record STK-119).

Kenny, 20 Oct 2026 21:19:36 UTC ("Check new ingredients in code"): "open every document
and then add to inventory, add orri butter 30% in EtOH eight/.eight too", then "50%"
(21:19:57). Weight/weight in ethanol, 50%, separate from the 10% DPG butter and Orris Liquid.
"""

import pytest

import engine.inventory_parser as inventory
from engine.material_resolver import resolve_material
from engine.odor_thresholds import lookup_odt_raw_name
from engine.pipeline.natural_absolute_decomposition import _resolve_profile_key

NAME = "Orris Butter 50% in EtOH"


def test_orris_butter_50_is_a_separate_mass_fraction_ethanol_stock():
    payload = inventory.load_current_user_inventory_overlay()
    rows = [r for r in payload["delta_records"] if r["canonical_name"] == NAME]
    assert len(rows) == 1
    record = rows[0]
    assert record["record_id"] == "INV-USER-20261014-STK-119"
    assert record["stock"]["fraction"] == 0.5
    assert record["stock"]["fraction_basis"] == "mass_fraction"
    assert record["stock"]["carrier"] == "ethanol"
    assert record["authority_limits"]["butter_source_asserted"] is False
    stocks = inventory.materialize_current_inventory().stocks
    new = [s for s in stocks if s.name == NAME]
    old = [s for s in stocks if s.name == "Orris Concrete Orris Butter"]
    assert len(new) == 1 and len(old) == 1
    assert new[0].dilution == pytest.approx(0.5)
    assert new[0].fraction_basis == "mass_fraction"
    assert new[0].carrier == "ethanol"
    assert new[0].execution_ready is True
    assert old[0].dilution == pytest.approx(0.1) and old[0].carrier == "dpg"


def test_orris_butter_50_uses_the_orris_butter_scenario_under_its_own_name():
    assert resolve_material(NAME).is_known
    assert _resolve_profile_key(NAME) == _resolve_profile_key("Orris Concrete Orris Butter")
    assert _resolve_profile_key(NAME)[1] == "literature_proxy"
    assert lookup_odt_raw_name(NAME) == lookup_odt_raw_name("Orris Concrete Orris Butter")
