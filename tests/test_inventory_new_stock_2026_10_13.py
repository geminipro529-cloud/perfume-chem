"""Kenny's new bottles of 2026-10-13: Pomelo EO, Ginger Lily Oil and neat Exaltolide."""

from __future__ import annotations

import copy
import hashlib
import json

import pytest

import engine.inventory_parser as inventory
from engine.pipeline.preflight import _dilution_consistency_check

OVERLAY_NAME = "inventory_user_authority_overlay_20261013_pomelo_ginger_lily_exaltolide.json"
RECORDS = {
    "INV-USER-20261013-NEW-001": "Pomelo EO",
    "INV-USER-20261013-NEW-002": "Ginger Lily Oil",
    "INV-USER-20261013-NEW-003": "Exaltolide",
}
V5_EXALTOLIDE_10_STOCK_IDS = {
    "inventory:v5:b061617eb60192cbeb5d",
    "inventory:v5:c17c932da02ecafc0c44",
}


def _head() -> dict:
    return json.loads(inventory.NEW_STOCK_20261013_USER_INVENTORY_OVERLAY_PATH.read_text(encoding="utf-8"))


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


def test_v25_is_pinned_to_v24_and_live_inventory() -> None:
    path = inventory.NEW_STOCK_20261013_USER_INVENTORY_OVERLAY_PATH
    assert path.name == OVERLAY_NAME
    normalized = path.read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(normalized).hexdigest() == inventory.NEW_STOCK_20261013_USER_INVENTORY_OVERLAY_SHA256
    head = _head()
    assert head["schema_version"].endswith("_v25")
    assert head["predecessor"] == {
        "path": "data/governance/inventory_user_authority_overlay_20261009_vertofix_coeur_neat.json",
        "normalized_text_sha256": inventory.VERTOFIX_COEUR_NEAT_USER_INVENTORY_OVERLAY_SHA256,
    }
    # Bound to inventory.txt as it was before the 2026-10-16 edit (Tuberose Base
    # and Leather FO removed); the current overlay carries the live binding.
    assert head["source"]["inventory_text_sha256"] == (
        "116c39815c81d148f0a259332b8acf734b9f3eced484b5e390dc4bc7df38cc58"
    )
    assert head["source"]["inventory_text_size_bytes"] == 35704
    assert [s["text"] for s in head["source"]["verbatim_user_statements"]] == [
        "osmanthus absolute 10% in DPG is restocked, pomelo EO is added to inventory, "
        "ginger lily is added to inventory, and neat exaltolide pendecanolide is added to inventory",
        "1. it is an oil 2. pomelo EO is neat. 3. Neat exaltolide is liquid",
    ]
    assert head["superseded_record_ids"] == []
    overlay = inventory.load_current_user_inventory_overlay(path)
    assert [r["record_id"] for r in overlay["delta_records"]] == list(RECORDS)
    assert overlay["retired_records"] == inventory.load_current_user_inventory_overlay(
        inventory.VERTOFIX_COEUR_NEAT_USER_INVENTORY_OVERLAY_PATH
    )["retired_records"]
    assert overlay["policy"]["compounding_authorized"] is False
    assert overlay["policy"]["formula_rebase_authorized"] is False
    assert overlay["policy"]["safety_or_release_asserted"] is False


@pytest.mark.parametrize("record_id,name", list(RECORDS.items()))
def test_each_new_bottle_is_one_neat_execution_ready_stock(record_id: str, name: str) -> None:
    neat = [stock for stock in _stocks(name) if stock.dilution == 1.0]
    assert len(neat) == 1
    stock = neat[0]
    assert stock.status == "owned"
    assert stock.stock_id.startswith("inventory:user-20261013:")
    assert (stock.fraction_basis, stock.carrier) == ("neat", "")
    assert stock.execution_ready is True
    assert stock.execution_hold_reason == ""
    assert stock.authority == inventory.NEW_STOCK_20261013_USER_INVENTORY_AUTHORITY
    assert stock.source_ref == f"data/governance/{OVERLAY_NAME}#{record_id}"


def test_ginger_lily_strength_is_recorded_as_supplied_not_as_stated() -> None:
    (record,) = [r for r in _head()["records"] if r["canonical_name"] == "Ginger Lily Oil"]
    assert record["stock"]["fraction_authority"] == "USER_STATED_AS_SUPPLIED_STRENGTH_NOT_STATED"
    assert record["authority_limits"]["fraction_basis_from_user_message"] is False
    assert record["authority_limits"]["fraction_assumed_as_supplied"] is True
    assert record["authority_limits"]["plant_part_asserted"] is False


def test_existing_exaltolide_10pct_stocks_are_unchanged() -> None:
    tens = {stock.stock_id for stock in _stocks("Exaltolide") if stock.dilution == 0.1}
    assert tens == V5_EXALTOLIDE_10_STOCK_IDS


@pytest.mark.parametrize("name", list(RECORDS.values()))
def test_preflight_passes_each_new_bottle_neat(name: str) -> None:
    (stock,) = [s for s in _stocks(name) if s.dilution == 1.0]
    check = _check(name)
    assert check.status == "PASS"
    assert check.data["issues"] == []
    assert check.data["resolved_stock_specs"][name]["stock_id"] == stock.stock_id


@pytest.mark.parametrize(
    "mutate",
    [
        lambda c: c["records"][0]["stock"].__setitem__("execution_ready", False),
        lambda c: c["records"][1]["stock"].__setitem__("fraction", 0.1),
        lambda c: c["source"]["verbatim_user_statements"][1].__setitem__("text", "ok"),
        lambda c: c["predecessor"].__setitem__("normalized_text_sha256", "0" * 64),
        lambda c: c["records"][2].__setitem__("record_id", "INV-USER-20261009-VTXC-NEAT-001"),
    ],
    ids=["execution_ready", "fraction", "statement", "predecessor_hash", "reused_id"],
)
def test_v25_loader_rejects_mutation(mutate) -> None:
    candidate = copy.deepcopy(_head())
    mutate(candidate)
    with pytest.raises(inventory.InventoryAuthorityError):
        inventory._load_20261013_pomelo_ginger_lily_exaltolide_successor(
            candidate, require_live_inventory_binding=False
        )
