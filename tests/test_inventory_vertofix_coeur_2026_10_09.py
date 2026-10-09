"""Owner stock record of 2026-10-09: Vertofix and Vertofix Coeur are two bottles."""

from __future__ import annotations

import copy
import hashlib
import json

import pytest

import engine.inventory_parser as inventory
from engine.pipeline.preflight import _dilution_consistency_check

V5_VERTOFIX_STOCK_ID = "inventory:v5:956f2505d56f3a21b129"
RECORD_ID = "INV-USER-20261009-VTXC-001"


def _head() -> dict:
    return json.loads(inventory.CURRENT_USER_INVENTORY_OVERLAY_PATH.read_text(encoding="utf-8"))


def _stocks(identity_name: str):
    return [
        stock for stock in inventory.parse_current_inventory(unique=False)
        if stock.identity_name == identity_name
    ]


def _check(name: str):
    return _dilution_consistency_check(
        {
            "ingredients_ul": {name: 50.0},
            "dilutions": {name: 1.0},
            "stock_specs": {
                name: {"fraction": 1.0, "fraction_basis": "neat", "carrier": "", "declared": True}
            },
        }
    )


def test_v23_is_current_and_pinned_to_v22_and_live_inventory() -> None:
    path = inventory.CURRENT_USER_INVENTORY_OVERLAY_PATH
    assert path.name == "inventory_user_authority_overlay_20261009_vertofix_coeur.json"
    normalized = path.read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(normalized).hexdigest() == inventory.CURRENT_USER_INVENTORY_OVERLAY_SHA256
    head = _head()
    assert head["schema_version"].endswith("_v23")
    assert head["predecessor"]["normalized_text_sha256"] == (
        inventory.E2MB_OSMANTHUS_MIMOSA_USER_INVENTORY_OVERLAY_SHA256
    )
    raw = inventory.INVENTORY_PATH.read_bytes().replace(b"\r\n", b"\n")
    assert head["source"]["inventory_text_sha256"] == hashlib.sha256(raw).hexdigest()
    assert head["source"]["verbatim_user_statement"] == "There's both"
    assert head["superseded_record_ids"] == []
    overlay = inventory.load_current_user_inventory_overlay(require_live_inventory_binding=True)
    assert [r["record_id"] for r in overlay["delta_records"]] == [RECORD_ID]


def test_plain_vertofix_keeps_its_v5_row_242_stock() -> None:
    stocks = _stocks("Vertofix")
    assert len(stocks) == 1
    stock = stocks[0]
    assert stock.stock_id == V5_VERTOFIX_STOCK_ID
    assert stock.source_rows == (242,)
    assert (stock.status, stock.dilution, stock.execution_ready) == ("owned", 1.0, True)


def test_vertofix_coeur_is_its_own_stock_held_for_intake() -> None:
    stocks = _stocks("Vertofix Coeur")
    assert len(stocks) == 1
    stock = stocks[0]
    assert stock.status == "owned"
    assert stock.stock_id.startswith("inventory:user-20261009:")
    assert stock.stock_id != V5_VERTOFIX_STOCK_ID
    assert (stock.dilution, stock.fraction_basis, stock.carrier) == (1.0, "neat", "")
    assert stock.execution_ready is False
    assert stock.execution_hold_reason == "STOCK_INTAKE_IDENTITY_ONLY"
    assert stock.authority == inventory.VERTOFIX_COEUR_USER_INVENTORY_AUTHORITY
    assert stock.source_ref.endswith(f"#{RECORD_ID}")


def test_pw_receipt_line_7_belongs_to_the_vertofix_coeur_record() -> None:
    overlay = inventory.load_current_user_inventory_overlay()
    claims = [r for r in overlay["records"] if r.get("receipt_line") == 7]
    assert [r["record_id"] for r in claims] == [RECORD_ID]
    assert claims[0]["supplier_product"] == {
        "supplier": "PerfumersWorld",
        "product_name": "Vertofix Couer",
        "sku": "3WY00465",
    }
    assert overlay["policy"]["pw_receipt_line_7_belongs_to_vertofix_coeur_stock"] is True
    assert overlay["policy"]["v5_row_242_plain_vertofix_stock_unchanged"] is True


def test_preflight_resolves_each_formula_row_to_its_own_bottle() -> None:
    plain = _check("Vertofix")
    assert plain.status == "PASS"
    assert plain.data["resolved_stock_specs"]["Vertofix"]["stock_id"] == V5_VERTOFIX_STOCK_ID

    coeur = _check("Vertofix Coeur")
    reasons = {issue.get("reason") for issue in coeur.data["issues"]}
    assert "not_in_inventory" not in reasons
    # Owned but held for intake, like the other new bottles on the 2026-10-07 receipt.
    assert reasons == {"inventory_stock_non_executable"}
    (issue,) = coeur.data["issues"]
    assert issue["execution_holds"] == ["STOCK_INTAKE_IDENTITY_ONLY"]
    assert issue["fraction_matches_formula"] is True


def test_v23_loader_rejects_mutation() -> None:
    candidate = copy.deepcopy(_head())
    candidate["records"][0]["stock"]["execution_ready"] = True
    with pytest.raises(inventory.InventoryAuthorityError):
        inventory._load_20261009_vertofix_coeur_successor(
            candidate, require_live_inventory_binding=False
        )
