"""Owned synthetic stock labels reach their sourced physics data.

Each case is an owned V5 stock label whose data existed under another name or
was missing a cited vapour pressure. The test checks the label, not the
record name, so a regression in name resolution shows up here.
"""

from __future__ import annotations

import pytest

from engine.material_resolver import resolve_material
from engine.pipeline.formula_state import build_formula_state


def _state(label: str):
    return build_formula_state({label: 1.0}, {label: 1.0}).materials[0]


@pytest.mark.parametrize("label", ["Styralyl Acetate", "Stralyl Acetate"])
def test_styralyl_acetate_labels_reach_one_record(label):
    resolved = resolve_material(label)
    assert resolved.registry_name == "Styralyl Acetate"
    record = resolved.registry_material
    assert record.cas == "93-92-5"
    assert record.vp_25c_pa == pytest.approx(7.0)
    assert record.odt_air_ppb == pytest.approx(40.0)
    assert record.supplier.perfumersworld_sku == "4GN00417"

    material = _state(label)
    assert material.odt_air_ppm == pytest.approx(0.04)
    assert material.vp_pure_pa is not None
    assert material.oav is not None


def test_aldehyde_c11_neat_label_is_undecylenic_aldehyde():
    # inventory.txt names Kenny's C11 stock "Aldehyde C11 undecylenic"
    # (10-undecenal), not undecanal (CAS 112-44-7).
    resolved = resolve_material("Aldehyde C11 neat")
    assert resolved.registry_name == "Aldehyde C11 Undecylenic"
    assert resolved.registry_material.cas == "112-45-8"

    material = _state("Aldehyde C11 neat")
    reference = _state("Aldehyde C11 Undecylenic")
    assert material.odt_air_ppm is not None
    assert material.odt_air_ppm == pytest.approx(reference.odt_air_ppm)
    assert material.vp_pure_pa == pytest.approx(reference.vp_pure_pa)
    assert material.oav is not None
