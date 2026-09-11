"""Tests for the PerfumersWorld supplier merge (#1).

Ensures the PW intake (relative impact, odour life, CAS, SKU) is attached to
material records and preserved by the generator path.
"""
from __future__ import annotations

import json
from pathlib import Path

from engine.knowledge.pw_supplier import (
    PW_FIELD_NAMES,
    load_pw_supplier_fields,
    merge_pw_supplier_fields,
    pw_fields_for,
)

ROOT = Path(__file__).resolve().parents[1]
MP_PATH = ROOT / "data" / "knowledge_graph" / "material_properties.json"


def test_pw_table_loads():
    assert len(load_pw_supplier_fields()) > 100


def test_pw_fields_for_known_material():
    fields = pw_fields_for("Hedione")
    assert fields is not None
    assert fields["pw_relative_impact"] == 65.0
    assert fields["pw_odour_life_hrs"] == 160.0
    assert fields["pw_sku"]


def test_merge_attaches_fields_and_is_idempotent():
    entries = [{"name": "Hedione"}, {"name": "Iso E Super"}]
    stats = merge_pw_supplier_fields(entries)
    assert stats["matched"] == 2
    for entry in entries:
        assert set(entry) & set(PW_FIELD_NAMES)
        assert entry["pw_evidence_class"] == "SUPPLIER_TECHNICAL"


def test_material_properties_has_pw_coverage():
    data = json.loads(MP_PATH.read_text(encoding="utf-8"))
    impact = sum(1 for e in data if e.get("pw_relative_impact") is not None)
    life = sum(1 for e in data if e.get("pw_odour_life_hrs") is not None)
    assert impact >= 100
    assert life >= 100
