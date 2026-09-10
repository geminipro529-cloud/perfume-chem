"""Source-bound depletion removes one physical stock and retains its history."""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import asdict

import pytest

import engine.inventory_parser as inventory
from engine.pipeline.preflight import resolve_inventory_stock_contract

ROMANDOLIDE_STOCK_ID = "inventory:v5:caba57d5d5c78d414d5c"
ZENOLIDE_STOCK_ID = "inventory:v5:3fec3fbd1ff43a62aac7"
AHSEE_SHA256 = "dd779bd93e1e9191988b67aeb637f8362dfefb9e4696f86354ef6a371b85ee5d"


def _check(name: str, stock_id: str = ""):
    return resolve_inventory_stock_contract({
        "ingredients_ul": {name: 100.0},
        "dilutions": {name: 1.0},
        "stock_specs": {name: {
            "fraction": 1.0, "fraction_basis": "neat", "carrier": "",
            "declared": True, "stock_id": stock_id,
        }},
    })


def _raw_head():
    return json.loads(
        inventory.ROMANDOLIDE_USER_INVENTORY_OVERLAY_PATH.read_text(encoding="utf-8")
    )


def test_depleted_stock_fails_as_inventory_gap_and_cannot_bind_retired_id():
    check = _check("Romandolide")
    assert check.status == "FAIL"
    assert check.data["issues"][0]["reason"] == "inventory_gap"
    exact = _check("Romandolide", ROMANDOLIDE_STOCK_ID)
    assert exact.status == "FAIL"
    assert exact.data["issues"][0]["reason"] == "stock_id_not_in_current_inventory"


def test_successor_removes_only_romandolide_and_preserves_other_stock_objects():
    base = inventory.materialize_current_inventory(apply_user_overlay=False)
    previous = inventory._apply_current_user_inventory_overlay(
        base, inventory.load_current_user_inventory_overlay(inventory.AHSEE_USER_INVENTORY_OVERLAY_PATH),
    )
    current = inventory._apply_current_user_inventory_overlay(
        base,
        inventory.load_current_user_inventory_overlay(
            inventory.ROMANDOLIDE_USER_INVENTORY_OVERLAY_PATH
        ),
    )
    prior = {s.stock_id: asdict(s) for s in previous.stocks}
    assert prior[ROMANDOLIDE_STOCK_ID]["source_rows"] == (211,)
    assert {s.stock_id: asdict(s) for s in current.stocks} == {
        stock_id: stock for stock_id, stock in prior.items() if stock_id != ROMANDOLIDE_STOCK_ID
    }
    assert {r.source_row: asdict(r) for r in current.requirements if r.source_row != 211} == {
        r.source_row: asdict(r) for r in previous.requirements if r.source_row != 211
    }
    assert len(current.requirements) == len(previous.requirements)
    row = next(r for r in current.requirements if r.source_row == 211)
    assert (row.identity_name, row.requested_fraction, row.fraction_basis, row.carrier) == (
        "Romandolide", 1.0, "neat", "",
    )
    assert row.disposition == "GAP" and "DEPLETED" in row.status


def test_legacy_and_native_available_views_exclude_depleted_romandolide():
    legacy = inventory.parse_inventory(unique=False, include_unavailable=True)
    row = next(r for r in legacy if r.identity_name == "Romandolide")
    assert row.status == "depleted" and not row.execution_ready
    for parser in (inventory.parse_inventory, inventory.parse_current_inventory):
        assert not any(r.identity_name == "Romandolide" for r in parser(
            unique=False, include_unavailable=False,
        ))
    native = [r for r in inventory.parse_current_inventory(unique=False, include_unavailable=True)
              if r.identity_name == "Romandolide"]
    assert len(native) == 1
    assert (native[0].stock_id, native[0].status, native[0].execution_ready) == (
        "requirement:v5:r211", "gap", False,
    )


def test_zenolide_neat_keeps_its_exact_current_stock_binding():
    check = _check("Zenolide", ZENOLIDE_STOCK_ID)
    assert check.status == "PASS", check.data.get("issues")
    resolved = check.data["resolved_stock_specs"]["Zenolide"]
    assert (resolved["stock_id"], resolved["fraction"], resolved["fraction_basis"], resolved["carrier"]) == (
        ZENOLIDE_STOCK_ID, 1.0, "neat", "",
    )


def test_historical_ahsee_bytes_and_origins_remain_loadable_after_depletion():
    path = inventory.AHSEE_USER_INVENTORY_OVERLAY_PATH
    assert hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest() == AHSEE_SHA256
    previous = inventory.load_current_user_inventory_overlay(path)
    current = inventory.load_current_user_inventory_overlay(
        inventory.ROMANDOLIDE_USER_INVENTORY_OVERLAY_PATH
    )
    assert previous["source"]["inventory_text_size_bytes"] == 23705
    assert previous["source"]["inventory_text_sha256"] == "216bd300c709b453d9e9786bf8cfff1c6a62aca65203013b47782891d9f3269c"
    assert current["records"][:-1] == previous["records"]
    assert current["retired_records"] == previous["retired_records"]
    assert all(current["record_origins"][key] == value for key, value in previous["record_origins"].items())
    for record in previous["delta_records"]:
        assert current["record_origins"][record["record_id"]]["sha256"] == AHSEE_SHA256


def test_successor_rejects_semantic_drift_without_relying_on_outer_file_pin():
    original = _raw_head()
    mutations = [
        lambda p: p["predecessor"].update(normalized_text_sha256="0" * 64),
        lambda p: p["policy"].update(formula_rebase_authorized=True),
        lambda p: p.update(superseded_record_ids=["INV-USER-20260908-AHSEE-001"]),
        lambda p: p["records"].append(copy.deepcopy(p["records"][0])),
        lambda p: p["records"][0].update(canonical_name="Zenolide"),
        lambda p: p["records"][0].update(state="OWNED"),
        lambda p: p["records"][0].update(stock={"fraction": 1.0}),
        lambda p: p["records"][0]["supersedes_parent_stocks"][0].update(source_row=252),
        lambda p: p["records"][0]["supersedes_parent_stocks"][0].update(fraction=0.1),
        lambda p: p["records"][0]["requirement_overrides"][0].update(disposition="OWNED"),
        lambda p: p["records"][0].update(evidence_refs=[]),
        lambda p: p["records"][0]["authority_limits"].update(safety_or_release_asserted=True),
    ]
    for mutate in mutations:
        payload = copy.deepcopy(original)
        mutate(payload)
        with pytest.raises(inventory.InventoryAuthorityError):
            inventory._load_20260908_romandolide_inventory_successor(payload)


def test_successor_rejects_live_text_and_outer_overlay_byte_drift(tmp_path, monkeypatch):
    altered = tmp_path / "inventory.txt"
    altered.write_bytes(inventory.INVENTORY_PATH.read_bytes() + b" ")
    with monkeypatch.context() as patch:
        patch.setattr(inventory, "INVENTORY_PATH", altered)
        with pytest.raises(inventory.InventoryAuthorityError, match="source binding drift"):
            inventory.load_current_user_inventory_overlay()
    altered_head = tmp_path / "overlay.json"
    altered_head.write_bytes(inventory.CURRENT_USER_INVENTORY_OVERLAY_PATH.read_bytes() + b" ")
    with pytest.raises(inventory.InventoryAuthorityError, match="overlay hash drift"):
        inventory.load_current_user_inventory_overlay(altered_head)


def test_depletion_receipt_byte_drift_is_rejected(tmp_path, monkeypatch):
    payload = _raw_head()
    relative = payload["source"]["confirmed_receipt"]
    altered = tmp_path / relative
    altered.parent.mkdir(parents=True)
    altered.write_bytes((inventory.PROJECT_ROOT / relative).read_bytes() + b" ")
    monkeypatch.setattr(inventory, "PROJECT_ROOT", tmp_path)
    with pytest.raises(inventory.InventoryAuthorityError, match="receipt drift"):
        inventory._load_20260908_romandolide_inventory_successor(payload)
