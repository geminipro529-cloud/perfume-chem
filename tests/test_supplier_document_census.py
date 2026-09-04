from __future__ import annotations

from collections import Counter
from pathlib import Path

from engine.supplier_document_census import build_supplier_document_census


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_census_preserves_all_273_inventory_rows_and_fails_closed_on_matches() -> None:
    rows = build_supplier_document_census(
        inventory_path=PROJECT_ROOT / "inventory.txt",
        supplier_snapshot_path=(
            PROJECT_ROOT
            / "data"
            / "materials"
            / "_sources"
            / "perfumersworld_stock.parsed.json"
        ),
    )

    assert len(rows) == 273
    assert [row.inventory_ordinal for row in rows] == list(range(1, 274))
    assert all(row.inventory_source_line > 0 for row in rows)

    match_counts = Counter(row.perfumersworld_match_state for row in rows)
    assert match_counts == {
        "REGISTRY_SKU": 164,
        "EXACT_NAME_SKU": 6,
        "AMBIGUOUS_EXACT_NAME": 12,
        "NO_EXACT_PW_MATCH": 91,
    }

    castoreum = next(row for row in rows if row.canonical_name == "Castoreum Synthetic")
    assert castoreum.stock_fraction == 0.10
    assert castoreum.stock_fraction_basis == "unspecified"
    assert castoreum.stock_carrier == "dep"
    assert castoreum.quantitative_execution_ready is False
    assert castoreum.execution_hold_reason == "FRACTION_BASIS_UNSPECIFIED"
    assert castoreum.perfumersworld_match_state == "REGISTRY_SKU"
    assert castoreum.perfumersworld_sku == "6UP07515"
    assert castoreum.perfumersworld_product_url == (
        "https://www.perfumersworld.com/view.php?pro_id=6UP07515"
    )
    assert castoreum.perfumersworld_document_url == (
        "https://www.perfumersworld.com/document-list.php?ifra=defaultOpen&pro_id=6UP07515"
    )


def test_census_does_not_collapse_distinct_working_stock_rows() -> None:
    rows = build_supplier_document_census(
        inventory_path=PROJECT_ROOT / "inventory.txt",
        supplier_snapshot_path=(
            PROJECT_ROOT
            / "data"
            / "materials"
            / "_sources"
            / "perfumersworld_stock.parsed.json"
        ),
    )

    geosmin = [row for row in rows if row.canonical_name == "Geosmin"]
    assert len(geosmin) == 2
    assert [row.stock_fraction for row in geosmin] == [0.001, 0.01]
    assert {row.perfumersworld_sku for row in geosmin} == {"5YW13682"}

    ambiguous_osmanthus = [
        row
        for row in rows
        if row.canonical_name == "Osmanthus Absolute"
        and row.perfumersworld_match_state == "AMBIGUOUS_EXACT_NAME"
    ]
    assert len(ambiguous_osmanthus) == 2
    assert all(row.perfumersworld_sku == "" for row in ambiguous_osmanthus)
    assert all(len(row.perfumersworld_candidate_skus) > 1 for row in ambiguous_osmanthus)
