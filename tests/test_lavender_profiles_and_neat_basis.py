"""Spike lavender, Lavender 40/42, neat-as-supplied basis and two ester/oxide spines."""

import pytest

from engine.inventory_parser import parse_stock_specification
from engine.pipeline.formula_state import build_formula_state
from engine.pipeline.natural_absolute_decomposition import (
    get_composite_metadata,
    get_constituents,
)
from engine.pipeline.preflight import _natural_composite_coverage_check

_SPIKE_KEY = "lavandula latifolia spanish type iso 4719 midpoint profile"


def test_spike_lavender_uses_iso_4719_midpoints_without_rescaling():
    constituents = get_constituents("Spike Lavender EO")
    assert constituents is not None
    assert {row[0]: row[1] for row in constituents} == pytest.approx(
        {
            "linalool": 0.420,
            "1,8-cineole": 0.275,
            "camphor": 0.120,
            "limonene": 0.0175,
            "alpha terpineol": 0.011,
            "linalyl acetate": 0.008,
        }
    )
    assert sum(row[1] for row in constituents) == pytest.approx(0.8515)

    metadata = get_composite_metadata("Spike Lavender EO")
    assert metadata.profile_key == _SPIKE_KEY
    assert metadata.resolution == "literature_proxy"
    assert metadata.characterized_fraction == pytest.approx(0.8515)
    assert metadata.unresolved_fraction == pytest.approx(0.1485)
    assert metadata.quantitative_evaluability == "PARTIAL_INPUT_COVERAGE"
    assert metadata.batch_specific is False
    assert metadata.sources and all(src.startswith("http") for src in metadata.sources)
    unresolved = {row["name"] for row in metadata.unresolved_constituents}
    assert "trans-alpha-bisabolene" in unresolved


def test_spike_lavender_is_modeled_but_still_warns_as_partial():
    state = build_formula_state({"Spike Lavender EO": 100.0, "Hedione": 900.0})
    spike = next(row for row in state.materials if row.name == "Spike Lavender EO")
    assert spike.oav is not None
    assert spike.sources["oav_model"] == "modeled:natural_constituent_composite"
    check = _natural_composite_coverage_check(state)
    assert check.status == "WARN"


@pytest.mark.parametrize("name", ["Lavender 40/42, Aroma&More", "Lavender 40/42"])
def test_lavender_40_42_is_a_named_proxy_of_the_lavender_profile(name):
    metadata = get_composite_metadata(name)
    assert metadata is not None
    assert metadata.resolution == "literature_proxy"
    assert metadata.profile_key == get_composite_metadata("Lavender EO").profile_key
    joined = " ".join(metadata.limitations)
    assert "40/42" in joined
    assert "lavandin" in joined.lower()


@pytest.mark.parametrize("name", ["Lavandin Grosso EO", "Lavandin EO"])
def test_lavandin_does_not_resolve_to_spike_or_lavender_profiles(name):
    metadata = get_composite_metadata(name)
    assert metadata is None or metadata.profile_key != _SPIKE_KEY


@pytest.mark.parametrize(
    "raw",
    [
        "neat / as supplied",
        "Neat/as supplied",
        "NEAT / undiluted supplied product",
        "neat (as supplied)",
        "pure, as supplied",
    ],
)
def test_neat_as_supplied_spellings_are_declared_neat(raw):
    spec = parse_stock_specification(raw)
    assert spec.declared is True
    assert spec.fraction == 1.0
    assert spec.fraction_basis == "neat"


@pytest.mark.parametrize(
    "raw",
    [
        "as supplied",
        "neat / as supplied; 10 mL",
        "neat-equivalent via prepared child route",
    ],
)
def test_neat_with_extra_text_stays_undeclared(raw):
    assert parse_stock_specification(raw).declared is False


@pytest.mark.parametrize(
    "name,mw,vp_25c_pa",
    [("Geranyl Acetate", 196.29, 6.17), ("Linalool Oxide", 170.25, 1.29)],
)
def test_registry_physics_for_geranyl_acetate_and_linalool_oxide(name, mw, vp_25c_pa):
    state = build_formula_state({name: 100.0, "Hedione": 900.0})
    row = next(row for row in state.materials if row.name == name)
    assert row.mw_g_mol == pytest.approx(mw)
    assert row.sources["mw"] == "registry:data_spine.mw"
    assert row.sources["vp"] == "registry:data_spine.vp_25c"
    assert row.vp_pure_pa / row.vp_temperature_factor == pytest.approx(vp_25c_pa, rel=1e-3)
    assert row.logp is not None
    # No verified air threshold was found, so OAV must stay unavailable.
    assert row.odt_air_ppm is None
    assert row.oav is None
