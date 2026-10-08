"""Owner corrections of 2026-10-08: one Tobacco stock, PerfumersWorld DBCA identity."""

from __future__ import annotations

import copy
import hashlib
import json

import pytest

import engine.inventory_parser as inventory
from engine.pipeline.preflight import _dilution_consistency_check


def _head() -> dict:
    return json.loads(inventory.CURRENT_USER_INVENTORY_OVERLAY_PATH.read_text(encoding="utf-8"))


def test_v20_is_current_and_pinned_to_v19_and_live_inventory() -> None:
    path = inventory.CURRENT_USER_INVENTORY_OVERLAY_PATH
    assert path.name == "inventory_user_authority_overlay_20261008_tobacco_dbca.json"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == inventory.CURRENT_USER_INVENTORY_OVERLAY_SHA256
    head = _head()
    assert head["predecessor"]["normalized_text_sha256"] == inventory.PW_RECEIVED_USER_INVENTORY_OVERLAY_SHA256
    raw = inventory.INVENTORY_PATH.read_bytes().replace(b"\r\n", b"\n")
    assert head["source"]["inventory_text_sha256"] == hashlib.sha256(raw).hexdigest()
    assert head["source"]["verbatim_user_statement"] == (
        "Tobacco Absolute is in 10% in DPG only, DBCA is whatever is found on perfumers world."
    )
    # The v19 head stays loadable as history.
    previous = inventory.load_current_user_inventory_overlay(inventory.PW_RECEIVED_USER_INVENTORY_OVERLAY_PATH)
    assert previous["schema_version"].endswith("_v19")


def test_tobacco_has_one_v5_row_229_stock_and_is_not_ambiguous() -> None:
    tobacco = [
        stock for stock in inventory.materialize_current_inventory().stocks
        if stock.identity_name == "Tobacco Absolute"
    ]
    assert len(tobacco) == 1
    stock = tobacco[0]
    assert stock.source_rows == (229,)
    assert stock.stock_id == "inventory:v5:e0fbf5a84fd0feb76599"
    assert (stock.dilution, stock.fraction_basis, stock.carrier) == (0.1, "mass_fraction", "dpg")
    record = next(r for r in _head()["records"] if r["canonical_name"] == "Tobacco Absolute")
    assert record["authority_limits"]["fraction_basis_from_user_message"] is False

    check = _dilution_consistency_check(
        {
            "ingredients_ul": {"Tobacco Absolute": 50.0},
            "dilutions": {"Tobacco Absolute": 0.1},
            "stock_specs": {
                "Tobacco Absolute": {"fraction": 0.1, "fraction_basis": "unspecified", "carrier": "dpg", "declared": True}
            },
        }
    )
    assert "ambiguous_live_stock" not in {issue.get("reason") for issue in check.data["issues"]}
    assert check.data["resolved_stock_specs"]["Tobacco Absolute"]["stock_id"] == stock.stock_id


def test_dbca_identity_is_perfumersworld_carbinyl_without_lot_claims() -> None:
    stocks = inventory.materialize_current_inventory().stocks
    assert not any("Carbonyl" in stock.name for stock in stocks)
    dbca = [s for s in stocks if s.identity_name == "Dimethyl Benzyl Carbinyl Acetate"]
    assert len(dbca) == 1
    assert dbca[0].source_rows == (257,)
    assert (dbca[0].dilution, dbca[0].fraction_basis) == (1.0, "neat")
    assert dbca[0].authority == inventory.TOBACCO_DBCA_USER_INVENTORY_AUTHORITY
    record = next(r for r in _head()["records"] if r["canonical_name"] == "Dimethyl Benzyl Carbinyl Acetate")
    product = record["supplier_product"]
    assert (product["supplier"], product["sku"], product["cas"], product["ec"], product["mw_g_mol"]) == (
        "PerfumersWorld", "3LF00157", "151-05-3", "205-781-3", 192.26,
    )
    limits = record["authority_limits"]
    assert limits["user_lot_asserted"] is False
    assert limits["density_asserted"] is False
    assert limits["receipt_or_lot_holds_cleared"] is False


def test_v20_loader_rejects_mutation() -> None:
    candidate = copy.deepcopy(_head())
    candidate["records"][1]["supplier_product"]["sku"] = "unverified"
    with pytest.raises(inventory.InventoryAuthorityError, match="exact metadata drift"):
        inventory._load_20261008_tobacco_dbca_successor(candidate, require_live_inventory_binding=False)
