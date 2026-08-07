"""Regression tests for optimizer use of the canonical FormulaState."""

from __future__ import annotations

import pytest

import engine.optimizer.scoring as scoring_module
import engine.pipeline.formula_state as formula_state_module
import engine.pipeline.natural_absolute_decomposition as natural_module
from engine.diffusion_model import (
    _DIFFUSION_INDEX,
    DIFFUSION_DATA,
    score_diffusion,
)
from engine.name_utils import normalize_name
from engine.optimizer.models import FormulaVector
from engine.optimizer.scoring import FormulaScorer
from engine.pipeline.formula_state import build_formula_state
from engine.pipeline.gates import (
    ReleaseGateConfig,
    _gate_data_coverage,
    _gate_material_coverage,
    _gate_vp_cross_source,
)
from engine.pipeline.natural_absolute_decomposition import (
    NaturalCompositeHeadspace,
    composite_headspace,
    composite_oav,
    composite_replacement_moles,
)
from engine.pipeline.release_scoring import _build_formula_vector
from engine.pipeline.simulator import simulate_formula
from engine.thermo.antoine import estimate_dhvap_from_vp_25c, vp_pa
from scripts.formula_simulator import simulate


def test_science_ingredients_apply_stock_dilution_exactly_once():
    fv = FormulaVector(
        ingredients={"Hedione": 50.0, "Ambrox Super": 50.0},
        dilutions={"Hedione": 0.10, "Ambrox Super": 1.0},
    )
    scorer = FormulaScorer(batch_volume_ml=10.0)

    raw_ul, dilutions = scorer._science_ingredients(fv)
    state = scorer._thermodynamic_state(fv)
    rows = {row.name: row for row in state.materials}

    assert raw_ul == {"Hedione": 5000.0, "Ambrox Super": 5000.0}
    assert dilutions == {"Hedione": 0.10}
    assert rows["Hedione"].active_ul == pytest.approx(500.0)
    assert rows["Ambrox Super"].active_ul == pytest.approx(5000.0)
    assert rows["Hedione"].active_ul / rows["Ambrox Super"].active_ul == pytest.approx(0.10)


def test_formula_state_gamma_changes_with_formula_composition():
    with_limonene = build_formula_state(
        {"Iso E Super": 5000.0, "D-Limonene": 5000.0},
        batch_volume_ml=10.0,
    )
    with_vanillin = build_formula_state(
        {"Iso E Super": 5000.0, "Vanillin": 5000.0},
        batch_volume_ml=10.0,
    )

    gamma_limonene = next(
        row.gamma for row in with_limonene.materials if row.name == "Iso E Super"
    )
    gamma_vanillin = next(
        row.gamma for row in with_vanillin.materials if row.name == "Iso E Super"
    )

    assert gamma_vanillin - gamma_limonene > 0.5


def test_diffusion_receives_the_identical_formula_state_gamma(monkeypatch):
    fv = FormulaVector(
        ingredients={"Iso E Super": 50.0, "Vanillin": 50.0},
    )
    scorer = FormulaScorer(batch_volume_ml=10.0)
    expected = {
        row.name: row.gamma for row in scorer._thermodynamic_state(fv).materials
    }
    captured: dict[str, dict[str, float]] = {}
    real_score_diffusion = score_diffusion

    def capture_diffusion(ingredients, dilutions=None, gamma_map=None):
        captured["gamma_map"] = dict(gamma_map or {})
        return real_score_diffusion(ingredients, dilutions, gamma_map)

    monkeypatch.setattr(scoring_module, "score_diffusion", capture_diffusion)
    scorer._run_enhancer_modules(fv)

    assert captured["gamma_map"] == pytest.approx(expected)


def test_diffusion_dynamic_gamma_replaces_reference_instead_of_compounding(monkeypatch):
    name = "Regression Gamma Reference"
    row = {
        "MW": 180.0,
        "VP_25": 1.0,
        "Kaw_eff": 0.01,
        "gamma_ref": 4.0,
    }
    monkeypatch.setitem(DIFFUSION_DATA, name, row)
    monkeypatch.setitem(_DIFFUSION_INDEX, normalize_name(name), row)

    baseline = score_diffusion({name: 100.0})
    same_gamma = score_diffusion({name: 100.0}, gamma_map={name: 4.0})
    ideal_gamma = score_diffusion({name: 100.0}, gamma_map={name: 1.0})

    assert same_gamma.projection_index == pytest.approx(baseline.projection_index)
    assert ideal_gamma.projection_index == pytest.approx(
        baseline.projection_index * 0.5
    )


def test_release_vector_preserves_raw_stock_percent_and_dilution():
    formula = {
        "ingredients_ul": {"Hedione": 500.0, "Ambrox Super": 500.0},
    }

    fv = _build_formula_vector(
        formula,
        {"Hedione": 0.10, "Ambrox Super": 1.0},
    )

    assert fv.ingredients == {"Hedione": 50.0, "Ambrox Super": 50.0}
    assert fv.dilutions == {"Hedione": 0.10, "Ambrox Super": 1.0}


def test_release_score_can_reuse_prebuilt_formula_state(monkeypatch):
    fv = FormulaVector(
        ingredients={"Iso E Super": 50.0, "Vanillin": 50.0},
    )
    state = build_formula_state(
        {"Iso E Super": 3000.0, "Vanillin": 3000.0},
        batch_volume_ml=30.0,
    )
    scorer = FormulaScorer(batch_volume_ml=10.0)

    def unexpected_rebuild(*args, **kwargs):
        raise AssertionError("canonical release state should be reused")

    monkeypatch.setattr(
        formula_state_module,
        "build_formula_state",
        unexpected_rebuild,
    )
    scores = scorer.score(fv, formula_state=state)

    assert scores["total"] >= 0.0
    assert scorer._thermodynamic_state(fv) is state
    assert scorer._science_ingredients(fv)[0] == {
        "Iso E Super": 3000.0,
        "Vanillin": 3000.0,
    }


def test_injected_formula_state_rejects_mismatched_raw_stock_contract():
    fv = FormulaVector(
        ingredients={"Iso E Super": 60.0, "Vanillin": 40.0},
    )
    mismatched_state = build_formula_state(
        {"Iso E Super": 3000.0, "Vanillin": 3000.0},
        batch_volume_ml=30.0,
    )

    with pytest.raises(ValueError, match="raw proportion"):
        FormulaScorer().score(fv, formula_state=mismatched_state)


def test_injected_formula_state_rejects_mismatched_dilution_contract():
    fv = FormulaVector(
        ingredients={"Hedione": 50.0, "Ambrox Super": 50.0},
        dilutions={"Hedione": 0.10, "Ambrox Super": 1.0},
    )
    mismatched_state = build_formula_state(
        {"Hedione": 500.0, "Ambrox Super": 500.0},
        {"Hedione": 1.0, "Ambrox Super": 1.0},
        batch_volume_ml=30.0,
    )

    with pytest.raises(ValueError, match="dilution"):
        FormulaScorer().score(fv, formula_state=mismatched_state)


def test_injected_formula_state_is_not_reused_after_vector_mutation():
    fv = FormulaVector(
        ingredients={"Iso E Super": 50.0, "Vanillin": 50.0},
    )
    state = build_formula_state(
        {"Iso E Super": 3000.0, "Vanillin": 3000.0},
        batch_volume_ml=30.0,
    )
    scorer = FormulaScorer(batch_volume_ml=10.0)
    scorer.score(fv, formula_state=state)

    fv.ingredients["Iso E Super"] = 75.0
    fv.ingredients["Vanillin"] = 25.0
    rebuilt = scorer._thermodynamic_state(fv)

    assert rebuilt is not state
    assert {row.name: row.raw_ul for row in rebuilt.materials} == pytest.approx(
        {"Iso E Super": 7500.0, "Vanillin": 2500.0}
    )


def test_formula_simulator_preserves_raw_stock_and_reuses_oav_state(monkeypatch):
    captured: dict[str, object] = {}

    def capture_score(self, fv, *, formula_state=None):
        captured["fv"] = fv
        captured["state"] = formula_state
        return {"total": 42.0}

    monkeypatch.setattr(FormulaScorer, "score", capture_score)

    result = simulate(
        {
            "name": "Thermodynamic Simulator Regression",
            "ingredients_ul": {"Hedione": 500.0, "Ambrox Super": 500.0},
            "dilutions": {"Hedione": 0.10, "Ambrox Super": 1.0},
        }
    )

    fv = captured["fv"]
    state = captured["state"]
    assert isinstance(fv, FormulaVector)
    assert fv.ingredients == {"Hedione": 50.0, "Ambrox Super": 50.0}
    assert fv.dilutions == {"Hedione": 0.10, "Ambrox Super": 1.0}
    assert state is not None
    assert {row.name: row.active_ul for row in state.materials} == pytest.approx(
        {"Hedione": 50.0, "Ambrox Super": 500.0}
    )
    assert result["scores"]["total"] == 42.0


def test_composite_oav_does_not_apply_qualitative_character_bonus(monkeypatch):
    material = "Synthetic Character Bonus Regression"
    monkeypatch.setitem(
        natural_module._ABSOLUTE_CONSTITUENTS,
        material.casefold(),
        [("marker", 1.0, 100.0, 1.0, 1000.0, 1.0)],
    )

    def unexpected_bonus(*_args):
        raise AssertionError("qualitative character bonus must not enter OAV")

    monkeypatch.setattr(natural_module, "_character_bonus", unexpected_bonus)
    actual = composite_oav(
        material,
        active_g=1.0,
        total_moles_in_formula=1.0,
        temperature_K=298.15,
    )
    expected_vapor_ppm = 1e6 * (0.01 * 1.0) / 101_325.0

    assert actual == pytest.approx(expected_vapor_ppm / 1.0)


def test_composite_oav_replaces_characterized_parent_moles(monkeypatch):
    material = "Synthetic Mole Replacement Regression"
    monkeypatch.setitem(
        natural_module._ABSOLUTE_CONSTITUENTS,
        material.casefold(),
        [("marker", 0.5, 100.0, 1.0, 1000.0, 1.0)],
    )
    parent_moles = 1.0 / 200.0
    formula_moles = 0.1 + parent_moles
    resolved_constituent_moles = 0.5 / 100.0
    residual_parent_moles = 0.5 / 100.0
    effective_total_moles = (
        formula_moles
        - parent_moles
        + residual_parent_moles
        + resolved_constituent_moles
    )

    actual = composite_oav(
        material,
        active_g=1.0,
        total_moles_in_formula=formula_moles,
        parent_moles=parent_moles,
        temperature_K=298.15,
    )
    expected_vapor_ppm = (
        1e6 * (resolved_constituent_moles / effective_total_moles) / 101_325.0
    )

    assert actual == pytest.approx(expected_vapor_ppm / 1.0)


def test_composite_headspace_reports_summed_vapor_and_pressure(monkeypatch):
    material = "Synthetic Composite Headspace Regression"
    monkeypatch.setitem(
        natural_module._ABSOLUTE_CONSTITUENTS,
        material.casefold(),
        [
            ("marker a", 0.5, 100.0, 1.0, 1000.0, 1.0),
            ("marker b", 0.5, 100.0, 2.0, 2000.0, 1.0),
        ],
    )

    result = composite_headspace(
        material,
        active_g=1.0,
        total_moles_in_formula=1.0,
        temperature_K=298.15,
    )

    assert result is not None
    assert result.constituent_count == 2
    assert result.partial_pressure_pa == pytest.approx(0.015)
    assert result.vapor_ppm == pytest.approx(1e6 * 0.015 / 101_325.0)
    assert result.oav == pytest.approx(
        (1e6 * 0.005 / 101_325.0) / 1.0
        + (1e6 * 0.010 / 101_325.0) / 2.0
    )


def test_natural_residual_moles_do_not_depend_on_arbitrary_parent_mw():
    low_parent = composite_replacement_moles(
        "Osmanthus Absolute",
        active_g=1.0,
        parent_moles=0.001,
    )
    high_parent = composite_replacement_moles(
        "Osmanthus Absolute",
        active_g=1.0,
        parent_moles=0.1,
    )

    assert low_parent is not None
    assert high_parent == pytest.approx(low_parent)


def test_composite_oav_temperature_corrects_constituent_vp(monkeypatch):
    material = "Synthetic Temperature Regression"
    monkeypatch.setitem(
        natural_module._ABSOLUTE_CONSTITUENTS,
        material.casefold(),
        [("marker", 1.0, 100.0, 1.0, 1000.0, 1.0)],
    )
    at_25c = composite_oav(
        material,
        active_g=1.0,
        total_moles_in_formula=1.0,
        temperature_K=298.15,
    )
    at_32c = composite_oav(
        material,
        active_g=1.0,
        total_moles_in_formula=1.0,
        temperature_K=305.15,
    )
    expected_ratio = vp_pa(
        305.15,
        vp_25c_pa=1.0,
        dhvap_kj_mol=estimate_dhvap_from_vp_25c(1.0),
    )

    assert at_25c is not None
    assert at_32c == pytest.approx(at_25c * expected_ratio)
    assert at_32c > at_25c


def test_formula_state_temperature_corrects_vp_with_material_specific_estimate():
    build_formula_state.cache_clear()
    at_25c = build_formula_state(
        {"D-Limonene": 50.0, "Vanillin": 50.0},
        temperature_K=298.15,
    )
    build_formula_state.cache_clear()
    at_32c = build_formula_state(
        {"D-Limonene": 50.0, "Vanillin": 50.0},
        temperature_K=305.15,
    )
    rows_25 = {row.name: row for row in at_25c.materials}
    rows_32 = {row.name: row for row in at_32c.materials}

    for name in rows_25:
        vp_25 = rows_25[name].vp_pure_pa
        assert vp_25 is not None
        expected = vp_pa(
            305.15,
            vp_25c_pa=vp_25,
            dhvap_kj_mol=estimate_dhvap_from_vp_25c(vp_25),
        )
        assert rows_32[name].vp_pure_pa == pytest.approx(expected)
        assert (
            rows_32[name].sources["vp_temperature"]
            == "heuristic:clausius_clapeyron_vp25_dhvap_correlation"
        )
        assert rows_32[name].sources["dhvap"].endswith(
            "doi:10.1021/es980812j"
        )

    limonene_factor = (
        rows_32["D-Limonene"].vp_pure_pa / rows_25["D-Limonene"].vp_pure_pa
    )
    vanillin_factor = (
        rows_32["Vanillin"].vp_pure_pa / rows_25["Vanillin"].vp_pure_pa
    )
    assert limonene_factor != pytest.approx(vanillin_factor)


def test_vp_gate_exposes_inferred_temperature_authority():
    build_formula_state.cache_clear()
    state = build_formula_state(
        {"D-Limonene": 50.0, "Vanillin": 50.0},
        temperature_K=305.15,
    )

    gate = _gate_vp_cross_source(
        state,
        ReleaseGateConfig(temperature_K=305.15, audit_enabled=False),
    )

    assert gate.status == "WARN"
    assert gate.data["inferred_dhvap_materials"] == [
        "D-Limonene",
        "Vanillin",
    ]
    assert gate.data["temperature_models"] == {
        "heuristic:clausius_clapeyron_vp25_dhvap_correlation": 2
    }


def test_formula_state_passes_parent_moles_and_temperature_to_composite(monkeypatch):
    captured: list[tuple[str, float, dict[str, float]]] = []

    def capture_composite(
        name,
        _active_g,
        total_moles,
        _gamma_estimate=0.6,
        **kwargs,
    ):
        captured.append((name, total_moles, dict(kwargs)))
        if name.casefold() != "osmanthus absolute":
            return None
        return NaturalCompositeHeadspace(
            oav=1.0,
            vapor_ppm=0.5,
            partial_pressure_pa=0.05,
            constituent_count=1,
            temperature_K=float(kwargs["temperature_K"]),
        )

    build_formula_state.cache_clear()
    monkeypatch.setattr(
        formula_state_module,
        "composite_headspace",
        capture_composite,
    )
    state = build_formula_state(
        {"Osmanthus Absolute": 101.234, "Iso E Super": 98.766},
        batch_volume_ml=30.0,
        temperature_K=310.15,
    )
    osmanthus = next(row for row in state.materials if row.name == "Osmanthus Absolute")
    osmanthus_total, osmanthus_kwargs = next(
        (total_moles, kwargs)
        for name, total_moles, kwargs in captured
        if name.casefold() == "osmanthus absolute"
    )
    parent_total = state.matrix_moles + sum(row.moles for row in state.materials)
    replacement = composite_replacement_moles(
        "Osmanthus Absolute",
        osmanthus.active_g,
        osmanthus.moles,
    )

    assert captured
    assert replacement is not None
    assert osmanthus_total == pytest.approx(
        parent_total - osmanthus.moles + replacement
    )
    assert osmanthus_kwargs["temperature_K"] == pytest.approx(310.15)


def test_temporal_formula_state_preserves_composite_temperature_contract(monkeypatch):
    build_formula_state.cache_clear()
    base = build_formula_state(
        {"Osmanthus Absolute": 103.21, "Iso E Super": 96.79},
        batch_volume_ml=30.0,
        temperature_K=307.15,
    )
    captured: list[tuple[str, float, dict[str, float]]] = []

    def capture_composite(
        name,
        _active_g,
        total_moles,
        _gamma_estimate=0.6,
        **kwargs,
    ):
        captured.append((name, total_moles, dict(kwargs)))
        if name.casefold() != "osmanthus absolute":
            return None
        return NaturalCompositeHeadspace(
            oav=1.0,
            vapor_ppm=0.5,
            partial_pressure_pa=0.05,
            constituent_count=1,
            temperature_K=float(kwargs["temperature_K"]),
        )

    monkeypatch.setattr(
        formula_state_module,
        "composite_headspace",
        capture_composite,
    )
    evolved = formula_state_module.FormulaState.from_base(
        base,
        new_raw_ul={"Osmanthus Absolute": 51.605, "Iso E Super": 48.395},
    )
    osmanthus = next(row for row in evolved.materials if row.name == "Osmanthus Absolute")
    osmanthus_total, osmanthus_kwargs = next(
        (total_moles, kwargs)
        for name, total_moles, kwargs in captured
        if name.casefold() == "osmanthus absolute"
    )
    parent_total = evolved.matrix_moles + sum(row.moles for row in evolved.materials)
    replacement = composite_replacement_moles(
        "Osmanthus Absolute",
        osmanthus.active_g,
        osmanthus.moles,
    )

    assert captured
    assert replacement is not None
    assert osmanthus_total == pytest.approx(
        parent_total - osmanthus.moles + replacement
    )
    assert osmanthus_kwargs["temperature_K"] == pytest.approx(307.15)


def test_multiple_naturals_share_one_decomposed_formula_mole_pool(monkeypatch):
    captured: list[tuple[str, float]] = []

    def capture_composite(
        name,
        _active_g,
        total_moles,
        _gamma_estimate=0.6,
        **_kwargs,
    ):
        captured.append((name, total_moles))
        if name.casefold() in {"osmanthus absolute", "olibanum resinoid"}:
            return NaturalCompositeHeadspace(
                oav=1.0,
                vapor_ppm=0.5,
                partial_pressure_pa=0.05,
                constituent_count=1,
                temperature_K=305.0,
            )
        return None

    build_formula_state.cache_clear()
    monkeypatch.setattr(
        formula_state_module,
        "composite_headspace",
        capture_composite,
    )
    state = build_formula_state(
        {
            "Osmanthus Absolute": 100.0,
            "Olibanum Resinoid": 100.0,
            "Iso E Super": 100.0,
        },
        temperature_K=305.0,
    )
    rows = {row.name: row for row in state.materials}
    expected_total = state.matrix_moles + sum(row.moles for row in state.materials)
    for name in ("Osmanthus Absolute", "Olibanum Resinoid"):
        row = rows[name]
        replacement = composite_replacement_moles(
            name,
            row.active_g,
            row.moles,
        )
        assert replacement is not None
        expected_total += replacement - row.moles

    natural_totals = {
        name.casefold(): total_moles
        for name, total_moles in captured
        if name.casefold() in {"osmanthus absolute", "olibanum resinoid"}
    }

    assert natural_totals == pytest.approx(
        {
            "osmanthus absolute": expected_total,
            "olibanum resinoid": expected_total,
        }
    )


def test_supported_natural_uses_constituent_headspace_and_is_known():
    build_formula_state.cache_clear()
    state = build_formula_state(
        {
            "Geranium EO (Pelargonium graveolens flower oil)": 100.0,
            "Hedione": 900.0,
        },
        temperature_K=305.0,
    )
    geranium = next(
        row
        for row in state.materials
        if row.name == "Geranium EO (Pelargonium graveolens flower oil)"
    )

    assert geranium.is_known is True
    assert geranium.sources["oav_model"] == "literature:natural_composite_gc_o"
    assert geranium.sources["vp"] == "literature:natural_composite_constituent_vp"
    assert geranium.vapor_ppm > 0
    assert geranium.partial_pressure_pa > 0
    assert geranium.oav is not None
    assert geranium.oav > 0
    assert _gate_material_coverage(state).status == "PASS"
    data_gate = _gate_data_coverage(state)
    assert data_gate.status == "PASS"
    assert data_gate.data["natural_composite_exemptions"] == {
        "Geranium EO (Pelargonium graveolens flower oil)": [
            "mw",
            "logp",
            "vp",
        ]
    }


def test_temporal_state_recomputes_gamma_and_matches_fresh_rebuild():
    build_formula_state.cache_clear()
    base = build_formula_state(
        {"D-Limonene": 900.0, "Vanillin": 100.0},
        temperature_K=305.0,
    )
    new_raw_ul = {"D-Limonene": 100.0, "Vanillin": 900.0}
    evolved = formula_state_module.FormulaState.from_base(
        base,
        new_raw_ul=new_raw_ul,
    )
    build_formula_state.cache_clear()
    rebuilt = build_formula_state(
        new_raw_ul,
        temperature_K=305.0,
    )

    base_rows = {row.name: row for row in base.materials}
    evolved_rows = {row.name: row for row in evolved.materials}
    rebuilt_rows = {row.name: row for row in rebuilt.materials}

    assert evolved_rows["D-Limonene"].gamma != pytest.approx(
        base_rows["D-Limonene"].gamma
    )
    for name in new_raw_ul:
        assert evolved_rows[name].gamma == pytest.approx(rebuilt_rows[name].gamma)
        assert evolved_rows[name].vapor_ppm == pytest.approx(
            rebuilt_rows[name].vapor_ppm
        )
        assert evolved_rows[name].oav == pytest.approx(rebuilt_rows[name].oav)


def test_explicit_solvent_matrix_lowers_natural_composite_oav():
    build_formula_state.cache_clear()
    concentrate = build_formula_state(
        {"Osmanthus Absolute": 100.0, "Iso E Super": 100.0},
        temperature_K=305.0,
    )
    finished = build_formula_state(
        {"Osmanthus Absolute": 100.0, "Iso E Super": 100.0},
        temperature_K=305.0,
        matrix_moles={"Ethanol": 0.4},
        matrix_mass_g=18.4,
        matrix_source="explicit",
    )
    concentrate_osmanthus = next(
        row for row in concentrate.materials if row.name == "Osmanthus Absolute"
    )
    finished_osmanthus = next(
        row for row in finished.materials if row.name == "Osmanthus Absolute"
    )

    assert concentrate_osmanthus.oav is not None
    assert finished_osmanthus.oav is not None
    assert finished_osmanthus.oav < concentrate_osmanthus.oav


def test_temporal_natural_composite_uses_constituent_headspace_for_loss():
    build_formula_state.cache_clear()
    frames = simulate_formula(
        {
            "Geranium EO (Pelargonium graveolens flower oil)": 100.0,
            "Hedione": 900.0,
        },
        temperature_K=305.0,
        windows=(("opening", 0.0), ("top", 300.0)),
    )
    opening = next(
        row
        for row in frames[0].state.materials
        if row.name == "Geranium EO (Pelargonium graveolens flower oil)"
    )
    top = next(
        row
        for row in frames[1].state.materials
        if row.name == "Geranium EO (Pelargonium graveolens flower oil)"
    )

    assert opening.sources["vp"] == "literature:natural_composite_constituent_vp"
    assert opening.partial_pressure_pa > 0.0
    assert top.raw_ul < opening.raw_ul


def test_temporal_simulation_is_monotonic_and_composition_dependent():
    build_formula_state.cache_clear()
    frames = simulate_formula(
        {"D-Limonene": 900.0, "Vanillin": 100.0},
        temperature_K=305.0,
        windows=(
            ("opening", 0.0),
            ("top", 300.0),
            ("heart", 1800.0),
        ),
    )
    totals = [frame.state.total_raw_ul for frame in frames]
    limonene_gamma = [
        next(row for row in frame.state.materials if row.name == "D-Limonene").gamma
        for frame in frames
    ]

    assert totals == sorted(totals, reverse=True)
    assert limonene_gamma[-1] != pytest.approx(limonene_gamma[0])


def test_temporal_windows_must_be_nondecreasing():
    with pytest.raises(ValueError, match="nondecreasing"):
        simulate_formula(
            {"Hedione": 100.0},
            windows=(("later", 300.0), ("earlier", 60.0)),
        )
