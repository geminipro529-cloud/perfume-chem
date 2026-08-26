import pytest

import engine.quantities as quantities
from engine.quantities import (
    Concentration,
    ConcentrationBasis,
    Density,
    Duration,
    Mass,
    MolarMass,
    OdorActivityValue,
    OdorThreshold,
    QuantityError,
    StandardUncertainty,
    Temperature,
    VaporPressure,
    Volume,
)


def test_volume_and_mass_conversions_use_canonical_units():
    assert Volume.from_ml(1.25).ul == pytest.approx(1250.0)
    assert Volume.from_ul(1250.0).ml == pytest.approx(1.25)
    assert Mass.from_mg(250.0).g == pytest.approx(0.25)


@pytest.mark.parametrize(
    "factory,value",
    [
        (Volume.from_ul, -1.0),
        (Mass.from_g, -1.0),
        (Density.from_g_ml, 0.0),
        (MolarMass.from_g_mol, 0.0),
        (VaporPressure.from_pa, -1.0),
        (Duration.from_seconds, -1.0),
    ],
)
def test_physical_quantities_reject_invalid_signs(factory, value):
    with pytest.raises(QuantityError):
        factory(value)


def test_temperature_converts_celsius_to_kelvin_without_accepting_below_absolute_zero():
    assert Temperature.from_celsius(25.0).kelvin == pytest.approx(298.15)
    with pytest.raises(QuantityError, match="absolute zero"):
        Temperature.from_celsius(-274.0)


def test_concentration_keeps_fraction_basis_and_medium_explicit():
    concentration = Concentration.from_ppm(
        2500.0,
        basis=ConcentrationBasis.MASS_FRACTION,
        medium="finished_product",
    )

    assert concentration.fraction == pytest.approx(0.0025)
    assert concentration.ppm == pytest.approx(2500.0)
    assert concentration.basis is ConcentrationBasis.MASS_FRACTION
    assert concentration.medium == "finished_product"

    with pytest.raises(QuantityError, match="basis"):
        Concentration(fraction=0.1, basis="ppm", medium="finished_product")


def test_liquid_mass_concentration_uses_a_unit_bearing_quantity():
    assert hasattr(quantities, "LiquidMassConcentration")

    concentration = quantities.LiquidMassConcentration.from_mg_l(250.0)

    assert concentration.g_l == pytest.approx(0.25)
    assert concentration.mg_l == pytest.approx(250.0)
    with pytest.raises(QuantityError):
        quantities.LiquidMassConcentration.from_g_l(-1.0)


def test_oav_requires_matching_concentration_and_threshold_basis():
    concentration = Concentration.from_ppm(
        20.0,
        basis=ConcentrationBasis.GAS_AMOUNT_FRACTION,
        medium="air",
    )
    threshold = OdorThreshold.from_ppm(
        2.0,
        basis=ConcentrationBasis.GAS_AMOUNT_FRACTION,
        medium="air",
    )

    assert OdorActivityValue.from_ratio(concentration, threshold).value == pytest.approx(10.0)

    incompatible = OdorThreshold.from_ppm(
        2.0,
        basis=ConcentrationBasis.MASS_FRACTION,
        medium="ethanol",
    )
    with pytest.raises(QuantityError, match="basis and medium"):
        OdorActivityValue.from_ratio(concentration, incompatible)


def test_standard_uncertainty_keeps_value_unit_and_nonnegative_uncertainty():
    measurement = StandardUncertainty(value=10.0, standard_uncertainty=0.1, unit="g")
    assert measurement.as_dict() == {
        "value": 10.0,
        "standard_uncertainty": 0.1,
        "unit": "g",
    }
    with pytest.raises(QuantityError):
        StandardUncertainty(value=10.0, standard_uncertainty=-0.1, unit="g")
