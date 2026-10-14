"""The preregistered smell-log calibration: factor rule, gates and leave-one-bottle-out."""

from math import isclose, sqrt

from app.services.smell_log_calibration import (
    SMELL_LOG_CALIBRATION_RULE,
    calibrate,
    calibration_window,
    chart_correction,
    corrected_ranking,
    fit_factors,
    held_out_by_bottle,
)

# The model ranks Ambrox 4th and Hedione 2nd; Kenny smells Ambrox leading and Hedione weak.
RANKED = [("Linalool", 0.4), ("Hedione", 0.25), ("Lavender EO", 0.2), ("Ambrox", 0.15)]


def _helpful(n_bottles):
    return [
        calibration_window(f"b{i}", "strip_1h", RANKED, ["Linalool", "Ambrox"], ["Hedione"])
        for i in range(n_bottles)
    ]


def test_rule_is_declared_in_code_with_its_version():
    assert SMELL_LOG_CALIBRATION_RULE == {
        "schema": "smell-log-calibration-v1",
        "data": "strip windows inside the model's range; model ranking by OAV share; Kenny's leads and weak",
        "factor": "exp(k * net / n_seen) per material; net = +1 lead outside top 3, -1 weak inside top 3",
        "k": "ln 2",
        "min_bottles_per_material": 3,
        "top_n": 3,
        "baseline": "plain model top 3 by OAV share",
        "score": "per window: Kenny-leading names in top 3 minus Kenny-weak names in top 3",
        "evaluation": "leave-one-bottle-out, summed over held-out windows",
        "gates": {"min_bottles": 10, "corrected_beats_baseline": "strictly greater"},
    }


def test_factor_counts_leads_outside_top3_and_weak_inside_top3_over_windows_seen():
    windows = [
        calibration_window("b1", "strip_10m", RANKED, ["ambrox"], []),
        calibration_window("b2", "strip_10m", RANKED, ["Ambrox"], ["Hedione"]),
        calibration_window("b3", "strip_1h", RANKED, [], ["Hedione"]),
        calibration_window("b3", "strip_3h", RANKED, ["Linalool"], ["Lavender EO", "Ambrox"]),
    ]

    factors = fit_factors(windows)

    # Ambrox: +1, +1, 0, 0 (weak outside the top 3 does not count) over 4 windows.
    assert factors["ambrox"]["net"] == 2 and factors["ambrox"]["n_seen"] == 4
    assert isclose(factors["ambrox"]["factor"], sqrt(2))
    assert isclose(factors["hedione"]["factor"], 2 ** (-2 / 4))
    assert factors["lavender eo"]["net"] == -1
    assert factors["linalool"]["factor"] == 1.0
    assert all(stats["status"] == "fitted" and stats["n_bottles"] == 3 for stats in factors.values())


def test_material_in_fewer_than_three_bottles_keeps_factor_one():
    windows = [
        calibration_window("b1", "strip_10m", RANKED, ["Ambrox"], []),
        calibration_window("b1", "strip_1h", RANKED, ["Ambrox"], []),
        calibration_window("b2", "strip_10m", RANKED, ["Ambrox"], []),
    ]

    ambrox = fit_factors(windows)["ambrox"]

    assert ambrox["factor"] == 1.0
    assert ambrox["status"] == "too few bottles"
    assert ambrox["n_seen"] == 3 and ambrox["n_bottles"] == 2


def test_factor_stays_within_half_and_double():
    up = fit_factors(_helpful(5))
    assert isclose(up["ambrox"]["factor"], 2.0)
    assert isclose(up["hedione"]["factor"], 0.5)
    assert corrected_ranking(RANKED, up) == ["Linalool", "Ambrox", "Lavender EO", "Hedione"]


def test_name_marked_both_ways_counts_as_neither():
    window = calibration_window("b1", "strip_1h", RANKED, ["Ambrox", "Hedione"], ["hedione"])

    assert window.leads == frozenset({"ambrox"})
    assert window.weak == frozenset()


def test_nine_bottles_is_unknown_even_when_the_correction_helps():
    result = calibrate(_helpful(9))

    assert result["evidence_class"] == "UNKNOWN"
    assert result["calibrated"] is False
    assert result["reason"] == "9 of 10 bottles logged"
    assert result["corrected_score"] > result["baseline_score"]


def test_ten_bottles_where_the_correction_helps_is_calibrated():
    result = calibrate(_helpful(10), n_bottles_skipped=2)

    assert result["evidence_class"] == "EMPIRICALLY_CALIBRATED"
    assert result["calibrated"] is True
    assert result["reason"] is None
    assert (result["n_bottles"], result["n_bottles_skipped"], result["n_entries"]) == (10, 2, 10)
    assert (result["baseline_score"], result["corrected_score"]) == (0, 20)
    by_name = {item["name"]: item for item in result["factors"]}
    assert by_name["Ambrox"]["label"] == "×2.0" and by_name["Ambrox"]["n_seen"] == 10
    assert by_name["Hedione"]["label"] == "×0.5"
    assert "not how strong" in result["basis"]


def test_ten_bottles_where_the_correction_does_not_help_is_unknown_with_reason():
    windows = [
        calibration_window(f"b{i}", "strip_1h", RANKED, ["Linalool", "Hedione"], ["Ambrox"])
        for i in range(10)
    ]

    result = calibrate(windows)

    assert result["evidence_class"] == "UNKNOWN"
    assert result["baseline_score"] == result["corrected_score"] == 20
    assert result["reason"] == (
        "10 bottles logged; the correction does not beat the plain model yet, so it is not used."
    )


def test_leave_one_out_does_not_let_a_bottle_fit_its_own_correction():
    # Ambrox is ranked in exactly three bottles. Held out, each of them leaves two
    # bottles to fit on, too few for a factor, so no held-out window can improve.
    # Fitting on all bottles including the held-out one would let it "predict" itself.
    windows = [
        calibration_window(f"b{i}", "strip_1h", RANKED, ["Ambrox"], []) for i in range(3)
    ] + [
        calibration_window(f"c{i}", "strip_1h", RANKED[:3], ["Linalool"], []) for i in range(7)
    ]

    result = calibrate(windows)

    assert fit_factors(windows)["ambrox"]["factor"] == 2.0
    assert result["baseline_score"] == result["corrected_score"] == 7
    assert result["evidence_class"] == "UNKNOWN"


def test_held_out_rows_score_each_bottle_without_itself_and_add_up_to_the_totals():
    windows = _helpful(10) + [calibration_window("b0", "strip_3h", RANKED, ["Iris"], ["Linalool"])]

    rows = held_out_by_bottle(windows)
    result = calibrate(windows)

    assert [row["bottle_id"] for row in rows] == [f"b{i}" for i in range(10)]
    assert rows[0]["windows"] == ["strip_1h", "strip_3h"]
    # strip_1h: Linalool and Ambrox lead, Hedione weak. Plain top 3 holds Linalool
    # (+1) and Hedione (-1); corrected top 3 holds Linalool and Ambrox (+2).
    # strip_3h: Iris is not ranked, so the best is 0; Linalool is weak in the top 3.
    assert (rows[1]["baseline_score"], rows[1]["corrected_score"], rows[1]["best_score"]) == (0, 2, 2)
    assert (rows[0]["baseline_score"], rows[0]["corrected_score"], rows[0]["best_score"]) == (-1, 1, 2)
    assert result["held_out"] == rows
    assert result["baseline_score"] == sum(row["baseline_score"] for row in rows)
    assert result["corrected_score"] == sum(row["corrected_score"] for row in rows)
    assert result["best_score"] == 20


def test_chart_correction_gives_bottles_always_and_the_factor_only_when_used():
    fitted = fit_factors(_helpful(10))

    used = chart_correction("Ambrox", fitted["ambrox"], True)
    unused = chart_correction("Ambrox", fitted["ambrox"], False)
    unknown = chart_correction("Iris", None, True)

    assert used == {"name": "Ambrox", "n_bottles": 10, "min_bottles": 3, "used": True, "factor": 2.0, "label": "×2.0"}
    assert unused == {"name": "Ambrox", "n_bottles": 10, "min_bottles": 3, "used": False, "factor": None, "label": None}
    assert unknown == {"name": "Iris", "n_bottles": 0, "min_bottles": 3, "used": False, "factor": None, "label": None}
    few = fit_factors(_helpful(2))["ambrox"]
    assert chart_correction("Ambrox", few, True)["used"] is False
