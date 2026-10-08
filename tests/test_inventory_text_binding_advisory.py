"""A hand edit to inventory.txt is reported as drift, not a release-gate crash."""

from __future__ import annotations

from dataclasses import replace

import pytest

import engine.inventory_parser as inventory
from engine.pipeline.formula_state import build_formula_state
from engine.pipeline.preflight import (
    PreflightCheck,
    build_formula_dose_receipt,
    run_release_preflight,
)


@pytest.fixture
def drifted_inventory(tmp_path, monkeypatch):
    changed = tmp_path / "inventory.txt"
    changed.write_bytes(inventory.INVENTORY_PATH.read_bytes() + b"\n# drift\n")
    monkeypatch.setattr(inventory, "INVENTORY_PATH", changed)
    return changed


def _preflight_binding_check() -> dict:
    formula = {
        "name": "Inventory Text Binding Test",
        "ingredients_ul": {"Hedione": 100.0},
        "dilutions": {"Hedione": 1.0},
    }
    resolved = {
        "Hedione": {
            "fraction": 1.0,
            "fraction_basis": "neat",
            "carrier": "",
            "approximate": False,
            "declared": True,
            "stock_id": "inventory:test:1",
            "authority": "formula_row+inventory_snapshot",
            "inventory_authority": "TEST_CURRENT_INVENTORY",
            "source_rows": [1],
        }
    }
    contract = PreflightCheck(
        "inventory_stock_contract",
        "PASS",
        "Synthetic exact stock contract.",
        {
            "inventory_snapshot_sha256": "a" * 64,
            "inventory_source_workbook_sha256": "b" * 64,
            "inventory_authority_sheet": "Test",
            "resolved_stock_specs": resolved,
            "issues": [],
            "matched_stocks": [],
        },
    )
    receipt = build_formula_dose_receipt(formula, contract)
    state = build_formula_state(
        formula["ingredients_ul"],
        formula["dilutions"],
        stock_specs=resolved,
        batch_volume_ml=30.0,
    )
    state = replace(
        state,
        dose_receipt_sha256=receipt.receipt_sha256,
        dose_receipt_status=receipt.status,
    )
    report = run_release_preflight(
        formula, state, stock_contract=contract, dose_receipt=receipt
    ).as_dict()
    check = next(
        c for c in report["checks"] if c["check_name"] == "inventory_text_binding"
    )
    return {"check": check, "warnings": report["warnings"]}


def test_default_load_ignores_inventory_text_drift(drifted_inventory, monkeypatch):
    drifted = inventory.load_current_user_inventory_overlay()
    monkeypatch.undo()
    undrifted = inventory.load_current_user_inventory_overlay()
    assert drifted["records"] == undrifted["records"]


def test_binding_helper_reports_drift_with_both_sizes(drifted_inventory):
    binding = inventory.live_inventory_text_binding()
    assert binding["bound"] is False
    assert binding["actual_size_bytes"] == binding["expected_size_bytes"] + len(b"\n# drift\n")
    assert binding["actual_sha256"] != binding["expected_sha256"]
    assert binding["overlay_path"] == (
        inventory.CURRENT_USER_INVENTORY_OVERLAY_PATH.relative_to(inventory.PROJECT_ROOT).as_posix()
    )


def test_binding_helper_reports_bound_without_drift():
    binding = inventory.live_inventory_text_binding()
    assert binding["bound"] is True
    assert binding["inventory_path"] == "inventory.txt"
    assert binding["actual_size_bytes"] == binding["expected_size_bytes"]


def test_strict_mode_still_raises_on_drift(drifted_inventory):
    with pytest.raises(inventory.InventoryAuthorityError, match="bound to live inventory text"):
        inventory.load_current_user_inventory_overlay(require_live_inventory_binding=True)


def test_preflight_warns_on_drift_and_passes_without(drifted_inventory, monkeypatch):
    drifted = _preflight_binding_check()
    assert drifted["check"]["status"] == "WARN"
    assert "inventory.txt" in drifted["check"]["detail"]
    assert drifted["check"]["detail"] in drifted["warnings"]
    monkeypatch.undo()
    clean = _preflight_binding_check()
    assert clean["check"]["status"] == "PASS"
    assert not any("inventory.txt" in warning for warning in clean["warnings"])
