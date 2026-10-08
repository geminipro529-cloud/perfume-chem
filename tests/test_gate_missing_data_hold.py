"""Missing-data paths of blocking gates return HOLD; real formula problems still FAIL."""

import engine.pipeline.gates as gates_module
from engine.pipeline.formula_state import build_formula_state
from engine.pipeline.gates import ReleaseGateConfig


def _stock(basis: str, fraction: float = 1.0) -> dict[str, object]:
    return {"fraction": fraction, "fraction_basis": basis, "carrier": "", "declared": True}


def _w_v_state(ingredients: dict[str, float]):
    return build_formula_state(
        ingredients,
        {name: 1.0 for name in ingredients},
        stock_specs={name: _stock("mass_per_volume") for name in ingredients},
    )


def _missing_mass_state():
    # D-Limonene is a w/w stock (no stock-solution density); Hedione's basis is
    # undeclared. Neither has an authoritative active mass.
    return build_formula_state(
        {"D-Limonene": 75.0, "Hedione": 25.0},
        {"D-Limonene": 0.25, "Hedione": 0.25},
        stock_specs={
            "D-Limonene": _stock("mass_fraction", 0.25),
            "Hedione": _stock("unspecified", 0.25),
        },
    )


EXPECTED_MISSING = [
    {"material": "D-Limonene", "reason": "unavailable:stock_solution_density_for_w_w"},
    {"material": "Hedione", "reason": "unavailable:stock_fraction_basis_unspecified"},
]


def test_phase_compatibility_holds_and_lists_missing_active_mass():
    result = gates_module._gate_phase_compatibility(_missing_mass_state())

    assert result.status == "HOLD"
    assert result.data["missing"] == EXPECTED_MISSING
    assert "D-Limonene (needs the density of its w/w stock solution)" in result.detail
    assert "Hedione (its dilution basis is not declared)" in result.detail


def test_phase_compatibility_still_fails_on_real_phase_out_risk():
    state = _w_v_state({"Vanillin": 30.0, "D-Limonene": 30.0, "Galaxolide": 30.0, "Hedione": 10.0})

    result = gates_module._gate_phase_compatibility(state)

    assert result.status == "FAIL"
    assert "phase-out risk" in result.detail


def test_chemistry_stability_holds_and_lists_missing_active_mass():
    result = gates_module._gate_chemistry_stability(
        _missing_mass_state(), ReleaseGateConfig(audit_enabled=False)
    )

    assert result.status == "HOLD"
    assert result.data["missing"] == EXPECTED_MISSING
    assert "D-Limonene (needs the density of its w/w stock solution)" in result.detail


def test_chemistry_stability_still_fails_on_schiff_base_risk():
    state = _w_v_state({"Aldehyde C10": 70.0, "Indole": 20.0, "Hedione": 10.0})

    result = gates_module._gate_chemistry_stability(state, ReleaseGateConfig(audit_enabled=False))

    assert result.status == "FAIL"
    assert "Schiff-base risk" in result.detail


def _basis_state(bases: dict[str, str]):
    return build_formula_state(
        {name: 100.0 for name in bases},
        {name: 0.1 for name in bases},
        stock_specs={name: _stock(basis, 0.1) for name, basis in bases.items()},
    )


def test_concentration_basis_holds_on_undeclared_basis_and_says_what_to_declare():
    result = gates_module._gate_concentration_basis(
        _basis_state({"Hedione": "unspecified"}), ReleaseGateConfig()
    )

    assert result.status == "HOLD"
    assert result.data["missing"] == [
        {"material": "Hedione", "reason": "unavailable:stock_fraction_basis_unspecified"}
    ]
    assert "declare 10% w/w or 10% v/v" in result.detail


def test_concentration_basis_fails_on_unsupported_basis_and_still_lists_undeclared_rows():
    result = gates_module._gate_concentration_basis(
        _basis_state({"Hedione": "unspecified", "Iso E Super": "banana"}), ReleaseGateConfig()
    )

    assert result.status == "FAIL"
    assert "banana" in result.detail
    assert "Hedione: concentration basis not declared; declare 10% w/w or 10% v/v" in result.detail
    assert result.data["missing"] == [
        {"material": "Hedione", "reason": "unavailable:stock_fraction_basis_unspecified"}
    ]
