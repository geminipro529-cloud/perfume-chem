"""Scope and active-dose behaviour of the fuckups (mistake) detector.

Audit findings RULE-36 (one-bottle rules fired as universal catastrophic bans)
and RULE-37 (dose ceilings compared raw µL and ignored stock dilution).
"""

from __future__ import annotations

from engine.fuckups import scan_formula

CAMPAIGN = "cassis_iris_smoke_2026-07-05"

IRIS_FRUITY_MATERIALS = {
    "Juniper Berry EO": 50,
    "Petitgrain EO Paraguay": 80,
    "Orivone": 30,
    "Alpha Irone": 200,
    "Ultralia": 10,
    "Beta Ionone": 20,
    "Geosmin": 15,
    "Cassis Base 345B": 50,
    "Vetiver EO": 90,
    "Cedarwood EO": 160,
    "Oakmoss Absolute": 72,
}
IRIS_FRUITY_DILUTIONS = {
    "Juniper Berry EO": 100,
    "Petitgrain EO Paraguay": 100,
    "Orivone": 100,
    "Alpha Irone": 30,
    "Ultralia": 100,
    "Beta Ionone": 1,
    "Geosmin": 0.1,
    "Cassis Base 345B": 100,
    "Vetiver EO": 100,
    "Cedarwood EO": 100,
    "Oakmoss Absolute": 10,
}
IRIS_FRUITY_BRIEF = "Modern fruity chypre, Aventus style, with an iris heart and pineapple"


def _scan(materials, dilutions, campaign_id=""):
    return scan_formula(
        materials=materials,
        dilutions=dilutions,
        intended_character=IRIS_FRUITY_BRIEF,
        target_family="fruity_chypre",
        oav_data={"Orivone": 833},
        campaign_id=campaign_id,
    )


def test_iris_fruity_formula_outside_campaign_gets_no_cassis_rules():
    assert _scan(IRIS_FRUITY_MATERIALS, IRIS_FRUITY_DILUTIONS) == []
    assert _scan(IRIS_FRUITY_MATERIALS, IRIS_FRUITY_DILUTIONS, "some_other_campaign") == []


def test_same_formula_inside_campaign_warns_with_comparison_suggestion():
    warnings = _scan(IRIS_FRUITY_MATERIALS, IRIS_FRUITY_DILUTIONS, CAMPAIGN)
    names = {w.pattern_name for w in warnings}
    assert "classical_chypre_skeleton" in names
    assert "iris_soliflore_collision" in names
    assert "aromatic_green_opening" in names
    for w in warnings:
        assert w.severity == "warn", w.pattern_name
        assert "with and without" in w.recommendation, w.pattern_name
        assert w.fuckup_reference == CAMPAIGN
        assert "zero iris" not in (w.matched_rule + w.recommendation).lower()


def test_vetiver_and_two_cedars_count_cedar_once():
    two_cedars = {"Vetiver EO": 90, "Cedarwood EO": 160, "Cedarwood oil Virginia": 120}
    warnings = scan_formula(
        two_cedars, dilutions={k: 100 for k in two_cedars}, campaign_id=CAMPAIGN
    )
    assert "classical_chypre_skeleton" not in {w.pattern_name for w in warnings}

    with_moss = {"Vetiver EO": 90, "Cedarwood EO": 160, "Oakmoss Absolute": 72}
    warnings = scan_formula(with_moss, dilutions={k: 100 for k in with_moss}, campaign_id=CAMPAIGN)
    assert "classical_chypre_skeleton" in {w.pattern_name for w in warnings}


def _juniper_flags(raw_ul: float, dilution_pct: float) -> list[str]:
    warnings = scan_formula(
        {"Juniper Berry EO": raw_ul},
        dilutions={"Juniper Berry EO": dilution_pct},
        campaign_id=CAMPAIGN,
    )
    return sorted(w.pattern_name for w in warnings)


def test_same_active_dose_in_ten_percent_and_neat_stock_gets_same_verdict():
    # 200 µL of 10% and 20 µL neat are both 20 µL active, under the 30 µL ceiling.
    assert _juniper_flags(200, 10) == _juniper_flags(20, 100) == []
    # 400 µL of 10% and 40 µL neat are both 40 µL active, over it.
    over_dilute = _juniper_flags(400, 10)
    assert over_dilute and over_dilute == _juniper_flags(40, 100)


def _geosmin_overdosed(raw_ul: float, dilution_pct: float) -> bool:
    warnings = scan_formula(
        {"Geosmin": raw_ul}, dilutions={"Geosmin": dilution_pct}, campaign_id=CAMPAIGN
    )
    return "Geosmin overdosed" in {w.pattern_name for w in warnings}


def test_geosmin_ceiling_is_active_geosmin():
    # 5 µL of 0.1% and 0.5 µL of 1% are the same 0.005 µL active: at the ceiling.
    assert not _geosmin_overdosed(5, 0.1)
    assert not _geosmin_overdosed(0.5, 1)
    # Raw 4 µL passed the old raw 5 µL ceiling; neat or 1% it is far over in active.
    assert _geosmin_overdosed(4, 100)
    assert _geosmin_overdosed(4, 1)


def test_missing_dilution_is_treated_as_neat_and_said():
    warnings = scan_formula({"Geosmin": 4}, campaign_id=CAMPAIGN)
    dose = [w for w in warnings if w.pattern_name == "Geosmin overdosed"]
    assert dose and "assumed neat" in dose[0].matched_rule
