import pytest

from engine.material_resolver import resolve_material
from engine.pipeline.formula_state import build_formula_state


@pytest.mark.parametrize("label,identity,fraction", [
    ("Anisaldehyde 10%", "Anisaldehyde", 0.1),
    ("Ethyl Maltol 1%", "Ethyl Maltol", 0.01),
    ("Helional 10% v/v", "Helional", 0.1),
    ("Hexyl Acetate 1%", "Hexyl Acetate", 0.01),
])
def test_registered_stock_alias_reuses_identity_data_without_dose_authority(
    label, identity, fraction,
):
    stock = build_formula_state({label: 10.0}, {label: fraction}).materials[0]
    plain = build_formula_state({identity: 10.0}, {identity: fraction}).materials[0]
    assert resolve_material(label).registry_name == identity
    assert resolve_material(label).profile is not None
    assert stock.name == label
    assert stock.raw_ul == 10.0
    assert stock.dilution == fraction
    assert stock.odt_air_ppm == plain.odt_air_ppm
    assert stock.odt_air_ppm is not None
    assert stock.oav == pytest.approx(plain.oav)
    assert stock.authoritative_active_g is None
    assert stock.active_mass_authority.startswith("unavailable:")


def test_unregistered_stock_like_label_is_not_guessed():
    label = "Unregistered invented substance 10%"
    assert resolve_material(label).is_known is False
    stock = build_formula_state({label: 10.0}, {label: 0.1}).materials[0]
    assert stock.oav is None
    assert stock.authoritative_active_g is None


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
