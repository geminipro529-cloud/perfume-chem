"""Lavender 40/42, Aroma&More passes the gate (Kenny, 20 Oct 2026 22:20:52 UTC, Formulation studio 3).

"Make it pass the gate, it is another lavender type". It was owned neat since 24 Sep, held only on a
lot/receipt hold that AGENTS.md Rule 6 says a formula does not need (as with Cedrat, STK-021). It keeps
its own lavender identity, with the Lavender EO threshold row and physics copied under its own name;
since 25 Oct 2026 its composition is its own 40/42-grade estimate (test_lavender_40_42_grade_profile_2026_10_25).
"""
from __future__ import annotations

import pytest

import engine.inventory_parser as inventory
from engine.ingredient_intelligence import get_profile
from engine.material_resolver import resolve_material
from engine.odor_thresholds import lookup_odt_raw_name
from engine.pipeline.natural_absolute_decomposition import _resolve_profile_key

NAME = "Lavender 40/42, Aroma&More"


def test_lavender_40_42_is_ready_neat_and_retires_the_held_record():
    payload = inventory.load_current_user_inventory_overlay()
    record = next(r for r in payload["delta_records"] if r["canonical_name"] == NAME)
    assert record["record_id"] == "INV-USER-20261014-STK-137"
    assert record["stock"]["fraction"] == 1.0 and record["stock"]["fraction_basis"] == "neat"
    assert record["stock"]["execution_ready"] is True
    assert "execution_hold_reason" not in record["stock"]
    assert record["supplier_product"]["sku"] == "Lav420811P"
    assert "INV-USER-20260924-R5-007" in payload["superseded_record_ids"]
    stocks = [s for s in inventory.materialize_current_inventory().stocks if s.name == NAME]
    assert len(stocks) == 1
    assert stocks[0].execution_ready is True and stocks[0].execution_hold_reason == ""
    assert stocks[0].dilution == pytest.approx(1.0)


def test_lavender_40_42_has_its_own_identity_with_lavender_eo_physics():
    resolved = resolve_material(NAME)
    assert resolved.is_known
    others = {resolve_material(n).canonical_name for n in ("Lavender EO", "Lavender EO (BONTAUX SAS)", "Spike Lavender EO")}
    assert resolved.canonical_name not in others
    assert lookup_odt_raw_name(NAME) == lookup_odt_raw_name("Lavender EO")
    assert _resolve_profile_key(NAME)[0] == "lavender 40/42 grade two published gc midpoint profile"
    own, ref = get_profile(NAME), get_profile("Lavender EO")
    assert own is not None and ref is not None
    assert (own.mw, own.vp) == (ref.mw, ref.vp)
