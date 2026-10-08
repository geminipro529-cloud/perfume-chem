"""User-authoritative September 10 stock forms and supplier identities."""

from __future__ import annotations

import copy
import hashlib
import json

import pytest

import engine.inventory_parser as inventory
from engine.data_spine.loader import load_registry


@pytest.mark.parametrize(
    "name,fraction,basis,carrier",
    [
        ("Anisaldehyde 10%", 0.10, "volume_fraction", "ethanol"),
        ("Ethyl Maltol 1%", 0.01, "volume_fraction", "ethanol"),
        ("Hexyl Acetate 1%", 0.01, "volume_fraction", "dpg"),
        ("Helional 10%", 0.10, "volume_fraction", "ethanol"),
    ],
)
def test_confirmed_volume_stocks_are_execution_ready(
    name: str,
    fraction: float,
    basis: str,
    carrier: str,
) -> None:
    rows = [
        row
        for row in inventory.materialize_current_inventory().stocks
        if row.name == name and row.dilution == pytest.approx(fraction)
    ]
    assert len(rows) == 1
    row = rows[0]
    assert row.dilution == pytest.approx(fraction)
    assert row.fraction_basis == basis
    assert row.carrier == carrier
    assert row.execution_ready is True
    assert row.execution_hold_reason == ""


def test_haitian_vetiver_replaces_current_indian_origin_stock() -> None:
    rows = inventory.materialize_current_inventory().stocks
    haitian = [row for row in rows if row.name == "Vetiver EO (Haiti)"]
    indian = [row for row in rows if row.name == "Vetiver EO (India)"]
    assert len(haitian) == 1
    assert haitian[0].dilution == pytest.approx(1.0)
    assert haitian[0].execution_ready is True
    assert indian == []


def test_current_overlay_is_pinned_to_live_inventory_and_receipts() -> None:
    overlay_path = inventory.CURRENT_USER_INVENTORY_OVERLAY_PATH
    normalized = overlay_path.read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(normalized).hexdigest() == inventory.CURRENT_USER_INVENTORY_OVERLAY_SHA256
    payload = inventory.load_current_user_inventory_overlay()
    # 2026-10-08: the E2MB/Osmanthus/Mimosa record (v22, five records) is the head.
    assert payload["schema_version"].endswith("_v22")
    assert len(payload["delta_records"]) == 5
    assert payload["predecessor"]["normalized_text_sha256"] == (
        inventory.AMBRETTOLIDE_NEAT_USER_INVENTORY_OVERLAY_SHA256
    )


def test_stock_clarification_internal_loader_rejects_any_record_mutation() -> None:
    payload = json.loads(
        inventory.STOCK_CLARIFICATIONS_USER_INVENTORY_OVERLAY_PATH.read_text(
            encoding="utf-8"
        )
    )
    candidate = copy.deepcopy(payload)
    candidate["records"][0]["aliases"].append("unverified alias")
    with pytest.raises(inventory.InventoryAuthorityError, match="exact records drift"):
        inventory._load_20260910_stock_clarification_inventory_successor(
            candidate,
            require_live_inventory_binding=False,
        )


def test_current_user_stock_forms_supersede_the_older_supplier_only_holds() -> None:
    registry = load_registry()
    liffarome = registry.get("Liffarome")
    methyl_laitone = registry.get("Methyl Laitone")
    assert liffarome is not None
    assert liffarome.cas == "67633-96-9"
    assert liffarome.user_stock_dilution == "10% w/w in DEP"
    assert "stock-solution density" in (liffarome.notes or "")
    assert methyl_laitone is not None
    assert methyl_laitone.user_stock_dilution == "20% v/v in ethanol"
    assert "separate current stock" in (methyl_laitone.notes or "")


def test_exact_coriander_supplier_product_and_haitian_registry_identity_exist() -> None:
    registry = load_registry()
    coriander = registry.get("Coriander Essential Oil")
    haitian = registry.get("Vetiver EO (Haiti)")
    assert coriander is not None
    assert coriander.cas == "8008-52-4"
    assert coriander.user_stock_dilution == pytest.approx(1.0)
    assert "7SL00125" in (coriander.notes or "")
    assert haitian is not None
    assert haitian.user_in_inventory is True
    assert haitian.user_stock_dilution == "neat"
    assert haitian.vp_25c_pa is None


def test_cinnamyl_alcohol_is_50_percent_mass_fraction_in_dpg() -> None:
    rows = [
        row
        for row in inventory.materialize_current_inventory().stocks
        if row.name == "Cinnamyl Alcohol"
    ]
    assert len(rows) == 1
    row = rows[0]
    assert row.dilution == pytest.approx(0.5)
    assert row.fraction_basis == "mass_fraction"
    assert row.carrier == "dpg"
    assert row.execution_ready is True

    material = load_registry().get("Cinnamyl Alcohol")
    assert material is not None
    assert material.user_in_inventory is True
    assert material.user_stock_dilution == "50% w/w in DPG"
    assert "exact active mass from volume" in (material.notes or "")
