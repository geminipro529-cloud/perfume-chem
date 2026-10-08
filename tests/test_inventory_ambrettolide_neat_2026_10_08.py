"""Owner correction of 2026-10-08: the Ambrettolide stock is neat, not 10% w/w in DPG."""

from __future__ import annotations

import copy
import hashlib
import json

import pytest

import engine.inventory_parser as inventory
from engine.pipeline.preflight import _dilution_consistency_check


def _head() -> dict:
    return json.loads(inventory.CURRENT_USER_INVENTORY_OVERLAY_PATH.read_text(encoding="utf-8"))


def _check(fraction: float, basis: str, carrier: str):
    return _dilution_consistency_check(
        {
            "ingredients_ul": {"Ambrettolide": 100.0},
            "dilutions": {"Ambrettolide": fraction},
            "stock_specs": {
                "Ambrettolide": {
                    "fraction": fraction,
                    "fraction_basis": basis,
                    "carrier": carrier,
                    "declared": True,
                }
            },
        }
    )


def test_v21_is_current_and_pinned_to_v20_and_live_inventory() -> None:
    path = inventory.CURRENT_USER_INVENTORY_OVERLAY_PATH
    assert path.name == "inventory_user_authority_overlay_20261008_ambrettolide_neat.json"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == inventory.CURRENT_USER_INVENTORY_OVERLAY_SHA256
    head = _head()
    assert head["predecessor"]["normalized_text_sha256"] == inventory.TOBACCO_DBCA_USER_INVENTORY_OVERLAY_SHA256
    raw = inventory.INVENTORY_PATH.read_bytes().replace(b"\r\n", b"\n")
    assert head["source"]["inventory_text_sha256"] == hashlib.sha256(raw).hexdigest()
    assert head["source"]["verbatim_user_statement"] == "My ambretteolide is neat"
    assert head["superseded_record_ids"] == ["INV-USER-20260904-001"]
    previous = inventory.load_current_user_inventory_overlay(inventory.TOBACCO_DBCA_USER_INVENTORY_OVERLAY_PATH)
    assert previous["schema_version"].endswith("_v20")


def test_ambrettolide_has_one_neat_stock_and_the_ten_percent_record_is_retired() -> None:
    stocks = [
        stock for stock in inventory.materialize_current_inventory().stocks
        if stock.identity_name == "Ambrettolide"
    ]
    assert len(stocks) == 1
    stock = stocks[0]
    assert (stock.dilution, stock.fraction_basis, stock.carrier) == (1.0, "neat", "")
    assert stock.source_rows == (27, 28)
    assert stock.authority == inventory.AMBRETTOLIDE_NEAT_USER_INVENTORY_AUTHORITY
    assert stock.stock_id.startswith("inventory:user-20261008:")
    assert stock.source_ref.endswith("#INV-USER-20261008-AMBNEAT-001")

    overlay = inventory.load_current_user_inventory_overlay()
    assert "INV-USER-20260904-001" not in {r["record_id"] for r in overlay["records"]}
    assert "INV-USER-20260904-001" not in overlay["record_origins"]
    assert "INV-USER-20260904-001" in {r["record_id"] for r in overlay["retired_records"]}
    record = next(r for r in overlay["delta_records"] if r["canonical_name"] == "Ambrettolide")
    limits = record["authority_limits"]
    assert limits["fraction_basis_from_user_message"] is True
    assert limits["ten_percent_dpg_stock_asserted"] is False
    assert limits["formula_rebase_authorized"] is False
    assert limits["density_asserted"] is False


def test_formula_declaring_the_old_ten_percent_stock_no_longer_resolves() -> None:
    old = _check(0.1, "mass_fraction", "dpg")
    assert old.status == "FAIL"
    assert "stock_fraction_mismatch" in {issue.get("reason") for issue in old.data["issues"]}

    neat = _check(1.0, "neat", "")
    assert neat.status == "PASS"
    assert neat.data["resolved_stock_specs"]["Ambrettolide"]["stock_id"].startswith("inventory:user-20261008:")


def test_v21_loader_rejects_mutation() -> None:
    candidate = copy.deepcopy(_head())
    candidate["records"][0]["stock"]["fraction"] = 0.1
    with pytest.raises(inventory.InventoryAuthorityError, match="exact metadata drift"):
        inventory._load_20261008_ambrettolide_neat_successor(candidate, require_live_inventory_binding=False)
