from __future__ import annotations

import json

import pytest

from engine.pipeline.stock_authority_spine import V5_AUTHORITY_SHA256
from engine.pipeline.v5_snapshot_provider import (
    V5SnapshotProviderError,
    load_v5_snapshot_json,
    snapshot_from_mapping,
)


def _payload(**overrides):
    payload = {
        "schema": "v5-inventory-snapshot-input-v1",
        "authority_filename": "Kenny_Current_Perfumery_Inventory_Master_Aug2026_v5.xlsx",
        "authority_sha256": V5_AUTHORITY_SHA256,
        "authority_sheet": "Ingredient Master",
        "records": [
            {
                "material": "Hedione",
                "stock_description": "neat / as supplied",
                "active_fraction": 1.0,
                "fraction_basis": "neat",
                "carrier": "",
                "inventory_owned": True,
                "product_basis": False,
                "source_row": 12,
            }
        ],
    }
    payload.update(overrides)
    return payload


def test_valid_exact_v5_packet_builds_snapshot():
    snapshot = snapshot_from_mapping(_payload())
    assert snapshot.authority_sha256 == V5_AUTHORITY_SHA256
    assert snapshot.resolve("Hedione").inventory_owned is True


def test_wrong_workbook_hash_hard_fails():
    with pytest.raises(V5SnapshotProviderError):
        snapshot_from_mapping(_payload(authority_sha256="0" * 64))


def test_wrong_workbook_filename_hard_fails():
    with pytest.raises(V5SnapshotProviderError):
        snapshot_from_mapping(_payload(authority_filename="inventory.txt"))


def test_duplicate_canonical_material_hard_fails():
    row = dict(_payload()["records"][0])
    duplicate = dict(row)
    duplicate["material"] = "hedione"
    with pytest.raises(V5SnapshotProviderError):
        snapshot_from_mapping(_payload(records=[row, duplicate]))


def test_missing_active_fraction_is_preserved_unknown_not_neat():
    row = dict(_payload()["records"][0])
    row["material"] = "Unknown Stock"
    row["active_fraction"] = None
    row["fraction_basis"] = "unspecified"
    snapshot = snapshot_from_mapping(_payload(records=[row]))
    record = snapshot.resolve("Unknown Stock")
    assert record.active_fraction is None
    assert record.fraction_basis == "unspecified"


def test_inventory_owned_must_be_explicit_boolean():
    row = dict(_payload()["records"][0])
    row["inventory_owned"] = "HOLD"
    with pytest.raises(V5SnapshotProviderError):
        snapshot_from_mapping(_payload(records=[row]))


def test_product_basis_never_requires_active_fraction():
    row = dict(_payload()["records"][0])
    row.update(
        material="Orris Liquid",
        stock_description="PerfumersWorld Orris Liquid as supplied",
        active_fraction=None,
        fraction_basis="product_basis",
        product_basis=True,
    )
    snapshot = snapshot_from_mapping(_payload(records=[row]))
    record = snapshot.resolve("Orris Liquid")
    assert record.product_basis is True
    assert record.active_fraction is None


def test_exact_stock_ref_is_rejected_from_inventory_packet():
    row = dict(_payload()["records"][0])
    row["exact_stock_ref"] = "stock:hedione:001"
    with pytest.raises(V5SnapshotProviderError):
        snapshot_from_mapping(_payload(records=[row]))


def test_unknown_top_level_fields_are_rejected():
    with pytest.raises(V5SnapshotProviderError):
        snapshot_from_mapping(_payload(beauty_score=99))


def test_json_loader_uses_same_validation(tmp_path):
    path = tmp_path / "v5-snapshot.json"
    path.write_text(json.dumps(_payload()), encoding="utf-8")
    snapshot = load_v5_snapshot_json(path)
    assert snapshot.resolve("Hedione") is not None


def test_json_loader_rejects_invalid_json(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{broken", encoding="utf-8")
    with pytest.raises(V5SnapshotProviderError):
        load_v5_snapshot_json(path)
