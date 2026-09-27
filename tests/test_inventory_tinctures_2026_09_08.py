"""The September 8 user amendments preserve history and unknown tincture bases."""

import copy
import hashlib

import pytest

import engine.inventory_parser as inventory


@pytest.mark.parametrize("name,fraction", [
    ("Turkish Storax Tincture", 0.20),
    ("Vietnamese Benzoin Tincture", 0.40),
    ("Kenyan Myrrh Ethanol Tincture", 0.20),
    ("Oman Frankincense Ethanol Tincture", 0.33),
])
def test_owned_tinctures_keep_nominal_model_and_unknown_final_strength(name, fraction):
    stocks = [s for s in inventory.materialize_current_inventory().stocks if s.name == name]
    assert len(stocks) == 1
    stock = stocks[0]
    assert stock.dilution == fraction
    assert stock.fraction_basis == "mass_fraction_starting_charge"
    assert stock.carrier == "ethanol"
    assert not stock.execution_ready
    assert stock.execution_hold_reason == "FINAL_DISSOLVED_FRACTION_UNMEASURED"
    assert stock.approximate is True
    assert stock.nominal_property_model_ready is True


def test_high_altitude_lavender_is_removed_without_removing_other_lavenders():
    current = inventory.materialize_current_inventory()
    assert not any("high altitude" in s.name.lower() for s in current.stocks)
    listed = inventory.parse_inventory(unique=False, include_unavailable=False)
    other_lavenders = [s for s in listed if "lavender" in s.name.lower()]
    assert other_lavenders and all("high altitude" not in s.name.lower() for s in other_lavenders)
    row = next(r for r in current.requirements if r.source_row == 156)
    assert row.disposition == "GAP"


def test_successor_preserves_all_unaffected_stocks_and_old_overlay_bytes():
    base = inventory.materialize_current_inventory(apply_user_overlay=False)
    old = inventory._apply_current_user_inventory_overlay(
        base, inventory.load_current_user_inventory_overlay(inventory.RECONCILED_USER_INVENTORY_OVERLAY_PATH)
    )
    current = inventory._apply_current_user_inventory_overlay(
        base, inventory.load_current_user_inventory_overlay(inventory.TINCTURES_USER_INVENTORY_OVERLAY_PATH)
    )
    expected = {s.stock_id: s for s in old.stocks if "high altitude" not in s.name.lower()}
    actual = {s.stock_id: s for s in current.stocks if s.stock_id in expected}
    assert actual == expected
    assert len(current.requirements) == len(old.requirements)
    raw = inventory.RECONCILED_USER_INVENTORY_OVERLAY_PATH.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == "4868678b5e742b309c929d4021530912630ef7ff172c6a7124a08baa07db7f77"


def test_latest_successor_rejects_live_text_drift(tmp_path, monkeypatch):
    changed = tmp_path / "inventory.txt"
    changed.write_text(inventory.INVENTORY_PATH.read_text(encoding="utf-8") + "\n# drift\n", encoding="utf-8")
    monkeypatch.setattr(inventory, "INVENTORY_PATH", changed)
    with pytest.raises(inventory.InventoryAuthorityError, match="bound to live inventory"):
        inventory.load_current_user_inventory_overlay()


def test_tincture_cannot_be_promoted_to_quantitative_readiness():
    payload = copy.deepcopy(inventory.load_current_user_inventory_overlay(
        inventory.TINCTURES_USER_INVENTORY_OVERLAY_PATH
    ))
    payload["records"] = copy.deepcopy(payload["delta_records"])
    payload["records"][0]["stock"]["execution_ready"] = True
    with pytest.raises(inventory.InventoryAuthorityError, match="tincture stock contract"):
        inventory._load_20260908_user_inventory_successor(payload)


@pytest.mark.parametrize("identity", ["Lemon FCF Oil Sicilian", "Cedarwood Virginia", "Jasmine Sambac Absolute"])
def test_current_owned_records_are_not_overruled_by_stale_notes(identity):
    names = {s.identity_name.casefold() for s in inventory.materialize_current_inventory().stocks}
    assert identity.casefold() in names
