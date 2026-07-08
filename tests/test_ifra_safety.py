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
