"""Current authority for the September 15 stock forms and tincture model."""

from __future__ import annotations

import copy
import hashlib
import json

import pytest

import engine.inventory_parser as inventory
from engine.data_spine.loader import load_registry
from engine.optimizer.gate_aware import _inventory_stock_dilutions
from engine.pipeline.preflight import resolve_inventory_stock_contract


def _stocks(name: str):
    # Display names now carry the bottle's strength ("2-Acetyl Pyrazine 1%"),
    # so a material is found by its identity as well as by its display name.
    return [
        row
        for row in inventory.materialize_current_inventory().stocks
        if name in {row.name, row.identity_name}
    ]


def _stock(name: str, fraction: float):
    matches = [
        row
        for row in _stocks(name)
        if row.dilution == pytest.approx(fraction)
    ]
    assert len(matches) == 1
    return matches[0]


def _preflight(name: str, fraction: float, basis: str, carrier: str):
    stock = _stock(name, fraction)
    return resolve_inventory_stock_contract(
        {
            "ingredients_ul": {name: 10.0},
            "dilutions": {name: fraction},
            "stock_specs": {
                name: {
                    "fraction": fraction,
                    "fraction_basis": basis,
                    "carrier": carrier,
                    "declared": True,
                    "stock_id": stock.stock_id,
                }
            },
        }
    )


@pytest.mark.parametrize(
    "name,fraction,basis,carrier",
    [
        ("Romandolide", 1.0, "neat", ""),
        ("Liffarome", 0.1, "mass_fraction", "dep"),
        ("Methyl Laitone", 0.2, "volume_fraction", "ethanol"),
        ("Castoreum Synthetic", 0.1, "mass_fraction", "dep"),
        ("Siam Benzoin", 0.5, "mass_fraction", "dpg"),
        ("Peru Balsam Resinoid", 0.5, "mass_fraction", "dep"),
        ("Evernyl", 0.1, "mass_fraction", "dpg"),
        ("Methyl Pamplemousse", 0.1, "mass_fraction", "ethanol"),
    ],
)
def test_confirmed_complete_stock_forms_are_execution_ready(
    name: str,
    fraction: float,
    basis: str,
    carrier: str,
) -> None:
    stock = _stock(name, fraction)
    assert (stock.fraction_basis, stock.carrier, stock.execution_ready) == (
        basis,
        carrier,
        True,
    )
    assert stock.authority == inventory.STOCK_FORMS_USER_INVENTORY_AUTHORITY
    assert stock.execution_hold_reason == ""

    check = _preflight(name, fraction, basis, carrier)
    assert check.status == "PASS", check.data.get("issues")


@pytest.mark.parametrize(
    "name,fraction,carrier,hold",
    [
        ("2-Acetyl Pyrazine", 0.01, "dpg", "FRACTION_BASIS_UNSPECIFIED"),
        ("Skatole", 0.01, "dpg", "FRACTION_BASIS_UNSPECIFIED"),
        ("Gamma Nonalactone", 0.1, "ethanol", "FRACTION_BASIS_UNSPECIFIED"),
    ],
)
def test_carrier_only_clarifications_preserve_missing_basis_holds(
    name: str,
    fraction: float,
    carrier: str,
    hold: str,
) -> None:
    stock = _stock(name, fraction)
    assert stock.fraction_basis == "unspecified"
    assert stock.carrier == carrier
    assert stock.execution_ready is False
    assert stock.execution_hold_reason == hold

    check = _preflight(name, fraction, "unspecified", carrier)
    assert check.status == "FAIL"
    assert check.data["issues"][0]["reason"] in {
        "inventory_stock_non_executable",
        "inventory_stock_metadata_incomplete",
    }


@pytest.mark.parametrize(
    "name,fraction",
    [
        ("Turkish Storax Tincture", 0.2),
        ("Vietnamese Benzoin Tincture", 0.4),
        ("Kenyan Myrrh Ethanol Tincture", 0.2),
        ("Oman Frankincense Ethanol Tincture", 0.33),
    ],
)
def test_tincture_starting_charge_is_nominal_model_authority_only(
    name: str,
    fraction: float,
) -> None:
    stock = _stock(name, fraction)
    assert stock.fraction_basis == "mass_fraction_starting_charge"
    assert stock.carrier == "ethanol"
    assert stock.approximate is True
    assert stock.execution_ready is False
    assert stock.execution_hold_reason == "FINAL_DISSOLVED_FRACTION_UNMEASURED"
    assert stock.nominal_property_model_ready is True
    assert stock.nominal_property_model_limit == (
        "STARTING_CHARGE_FRACTION_IS_NOT_A_FINAL_FILTRATE_ASSAY"
    )


def test_optimizer_uses_only_executable_or_explicit_nominal_model_stocks() -> None:
    inferred = _inventory_stock_dilutions(
        [
            "Turkish Storax Tincture",
            "Vietnamese Benzoin Tincture",
            "Skatole",
            "Methyl Pamplemousse",
            "Maple Lactone",
        ],
        {},
    )
    assert inferred == {
        "Turkish Storax Tincture": pytest.approx(0.2),
        "Vietnamese Benzoin Tincture": pytest.approx(0.4),
        "Methyl Pamplemousse": pytest.approx(0.1),
    }


def test_maple_lactone_is_removed_from_current_physical_inventory() -> None:
    # Characterize the immutable removal, not the later newly received stock.
    base = inventory.materialize_current_inventory(apply_user_overlay=False)
    materialized = inventory._apply_current_user_inventory_overlay(
        base, inventory.load_current_user_inventory_overlay(
            inventory.STOCK_FORMS_AND_TINCTURE_MODEL_USER_INVENTORY_OVERLAY_PATH,
        ),
    )
    assert not any(
        row.identity_name == "Maple Lactone" for row in materialized.stocks
    )
    requirement = next(
        row for row in materialized.requirements if row.source_row == 271
    )
    assert requirement.disposition == "GAP"
    assert "NO MAPLE LACTONE" in requirement.status

    registry = load_registry()
    material = registry.get("Maple Lactone")
    assert material is not None
    assert material.user_in_inventory is True  # October purchase is separate.


def test_unaffected_parallel_stocks_remain_available() -> None:
    pyrazine_neat = _stock("2-Acetyl Pyrazine", 1.0)
    evernyl_neat = _stock("Evernyl Crystals", 1.0)
    assert pyrazine_neat.execution_ready is True
    assert evernyl_neat.execution_ready is True


def test_current_successor_is_pinned_to_aimi_receipt_inventory_and_v17_predecessor() -> None:
    overlay_path = inventory.CURRENT_USER_INVENTORY_OVERLAY_PATH
    overlay_normalized = overlay_path.read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(overlay_normalized).hexdigest() == (
        inventory.CURRENT_USER_INVENTORY_OVERLAY_SHA256
    )
    predecessor = inventory.R5_REMAINING_STOCK_FORMS_V3_USER_INVENTORY_OVERLAY_PATH
    predecessor_normalized = predecessor.read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(predecessor_normalized).hexdigest() == (
        inventory.R5_REMAINING_STOCK_FORMS_V3_USER_INVENTORY_OVERLAY_SHA256
    )
    receipt = (
        inventory.PROJECT_ROOT
        / "data/governance/"
        "inventory_user_confirmation_20260930_aimi_identity.json"
    )
    assert hashlib.sha256(receipt.read_bytes()).hexdigest() == (
        inventory.AIMI_IDENTITY_CONFIRMATION_SHA256
    )
    payload = json.loads(overlay_path.read_text(encoding="utf-8"))
    inventory_normalized = inventory.INVENTORY_PATH.read_bytes().replace(
        b"\r\n", b"\n"
    )
    assert payload["source"]["inventory_text_size_bytes"] == len(
        inventory_normalized
    )
    assert payload["source"]["inventory_text_sha256"] == hashlib.sha256(
        inventory_normalized
    ).hexdigest()

    loaded = inventory.load_current_user_inventory_overlay(
        inventory.AIMI_IDENTITY_USER_INVENTORY_OVERLAY_PATH,
    )
    assert loaded["schema_version"].endswith("_v18")
    assert len(loaded["delta_records"]) == 1
    assert loaded["superseded_record_ids"] == ["INV-USER-20260904-003"]


def test_stock_form_predecessor_remains_loadable_and_pinned() -> None:
    loaded = inventory.load_current_user_inventory_overlay(
        inventory.STOCK_FORMS_AND_TINCTURE_MODEL_USER_INVENTORY_OVERLAY_PATH
    )
    assert loaded["schema_version"].endswith("_v12")
    assert len(loaded["delta_records"]) == 16
    assert len(loaded["superseded_record_ids"]) == 10


def test_evernyl_predecessor_remains_loadable_and_pinned() -> None:
    loaded = inventory.load_current_user_inventory_overlay(
        inventory.EVERNYL_10WW_DPG_USER_INVENTORY_OVERLAY_PATH
    )
    assert loaded["schema_version"].endswith("_v13")
    assert len(loaded["delta_records"]) == 1
    assert loaded["superseded_record_ids"] == ["INV-USER-20260915-STOCK-004"]


def test_current_successor_rejects_record_mutation() -> None:
    payload = json.loads(
        inventory.AIMI_IDENTITY_USER_INVENTORY_OVERLAY_PATH.read_text(encoding="utf-8")
    )
    candidate = copy.deepcopy(payload)
    candidate["records"][0]["stock"]["carrier"] = "ethanol"

    with pytest.raises(inventory.InventoryAuthorityError, match="exact records drift"):
        inventory._load_20260930_aimi_identity_successor(
            candidate,
            require_live_inventory_binding=False,
        )


def test_current_inventory_counts_reflect_r5_stock_clarifications() -> None:
    base = inventory.materialize_current_inventory(apply_user_overlay=False)
    materialized = inventory._apply_current_user_inventory_overlay(
        base, inventory.load_current_user_inventory_overlay(inventory.AIMI_IDENTITY_USER_INVENTORY_OVERLAY_PATH),
    )
    assert len(materialized.stocks) == 244
    assert sum(row.execution_ready for row in materialized.stocks) == 183
    assert sum(not row.execution_ready for row in materialized.stocks) == 61
