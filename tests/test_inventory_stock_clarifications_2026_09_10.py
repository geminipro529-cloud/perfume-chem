"""The September 10 successor binds only confirmed stock facts."""

from __future__ import annotations

import json

import pytest

import engine.inventory_parser as inventory
from engine.pipeline.preflight import resolve_inventory_stock_contract


@pytest.mark.parametrize(
    "name,fraction,basis,carrier",
    [
        ("Anisaldehyde", 0.1, "volume_fraction", "ethanol"),
        ("Ethyl Maltol", 0.01, "volume_fraction", "ethanol"),
        ("Hexyl Acetate", 0.01, "volume_fraction", "dpg"),
        ("Helional", 0.1, "volume_fraction", "ethanol"),
    ],
)
def test_confirmed_working_stocks_bind_exactly(name, fraction, basis, carrier):
    formula = {
        "ingredients_ul": {name: 100.0},
        "dilutions": {name: fraction},
        "stock_specs": {
            name: {
                "fraction": fraction,
                "fraction_basis": basis,
                "carrier": carrier,
                "declared": True,
            }
        },
    }
    result = resolve_inventory_stock_contract(formula)
    assert result.status == "PASS", result.data.get("issues")
    resolved = result.data["resolved_stock_specs"][name]
    assert (resolved["fraction"], resolved["fraction_basis"], resolved["carrier"]) == (
        fraction,
        basis,
        carrier,
    )


@pytest.mark.parametrize("name", ["Liffarome", "Methyl Laitone"])
def test_supplier_product_identity_does_not_clear_user_stock_hold(name):
    stock = next(
        row for row in inventory.materialize_current_inventory().stocks if row.name == name
    )
    assert not stock.execution_ready
    assert stock.execution_hold_reason


def test_tincture_starting_charge_cannot_be_promoted_to_active_fraction():
    payload = json.loads(
        inventory.CURRENT_USER_INVENTORY_OVERLAY_PATH.read_text(encoding="utf-8")
    )
    tincture = payload["records"][4]
    tincture["stock"]["fraction"] = tincture["stock"]["starting_charge_fraction"]
    tincture["stock"]["execution_ready"] = True
    with pytest.raises(inventory.InventoryAuthorityError, match="tincture contract drift"):
        inventory._load_20260910_stock_clarification_successor(payload)


def test_predecessor_records_and_stock_ids_are_preserved_except_explicit_successors():
    previous = inventory.load_current_user_inventory_overlay(
        inventory.ROMANDOLIDE_USER_INVENTORY_OVERLAY_PATH
    )
    current = inventory.load_current_user_inventory_overlay()
    retired = set(current["superseded_record_ids"])
    expected = [row for row in previous["records"] if row["record_id"] not in retired]
    assert current["records"][: len(expected)] == expected
    assert all(
        current["record_origins"][row["record_id"]]
        == previous["record_origins"][row["record_id"]]
        for row in expected
    )
