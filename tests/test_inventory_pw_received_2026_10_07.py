"""Received purchase facts, stock separation, and immutable predecessor contracts."""

from __future__ import annotations

import copy
import hashlib
import json
from decimal import Decimal
from pathlib import Path

import pytest

import engine.inventory_parser as inventory
from engine.name_utils import normalize_name
from engine.personal_inventory import materialize_personal_inventory


def _receipt() -> dict:
    return json.loads(inventory.PW_RECEIVED_INVENTORY_RECEIPT_PATH.read_text(encoding="utf-8"))


def _head() -> dict:
    return json.loads(inventory.CURRENT_USER_INVENTORY_OVERLAY_PATH.read_text(encoding="utf-8"))


def test_received_order_totals_and_all_stock_forms_are_visible() -> None:
    receipt = _receipt()
    assert len(receipt["records"]) == 53
    assert sum(Decimal(row["received_quantity_g"]) for row in receipt["records"]) == 133
    stocks = materialize_personal_inventory().stocks
    for row in receipt["records"]:
        assert any(
            normalize_name(stock.identity_name or stock.name) == normalize_name(row["inventory_identity"])
            and stock.dilution == float(row["stock_fraction_decimal"])
            and stock.carrier.casefold() == row["carrier"].casefold()
            for stock in stocks
        ), row["supplier_product_name"]


def test_v19_binds_live_inventory_and_preserves_v18_stock_identity() -> None:
    head = _head()
    raw = inventory.INVENTORY_PATH.read_bytes().replace(b"\r\n", b"\n")
    assert head["source"]["inventory_text_sha256"] == hashlib.sha256(raw).hexdigest()
    assert head["source"]["inventory_text_size_bytes"] == len(raw)
    assert head["predecessor"]["normalized_text_sha256"] == inventory.AIMI_IDENTITY_USER_INVENTORY_OVERLAY_SHA256
    stocks = inventory.materialize_current_inventory().stocks
    aimi = [stock for stock in stocks if stock.identity_name == "Alpha Isomethyl Ionone"]
    assert len(aimi) == 1
    assert aimi[0].stock_id == "inventory:user-20260930:0f2e7662198d3a10bd1a"
    assert aimi[0].execution_ready is True


def test_new_dilutions_and_iris_products_are_not_collapsed() -> None:
    stocks = materialize_personal_inventory().stocks
    buccoxime = [stock for stock in stocks if stock.identity_name == "Buccoxime"]
    assert {(stock.dilution, stock.carrier) for stock in buccoxime} == {(1.0, ""), (0.1, "dpg")}
    ambrocenide = next(stock for stock in stocks if stock.identity_name == "Ambrocenide")
    assert (ambrocenide.dilution, ambrocenide.fraction_basis, ambrocenide.carrier) == (0.1, "unspecified", "tec")
    assert ambrocenide.execution_ready is False
    butter = next(stock for stock in stocks if stock.identity_name == "Orris Concrete Orris Butter")
    assert butter.dilution == 0.1 and butter.carrier == "dpg"
    liquid = [stock for stock in stocks if stock.identity_name == "Orris Liquid"]
    assert liquid and all(inventory.is_user_compounding_held(stock) for stock in liquid)
    assert not inventory.is_user_compounding_held(butter)


def test_received_kephalis_supersedes_absence_without_rewriting_history() -> None:
    previous = inventory.load_current_user_inventory_overlay(inventory.AIMI_IDENTITY_USER_INVENTORY_OVERLAY_PATH)
    old = next(record for record in previous["records"] if record["record_id"] == "INV-USER-20260907-007")
    assert old["state"] == "NOT_OWNED"
    current = inventory.load_current_user_inventory_overlay()
    assert old in current["retired_records"]
    assert any(record["canonical_name"] == "Kephalis" and record["state"] == "OWNED" for record in current["records"])
    admitted = [stock for stock in inventory.materialize_current_inventory().stocks if "user-20261007:" in stock.stock_id]
    assert len(admitted) == 43
    assert all(stock.execution_ready is False for stock in admitted)


def test_successor_rejects_changed_dose_or_authority() -> None:
    for field, value in (("fraction", 1.0), ("execution_ready", True)):
        candidate = copy.deepcopy(_head())
        candidate["records"][0]["stock"][field] = value
        with pytest.raises(inventory.InventoryAuthorityError, match="exact metadata drift"):
            inventory._load_20261007_pw_received_successor(candidate, require_live_inventory_binding=False)


def test_changed_receipt_or_live_text_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text("{}", encoding="utf-8")
    with monkeypatch.context() as patch:
        patch.setattr(inventory, "PW_RECEIVED_INVENTORY_RECEIPT_PATH", receipt_path)
        with pytest.raises(inventory.InventoryAuthorityError, match="receipt drift"):
            inventory._load_20261007_pw_received_successor(_head())
    text_path = tmp_path / "inventory.txt"
    text_path.write_text("changed", encoding="utf-8")
    with monkeypatch.context() as patch:
        patch.setattr(inventory, "INVENTORY_PATH", text_path)
        with pytest.raises(inventory.InventoryAuthorityError, match="live inventory text"):
            inventory._load_20261007_pw_received_successor(_head())


def test_receipt_and_predecessor_participate_in_materialization_fingerprint() -> None:
    fingerprint = inventory._inventory_materialization_fingerprint(
        inventory.CURRENT_INVENTORY_SNAPSHOT_PATH,
        apply_user_overlay=True,
        apply_user_completions=True,
    )
    paths = {record[0] for record in fingerprint}
    assert str(inventory.PW_RECEIVED_INVENTORY_RECEIPT_PATH.resolve()) in paths
    assert str(inventory.AIMI_IDENTITY_USER_INVENTORY_OVERLAY_PATH.resolve()) in paths
