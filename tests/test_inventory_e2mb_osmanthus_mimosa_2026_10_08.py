"""Owner stock record of 2026-10-08: Osmanthus w/w, Mimosa kept, E2MB trace solutions."""

from __future__ import annotations

import copy
import hashlib
import json

import pytest

import engine.inventory_parser as inventory
from engine.pipeline.preflight import _dilution_consistency_check


def _head() -> dict:
    return json.loads(inventory.CURRENT_USER_INVENTORY_OVERLAY_PATH.read_text(encoding="utf-8"))


def _stocks(identity_name: str):
    return [
        stock for stock in inventory.materialize_current_inventory().stocks
        if stock.identity_name == identity_name
    ]


def _check(name: str, fraction: float, basis: str, carrier: str):
    return _dilution_consistency_check(
        {
            "ingredients_ul": {name: 50.0},
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
    )


def test_v22_is_current_and_pinned_to_v21_and_live_inventory() -> None:
    path = inventory.CURRENT_USER_INVENTORY_OVERLAY_PATH
    assert path.name == "inventory_user_authority_overlay_20261008_e2mb_osmanthus_mimosa.json"
    normalized = path.read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(normalized).hexdigest() == inventory.CURRENT_USER_INVENTORY_OVERLAY_SHA256
    head = _head()
    assert head["schema_version"].endswith("_v22")
    assert head["predecessor"]["normalized_text_sha256"] == (
        inventory.AMBRETTOLIDE_NEAT_USER_INVENTORY_OVERLAY_SHA256
    )
    raw = inventory.INVENTORY_PATH.read_bytes().replace(b"\r\n", b"\n")
    assert head["source"]["inventory_text_sha256"] == hashlib.sha256(raw).hexdigest()
    assert "Osmanthus is made by w/w, e2mb just record as the percentage" in (
        head["source"]["verbatim_user_statements"]
    )
    assert head["superseded_record_ids"] == [
        "INV-USER-20260828-006",
        "INV-USER-20260924-R5-011",
    ]


def test_superseded_osmanthus_and_mimosa_records_are_retired() -> None:
    overlay = inventory.load_current_user_inventory_overlay()
    live = {r["record_id"] for r in overlay["records"]}
    retired = {r["record_id"] for r in overlay["retired_records"]}
    for record_id in ("INV-USER-20260828-006", "INV-USER-20260924-R5-011"):
        assert record_id not in live
        assert record_id not in overlay["record_origins"]
        assert record_id in retired
    assert len(overlay["delta_records"]) == 5


def test_osmanthus_is_one_ten_percent_w_w_dpg_stock() -> None:
    stocks = _stocks("Osmanthus Absolute")
    assert len(stocks) == 1
    stock = stocks[0]
    assert stock.dilution == pytest.approx(0.1)
    assert (stock.fraction_basis, stock.carrier) == ("mass_fraction", "dpg")
    assert stock.execution_ready is True
    assert stock.authority == inventory.E2MB_OSMANTHUS_MIMOSA_USER_INVENTORY_AUTHORITY
    assert stock.source_ref.endswith("#INV-USER-20261008-V22-001")


def test_mimosa_is_kept_as_is_with_its_missing_receipts_recorded() -> None:
    stocks = _stocks("Mimosa Absolute")
    assert len(stocks) == 1
    assert stocks[0].execution_ready is True
    record = next(r for r in _head()["records"] if r["canonical_name"] == "Mimosa Absolute")
    limits = record["authority_limits"]
    assert limits["bottle_lot_receipt_asserted"] is False
    assert limits["preparation_receipt_asserted"] is False


def test_e2mb_trace_solutions_are_recorded_at_nominal_percentages() -> None:
    by_fraction = {
        round(stock.dilution, 6): stock
        for stock in _stocks("Ethyl 2-Methylbutyrate")
        if stock.carrier == "dpg"
    }
    assert set(by_fraction) == {0.01, 0.001, 0.0001}
    for fraction, stock in by_fraction.items():
        assert stock.fraction_basis == "mass_fraction"
        assert stock.execution_ready is True
        assert stock.stock_id.startswith("inventory:user-20261008:")
        result = _check("Ethyl 2-Methylbutyrate", fraction, "mass_fraction", "dpg")
        assert result.status == "PASS"
        resolved = result.data["resolved_stock_specs"]["Ethyl 2-Methylbutyrate"]
        assert resolved["stock_id"] == stock.stock_id
    for record in _head()["records"]:
        if record["canonical_name"] == "Ethyl 2-Methylbutyrate":
            assert record["authority_limits"]["nominal_percentage_only"] is True
            assert record["authority_limits"]["preparation_weights_asserted"] is False


def test_trace_stock_fractions_no_longer_match_a_neighbour_stock() -> None:
    # Before 2026-10-08 preflight used a flat 0.005 tolerance, so a 0.5% declaration
    # matched the owned 1% Calone stock and a 0.05% E2MB row matched the 0.1% solution.
    calone = _check("Calone", 0.005, "mass_fraction", "dpg")
    assert calone.status == "FAIL"
    assert "stock_fraction_mismatch" in {i.get("reason") for i in calone.data["issues"]}
    assert _check("Calone", 0.01, "mass_fraction", "dpg").status == "PASS"

    e2mb = _check("Ethyl 2-Methylbutyrate", 0.0005, "mass_fraction", "dpg")
    assert e2mb.status == "FAIL"
    assert "stock_fraction_mismatch" in {i.get("reason") for i in e2mb.data["issues"]}


def test_v22_loader_rejects_mutation() -> None:
    candidate = copy.deepcopy(_head())
    candidate["records"][0]["stock"]["fraction"] = 0.2
    with pytest.raises(inventory.InventoryAuthorityError):
        inventory._load_20261008_e2mb_osmanthus_mimosa_successor(
            candidate, require_live_inventory_binding=False
        )
