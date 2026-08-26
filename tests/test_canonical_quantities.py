import random

import pytest

from engine.quantities import (
    ConcentrationBasis,
    Density,
    DensityConditions,
    IncomparabilityReason,
    Mass,
    MeasurementResolution,
    StandardUncertainty,
    Volume,
    VolumeBalance,
    convert_mass_to_volume,
    convert_raw_to_active_mass,
    partition_raw_mass,
)


def test_mass_volume_conversion_requires_applicable_density():
    missing = convert_mass_to_volume(Mass.from_g(1), density=None)
    assert missing.reason is IncomparabilityReason.MISSING_DENSITY

    outside = convert_mass_to_volume(
        Mass.from_g(1),
        density=Density.from_g_ml(0.8),
        conditions=DensityConditions(
            measured_temperature_c=20,
            minimum_temperature_c=15,
            maximum_temperature_c=25,
        ),
        requested_temperature_c=30,
    )
    assert (
        outside.reason
        is IncomparabilityReason.DENSITY_OUTSIDE_VALID_RANGE
    )

    converted = convert_mass_to_volume(
        Mass.from_g(0.8),
        density=Density.from_g_ml(0.8),
    )
    assert converted.reason is None
    assert isinstance(converted.value, Volume)
    assert converted.value.ml == pytest.approx(1.0)


def test_raw_active_conversion_fails_closed_on_basis_fraction_and_uncertainty():
    assert (
        convert_raw_to_active_mass(
            Mass.from_g(1),
            active_fraction=0.1,
            basis=None,
        ).reason
        is IncomparabilityReason.UNSPECIFIED_CONCENTRATION_BASIS
    )
    assert (
        convert_raw_to_active_mass(
            Mass.from_g(1),
            active_fraction=None,
            basis=ConcentrationBasis.MASS_FRACTION,
        ).reason
        is IncomparabilityReason.MISSING_ACTIVE_FRACTION
    )
    assert (
        convert_raw_to_active_mass(
            Mass.from_g(1),
            active_fraction=0.1,
            basis=ConcentrationBasis.VOLUME_FRACTION,
        ).reason
        is IncomparabilityReason.UNIT_NOT_CONVERTIBLE
    )
    assert (
        convert_raw_to_active_mass(
            Mass.from_g(1),
            active_fraction=0.1,
            basis=ConcentrationBasis.MASS_FRACTION,
            uncertainty=StandardUncertainty(1, 0.6, "g"),
            maximum_relative_uncertainty=0.5,
        ).reason
        is IncomparabilityReason.UNCERTAINTY_TOO_LARGE
    )


def test_partition_separates_active_carrier_and_named_solvents():
    unknown = partition_raw_mass(
        Mass.from_g(10),
        active_fraction=0.2,
        basis=ConcentrationBasis.MASS_FRACTION,
        diluent_fractions=None,
    )
    assert unknown.reason is IncomparabilityReason.UNKNOWN_DILUENT

    result = partition_raw_mass(
        Mass.from_g(10),
        active_fraction=0.2,
        basis=ConcentrationBasis.MASS_FRACTION,
        diluent_fractions={
            "ethanol": 0.75,
            "water": 0.20,
            "other-solvent": 0.05,
        },
    )
    assert result.reason is None
    assert result.value is not None
    assert result.value.raw_mass_g == pytest.approx(10)
    assert result.value.active_mass_g == pytest.approx(2)
    assert result.value.carrier_mass_g == pytest.approx(8)
    assert result.value.ethanol_mass_g == pytest.approx(6)
    assert result.value.water_mass_g == pytest.approx(1.6)
    assert result.value.other_solvent_mass_g == pytest.approx(0.4)


def test_partition_raw_mass_seeded_property_fuzz_conserves_every_role():
    rng = random.Random(20260730)

    for _case in range(512):
        raw_mass_g = 10 ** rng.uniform(-6, 3)
        active_fraction = rng.random()
        allocation_budget = rng.random()
        weights = [rng.random() for _ in range(3)]
        weight_total = sum(weights)
        diluent_fractions = {
            "ethanol": allocation_budget * weights[0] / weight_total,
            "water": allocation_budget * weights[1] / weight_total,
            "other-solvent": allocation_budget * weights[2] / weight_total,
        }

        result = partition_raw_mass(
            Mass.from_g(raw_mass_g),
            active_fraction=active_fraction,
            basis=ConcentrationBasis.MASS_FRACTION,
            diluent_fractions=diluent_fractions,
        )

        assert result.reason is None
        assert result.value is not None
        balance = result.value
        assert balance.active_mass_g + balance.carrier_mass_g == pytest.approx(
            balance.raw_mass_g,
            rel=1e-12,
            abs=1e-12,
        )
        assert (
            balance.ethanol_mass_g
            + balance.water_mass_g
            + balance.other_solvent_mass_g
            + balance.unallocated_mass_g
        ) == pytest.approx(
            balance.carrier_mass_g,
            rel=1e-12,
            abs=1e-12,
        )


def test_volume_roles_and_measurement_resolution_are_distinct():
    volumes = VolumeBalance(
        raw_volume=Volume.from_ml(10),
        active_volume=Volume.from_ml(2),
        carrier_volume=Volume.from_ml(8),
        solvent_volume=Volume.from_ml(8),
    )
    resolution = MeasurementResolution(0.01, "g")

    assert volumes.raw_volume.ml == pytest.approx(10)
    assert volumes.active_volume.ml == pytest.approx(2)
    assert volumes.carrier_volume.ml == pytest.approx(8)
    assert volumes.solvent_volume.ml == pytest.approx(8)
    assert resolution.value == pytest.approx(0.01)
    assert resolution.unit == "g"
