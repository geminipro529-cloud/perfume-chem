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


def test_v17_overlay_is_pinned_to_current_receipt_and_inventory() -> None:
    path = inventory.CURRENT_USER_INVENTORY_OVERLAY_PATH
    normalized = path.read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(normalized).hexdigest() == (
        inventory.CURRENT_USER_INVENTORY_OVERLAY_SHA256
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    inventory_normalized = inventory.INVENTORY_PATH.read_bytes().replace(
        b"\r\n", b"\n"
    )
    assert payload["schema_version"].endswith("_v17")
    assert payload["source"]["inventory_text_size_bytes"] == len(
        inventory_normalized
    )
    assert payload["source"]["inventory_text_sha256"] == hashlib.sha256(
        inventory_normalized
    ).hexdigest()

    receipt = (
        inventory.PROJECT_ROOT
        / "data/governance/"
        "inventory_user_confirmation_20260924_r5_remaining_stock_forms_v3.json"
    )
    assert hashlib.sha256(receipt.read_bytes()).hexdigest() == (
        inventory.R5_REMAINING_STOCK_FORMS_V3_CONFIRMATION_SHA256
    )


@pytest.mark.parametrize(
    ("identity_name", "fraction", "carrier"),
    [
        ("Labdanum Resinoid", 0.1, "dpg"),
        ("Tonka Bean Absolute", 0.1, "dpg"),
        ("Olibanum Resinoid", 0.5, "dpg"),
        ("Opoponax Resinoid", 0.5, "dep"),
        ("Mimosa Absolute", 0.1, "dpg"),
    ],
)
def test_percentage_stocks_are_mass_fraction_without_false_lineage_readiness(
    identity_name: str,
    fraction: float,
    carrier: str,
) -> None:
    stocks = _stocks(identity_name)
    assert len(stocks) == 1
    stock = stocks[0]
    assert stock.dilution == pytest.approx(fraction)
    assert stock.fraction_basis == "mass_fraction"
    assert stock.carrier == carrier
    assert stock.execution_ready is False
    assert stock.execution_hold_reason == (
        "BOTTLE_LOT_AND_PREPARATION_RECEIPTS_MISSING"
    )


@pytest.mark.parametrize(
    "identity_name",
    [
        "Ethyl Linalool",
        "Geranyl Acetate",
        "Spike Lavender EO",
        "Linalool Oxide",
        "Hedione HC",
        "Cedrat FCF Sicilian",
    ],
)
def test_exact_neat_products_are_materialized_but_lineage_held(
    identity_name: str,
) -> None:
    stocks = _stocks(identity_name)
    assert len(stocks) == 1
    stock = stocks[0]
    assert stock.dilution == pytest.approx(1.0)
    assert stock.fraction_basis == "neat"
    assert stock.carrier == ""
    assert stock.execution_ready is False


def test_gamma_coeur_is_depleted_without_family_substitution() -> None:
    assert _stocks("Methyl Ionone Gamma Coeur") == []
    payload = inventory.load_current_user_inventory_overlay()
    record = next(
        record
        for record in payload["records"]
        if record["canonical_name"] == "Methyl Ionone Gamma Coeur"
    )
    assert record["state"] == "NOT_OWNED"
    assert record["stock"] is None
    assert all(
        stock.identity_name != "Givaudan AIMI"
        for stock in inventory.materialize_current_inventory().stocks
        if stock.identity_name == "Methyl Ionone Gamma Coeur"
    )


@pytest.mark.parametrize(
    ("identity_name", "stock_id"),
    [
        ("Heliotropal", "inventory:v5:593f575b080f30401f9b"),
        ("Black Pepper EO", "inventory:v5:4bb69da9b62fe8fbd8bb"),
        ("Nutmeg EO", "inventory:user-20260830:caa7c7f7418d43c86660"),
    ],
)
def test_neat_parent_does_not_create_required_r5_working_stock(
    identity_name: str,
    stock_id: str,
) -> None:
    stock = next(
        stock
        for stock in inventory.materialize_current_inventory().stocks
        if stock.stock_id == stock_id
    )
    assert stock.identity_name == identity_name
    assert stock.dilution == pytest.approx(1.0)
    assert stock.fraction_basis == "neat"


def test_v17_loader_rejects_record_mutation() -> None:
    payload = json.loads(
        inventory.CURRENT_USER_INVENTORY_OVERLAY_PATH.read_text(encoding="utf-8")
    )
    candidate = copy.deepcopy(payload)
    candidate["records"][0]["stock"]["fraction_basis"] = "volume_fraction"
    with pytest.raises(inventory.InventoryAuthorityError, match="exact records drift"):
        inventory._load_20260924_r5_remaining_stock_forms_v3_successor(
            candidate,
            require_live_inventory_binding=False,
        )


def test_v16_predecessor_remains_loadable_and_pinned() -> None:
    predecessor = inventory.load_current_user_inventory_overlay(
        inventory.R5_STOCK_CLARIFICATIONS_V2_USER_INVENTORY_OVERLAY_PATH
    )
    assert predecessor["schema_version"].endswith("_v16")
    assert len(predecessor["delta_records"]) == 3
