"""Exact current-stock resolution for the owned PerfumersWorld AIMI bottle."""

from __future__ import annotations

import copy
import hashlib
import json

import pytest

import engine.inventory_parser as inventory
from engine.data_spine.loader import load_registry
from engine.formulation_intelligence.material_capability_index import (
    build_material_capability_index,
)
from engine.material_identity import resolve_material_identity
from engine.name_utils import normalize_name
from engine.personal_inventory import materialize_personal_inventory
from engine.pipeline.preflight import resolve_inventory_stock_contract

ALIASES = (
    "AIMI",
    "Alpha Methyl Ionone",
    "Alpha-Isomethyl Ionone",
    "Alpha Isomethyl Ionone",
    "Alpha Isomethyl Ionone (Methyl Ionone Pure)",
    "Givaudan AIMI",
    "Methyl Ionone Pure",
    "PerfumersWorld Alpha Isomethyl Ionone",
)


def _stock_check(label: str):
    formula = {
        "ingredients_ul": {label: 10.0},
        "dilutions": {label: 1.0},
        "stock_specs": {
            label: {
                "fraction": 1.0,
                "fraction_basis": "neat",
                "carrier": "",
                "declared": True,
            }
        },
    }
    return resolve_inventory_stock_contract(formula)


def test_v18_overlay_remains_bound_to_its_historical_receipt() -> None:
    overlay_path = inventory.AIMI_IDENTITY_USER_INVENTORY_OVERLAY_PATH
    normalized_overlay = overlay_path.read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(normalized_overlay).hexdigest() == (
        inventory.AIMI_IDENTITY_USER_INVENTORY_OVERLAY_SHA256
    )

    payload = json.loads(overlay_path.read_text(encoding="utf-8"))
    assert payload["schema_version"].endswith("_v18")
    assert payload["predecessor"]["normalized_text_sha256"] == (
        inventory.R5_REMAINING_STOCK_FORMS_V3_USER_INVENTORY_OVERLAY_SHA256
    )
    assert payload["source"]["inventory_text_size_bytes"] == 28082
    assert payload["source"]["inventory_text_sha256"] == (
        "6b11f3aa198b9483f9f7f9567e362f987a8447b47915853ea22fada66ff3cbe3"
    )
    inventory.load_current_user_inventory_overlay(overlay_path)

    receipt_path = (
        inventory.PROJECT_ROOT
        / "data/governance/inventory_user_confirmation_20260930_aimi_identity.json"
    )
    assert hashlib.sha256(receipt_path.read_bytes()).hexdigest() == (
        inventory.AIMI_IDENTITY_CONFIRMATION_SHA256
    )


def test_current_inventory_has_one_owned_aimi_bottle_and_no_alias_duplicate() -> None:
    materialized = inventory.materialize_current_inventory()
    aimi = [
        stock
        for stock in materialized.stocks
        if stock.identity_name == "Alpha Isomethyl Ionone"
    ]
    assert len(aimi) == 1
    stock = aimi[0]
    assert stock.dilution == pytest.approx(1.0)
    assert stock.fraction_basis == "neat"
    assert stock.carrier == ""
    assert stock.physical_form == "as_supplied_oily_liquid"
    assert stock.execution_ready is True
    assert stock.authority == inventory.AIMI_IDENTITY_USER_INVENTORY_AUTHORITY
    assert stock.stock_id == "inventory:user-20260930:0f2e7662198d3a10bd1a"
    assert not any(
        candidate.identity_name in {"Givaudan AIMI", "Methyl Ionone Pure"}
        for candidate in materialized.stocks
    )
    assert not any(
        candidate.identity_name == "Methyl Ionone Gamma Coeur"
        for candidate in materialized.stocks
    )


@pytest.mark.parametrize("label", ALIASES)
def test_every_aimi_alias_resolves_to_the_same_owned_stock(label: str) -> None:
    check = _stock_check(label)
    assert check.status == "PASS"
    spec = check.data["resolved_stock_specs"][label]
    assert spec["stock_id"] == "inventory:user-20260930:0f2e7662198d3a10bd1a"
    assert spec["inventory_authority"] == (
        inventory.AIMI_IDENTITY_USER_INVENTORY_AUTHORITY
    )
    assert normalize_name(label) == "alpha-isomethyl ionone"
    identity = resolve_material_identity(label)
    assert identity is not None
    assert identity.label == "Alpha Isomethyl Ionone"


def test_data_spine_aliases_bind_to_one_perfumersworld_identity() -> None:
    registry = load_registry()
    for label in ALIASES:
        material = registry.get(label)
        assert material is not None
        assert material.canonical_name == "Alpha Isomethyl Ionone"
        assert material.cas == "127-51-5"
        assert material.supplier.perfumersworld_sku == "3IW00300"
    assert registry.get("Methyl Ionone Gamma Coeur") is None


def test_inventory_ui_and_formula_studio_receive_the_canonical_owned_stock() -> None:
    personal = materialize_personal_inventory()
    stocks = [
        stock
        for stock in personal.stocks
        if stock.identity_name == "Alpha Isomethyl Ionone"
    ]
    assert len(stocks) == 1
    assert stocks[0].stock_id == "inventory:user-20260930:0f2e7662198d3a10bd1a"
    assert stocks[0].execution_ready is True

    capabilities = build_material_capability_index()
    for label in ("AIMI", "Alpha Methyl Ionone", "Givaudan AIMI"):
        matches = capabilities.exact_matches(label)
        assert len(matches) == 1
        assert matches[0].identity_name == "Alpha Isomethyl Ionone"
        assert matches[0].design_ready is True
        assert matches[0].execution_ready is True


def test_gamma_coeur_remains_depleted_and_cannot_resolve_as_aimi() -> None:
    check = _stock_check("Methyl Ionone Gamma Coeur")
    assert check.status == "FAIL"
    assert check.data["issues"][0]["reason"] in {
        "inventory_gap",
        "inventory_stock_unavailable",
        "not_in_inventory",
    }
    assert normalize_name("Methyl Ionone Gamma Coeur") != normalize_name("AIMI")


def test_v17_history_retains_old_label_but_v18_supersedes_it() -> None:
    historical = inventory.load_current_user_inventory_overlay(
        inventory.R5_REMAINING_STOCK_FORMS_V3_USER_INVENTORY_OVERLAY_PATH
    )
    assert any(
        record["record_id"] == "INV-USER-20260904-003"
        and record["canonical_name"] == "Givaudan AIMI"
        for record in historical["records"]
    )
    current = inventory.load_current_user_inventory_overlay()
    assert not any(
        record["record_id"] == "INV-USER-20260904-003"
        for record in current["records"]
    )
    historical_v18 = inventory.load_current_user_inventory_overlay(
        inventory.AIMI_IDENTITY_USER_INVENTORY_OVERLAY_PATH
    )
    assert historical_v18["delta_records"][0]["canonical_name"] == (
        "Alpha Isomethyl Ionone"
    )


def test_v18_loader_rejects_identity_or_supplier_mutation() -> None:
    payload = json.loads(
        inventory.AIMI_IDENTITY_USER_INVENTORY_OVERLAY_PATH.read_text(encoding="utf-8")
    )
    candidate = copy.deepcopy(payload)
    candidate["records"][0]["supplier_product"]["sku"] = "unverified"
    with pytest.raises(inventory.InventoryAuthorityError, match="exact records drift"):
        inventory._load_20260930_aimi_identity_successor(
            candidate,
            require_live_inventory_binding=False,
        )
