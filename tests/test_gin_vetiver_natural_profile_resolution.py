"""Exact gin-vetiver stock labels may use proxies, never implied lot assays."""

import pytest

from engine.ingredient_intelligence import get_profile
from engine.name_utils import normalize_name
from engine.odor_thresholds import lookup_odt_entry, lookup_odt_raw_name
from engine.pipeline.formula_state import build_formula_state
from engine.pipeline.gates import (
    ReleaseGateConfig,
    _gate_odt_completeness,
    _gate_odt_sanity,
    _gate_vp_cross_source,
)
from engine.pipeline.natural_absolute_decomposition import get_composite_metadata
from engine.pipeline.preflight import _state_sanity_check


def test_coriander_seed_eo_label_resolves_to_generic_seed_oil_physics_profile():
    """Catch the formula label bypassing the existing generic seed-oil proxy."""
    assert normalize_name("Coriander Seed EO") == "coriander essential oil"

    odt = lookup_odt_entry("Coriander Seed EO")
    assert lookup_odt_raw_name("Coriander Seed EO") == "coriander essential oil"
    assert odt is not None
    assert odt["odt_air"] == pytest.approx(1.5)
    assert odt["odt_eth"] == pytest.approx(0.5)

    profile = get_profile("Coriander Seed EO")
    assert profile is not None
    assert profile.name == "Coriander Essential Oil"
    assert profile.vp == pytest.approx(15.0)
    assert profile.odt == pytest.approx(1.5)
    assert profile.odt_ppm == pytest.approx(0.5)
    assert profile.material_kind == "NATURAL_MIXTURE"
    assert profile.evidence["vp"]["status"] != "MEASURED_SUPPLIER_LOT"


@pytest.mark.parametrize(
    "stock_label,profile_key,coverage",
    [
        ("Coriander Seed EO", "coriander essential oil", 0.7975),
        ("Grapefruit FCF oil Sicilian", "citrus paradisi expressed oil iso 3053 midpoint profile", 0.9816),
    ],
)
def test_exact_stock_labels_resolve_as_partial_non_batch_proxies(
    stock_label, profile_key, coverage
):
    metadata = get_composite_metadata(stock_label)
    assert metadata is not None
    assert metadata.profile_key == profile_key
    assert metadata.resolution == "literature_proxy"
    assert metadata.composition_authority == "LITERATURE_PARTIAL_PROXY"
    assert metadata.batch_specific is False
    assert metadata.characterized_fraction == pytest.approx(coverage)
    assert metadata.unresolved_fraction == pytest.approx(1.0 - coverage)
    assert metadata.unresolved_odor_contribution == "UNKNOWN_NOT_ZERO"


@pytest.mark.parametrize(
    "stock_label,raw_ul",
    [("Coriander Seed EO", 70.0), ("Grapefruit FCF oil Sicilian", 550.0)],
)
def test_formula_state_retains_stock_label_and_uses_constituent_headspace(stock_label, raw_ul):
    state = build_formula_state({stock_label: raw_ul, "Hedione": 1250.0}, batch_volume_ml=30.0)
    material = next(row for row in state.materials if row.name == stock_label)
    assert material.raw_ul == raw_ul
    assert material.active_ul == raw_ul
    assert material.sources["oav_model"] == "modeled:natural_constituent_composite"
    assert material.oav is not None and material.oav > 0.0
    assert material.vapor_ppm > 0.0
    assert material.natural_composite_metadata["resolution"] == "literature_proxy"
    assert material.natural_composite_metadata["batch_specific"] is False
    assert state.headspace_basis == "MODELED_ACTIVE_CONCENTRATE_SCREEN"


def test_grapefruit_composite_odt_and_vp_authority_do_not_require_bulk_proxies():
    state = build_formula_state(
        {"Grapefruit FCF Oil Sicilian": 300.0, "Hedione": 310.0},
        batch_volume_ml=30.1,
    )
    grapefruit = next(row for row in state.materials if "Grapefruit" in row.name)
    assert grapefruit.odt_air_ppm is None
    assert grapefruit.vp_pure_pa is None
    assert grapefruit.has_constituent_resolved_oav is True
    assert grapefruit.has_odt_authority is True
    assert grapefruit.has_vp_authority is True

    sanity = _state_sanity_check(state)
    assert sanity.status != "FAIL"
    assert sanity.data["natural_composite_odt_authority"] == [
        "Grapefruit FCF Oil Sicilian"
    ]

    config = ReleaseGateConfig()
    odt_sanity = _gate_odt_sanity(state, config)
    assert odt_sanity.status == "PASS"
    assert odt_sanity.data["natural_composite_exemptions"] == [
        "Grapefruit FCF Oil Sicilian"
    ]
    assert _gate_odt_completeness(state, config).status == "PASS"
    vp = _gate_vp_cross_source(state, config)
    assert vp.data["no_vp"] == []
    assert vp.data["natural_composite_exemptions"] == [
        "Grapefruit FCF Oil Sicilian"
    ]


@pytest.mark.parametrize(
    "different_material",
    ["Coriander Leaf EO", "Cilantro Leaf Oil", "Grapefruit Expressed Oil", "Grapefruit Oil"],
)
def test_proxy_lookup_does_not_swallow_other_parts_or_non_fcf_grapefruit(
    different_material,
):
    assert get_composite_metadata(different_material) is None
