"""PerfumersWorld documents attached to the Orris Liquid and Alpha Irone stocks (STK-120, STK-121).

Kenny, 20 Oct 2026 21:19 UTC ("Check new ingredients in code"): "open every document and then add
to inventory". The two records re-issue the 2026-09-05 Orris Liquid and 2026-08-28 Alpha Irone
records with the document data attached; the stocks themselves do not change.
"""

import pytest

import engine.inventory_parser as inventory


def _delta(name):
    payload = inventory.load_current_user_inventory_overlay()
    rows = [r for r in payload["delta_records"] if r["canonical_name"] == name]
    assert len(rows) == 1
    return rows[0]


@pytest.mark.parametrize(
    "name,record_id,old_id,sku,fraction",
    [
        ("Orris Liquid", "INV-USER-20261014-STK-120", "INV-USER-20260905-001", "8IQ24653", 0.09),
        ("Alpha Irone", "INV-USER-20261014-STK-121", "INV-USER-20260828-003", "8II00243", 0.10),
    ],
)
def test_reissue_carries_the_stock_over_and_attaches_the_documents(name, record_id, old_id, sku, fraction):
    record = _delta(name)
    assert record["record_id"] == record_id
    assert record["stock"]["fraction"] == pytest.approx(fraction)
    assert record["stock"]["fraction_basis"] == "mass_fraction"
    assert record["stock"]["carrier"] == "dep"
    assert old_id in record["stock"]["execution_basis"]
    assert record["supplier_product"]["sku"] == sku
    docs = record["supplier_documents"]
    assert docs["coa"]["irone_assay"] is None
    assert docs["coa"]["lot_field"] == "19102026"
    assert docs["ifra_51_certificate"]["category_4_max_pct_of_supplied_product"] == 25.0
    assert record["authority_limits"]["lot_tied_to_user_bottle"] is False
    assert record["authority_limits"]["irone_assay_asserted"] is False
    payload = inventory.load_current_user_inventory_overlay()
    assert old_id in {r["record_id"] for r in payload["retired_records"]}
    stocks = [s for s in inventory.materialize_current_inventory().stocks if s.name == name]
    assert len(stocks) == 1
    assert stocks[0].dilution == pytest.approx(fraction)
    assert stocks[0].carrier == "dep"


def test_orris_liquid_documents_record_the_contradiction_and_the_typo():
    docs = _delta("Orris Liquid")["supplier_documents"]
    assert docs["pw_email_19_oct_2026"]["cas"] == "8002-73-1"
    assert "typo" in docs["pw_email_19_oct_2026"]["website_80_85_pct_irone"]
    assert any("contradicts" in flag for flag in docs["flags"])


def test_alpha_irone_stocks_are_still_the_10pct_dep_and_the_25pct_ipm():
    rows = sorted(
        (s.dilution, s.carrier)
        for s in inventory.materialize_current_inventory().stocks
        if s.name.startswith("Alpha Irone")
    )
    assert rows == [(pytest.approx(0.10), "dep"), (pytest.approx(0.25), "ipm")]
