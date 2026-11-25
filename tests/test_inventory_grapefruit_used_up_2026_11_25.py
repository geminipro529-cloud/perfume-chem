"""Kenny ran out of his Grapefruit FCF oil Sicilian (25 Nov 2026, overlay STK-248).

His words, in another project thread relayed to the Stock data thread: "No, i run out of FCF free
and i am conidering alternative if any ill mell better and till pa  IFRA" (09:40:29 UTC). His only
grapefruit oil left is Pomelo EO, Synarome Pomelo Corsica rectified (Citrus paradisi)."""

from __future__ import annotations

from engine import inventory_parser as inventory
from engine.inventory_parser import parse_current_inventory
from engine.research.request_interpretation import _MATERIAL_ALIASES


def test_grapefruit_fcf_is_recorded_used_up_from_his_words():
    overlay = inventory.load_current_user_inventory_overlay(require_live_inventory_binding=True)
    (record,) = [r for r in overlay["delta_records"] if r["record_id"] == "INV-USER-20261014-STK-248"]
    assert record["canonical_name"] == "Grapefruit FCF Oil Sicilian"
    assert record["state"] == "NOT_OWNED" and record["stock"] is None
    assert record["source_quote"].startswith("No, i run out of FCF")
    assert record["supersedes_parent_stocks"] == [{"source_row": 123}]


def test_no_grapefruit_fcf_stock_is_owned_and_pomelo_still_is():
    stocks = parse_current_inventory(unique=False)
    owned = {s.name for s in stocks if s.status == "owned"}
    assert "Grapefruit FCF Oil Sicilian" not in owned
    assert "Pomelo EO" in owned


def test_a_grapefruit_brief_names_his_pomelo_oil():
    assert _MATERIAL_ALIASES["grapefruit"] == "Pomelo EO"
