"""Owned stock labels reach data that already exists under another name.

Each link joins two labels for the same material (same CAS in the data spine,
or a word-order variant of one stock label). No numeric data is added.
"""

from __future__ import annotations

import pytest

from engine.material_resolver import resolve_material
from engine.odor_thresholds import lookup_odt_entry, lookup_odt_raw_name
from engine.pipeline.formula_state import build_formula_state


@pytest.mark.parametrize(
    ("stock_label", "odt_key"),
    [
        ("Aldehyde C-18", "gamma nonalactone"),
        ("Aldehyde C-12 Lauric Dodecanal", "aldehyde c12 lauric"),
        ("Phenyl Acetaldehyde", "phenylacetaldehyde"),
    ],
)
def test_receipt_label_uses_same_molecule_threshold(stock_label, odt_key):
    assert lookup_odt_raw_name(stock_label) == odt_key
    entry = lookup_odt_entry(stock_label)
    assert entry is not None and entry["odt_air"] is not None
    assert entry["odt_air"] == lookup_odt_entry(odt_key)["odt_air"]

    material = build_formula_state({stock_label: 1.0}, {stock_label: 1.0}).materials[0]
    assert material.is_known
    assert material.oav is not None


@pytest.mark.parametrize(
    ("stock_label", "registry_name"),
    [
        ("Cedarwood Himalayan EO", "Himalayan Cedarwood EO"),
    ],
)
def test_word_order_label_resolves_to_existing_record(stock_label, registry_name):
    resolved = resolve_material(stock_label)
    assert resolved.is_known
    assert resolved.registry_name == registry_name
    assert resolved.canonical_name == resolve_material(registry_name).canonical_name
