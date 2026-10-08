"""Oakmoss/treemoss must be declared as Evernia allergens in both allergen paths."""

from __future__ import annotations

from dataclasses import replace

import pytest

import engine.pipeline.gates as gates_module
from engine.ifra_safety import score_ifra_compliance
from engine.pipeline.formula_state import build_formula_state
from engine.pipeline.gates import ReleaseGateConfig


@pytest.mark.parametrize(
    ("material", "inci"),
    [
        ("Oakmoss Absolute", "Evernia Prunastri"),
        ("oakmoss absolute (10% in DPG)", "Evernia Prunastri"),
        ("Treemoss Absolute", "Evernia Furfuracea"),
    ],
)
def test_ifra_score_declares_moss_allergen(material, inci):
    report = score_ifra_compliance({material: 250.0}, {material: 0.10}, total_volume_ml=30.0)
    assert inci in report.allergen_declarations


def test_ifra_score_trace_moss_not_declared():
    report = score_ifra_compliance(
        {"Oakmoss Absolute": 0.001}, {"Oakmoss Absolute": 0.10}, total_volume_ml=30.0
    )
    assert "Evernia Prunastri" not in report.allergen_declarations


def _moss_gate(name: str):
    state = build_formula_state(
        {name: 100.0},
        {name: 1.0},
        stock_specs={
            name: {
                "fraction": 1.0,
                "fraction_basis": "mass_per_volume",
                "carrier": "",
                "declared": True,
            }
        },
        matrix_moles={"Ethanol": 0.43},
        matrix_mass_g=20.0,
        matrix_source="explicit",
    )
    row = state.materials[0]
    assert row.active_finished_product_ppm_w_w is not None
    state = replace(state, materials=(replace(row, oav=0.0, screening_oav=0.0),))
    return gates_module._gate_eu_allergen_declaration(
        state, ReleaseGateConfig(audit_enabled=False)
    )


@pytest.mark.parametrize(
    ("material", "inci"),
    [
        ("Oakmoss Absolute", "evernia prunastri"),
        ("Treemoss Absolute", "evernia furfuracea"),
    ],
)
def test_eu_allergen_gate_declares_moss(material, inci):
    result = _moss_gate(material)
    assert result.status == "WARN"
    assert [r["allergen"] for r in result.data["declaration_candidates"]] == [inci]
