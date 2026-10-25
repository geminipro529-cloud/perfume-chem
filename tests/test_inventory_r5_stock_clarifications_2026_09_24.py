import copy
import hashlib
import json

import pytest

from engine import inventory_parser as inventory


def _stocks(identity_name: str):
    return [
        stock
        for stock in inventory.materialize_current_inventory().stocks
        if stock.identity_name == identity_name
    ]


def test_v16_overlay_is_pinned_to_user_receipt_product_evidence_and_inventory():
    path = inventory.R5_STOCK_CLARIFICATIONS_V2_USER_INVENTORY_OVERLAY_PATH
    normalized = path.read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(normalized).hexdigest() == (
        inventory.R5_STOCK_CLARIFICATIONS_V2_USER_INVENTORY_OVERLAY_SHA256
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema_version"].endswith("_v16")

    confirmation = (
        inventory.PROJECT_ROOT
        / "data/governance/"
        "inventory_user_confirmation_20260924_r5_stock_clarifications_v2.json"
    )
    product_resolution = (
        inventory.PROJECT_ROOT
        / "data/governance/"
        "inventory_supplier_product_resolution_20260924_"
        "aroma_more_lavender_4042.json"
    )
    assert hashlib.sha256(confirmation.read_bytes()).hexdigest() == (
        inventory.R5_STOCK_CLARIFICATIONS_V2_CONFIRMATION_SHA256
    )
    assert hashlib.sha256(product_resolution.read_bytes()).hexdigest() == (
        inventory.AROMA_MORE_LAVENDER_4042_PRODUCT_RESOLUTION_SHA256
    )


def test_ambrox_crystals_are_separate_from_the_existing_solution():
    stocks = _stocks("Ambrox Super")
    # Crystals, the 25% solution, and Kenny's 10% bottle (21 Oct 2026, STK-146).
    assert len(stocks) == 3
    crystals = next(stock for stock in stocks if stock.physical_form == "crystals")
    solution = next(stock for stock in stocks if stock.dilution == 0.25)
    assert (
        crystals.dilution,
        crystals.fraction_basis,
        crystals.carrier,
        crystals.execution_ready,
    ) == (1.0, "neat", "", True)
    assert crystals.raw_name == "crystals / neat / as supplied"
    assert solution.stock_id == "inventory:user-20260902:9e69f9db20c45cfe37e6"
    assert solution.carrier == "dpg + ipm + ethanol"


def test_vetiveryl_is_neat_and_the_old_ten_percent_record_is_retired():
    # 2026-09-24 made Vetiveryl Acetate neat (R5-002) and retired the old 10% record.
    # 2026-10-25: Kenny is out of it ("i am out of vetiveryl acetate", overlay STK-169),
    # so both records are retired and no Vetiveryl Acetate stock remains.
    assert _stocks("Vetiveryl Acetate") == []
    payload = inventory.load_current_user_inventory_overlay()
    retired = {record["record_id"]: record for record in payload["retired_records"]}
    assert "INV-USER-20260907-002" in retired
    neat = retired["INV-USER-20260924-R5-002"]
    assert (neat["stock"]["fraction"], neat["stock"]["fraction_basis"], neat["stock"]["carrier"]) == (
        1.0,
        "neat",
        "",
    )


@pytest.mark.parametrize(
    ("identity_name", "source_row"),
    [
        ("Norlimbanol Dextro", 183),
        ("Hay Absolute", 127),
    ],
)
def test_dpg_clarifications_bind_mass_basis_but_preserve_lineage_hold(
    identity_name: str,
    source_row: int,
):
    stocks = _stocks(identity_name)
    assert len(stocks) == 1
    stock = stocks[0]
    assert stock.dilution == pytest.approx(0.1)
    assert stock.carrier == "dpg"
    assert stock.fraction_basis == "mass_fraction"
    assert stock.physical_form == "solution"
    assert stock.execution_ready is False
    assert stock.execution_hold_reason == (
        "PREPARATION_QUANTITIES_DATE_AND_LOTS_MISSING"
    )
    assert stock.source_rows == (source_row,)


def test_aroma_more_catalog_identity_is_materialized_from_direct_ownership_only():
    payload = json.loads(
        (
            inventory.PROJECT_ROOT
            / "data/governance/"
            "inventory_supplier_product_resolution_20260924_"
            "aroma_more_lavender_4042.json"
        ).read_text(encoding="utf-8")
    )
    assert payload["resolution_state"] == (
        "EXACT_CATALOG_PRODUCT_IDENTIFIED_PHYSICAL_STOCK_UNBOUND"
    )
    assert payload["product"]["supplier_reference"] == "Lav420811P"
    assert payload["authority_limits"]["physical_ownership_confirmed"] is False
    stocks = _stocks("Lavender 40/42, Aroma&More")
    assert len(stocks) == 1
    stock = stocks[0]
    assert (stock.dilution, stock.fraction_basis, stock.physical_form) == (
        1.0,
        "neat",
        "as_supplied",
    )
    # 2026-10-20: Kenny, "Make it pass the gate, it is another lavender type":
    # re-issued as STK-137 with the lot-receipt hold cleared (AGENTS.md Rule 6).
    assert stock.execution_ready is True
    assert stock.execution_hold_reason == ""
    assert stock.stock_id.startswith("inventory:user-20261014:")


def test_v16_loader_rejects_record_mutation():
    payload = json.loads(
        inventory.R5_STOCK_CLARIFICATIONS_V2_USER_INVENTORY_OVERLAY_PATH.read_text(
            encoding="utf-8"
        )
    )
    candidate = copy.deepcopy(payload)
    candidate["records"][0]["stock"]["physical_form"] = "powder"
    with pytest.raises(inventory.InventoryAuthorityError, match="exact records drift"):
        inventory._load_20260924_r5_stock_clarifications_v2_successor(
            candidate,
            require_live_inventory_binding=False,
        )


def test_v15_predecessor_remains_loadable_and_pinned():
    path = inventory.R5_STOCK_CLARIFICATIONS_USER_INVENTORY_OVERLAY_PATH
    normalized = path.read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(normalized).hexdigest() == (
        inventory.R5_STOCK_CLARIFICATIONS_USER_INVENTORY_OVERLAY_SHA256
    )
    predecessor = inventory.load_current_user_inventory_overlay(path)
    assert predecessor["schema_version"].endswith("_v15")
    assert len(predecessor["delta_records"]) == 4


def test_v14_predecessor_remains_loadable_and_pinned():
    path = inventory.METHYL_PAMPLEMOUSSE_10WW_ETHANOL_USER_INVENTORY_OVERLAY_PATH
    normalized = path.read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(normalized).hexdigest() == (
        inventory.METHYL_PAMPLEMOUSSE_10WW_ETHANOL_USER_INVENTORY_OVERLAY_SHA256
    )
    predecessor = inventory.load_current_user_inventory_overlay(path)
    assert predecessor["schema_version"].endswith("_v14")
    assert len(predecessor["delta_records"]) == 1
