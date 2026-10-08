"""Finished-product % w/w: stocks plus ethanol topped up to the bottle volume."""

import pytest

from engine.ifra_standards import (
    FinishedProductRow,
    estimate_finished_product_pct_w_w,
)


def test_worked_example_by_hand():
    # 0.3 mL neat (1.0 g/mL) + 1.0 mL of 10 % in DPG, topped up to 30 mL with ethanol.
    # Mass: 0.3 + 0.1 + 0.9 * 1.023 + 28.7 * 0.789 = 23.9650 g.
    est = estimate_finished_product_pct_w_w(
        [
            FinishedProductRow("Neat", 300.0, 1.0, active_density_g_ml=1.0),
            FinishedProductRow("Diluted", 1000.0, 0.1, active_density_g_ml=1.0, carrier="DPG"),
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
