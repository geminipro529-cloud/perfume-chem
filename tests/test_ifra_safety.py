from engine.ifra_safety import score_ifra_compliance


def test_ifra_safety_preserves_formal_cat4_violation_logic_and_adds_dermal_overlay():
    report = score_ifra_compliance(
        {"Hydroxycitronellal": 400.0, "Hedione": 5600.0},
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
