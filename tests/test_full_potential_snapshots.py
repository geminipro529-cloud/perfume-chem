"""Checkpoint 11 source adapters for all three immutable comparators."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from engine.research.snapshots import (
    DEFAULT_PARALLEL_A_FORMULA,
    DEFAULT_R5_MANIFEST,
    DEFAULT_R6_MANIFEST,
    SnapshotSourceError,
    load_parallel_a_design_snapshot,
    load_r5_design_snapshot,
    load_r6_design_snapshot,
)


def _rows_by_source(load) -> dict[int, object]:
    return {row.source_row: row for row in load.snapshot.components}


def test_r5_loads_as_design_snapshot_without_merging_mass_and_volume() -> None:
    loaded = load_r5_design_snapshot()
    assert loaded.snapshot.design_only is True
    assert len(loaded.snapshot.components) == 63
    assert loaded.liquid_total_ul_decimal == "5600"
    assert loaded.solid_total_mg_decimal == "300"
    assert loaded.snapshot.parent_formula_sha256 is None
    assert "PARENT_BYTES_NOT_AVAILABLE" in loaded.reason_codes
    crystal = loaded.snapshot.components[-1]
    assert crystal.source_material_label == "Ambrox Super"
    assert crystal.amount_decimal == "300"
    assert crystal.amount_unit == "mg"
    assert crystal.operation == "MASS_ADD"
    assert all(row.stock_id is None for row in loaded.snapshot.components)


def test_r6_reconstructs_exactly_one_row_delta_through_same_snapshot_model() -> None:
    r5 = load_r5_design_snapshot()
    r6 = load_r6_design_snapshot()
    assert type(r5.snapshot) is type(r6.snapshot)
    assert r6.snapshot.parent_formula_sha256 == r5.snapshot.sha256
    assert len(r6.snapshot.components) == 63
    assert r6.liquid_total_ul_decimal == "5600"
    assert r6.solid_total_mg_decimal == "300"
    r5_rows = _rows_by_source(r5)
    r6_rows = _rows_by_source(r6)
    changed = [key for key in r5_rows if r5_rows[key] != r6_rows[key]]
    assert changed == [47]
    assert r5_rows[47].source_material_label == "Methyl Ionone Gamma Coeur"
    assert r6_rows[47].source_material_label == "Givaudan AIMI"
    assert r6_rows[47].amount_decimal == "50"
    assert r6_rows[69].amount_unit == "mg"


def test_parallel_a_loads_same_contract_with_separate_crystal_mass() -> None:
    loaded = load_parallel_a_design_snapshot()
    assert loaded.snapshot.design_only is True
    assert loaded.snapshot.formula_id == "LAP-PARALLEL-A-20260927"
    assert len(loaded.snapshot.components) == 24
    assert loaded.liquid_total_ul_decimal == "5600"
    assert loaded.solid_total_mg_decimal == "300"
    assert sum(
        Decimal(row.amount_decimal)
        for row in loaded.snapshot.components
        if row.amount_unit == "uL"
    ) == Decimal("5600")
    crystal = loaded.snapshot.components[-1]
    assert crystal.source_material_label == "Ambrox Super Crystals"
    assert crystal.amount_unit == "mg"
    assert crystal.amount_decimal == "300"
    assert crystal.operation == "MASS_ADD"


def test_all_comparators_use_unbound_design_rows_not_inventory_assertions() -> None:
    loads = (
        load_r5_design_snapshot(),
        load_r6_design_snapshot(),
        load_parallel_a_design_snapshot(),
    )
    for loaded in loads:
        assert loaded.validation_state == "WITHHOLD_UNKNOWN"
        assert all(row.stock_id is None for row in loaded.snapshot.components)
        assert all(row.source_material_label for row in loaded.snapshot.components)
        assert all(row.required_stock_description for row in loaded.snapshot.components)


@pytest.mark.parametrize(
    ("source", "loader"),
    [
        (DEFAULT_R5_MANIFEST, load_r5_design_snapshot),
        (DEFAULT_R6_MANIFEST, load_r6_design_snapshot),
    ],
)
def test_manifest_source_drift_fails_closed(tmp_path: Path, source: Path, loader) -> None:
    changed = json.loads(source.read_text(encoding="utf-8"))
    if source == DEFAULT_R5_MANIFEST:
        changed["rows"][0]["dose"] += 1
        changed_path = tmp_path / "r5.json"
        changed_path.write_text(json.dumps(changed), encoding="utf-8")
        with pytest.raises(SnapshotSourceError, match="row hash mismatch"):
            loader(changed_path)
    else:
        changed["row_replacement"]["successor_row"]["dose"] = 51
        changed_path = tmp_path / "r6.json"
        changed_path.write_text(json.dumps(changed), encoding="utf-8")
        with pytest.raises(SnapshotSourceError, match="row hash mismatch"):
            loader(changed_path)


def test_parallel_markdown_total_drift_fails_closed(tmp_path: Path) -> None:
    changed = DEFAULT_PARALLEL_A_FORMULA.read_text(encoding="utf-8").replace(
        "Liquid stock-charge target: 5600 uL",
        "Liquid stock-charge target: 5601 uL",
        1,
    )
    path = tmp_path / "parallel.md"
    path.write_text(changed, encoding="utf-8")
    with pytest.raises(SnapshotSourceError, match="liquid total"):
        load_parallel_a_design_snapshot(path)
