"""Kenny's stock changes of 27 Nov 2026 (overlay STK-040, STK-248, STK-249).

His words in the project chat, relayed to the Stock data thread (07:13:54 UTC): "I have ran out of
blackcurrant absolute but now have grapefruit FCF silicon and muscone in stock now. Grapefruit FCF
silician and hexysalicylate is waiting for shipping." His PerfumersWorld mails show the grapefruit
FCF and muscone came in order 261125-053816ecd; the order still on its way holds Blackcurrant
Absolute 10% and Hexyl Salicylate."""

from __future__ import annotations

from engine import inventory_parser as inventory
from engine.inventory_parser import parse_current_inventory
from engine.research.request_interpretation import _MATERIAL_ALIASES

QUOTE = (
    "I have ran out of blackcurrant absolute but now have grapefruit FCF silicon and muscone in stock now. "
    "Grapefruit FCF silician and hexysalicylate is waiting for shipping."
)


def _records() -> dict:
    overlay = inventory.load_current_user_inventory_overlay(require_live_inventory_binding=True)
    return {r["record_id"]: r for r in overlay["delta_records"]}


def _owned(name: str) -> list:
    return [s for s in parse_current_inventory(unique=False) if s.name == name and s.status == "owned"]


def test_blackcurrant_absolute_10pct_is_used_up_and_keeps_its_old_stock():
    record = _records()["INV-USER-20261014-STK-040"]
    assert record["state"] == "NOT_OWNED" and record["stock"] is None
    assert record["source_quote"] == QUOTE
    assert record["used_up_stock"]["fraction"] == 0.1 and record["used_up_stock"]["carrier"] == "dpg"
    assert record["supersedes_parent_stocks"] == [{"source_row": 49, "fraction": 0.1}]
    assert _owned("Blackcurrant Absolute 10%") == []
    assert _owned("Cassis Base 345B")


def test_new_grapefruit_fcf_bottle_replaces_the_v5_row():
    record = _records()["INV-USER-20261014-STK-248"]
    assert record["state"] == "OWNED"
    assert record["supplier_product"]["sku"] == "7CA24030"
    assert record["supersedes_parent_stocks"] == [{"source_row": 123, "fraction": 1.0}]
    (stock,) = _owned("Grapefruit FCF Oil Sicilian")
    assert stock.stock_id.startswith("inventory:user-20261014:")
    assert (stock.dilution, stock.carrier, stock.physical_form) == (1.0, "", "liquid")
    assert stock.execution_ready is True
    assert _MATERIAL_ALIASES["grapefruit"] == "Grapefruit FCF Oil Sicilian"


def test_muscone_is_owned_neat_liquid():
    record = _records()["INV-USER-20261014-STK-249"]
    assert record["supplier_product"]["sku"] == "4XU05022"
    (stock,) = _owned("Muscone")
    assert (stock.dilution, stock.carrier, stock.physical_form) == (1.0, "", "liquid")
    assert stock.execution_ready is True


def test_muscone_physics_and_ifra_row_are_loaded():
    import json
    from pathlib import Path

    from engine.pipeline import simulator

    (material,) = simulator.simulate_formula({"Muscone": 10.0}, {"Muscone": 1.0})[0].state.materials
    assert material.mw_g_mol == 238.41
    assert material.logp == 6.06
    assert material.odt_air_ppm == 0.00046
    assert material.vp_pure_pa is not None
    table = json.loads(
        (Path(__file__).resolve().parents[1] / "data/regulatory/ifra_cat4_51.json").read_text(encoding="utf-8")
    )
    row = table["materials"]["Muscone"]
    assert row["status"] == "no_standard" and row["cas"] == ["541-91-3", "10403-00-6"]


def test_aag_is_owned_only_as_10pct_in_dpg():
    # Kenny, 27 Nov 2026 10:19 UTC: "Also, only have AAG in 10% DPG".
    records = _records()
    assert records["INV-USER-20261014-STK-157"]["state"] == "NOT_OWNED"
    assert records["INV-USER-20261014-STK-157"]["used_up_stock"]["fraction"] == 1.0
    assert records["INV-USER-20261014-STK-084"]["supersedes_parent_stocks"] == [{"source_row": 7}]
    stocks = [
        s for s in parse_current_inventory(unique=False)
        if s.status == "owned" and "amyl glycolate" in (s.identity_name or s.name).casefold()
    ]
    assert [(s.dilution, s.carrier, s.fraction_basis) for s in stocks] == [(0.1, "dpg", "mass_fraction")]
