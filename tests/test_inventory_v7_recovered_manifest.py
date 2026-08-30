from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = (
    PROJECT_ROOT
    / "data"
    / "governance"
    / "inventory_v7_recovered_manifest_20260830.json"
)


def test_recovered_v7_manifest_freezes_exclusive_working_stock_and_version_lineage() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    assert manifest["schema_version"] == "perfume_chem_inventory_v7_recovery_v1"
    assert manifest["disposition"] == "CURRENT_USER_AUTHORITY_SUCCESSOR"
    assert manifest["historical_formula_rebase_authorized"] is False

    stocks = {row["canonical_name"]: row for row in manifest["recovered_stocks"]}
    assert set(stocks) == {
        "Liffarome",
        "Cis-3-Hexenyl Salicylate",
        "Caryophyllene Acetate",
    }
    for name, fraction in {
        "Liffarome": 0.1,
        "Cis-3-Hexenyl Salicylate": 0.2,
        "Caryophyllene Acetate": 0.2,
    }.items():
        stock = stocks[name]
        assert "current_parent_stock" not in stock
        assert stock["current_working_stock"]["fraction"] == fraction
        assert stock["current_working_stock"]["fraction_basis"] == "mass_fraction"
        assert stock["current_working_stock"]["carrier"] is None
        assert stock["current_working_stock"]["only_current_concentration"] is True
        assert stock["current_working_stock"]["neat_stock_owned"] is False
        assert stock["current_working_stock"]["parallel_stock_authorized"] is False
        assert stock["current_working_stock"]["execution_ready"] is False
        assert (
            stock["current_working_stock"]["execution_hold_reason"]
            == "CARRIER_UNSPECIFIED"
        )

    assert manifest["version_lineage"]["v6_recipe_stocks_are_current_authority"] is False
    assert manifest["version_lineage"]["v7_original_workbook_bytes_available"] is False
    assert manifest["authority_limits"]["only_current_working_concentrations_confirmed"] is True
    assert manifest["authority_limits"]["parallel_current_stocks_authorized"] is False
    assert manifest["authority_limits"]["formulation_selection_ready"] is True
    assert manifest["authority_limits"]["quantitative_dosing_ready"] is False
    assert manifest["authority_limits"]["sensory_tested"] is False
    assert manifest["authority_limits"]["release_authorized"] is False
