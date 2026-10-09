"""Owner confirmation of 2026-10-09: the Vertofix Coeur bottle is neat as supplied."""

from __future__ import annotations

import copy
import hashlib
import json

import pytest

import engine.inventory_parser as inventory
from engine.pipeline.preflight import _dilution_consistency_check

V5_VERTOFIX_STOCK_ID = "inventory:v5:956f2505d56f3a21b129"
RETIRED_V23_COEUR_STOCK_ID = "inventory:user-20261009:2b90a1fc6cde70ed8992"
V23_RECORD_ID = "INV-USER-20261009-VTXC-001"
RECORD_ID = "INV-USER-20261009-VTXC-NEAT-001"


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


def test_v24_is_current_and_pinned_to_v23_and_live_inventory() -> None:
    path = inventory.CURRENT_USER_INVENTORY_OVERLAY_PATH
    assert path.name == "inventory_user_authority_overlay_20261009_vertofix_coeur_neat.json"
    normalized = path.read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(normalized).hexdigest() == inventory.CURRENT_USER_INVENTORY_OVERLAY_SHA256
    head = _head()
    assert head["schema_version"].endswith("_v24")
    assert head["predecessor"] == {
        "path": "data/governance/inventory_user_authority_overlay_20261009_vertofix_coeur.json",
        "normalized_text_sha256": inventory.VERTOFIX_COEUR_USER_INVENTORY_OVERLAY_SHA256,
    }
    raw = inventory.INVENTORY_PATH.read_bytes().replace(b"\r\n", b"\n")
    assert head["source"]["inventory_text_sha256"] == hashlib.sha256(raw).hexdigest()
    assert head["source"]["inventory_text_size_bytes"] == len(raw)
    assert head["source"]["verbatim_user_statement"] == "Yes, neat"
    assert head["source"]["question"] == (
        "Confirm your Vertofix Coeur bottle is neat, as it came from PerfumersWorld?"
    )
    assert head["source"]["message_timestamp_utc"] == "2026-10-09T06:15:23Z"
    assert head["superseded_record_ids"] == [V23_RECORD_ID]
    overlay = inventory.load_current_user_inventory_overlay(require_live_inventory_binding=True)
    assert [r["record_id"] for r in overlay["delta_records"]] == [RECORD_ID]
    live = {r["record_id"] for r in overlay["records"]}
    retired = {r["record_id"] for r in overlay["retired_records"]}
    assert RECORD_ID in live and V23_RECORD_ID not in live
    assert V23_RECORD_ID in retired
    assert overlay["policy"]["compounding_authorized"] is False
    assert overlay["policy"]["formula_rebase_authorized"] is False
    assert overlay["policy"]["safety_or_release_asserted"] is False


def test_vertofix_coeur_is_one_neat_execution_ready_stock() -> None:
    stocks = _stocks("Vertofix Coeur")
    assert len(stocks) == 1
    stock = stocks[0]
    assert stock.status == "owned"
    assert stock.stock_id.startswith("inventory:user-20261009:")
    assert stock.stock_id not in {RETIRED_V23_COEUR_STOCK_ID, V5_VERTOFIX_STOCK_ID}
    assert (stock.dilution, stock.fraction_basis, stock.carrier) == (1.0, "neat", "")
    assert stock.execution_ready is True
    assert stock.execution_hold_reason == ""
    assert stock.authority == inventory.VERTOFIX_COEUR_NEAT_USER_INVENTORY_AUTHORITY
    assert stock.source_ref == (
        "data/governance/inventory_user_authority_overlay_20261009_vertofix_coeur_neat.json"
        f"#{RECORD_ID}"
    )
    all_ids = {s.stock_id for s in inventory.parse_current_inventory(unique=False)}
    assert RETIRED_V23_COEUR_STOCK_ID not in all_ids


def test_new_record_keeps_v23_identity_and_receipt_facts() -> None:
    v23 = json.loads(
        inventory.VERTOFIX_COEUR_USER_INVENTORY_OVERLAY_PATH.read_text(encoding="utf-8")
    )["records"][0]
    (record,) = _head()["records"]
    for key in (
        "canonical_name", "aliases", "state", "category", "supplier_product",
        "received_quantity_g", "receipt_line",
    ):
        assert record[key] == v23[key], key
    assert record["stock"] == {
        "physical_form": "as_supplied",
        "fraction": 1.0,
        "fraction_basis": "neat",
        "carrier": "",
        "fraction_authority": "EXPLICIT_USER_ASSERTION",
        "execution_ready": True,
        "execution_scope": "RAW_STOCK_VOLUME_TRANSFER_ONLY",
        "execution_basis": (
            "INV-USER-20261009-VTXC-001_INTAKE_HOLD_CLEARED_BY_USER_NEAT_CONFIRMATION"
        ),
    }
    overlay = inventory.load_current_user_inventory_overlay()
    claims = [r for r in overlay["records"] if r.get("receipt_line") == 7]
    assert [r["record_id"] for r in claims] == [RECORD_ID]


def test_plain_vertofix_keeps_its_v5_row_242_stock() -> None:
    stocks = _stocks("Vertofix")
    assert len(stocks) == 1
    stock = stocks[0]
    assert stock.stock_id == V5_VERTOFIX_STOCK_ID
    assert stock.source_rows == (242,)
    assert (stock.status, stock.dilution, stock.execution_ready) == ("owned", 1.0, True)


def test_preflight_passes_both_vertofix_bottles() -> None:
    plain = _check("Vertofix")
    assert plain.status == "PASS"
    assert plain.data["resolved_stock_specs"]["Vertofix"]["stock_id"] == V5_VERTOFIX_STOCK_ID

    (coeur_stock,) = _stocks("Vertofix Coeur")
    coeur = _check("Vertofix Coeur")
    assert coeur.status == "PASS"
    assert coeur.data["issues"] == []
    assert coeur.data["resolved_stock_specs"]["Vertofix Coeur"]["stock_id"] == (
        coeur_stock.stock_id
    )


@pytest.mark.parametrize(
    "mutate",
    [
        lambda c: c["records"][0]["stock"].__setitem__("execution_ready", False),
        lambda c: c["records"][0]["stock"].__setitem__("fraction", 0.1),
        lambda c: c["source"].__setitem__("verbatim_user_statement", "Yes"),
        lambda c: c["predecessor"].__setitem__("normalized_text_sha256", "0" * 64),
        lambda c: c.__setitem__("superseded_record_ids", []),
    ],
    ids=["execution_ready", "fraction", "statement", "predecessor_hash", "superseded"],
)
def test_v24_loader_rejects_mutation(mutate) -> None:
    candidate = copy.deepcopy(_head())
    mutate(candidate)
    with pytest.raises(inventory.InventoryAuthorityError):
        inventory._load_20261009_vertofix_coeur_neat_successor(
            candidate, require_live_inventory_binding=False
        )


def test_v24_loader_accepts_the_committed_overlay() -> None:
    overlay = inventory._load_20261009_vertofix_coeur_neat_successor(
        _head(), require_live_inventory_binding=False
    )
    assert overlay["record_origins"][RECORD_ID] == {
        "path": "data/governance/inventory_user_authority_overlay_20261009_vertofix_coeur_neat.json",
        "sha256": inventory.CURRENT_USER_INVENTORY_OVERLAY_SHA256,
    }
