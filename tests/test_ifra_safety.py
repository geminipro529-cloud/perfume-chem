import pytest

from engine.ifra_safety import score_ifra_compliance
from engine.ifra_standards import FinishedProductRow, estimate_finished_product_pct_w_w


def _pct(report, name):
    return next(row["pct_in_product"] for row in report.dermal_exposure if row["material"] == name)


def test_ifra_safety_preserves_formal_cat4_violation_logic_and_adds_dermal_overlay():
    # 700 uL in a 30 mL bottle is about 2.8 % w/w, above Hydroxycitronellal's 2.1 % limit.
    report = score_ifra_compliance(
        {"Hydroxycitronellal": 700.0, "Hedione": 5300.0},
        total_volume_ml=30.0,
    )

    assert any(row["material"] == "Hydroxycitronellal" for row in report.ifra_violations)
    assert any(row["material"] == "Hydroxycitronellal" for row in report.dermal_exposure)
    assert report.uptake_weighted_sensitizers
    assert report.uptake_weighted_sensitizers[0]["material"] == "Hydroxycitronellal"
    assert report.uptake_weighted_sensitizers[0]["effective_exposure_index"] > 0
    assert any("Dermal uptake overlay" in message for message in report.diagnostics)


def test_ifra_safety_declares_inventory_relevant_2023_allergens():
    report = score_ifra_compliance(
        {"Linalyl Acetate": 200.0, "Methyl Salicylate": 200.0, "Hedione": 5600.0},
        total_volume_ml=30.0,
    )

    assert "Linalyl Acetate" in report.allergen_declarations
    assert "Methyl Salicylate" in report.allergen_declarations
    assert any("EU fragrance allergen" in message for message in report.diagnostics)


def test_ifra_safety_uses_leave_on_vs_rinse_off_thresholds():
    leave_on = score_ifra_compliance(
        {"Linalyl Acetate": 2.0, "Hedione": 5998.0},
        total_volume_ml=30.0,
        leave_on=True,
    )
    rinse_off = score_ifra_compliance(
        {"Linalyl Acetate": 2.0, "Hedione": 5998.0},
        total_volume_ml=30.0,
        leave_on=False,
    )

    assert "Linalyl Acetate" in leave_on.allergen_declarations
    assert "Linalyl Acetate" not in rinse_off.allergen_declarations


def test_ifra_safety_judges_finished_product_pct_w_w_estimated_from_stocks():
    # 300 uL neat + 1000 uL of a 10 % stock (carrier unknown) topped up with ethanol to 30 mL.
    # Unknown densities and carrier at 1.0 g/mL: 0.300 + 0.100 + 0.900 + 28.7 * 0.789
    # = 23.9443 g, so the neat row is 0.300 / 23.9443 = 1.252908 % w/w (it was 1.0 % v/v).
    report = score_ifra_compliance(
        {"Hydroxycitronellal": 300.0, "Hedione": 1000.0},
        {"Hedione": 0.10},
        total_volume_ml=30.0,
    )

    assert _pct(report, "Hydroxycitronellal") == pytest.approx(30.0 / 23.9443, rel=1e-6)
    assert _pct(report, "Hedione") == pytest.approx(10.0 / 23.9443, rel=1e-6)


def test_ifra_safety_uses_given_finished_pct_w_w():
    # With the 10 % stock's DPG carrier known: 0.300 + 0.100 + 0.900 * 1.023 + 28.7 * 0.789
    # = 23.9650 g, neat row 1.25183 % w/w.
    estimate = estimate_finished_product_pct_w_w(
        [
            FinishedProductRow("Hydroxycitronellal", 300.0),
            FinishedProductRow("Hedione", 1000.0, active_fraction=0.10, carrier="DPG"),
        ],
        30.0,
    )
    assert estimate.finished_mass_g == pytest.approx(23.9650, abs=1e-4)
    report = score_ifra_compliance(
        {"Hydroxycitronellal": 300.0, "Hedione": 1000.0},
        {"Hedione": 0.10},
        total_volume_ml=30.0,
        finished_pct_w_w=estimate.pct_w_w,
    )
    assert _pct(report, "Hydroxycitronellal") == pytest.approx(1.25183, abs=1e-5)

    over = score_ifra_compliance(
        {"Hydroxycitronellal": 1.0},
        total_volume_ml=30.0,
        finished_pct_w_w={"Hydroxycitronellal": 3.0},
    )
    assert [(v["material"], v["actual_pct"], v["limit_pct"]) for v in over.ifra_violations] == [
        ("Hydroxycitronellal", 3.0, 2.1)
    ]


def test_ifra_safety_totals_oakmoss_and_treemoss():
    report = score_ifra_compliance(
        {"Oakmoss Absolute": 1.0, "Treemoss Absolute": 1.0},
        total_volume_ml=30.0,
        finished_pct_w_w={"Oakmoss Absolute": 0.06, "Treemoss Absolute": 0.06},
    )

    assert [v["material"] for v in report.ifra_violations] == ["oakmoss_treemoss_total"]
    group = report.ifra_violations[0]
    assert group["actual_pct"] == pytest.approx(0.12)
    assert group["limit_pct"] == 0.1
    assert group["members"] == {"Oakmoss Absolute": 0.06, "Treemoss Absolute": 0.06}


def test_ifra_safety_does_not_flag_evernyl():
    report = score_ifra_compliance(
        {"Evernyl": 1.0},
        total_volume_ml=30.0,
        finished_pct_w_w={"Evernyl": 1.0},
    )

    assert report.ifra_violations == []
    assert report.ifra_warnings == []
    assert report.banned_flags == []


def test_ifra_safety_birch_tar_rectified_is_specification_not_banned():
    report = score_ifra_compliance(
        {"Birch Tar Rectified": 1.0},
        total_volume_ml=30.0,
        finished_pct_w_w={"Birch Tar Rectified": 0.05},
    )

    assert report.banned_flags == []
    assert report.ifra_violations == []
    assert any("specification standard" in message for message in report.diagnostics)


def test_ifra_safety_flags_lilial_as_banned():
    report = score_ifra_compliance(
        {"Lilial": 1.0, "Hedione": 100.0},
        total_volume_ml=30.0,
    )

    assert report.banned_flags == ["Lilial"]
    assert report.ifra_score == 0.0
