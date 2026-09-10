"""Current-stock and scientific-data contract for Simple Scents DIY Florhydral."""

from __future__ import annotations

import hashlib
import json

import pytest

import engine.inventory_parser as inventory
from engine.data_spine.loader import load_registry
from engine.ingredient_intelligence import get_profile
from engine.odor_thresholds import lookup_odt_entry
from engine.pipeline.preflight import resolve_inventory_stock_contract


def test_florhydral_is_current_owned_neat_and_executable() -> None:
    current = inventory.materialize_current_inventory()
    rows = [row for row in current.stocks if row.identity_name == "Florhydral"]
    assert len(rows) == 1
    row = rows[0]
    assert row.dilution == pytest.approx(1.0)
    assert row.fraction_basis == "neat"
    assert row.carrier == ""
    assert row.execution_ready is True
    assert row.authority == inventory.FLORHYDRAL_USER_INVENTORY_AUTHORITY

    check = resolve_inventory_stock_contract(
        {
            "ingredients_ul": {"Florhydral": 100.0},
            "dilutions": {"Florhydral": 1.0},
            "stock_specs": {
                "Florhydral": {
                    "fraction": 1.0,
                    "fraction_basis": "neat",
                    "carrier": "",
                    "declared": True,
                    "stock_id": row.stock_id,
                }
            },
        }
    )
    assert check.status == "PASS", check.data.get("issues")


def test_florhydral_overlay_is_pinned_to_receipt_and_live_inventory() -> None:
    path = inventory.FLORHYDRAL_USER_INVENTORY_OVERLAY_PATH
    normalized = path.read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(normalized).hexdigest() == inventory.FLORHYDRAL_USER_INVENTORY_OVERLAY_SHA256
    payload = inventory._load_20260910_florhydral_inventory_successor(
        json.loads(path.read_text(encoding="utf-8")),
        require_live_inventory_binding=False,
    )
    record = payload["delta_records"][0]
    assert record["canonical_name"] == "Florhydral"
    assert record["supplier"]["name"] == "Simple Scents DIY"
    assert record["stock"] == {
        "fraction": 1.0,
        "fraction_basis": "neat",
        "carrier": "",
        "fraction_authority": "DIRECT_USER_CONFIRMATION",
        "execution_ready": True,
    }

    receipt_path = (
        inventory.PROJECT_ROOT
        / "data/governance/inventory_user_confirmation_20260910_florhydral.json"
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["supplier"]["sku"] == "8F3094005319"
    assert receipt["authority_limits"]["analytical_purity_asserted"] is False


def test_florhydral_scientific_paths_are_populated() -> None:
    material = load_registry().get("Florhydral")
    assert material is not None
    assert material.user_in_inventory is True
    assert material.user_stock_dilution == pytest.approx(1.0)
    assert material.cas == "125109-85-5"
    assert material.mw_g_mol == pytest.approx(190.3)
    assert material.logp == pytest.approx(3.8)
    assert material.vp_25c_pa == pytest.approx(2.0)
    assert material.odt_air_ppb == pytest.approx(0.3)
    assert material.odt_eth_ppm == pytest.approx(0.2)

    profile = get_profile("Florhydral")
    assert profile is not None
    assert profile.cas == "125109-85-5"
    assert profile.mw == pytest.approx(190.3)
    assert profile.vp == pytest.approx(2.0)
    assert profile.or_family == "muguet"
    assert profile.activity_coef == pytest.approx(1.5)
    assert lookup_odt_entry("Florhydral") is not None
