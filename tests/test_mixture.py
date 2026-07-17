import pytest

from engine.mixture import MixtureComponent, MixtureRole, MixtureState
from engine.quantities import Density, MolarMass, Volume


def test_finished_mixture_includes_solvent_in_mass_and_amount_fractions():
    state = MixtureState.from_components(
        (
            MixtureComponent(
                name="Hedione",
                role=MixtureRole.ODORANT,
                volume=Volume.from_ml(1.0),
                density=Density.from_g_ml(1.03),
                molar_mass=MolarMass.from_g_mol(226.32),
            ),
            MixtureComponent(
                name="Ethanol",
                role=MixtureRole.SOLVENT,
                volume=Volume.from_ml(9.0),
                density=Density.from_g_ml(0.789),
                molar_mass=MolarMass.from_g_mol(46.06844),
            ),
        )
    )

    hedione = state.component("Hedione")
    ethanol = state.component("Ethanol")
    assert state.complete is True
    assert state.total_volume.ml == pytest.approx(10.0)
    assert state.total_mass.g == pytest.approx(1.03 + 9.0 * 0.789)
    assert hedione.amount_fraction + ethanol.amount_fraction == pytest.approx(1.0)
    assert hedione.mass_fraction_ppm + ethanol.mass_fraction_ppm == pytest.approx(1_000_000.0)
    assert hedione.amount_fraction < 0.1


def test_finished_mixture_withholds_exact_fractions_when_physics_is_missing():
    state = MixtureState.from_components(
        (
            MixtureComponent(
                name="Unknown stock",
                role=MixtureRole.ODORANT,
                volume=Volume.from_ml(1.0),
                density=None,
                molar_mass=None,
            ),
            MixtureComponent(
                name="Ethanol",
                role=MixtureRole.SOLVENT,
                volume=Volume.from_ml(9.0),
                density=Density.from_g_ml(0.789),
                molar_mass=MolarMass.from_g_mol(46.06844),
            ),
        )
    )

    assert state.complete is False
    assert state.total_mass is None
    assert state.total_moles is None
    assert state.component("Unknown stock").amount_fraction is None
    assert set(state.missing_inputs) == {
        "Unknown stock.density_g_ml",
        "Unknown stock.molar_mass_g_mol",
    }


def test_finished_mixture_rejects_duplicate_component_names():
    ethanol = MixtureComponent(
        name="Ethanol",
        role=MixtureRole.SOLVENT,
        volume=Volume.from_ml(5.0),
        density=Density.from_g_ml(0.789),
        molar_mass=MolarMass.from_g_mol(46.06844),
    )

    with pytest.raises(ValueError, match="unique"):
        MixtureState.from_components((ethanol, ethanol))
