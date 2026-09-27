"""Current-stock authority for the user's neat Aroma&More Pink Pepper EO."""

from __future__ import annotations

import copy
import hashlib
import json

import pytest

import engine.inventory_parser as inventory
from engine.data_spine.loader import load_registry
from engine.name_utils import names_match, normalize_name
from engine.pipeline.preflight import resolve_inventory_stock_contract


def _pink_stock():
    rows = [
        row
        for row in inventory.materialize_current_inventory().stocks
        if row.name == "Pink Pepper EO"
    ]
    assert len(rows) == 1
    return rows[0]


def _check(label: str):
    stock = _pink_stock()
    return resolve_inventory_stock_contract(
        {
            "ingredients_ul": {label: 10.0},
            "dilutions": {label: 1.0},
            "stock_specs": {
                label: {
                    "fraction": 1.0,
                    "fraction_basis": "neat",
                    "carrier": "",
                    "declared": True,
                    "stock_id": stock.stock_id,
                }
            },
        }
    )


def test_pink_pepper_eo_materializes_as_one_execution_ready_neat_stock() -> None:
    stock = _pink_stock()

    assert stock.dilution == pytest.approx(1.0)
    assert stock.fraction_basis == "neat"
    assert stock.carrier == ""
    assert stock.execution_ready is True
    assert stock.authority == inventory.PINK_PEPPER_USER_INVENTORY_AUTHORITY
    assert stock.source_rows == ()
    assert stock.source_ref.endswith(
        "inventory_user_authority_overlay_20260915_pink_pepper.json#INV-USER-20260903-001"
    )

    material = load_registry().get("Pink Pepper EO")
    assert material is not None
    assert material.user_stock_dilution == pytest.approx(1.0)
    assert material.supplier.other["supplier"] == "Aroma&More"
    assert material.supplier.other["product_reference"] == "PinPP0324P"


@pytest.mark.parametrize(
    "label",
    [
        "Pink Pepper EO",
        "Pink Pepper EO (Schinus molle)",
        "Pink Pepper EO (Schinus molle; neat / as supplied)",
        "Schinus molle EO",
    ],
)
def test_pink_pepper_eo_labels_bind_to_the_same_current_stock(label: str) -> None:
    check = _check(label)

    assert check.status == "PASS", check.data.get("issues")
    matched = check.data["matched_stocks"]
    assert len(matched) == 1
    assert matched[0]["stock_id"] == _pink_stock().stock_id
    assert matched[0]["fraction"] == pytest.approx(1.0)
    assert matched[0]["fraction_basis"] == "neat"


def test_pink_pepper_eo_does_not_close_the_separate_eo_or_co2_gap() -> None:
    materialized = inventory.materialize_current_inventory()
    requirements = [
        row
        for row in materialized.requirements
        if row.canonical_name == "Pink Pepper EO / CO2"
    ]
    gap_stocks = [
        row
        for row in materialized.stocks
        if row.identity_name == "Pink Pepper EO / CO2"
    ]

    assert len(requirements) == 1
    assert requirements[0].source_row == 207
    assert requirements[0].disposition == "GAP"
    assert gap_stocks == []
    assert names_match("Pink Pepper EO", "Pink Pepper EO / CO2") is False
    assert normalize_name("Pink Pepper EO (Schinus molle; neat / as supplied)") == (
        "pink pepper eo"
    )


def test_pink_pepper_successor_is_pinned_to_predecessor_receipt_and_inventory() -> None:
    overlay_path = inventory.PINK_PEPPER_USER_INVENTORY_OVERLAY_PATH
    overlay_normalized = overlay_path.read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(overlay_normalized).hexdigest() == (
        inventory.PINK_PEPPER_USER_INVENTORY_OVERLAY_SHA256
    )
    predecessor = inventory.STOCK_CLARIFICATIONS_USER_INVENTORY_OVERLAY_PATH
    predecessor_normalized = predecessor.read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(predecessor_normalized).hexdigest() == (
        inventory.STOCK_CLARIFICATIONS_USER_INVENTORY_OVERLAY_SHA256
    )
    receipt = (
        inventory.PROJECT_ROOT
        / "data/governance/inventory_user_confirmation_20260915_pink_pepper.json"
    )
    assert hashlib.sha256(receipt.read_bytes()).hexdigest() == (
        inventory.PINK_PEPPER_CONFIRMATION_SHA256
    )
    payload = json.loads(overlay_path.read_text(encoding="utf-8"))
    assert payload["source"]["inventory_text_size_bytes"] == 25316
    assert payload["source"]["inventory_text_sha256"] == (
        "575f0b2832683341bb5759720f2a1a566eb20bd23cd62cf9e1cc08b4edf0f327"
    )
    loaded = inventory.load_current_user_inventory_overlay(overlay_path)
    assert loaded["schema_version"].endswith("_v11")
    assert loaded["delta_records"][0]["record_id"] == "INV-USER-20260903-001"


def test_pink_pepper_internal_loader_rejects_record_mutation() -> None:
    payload = json.loads(
        inventory.PINK_PEPPER_USER_INVENTORY_OVERLAY_PATH.read_text(encoding="utf-8")
    )
    candidate = copy.deepcopy(payload)
    candidate["records"][0]["aliases"].append("unverified alias")

    with pytest.raises(inventory.InventoryAuthorityError, match="exact stock record drift"):
        inventory._load_20260915_pink_pepper_inventory_successor(
            candidate,
            require_live_inventory_binding=False,
        )


def test_derived_material_cache_reflects_both_inventory_closures() -> None:
    cache = json.loads(
        (
            inventory.PROJECT_ROOT
            / "data/knowledge_graph/material_properties.json"
        ).read_text(encoding="utf-8")
    )
    by_name = {row["name"]: row for row in cache}
    pepper = by_name["Pink Pepper EO"]
    pyrazine = by_name["2-Acetyl Pyrazine"]

    assert pepper["in_inventory"] is True
    assert pepper["inventory_status"] == "BOUND_CURRENT_STOCK"
    assert pepper["stock_authority"] == inventory.CURRENT_USER_INVENTORY_OVERLAY_SHA256
    assert pepper["quantitative_stock_ready"] is True
    assert pepper["current_stocks"][0]["stock_id"] == _pink_stock().stock_id

    pyrazine_by_fraction = {
        row["dilution"]: row for row in pyrazine["current_stocks"]
    }
    assert pyrazine_by_fraction[1.0]["execution_ready"] is True
    assert pyrazine_by_fraction[0.01]["execution_ready"] is False

    for name in (
        "Blood Orange oil Sicilian",
        "Blue Chamomile EO",
        "Elemi EO",
        "Lime Distilled EO",
        "Orange Peel EO",
        "Pine EO",
        "Helichrysum EO",
    ):
        material = by_name[name]
        assert material["quantitative_stock_ready"] is True
        assert material["current_stocks"][0]["execution_ready"] is True
