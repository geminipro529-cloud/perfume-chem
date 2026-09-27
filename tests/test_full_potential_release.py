"""Checkpoint 14 finite-release invariants and scenario boundaries."""

from __future__ import annotations

import pytest

from engine.research.contracts import ReleaseScenarioV1
from engine.research.release import (
    ReleaseModelPipelineV1,
    FiniteReleaseParametersV1,
    ReleaseComponentV1,
    default_release_pipeline,
    simulate_finite_release,
)


def _scenario(substrate: str = "GLASS", mass: str = "0.01") -> ReleaseScenarioV1:
    return ReleaseScenarioV1(
        scenario_id=f"scenario-{substrate.lower()}",
        matrix_id="ethanol-water-80-20",
        substrate=substrate,
        deposit_mass_g_decimal=mass,
        surface_area_m2_decimal="0.0001",
        temperature_k=298.15,
        relative_humidity_decimal="0.5",
        airflow_m_s_decimal="0.1",
        delivery_volume_m3_decimal="0.001",
        sampling_geometry="sealed-cell-with-defined-exchange",
        timepoints_seconds=(0.0, 10.0, 60.0),
    )


def _parameters(
    *, model: str = "NONIDEAL_PARAMETERIZED", substrates: tuple[str, ...] = ("GLASS",)
) -> FiniteReleaseParametersV1:
    return FiniteReleaseParametersV1(
        capability_id="finite-release-test-v1",
        equilibrium_model=model,
        matrix_ids=("ethanol-water-80-20",),
        supported_substrates=substrates,
        mass_transfer_coefficient_m_s_decimal="0.0001",
        air_exchange_rate_s_decimal="0.1",
        delivered_capture_fraction_decimal="0.25",
        maximum_step_seconds_decimal="0.25",
        calibration_state="UNCALIBRATED",
    )


def _component(**changes) -> ReleaseComponentV1:
    values = {
        "material_id": "example",
        "initial_mass_g_decimal": "0.01",
        "molecular_weight_g_mol": 100.0,
        "vapor_pressure_pa": 1.0,
        "activity_coefficient": 1.2,
    }
    values.update(changes)
    return ReleaseComponentV1(**values)


def test_every_frame_conserves_finite_initial_material() -> None:
    result = simulate_finite_release(
        (_component(substrate_retained_fraction_decimal="0.2", desorption_rate_s_decimal="0.01"),),
        scenario=_scenario(),
        parameters=_parameters(),
    )
    assert result["validation_state"] == "ADVISORY_FINDINGS"
    assert "HELD_OUT_SCENARIO_VALIDATION_MISSING" in result["reason_codes"]
    for frame in result["frames"]:
        assert frame["mass_balance_error_g"] == pytest.approx(0.0, abs=1e-12)
        assert frame["materials"][0]["mass_balance_error_g"] == pytest.approx(0.0, abs=1e-12)
    final = result["frames"][-1]["materials"][0]
    assert final["available_g"] + final["substrate_retained_g"] < 0.01
    assert final["delivered_g"] > 0
    assert final["delivered_cumulative_ug_l"] == pytest.approx(
        final["delivered_g"] * 1000 / 0.001
    )
    assert final["delivered_increment_ug_l"] == pytest.approx(
        final["delivered_increment_g"] * 1000 / 0.001
    )


def test_zero_dose_row_emits_nothing_without_fabricated_physics() -> None:
    result = simulate_finite_release(
        (
            _component(),
            ReleaseComponentV1(material_id="zero", initial_mass_g_decimal="0"),
        ),
        scenario=_scenario(),
        parameters=_parameters(),
    )
    zero = result["frames"][-1]["materials"][1]
    assert zero["available_g"] == 0
    assert zero["delivered_g"] == 0
    assert zero["local_gas_ug_l"] == 0


def test_missing_molecular_weight_or_vapor_pressure_is_unavailable_not_zero() -> None:
    for component in (
        _component(molecular_weight_g_mol=None),
        _component(vapor_pressure_pa=None),
    ):
        result = simulate_finite_release(
            (component,), scenario=_scenario(), parameters=_parameters()
        )
        assert result["validation_state"] == "WITHHOLD_UNKNOWN"
        assert result["applicability_state"] == "UNAVAILABLE"
        assert result["frames"] == []
        assert result["positive_mass_coverage_decimal"] == "0"


def test_substrates_and_matrices_are_not_interchangeable() -> None:
    result = simulate_finite_release(
        (_component(),),
        scenario=_scenario("BLOTTER"),
        parameters=_parameters(substrates=("GLASS",)),
    )
    assert result["applicability_state"] == "OUT_OF_DOMAIN"
    assert "SUBSTRATE_OUT_OF_DOMAIN" in result["reason_codes"]
    assert result["frames"] == []


def test_ideal_and_hansen_routes_are_explicit_sensitivity_scenarios() -> None:
    ideal = simulate_finite_release(
        (_component(activity_coefficient=None),),
        scenario=_scenario(),
        parameters=_parameters(model="IDEAL_SENSITIVITY"),
    )
    hansen = simulate_finite_release(
        (_component(),),
        scenario=_scenario(),
        parameters=_parameters(model="HANSEN_SENSITIVITY"),
    )
    for result in (ideal, hansen):
        assert result["prediction_certificate"] is False
        assert "SENSITIVITY_SCENARIO_NOT_EMPIRICAL_PREDICTION" in result["reason_codes"]


def test_precipitated_and_unknown_natural_remainder_are_preserved() -> None:
    result = simulate_finite_release(
        (
            _component(initial_mass_g_decimal="0.008", precipitated_fraction_decimal="0.25"),
            ReleaseComponentV1(
                material_id="unknown-natural-remainder",
                initial_mass_g_decimal="0.002",
                identity_state="UNKNOWN_NATURAL_REMAINDER",
            ),
        ),
        scenario=_scenario(),
        parameters=_parameters(),
    )
    final = {row["material_id"]: row for row in result["frames"][-1]["materials"]}
    assert final["example"]["precipitated_g"] == pytest.approx(0.002)
    assert final["unknown-natural-remainder"]["unknown_remainder_g"] == pytest.approx(0.002)
    assert final["unknown-natural-remainder"]["interfacial_pressure_pa"] is None
    assert "UNKNOWN_NATURAL_REMAINDER_PRESERVED" in result["reason_codes"]


def test_declared_deposit_must_equal_component_mass() -> None:
    result = simulate_finite_release(
        (_component(),), scenario=_scenario(mass="0.02"), parameters=_parameters()
    )
    assert result["validation_state"] == "INVALID_INPUT"
    assert result["reason_codes"] == ["DEPOSIT_MASS_DOES_NOT_MATCH_COMPONENT_MASS"]


def test_release_pipeline_stages_are_composable_and_invoked() -> None:
    default = default_release_pipeline()
    calls: list[str] = []

    class CompositionSpy:
        def resolve(self, components, initial_by_id):
            calls.append("composition")
            return default.composition_resolver.resolve(components, initial_by_id)

    class EquilibriumSpy:
        def pressures(self, components, state, initial_by_id, equilibrium_model):
            calls.append("equilibrium")
            return default.equilibrium_model.pressures(
                components, state, initial_by_id, equilibrium_model
            )

    class SubstrateSpy:
        def advance(self, component, compartment, dt_seconds):
            calls.append("substrate")
            default.substrate_model.advance(component, compartment, dt_seconds)

    class TransferSpy:
        def advance(self, component, compartment, **kwargs):
            calls.append("transfer")
            default.transfer_model.advance(component, compartment, **kwargs)

    class DeliverySpy:
        def advance(self, compartment, **kwargs):
            calls.append("delivery")
            default.delivery_model.advance(compartment, **kwargs)

    pipeline = ReleaseModelPipelineV1(
        composition_resolver=CompositionSpy(),
        equilibrium_model=EquilibriumSpy(),
        substrate_model=SubstrateSpy(),
        transfer_model=TransferSpy(),
        delivery_model=DeliverySpy(),
    )
    result = simulate_finite_release(
        (_component(),),
        scenario=_scenario(),
        parameters=_parameters(),
        pipeline=pipeline,
    )

    assert result["frames"]
    assert set(calls) == {
        "composition",
        "equilibrium",
        "substrate",
        "transfer",
        "delivery",
    }
