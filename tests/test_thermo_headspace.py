from __future__ import annotations

import pytest

from engine.thermo.headspace import (
    HeadspaceInputError,
    headspace_from_wt_pct,
    partial_pressures,
)
from engine.thermo.trajectory import evaporate

MW = {"Hedione": 226.32, "Limonene": 136.24}
VP = {"Hedione": 0.8, "Limonene": 200.0}
WT = {"Hedione": 70.0, "Limonene": 30.0}


def test_complete_inputs_preserve_standalone_headspace_calculation() -> None:
    result = headspace_from_wt_pct(WT, mw_table=MW, vp_table=VP)

    assert set(result) == set(WT)
    assert sum(row.mole_fraction for row in result.values()) == pytest.approx(1.0)
    assert all(row.vp_pure_pa > 0.0 for row in result.values())
    assert all(row.vapor_ppm > 0.0 for row in result.values())


def test_missing_mw_is_unknown_instead_of_using_200_g_per_mol() -> None:
    with pytest.raises(HeadspaceInputError, match="molecular weight: Hedione"):
        headspace_from_wt_pct(WT, mw_table={"Limonene": 136.24}, vp_table=VP)


def test_missing_vp_is_unknown_instead_of_zero_emission() -> None:
    with pytest.raises(HeadspaceInputError, match="vapor pressure: Hedione"):
        headspace_from_wt_pct(WT, mw_table=MW, vp_table={"Limonene": 200.0})


def test_valid_antoine_input_satisfies_vapor_pressure_preflight() -> None:
    result = headspace_from_wt_pct(
        {"Water": 100.0},
        T_K=298.15,
        mw_table={"Water": 18.015},
        antoine_table={"Water": (8.07131, 1730.63, 233.426)},
    )

    assert result["Water"].vp_pure_pa == pytest.approx(3157.92, rel=0.01)


@pytest.mark.parametrize(
    "invalid_antoine",
    [(), (8.0, 1700.0), (8.0, float("nan"), 230.0)],
)
def test_malformed_antoine_input_is_reported_as_missing_physics(
    invalid_antoine: tuple[float, ...],
) -> None:
    with pytest.raises(HeadspaceInputError, match="vapor pressure: Water"):
        headspace_from_wt_pct(
            {"Water": 100.0},
            mw_table={"Water": 18.015},
            antoine_table={"Water": invalid_antoine},  # type: ignore[arg-type]
        )


def test_partial_pressure_convenience_api_propagates_missing_physics() -> None:
    with pytest.raises(HeadspaceInputError, match="vapor pressure: Hedione"):
        partial_pressures(WT, mw_table=MW, vp_table={"Limonene": 200.0})


def test_standalone_trajectory_inherits_fail_closed_physics_preflight() -> None:
    with pytest.raises(HeadspaceInputError, match="molecular weight.*Hedione"):
        evaporate(
            WT,
            mw_table={"Limonene": 136.24},
            vp_table=VP,
            duration_s=60.0,
            n_steps=2,
        )
