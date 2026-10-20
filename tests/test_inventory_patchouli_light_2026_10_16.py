"""Patchouli Light Essential Oil from PerfumersWorld (v26 record STK-118).

Kenny, 16 Oct 2026 09:00:44 UTC (Formulation studio 3): "add patchouli light eential oil
from perfumerorld to inventory". No strength given; PW lists 7WB13670 as a neat essential
oil, so it is recorded neat as supplied, as a separate stock from Patchouli EO.
"""

import pytest

import engine.inventory_parser as inventory
from engine.ifra_standards import load_ifra_table
from engine.ingredient_intelligence import get_profile
from engine.material_resolver import resolve_material
from engine.odor_thresholds import lookup_odt_raw_name
from engine.pipeline.natural_absolute_decomposition import _resolve_profile_key

NAME = "Patchouli Light Essential Oil"


def _record():
    payload = inventory.load_current_user_inventory_overlay()
    rows = [r for r in payload["delta_records"] if r["canonical_name"] == NAME]
    assert len(rows) == 1
    return rows[0]


def test_patchouli_light_is_a_separate_neat_stock():
    record = _record()
    assert record["record_id"] == "INV-USER-20261014-STK-118"
    assert record["stock"]["fraction"] == 1.0
    assert record["stock"]["fraction_basis"] == "neat"
    assert record["supplier_product"]["sku"] == "7WB13670"
    assert record["authority_limits"]["strength_from_user_message"] is False
    assert record["authority_limits"]["fraction_from_supplier_listing"] is True
    stocks = inventory.materialize_current_inventory().stocks
    light = [s for s in stocks if s.name == NAME]
    regular = [s for s in stocks if s.name == "Patchouli EO"]
    assert len(light) == 1 and len(regular) == 1
    assert light[0].dilution == pytest.approx(1.0)
    assert light[0].execution_ready is True
    assert light[0].stock_id != regular[0].stock_id


def test_patchouli_light_links_to_the_patchouli_data_under_its_own_name():
    table = load_ifra_table()
    material = table.lookup(NAME)
    assert material is not None
    assert material.name == NAME
    assert material.status == "natural_no_own_standard"
    assert material is not table.lookup("Patchouli EO")
    assert lookup_odt_raw_name(NAME) == lookup_odt_raw_name("Patchouli EO")
    assert _resolve_profile_key(NAME) == ("patchouli eo", "literature_proxy")
    assert resolve_material(NAME).is_known
    profile = get_profile(NAME)
    assert profile.name == NAME
    assert profile.mw and profile.vp and profile.clogp
