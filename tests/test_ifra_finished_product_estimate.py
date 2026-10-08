"""Finished-product % w/w: stocks plus ethanol topped up to the bottle volume."""

import pytest

from engine.ifra_standards import (
    FinishedProductRow,
    estimate_finished_product_pct_w_w,
)


def test_worked_example_by_hand():
    # 0.3 mL neat (1.0 g/mL) + 1.0 mL of 10 % v/v in DPG, topped up to 30 mL with ethanol.
    # Mass: 0.3 + 0.1 + 0.9 * 1.023 + 28.7 * 0.789 = 23.9650 g.
    est = estimate_finished_product_pct_w_w(
        [
            FinishedProductRow("Neat", 300.0, 1.0, active_density_g_ml=1.0),
            FinishedProductRow(
                "Diluted", 1000.0, 0.1, active_density_g_ml=1.0, carrier="DPG",
                fraction_basis="volume_fraction",
            ),
        ],
        30.0,
    )
    assert est.finished_mass_g == pytest.approx(23.9650, abs=1e-4)
    assert est.concentrate_ml == pytest.approx(1.3)
    assert est.ethanol_ml == pytest.approx(28.7)
    assert est.pct_w_w["Neat"] == pytest.approx(1.25183, abs=1e-4)
    assert est.pct_w_w["Diluted"] == pytest.approx(0.41728, abs=1e-4)
    assert not est.overfilled
    assert est.assumptions == ()


def test_weight_basis_reads_higher_than_the_old_volume_basis():
    est = estimate_finished_product_pct_w_w(
        [FinishedProductRow("Coumarin", 450.0, 1.0, active_density_g_ml=1.0)], 30.0
    )
    volume_pct = 0.45 / 30.0 * 100.0  # 1.5 %, exactly at the limit by volume
    assert est.pct_w_w["Coumarin"] > volume_pct * 1.2


def test_known_active_mass_wins_and_rows_with_one_name_add_up():
    est = estimate_finished_product_pct_w_w(
        [
            FinishedProductRow("A", 100.0, 1.0, active_g=0.2),
            FinishedProductRow("A", 100.0, 1.0, active_density_g_ml=1.0),
        ],
        10.0,
    )
    mass = 0.2 + 0.1 + 9.8 * 0.789
    assert est.finished_mass_g == pytest.approx(mass)
    assert est.pct_w_w == {"A": pytest.approx(100.0 * 0.3 / mass)}


def test_missing_densities_fall_back_and_are_reported():
    est = estimate_finished_product_pct_w_w(
        [FinishedProductRow("X", 500.0, 0.5, carrier="Mystery Solvent")], 10.0
    )
    assert est.finished_mass_g == pytest.approx(0.25 + 0.25 + 9.5 * 0.789)
    assert len(est.assumptions) == 2
    assert "X: density unknown" in est.assumptions[0]
    assert "Mystery Solvent" in est.assumptions[1]


def test_ethanol_carrier_uses_ethanol_density():
    est = estimate_finished_product_pct_w_w(
        [FinishedProductRow("Tincture", 1000.0, 0.2, active_density_g_ml=1.0, carrier="Ethanol")],
        10.0,
    )
    assert est.finished_mass_g == pytest.approx(0.2 + 0.8 * 0.789 + 9.0 * 0.789)


def test_stocks_larger_than_the_bottle_are_flagged_overfilled():
    est = estimate_finished_product_pct_w_w(
        [FinishedProductRow("Big", 12000.0, 1.0, active_density_g_ml=1.0)], 10.0
    )
    assert est.overfilled
    assert est.ethanol_ml == 0.0
    assert est.pct_w_w["Big"] == pytest.approx(100.0)


def test_batch_volume_must_be_positive():
    with pytest.raises(ValueError):
        estimate_finished_product_pct_w_w([], 0.0)


# 1000 uL of a 10 % stock in a 10 mL bottle; active density 0.9, carrier DEP 1.12 g/mL.
# Ethanol: 9 mL x 0.789 = 7.101 g.
_ETHANOL_G = 9.0 * 0.789
_WW_STOCK_DENSITY = 1.0 / (0.1 / 0.9 + 0.9 / 1.12)  # 1.09328 g/mL, ideal mixing


def _ten_percent(basis, **kwargs):
    row = FinishedProductRow(
        "X", 1000.0, 0.1, active_density_g_ml=0.9, carrier="DEP", fraction_basis=basis, **kwargs
    )
    return estimate_finished_product_pct_w_w([row], 10.0)


def _active_g(est):
    return est.pct_w_w["X"] / 100.0 * est.finished_mass_g


@pytest.mark.parametrize(
    ("basis", "active_g", "carrier_g"),
    [
        ("mass_fraction", 0.109328, 0.9 * _WW_STOCK_DENSITY),
        ("w/w", 0.109328, 0.9 * _WW_STOCK_DENSITY),
        ("volume_fraction", 0.09, 0.9 * 1.12),
        ("v/v", 0.09, 0.9 * 1.12),
        ("mass_per_volume", 0.1, (1.0 - 0.1 / 0.9) * 1.12),
        ("w/v", 0.1, (1.0 - 0.1 / 0.9) * 1.12),
    ],
)
def test_declared_dilution_basis_sets_the_active_mass(basis, active_g, carrier_g):
    est = _ten_percent(basis)
    assert _WW_STOCK_DENSITY == pytest.approx(1.09328, abs=1e-5)
    assert _active_g(est) == pytest.approx(active_g, abs=1e-6)
    assert est.finished_mass_g == pytest.approx(active_g + carrier_g + _ETHANOL_G, abs=1e-6)
    assert est.assumptions == ()


def test_w_w_uses_a_given_stock_density():
    est = _ten_percent("mass_fraction", stock_density_g_ml=1.05)
    assert _active_g(est) == pytest.approx(0.105)
    assert est.finished_mass_g == pytest.approx(1.05 + _ETHANOL_G)


def test_unspecified_basis_takes_the_reading_with_more_active_and_says_so():
    est = _ten_percent("unspecified")
    assert _active_g(est) == pytest.approx(0.109328, abs=1e-6)
    assert est.finished_mass_g == pytest.approx(_WW_STOCK_DENSITY + _ETHANOL_G, abs=1e-6)
    (note,) = est.assumptions
    assert note.startswith("X:") and "w/w" in note


def test_unspecified_basis_with_unknown_densities_adds_no_basis_assumption():
    est = estimate_finished_product_pct_w_w([FinishedProductRow("X", 1000.0, 0.1)], 10.0)
    assert _active_g(est) == pytest.approx(0.1)
    assert len(est.assumptions) == 2
    assert not any("basis" in a for a in est.assumptions)
