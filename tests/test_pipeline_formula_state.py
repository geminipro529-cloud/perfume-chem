from dataclasses import replace

import pytest

import engine.pipeline.formula_state as formula_state_module
from engine.pipeline.formula_state import FormulaState, build_formula_state
from engine.pipeline.oav_authority import OAVAuthorityRequest, analyze_oav_authority


def test_formula_state_preserves_raw_and_active_dose():
    state = build_formula_state(
        {"Hedione": 100.0, "Geosmin": 10.0},
        {"Hedione": 1.0, "Geosmin": 0.01},
        batch_volume_ml=30.0,
    )

    hedione = next(m for m in state.materials if m.name == "Hedione")
    geosmin = next(m for m in state.materials if m.name == "Geosmin")

    assert state.total_raw_ul == 110.0
    assert round(state.total_active_ul, 3) == 100.1
    assert hedione.active_ul == 100.0
    assert geosmin.raw_ul == 10.0
    assert round(geosmin.active_ul, 3) == 0.1
    assert abs(sum(m.mole_fraction for m in state.materials) - 1.0) < 1e-9


def test_formula_state_computes_ppm_and_oav_when_data_exists():
    state = build_formula_state(
        {"Hedione": 1000.0, "Iso E Super": 1000.0},
        batch_volume_ml=30.0,
    )

    rows = {m.name: m for m in state.materials}
    assert rows["Hedione"].vapor_ppm >= 0
    assert rows["Hedione"].odt_air_ppm is not None
    assert rows["Hedione"].oav is not None
    assert rows["Iso E Super"].mw_g_mol is not None
    assert "vp" not in rows["Iso E Super"].missing_fields


def test_formula_state_adds_chemistry_metadata_and_hsp_fallback():
    state = build_formula_state(
        {
            "Hedione": 1000.0,
            "D-Limonene": 500.0,
            "Aldehyde C12 MNA": 50.0,
            "Indole": 10.0,
        },
        batch_volume_ml=30.0,
    )

    rows = {m.name: m for m in state.materials}
    assert rows["Hedione"].hsp is not None
    assert rows["Hedione"].hsp_source == "fallback:science_data.hsp"
    assert "ester" in rows["Hedione"].functional_groups
    assert "terpene" in rows["D-Limonene"].functional_groups
    assert "aldehyde" in rows["Aldehyde C12 MNA"].functional_groups
    assert "amine" in rows["Indole"].functional_groups


def test_formula_state_reuses_cached_result_for_identical_requests():
    build_formula_state.cache_clear()
    state_a = build_formula_state(
        {"Hedione": 1000.0, "Iso E Super": 1000.0},
        batch_volume_ml=30.0,
        temperature_K=305.0,
    )
    state_b = build_formula_state(
        {"Hedione": 1000.0, "Iso E Super": 1000.0},
        batch_volume_ml=30.0,
        temperature_K=305.0,
    )

    assert state_a is state_b


def test_headspace_basis_distinguishes_concentrate_from_finished_matrix():
    concentrate = build_formula_state({"Hedione": 1000.0})
    finished = build_formula_state(
        {"Hedione": 1000.0},
        matrix_moles={"Ethanol": 0.4},
        matrix_mass_g=18.4,
        matrix_source="explicit",
    )

    assert concentrate.headspace_basis == "MODELED_ACTIVE_CONCENTRATE_SCREEN"
    assert finished.headspace_basis == "MODELED_FINISHED_PRODUCT_EXPLICIT_MATRIX"
    assert finished.materials[0].mole_fraction < concentrate.materials[0].mole_fraction
    assert finished.materials[0].vapor_ppm < concentrate.materials[0].vapor_ppm


@pytest.mark.parametrize(
    ("matrix_moles", "matrix_mass_g"),
    [
        ({}, 0.0),
        ({"Ethanol": 0.4}, 0.0),
        ({}, 18.4),
    ],
)
def test_explicit_matrix_requires_positive_mass_and_component_moles(
    matrix_moles,
    matrix_mass_g,
):
    with pytest.raises(ValueError, match="explicit matrix authority requires"):
        build_formula_state(
            {"Hedione": 1000.0},
            matrix_moles=matrix_moles,
            matrix_mass_g=matrix_mass_g,
            matrix_source="explicit",
        )


@pytest.mark.parametrize(
    ("matrix_moles", "matrix_mass_g"),
    [
        ({"Ethanol": float("nan")}, 18.4),
        ({"Ethanol": float("inf")}, 18.4),
        ({"Ethanol": 0.4}, float("nan")),
        ({"Ethanol": 0.4}, float("inf")),
    ],
)
def test_matrix_inputs_reject_nonfinite_values(matrix_moles, matrix_mass_g):
    with pytest.raises(ValueError, match="finite"):
        build_formula_state(
            {"Hedione": 1000.0},
            matrix_moles=matrix_moles,
            matrix_mass_g=matrix_mass_g,
            matrix_source="explicit",
        )


def test_diluted_stock_with_partial_matrix_exposes_unresolved_carrier_scope():
    state = build_formula_state(
        {"Ambrettolide": 100.0},
        {"Ambrettolide": 0.1},
        matrix_moles={"Ethanol": 0.4},
        matrix_mass_g=18.4,
        matrix_source="incomplete_stock_carrier",
    )

    assert state.headspace_basis == "MODELED_FINISHED_PRODUCT_PARTIAL_MATRIX"
    assert state.stock_carrier_inclusion == "UNRESOLVED"


def test_w_w_stock_separates_screening_physics_from_input_complete_values():
    state = build_formula_state(
        {"Hedione": 100.0},
        {"Hedione": 0.25},
        stock_specs={
            "Hedione": {
                "fraction_basis": "mass_fraction",
                "carrier": "dpg",
                "declared": True,
            }
        },
    )
    row = state.materials[0]

    assert row.authoritative_active_g is None
    assert row.active_mass_authority == "unavailable:stock_solution_density_for_w_w"
    assert row.physics_status == "SCREENING_SENSITIVITY_ONLY"
    assert "ACTIVE_MASS_CHAIN_INCOMPLETE" in row.physics_blockers
    assert row.screening_vapor_ppm is not None and row.screening_vapor_ppm > 0.0
    assert row.screening_oav is not None and row.screening_oav > 0.0
    assert row.canonical_vapor_ppm is None
    assert row.canonical_oav is None
    assert row.formula_optimization_authority is False
    assert state.quantitative_authority["formula_optimization_authority"] is False
    assert state.quantitative_authority["sensory_endpoint_authority"] == {
        "character": False,
        "measured_intensity": False,
        "pleasantness": False,
        "liking": False,
    }
    assert state.quantitative_authority["measured_curve_input_authority"] is False
    assert (
        state.quantitative_authority["modeled_delivery_status"]
        == "MODELED_HEADSPACE_NOT_MEASURED_DELIVERY"
    )


def test_from_base_recomputes_odorant_volume_and_invalidates_dose_receipt():
    base = build_formula_state(
        {"Hedione": 100.0, "DPG": 50.0},
        stock_specs=_exact_test_stock_specs("Hedione", "DPG"),
    )
    bound = replace(
        base,
        dose_receipt_sha256="a" * 64,
        dose_receipt_status="BOUND",
    )

    changed = FormulaState.from_base(
        bound,
        new_raw_ul={"Hedione": 80.0, "DPG": 50.0},
    )

    assert changed.odorant_active_ul == 80.0
    assert changed.dose_receipt_sha256 == "a" * 64
    assert changed.dose_receipt_status == "INVALIDATED_BY_RECOMPUTE"

    unchanged = FormulaState.from_base(
        bound,
        new_raw_ul={"Hedione": 100.0, "DPG": 50.0},
    )
    assert unchanged.dose_receipt_status == "BOUND"


def _exact_test_stock_specs(*materials: str) -> dict[str, dict[str, object]]:
    return {
        material: {
            "fraction_basis": "mass_per_volume",
            "carrier": "",
            "declared": True,
        }
        for material in materials
    }


def test_missing_mw_invalidates_formula_wide_canonical_headspace(monkeypatch):
    original_resolve = formula_state_module.resolve_material

    def resolve_without_hedione_mw(name: str):
        identity = original_resolve(name)
        if name != "Hedione":
            return identity
        return replace(
            identity,
            profile=replace(identity.profile, mw=None),
            registry_material=replace(identity.registry_material, mw_g_mol=None),
        )

    monkeypatch.setattr(
        formula_state_module,
        "resolve_material",
        resolve_without_hedione_mw,
    )
    build_formula_state.cache_clear()
    try:
        state = build_formula_state(
            {"Hedione": 100.0, "Iso E Super": 100.0},
            stock_specs=_exact_test_stock_specs("Hedione", "Iso E Super"),
        )
        rows = {row.name: row for row in state.materials}

        assert rows["Hedione"].mw_g_mol is None
        assert rows["Hedione"].screening_vapor_ppm is not None
        assert rows["Hedione"].canonical_vapor_ppm is None
        # The missing MW corrupts the shared mole-fraction denominator, so a
        # complete neighbor cannot retain a precise-looking canonical result.
        assert rows["Iso E Super"].canonical_vapor_ppm is None
        assert all(
            "MOLECULAR_WEIGHT_CHAIN_INCOMPLETE" in row.physics_blockers
            for row in state.materials
        )
        assert state.canonical_total_vapor_ppm is None

        recomputed = FormulaState.from_base(
            state,
            new_raw_ul={"Hedione": 90.0, "Iso E Super": 110.0},
        )
        assert all(
            "MOLECULAR_WEIGHT_CHAIN_INCOMPLETE" in row.physics_blockers
            for row in recomputed.materials
        )
        assert recomputed.canonical_total_vapor_ppm is None
    finally:
        build_formula_state.cache_clear()


def test_missing_vp_is_unknown_not_zero_emission(monkeypatch):
    original_resolve = formula_state_module.resolve_material

    def resolve_without_hedione_vp(name: str):
        identity = original_resolve(name)
        if name != "Hedione":
            return identity
        return replace(
            identity,
            profile=replace(identity.profile, vp=None),
            registry_material=replace(
                identity.registry_material,
                vp_25c_pa=None,
                antoine=None,
                dhvap_kj_mol=None,
            ),
        )

    monkeypatch.setattr(
        formula_state_module,
        "resolve_material",
        resolve_without_hedione_vp,
    )
    build_formula_state.cache_clear()
    try:
        state = build_formula_state(
            {"Hedione": 100.0},
            stock_specs=_exact_test_stock_specs("Hedione"),
        )
        row = state.materials[0]
        serialized = row.as_dict()

        assert row.vp_pure_pa is None
        assert row.sources["vp"] == "missing"
        assert row.screening_partial_pressure_pa is None
        assert row.screening_vapor_ppm is None
        assert row.screening_oav is None
        assert row.canonical_partial_pressure_pa is None
        assert row.canonical_vapor_ppm is None
        assert row.canonical_oav is None
        assert row.physics_status == "WITHHELD"
        assert "VAPOR_PRESSURE_UNAVAILABLE" in row.physics_blockers
        assert serialized["vapor_ppm"] is None
        assert serialized["oav"] is None
        assert state.as_dict()["total_vapor_ppm"] is None

        authority = analyze_oav_authority(
            OAVAuthorityRequest(
                formula_name="Missing VP authority probe",
                ingredients_ul={"Hedione": 100.0},
                stock_specs=_exact_test_stock_specs("Hedione"),
            )
        )
        assert authority.material_rows[0].vapor_ppm is None
        assert authority.material_rows[0].oav is None
        assert all(
            window.total_vapor_ppm is None for window in authority.time_windows
        )

        recomputed = FormulaState.from_base(
            state,
            new_raw_ul={"Hedione": 80.0},
        )
        new_row = recomputed.materials[0]
        assert new_row.screening_vapor_ppm is None
        assert new_row.physics_status == "WITHHELD"
    finally:
        build_formula_state.cache_clear()
