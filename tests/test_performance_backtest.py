from engine.calibration.performance_backtest import (
    FAINT,
    LASTING,
    UNKNOWN,
    Reading,
    backtest,
    dedupe_population,
    extract_performance_numbers,
    label_from_strengths,
    normalise_label,
    oriented_percentile,
    separation,
    spearman,
    strengths_from_wears,
)


def _entry(
    *,
    formula_hash="h1",
    longevity=80.0,
    sillage=100.0,
    ll_ul=70.0,
    vapour_4h=30.0,
    subliminal_4h=0.01,
    perceptible_4h=30,
    oil_4h=4000.0,
):
    return {
        "formula_hash": formula_hash,
        "scores": {"longevity": longevity, "sillage": sillage, "skin_performance": 60.0},
        "industry_10": {"tenacity": 2.5, "diffusion": 100.0},
        "gates": [
            {"gate": "tenacity_projection", "data": {
                "long_lasting_ul_per_ml": ll_ul, "long_lasting_pct": 40.0, "deep_pct": 8.0,
                "concentrate_pct": 22.0,
            }},
            {"gate": "carles_pyramid", "data": {"6h_heart": 40.0, "12h_heart_base": 4.0,
                                                "24h+_base": 13.0}},
            {"gate": "performance_prediction", "data": {"fixative_loading": [0.275, "Standard"]}},
        ],
        "time_windows": [
            {"t_seconds": 0.0, "total_vapor_ppm": 120.0, "perceptible_materials": 30},
            {"t_seconds": 300.0, "total_vapor_ppm": 200.0, "perceptible_materials": 30},
            {"t_seconds": 1800.0, "total_vapor_ppm": 500.0, "perceptible_materials": 30},
            {"t_seconds": 7200.0, "total_vapor_ppm": 50.0, "perceptible_materials": 30},
            {"t_seconds": 14400.0, "total_vapor_ppm": vapour_4h,
             "perceptible_materials": perceptible_4h, "subliminal_mass_ratio": subliminal_4h},
        ],
        "time_series": [
            {"t_seconds": 0.0, "state": {"odorant_active_ul": 5000.0}},
            {"t_seconds": 14400.0, "state": {"odorant_active_ul": oil_4h}},
        ],
    }


def test_extracts_every_number_from_a_full_report_or_an_entry():
    report = {"formulas": [_entry()]}
    numbers = extract_performance_numbers(report)
    assert numbers == extract_performance_numbers(_entry())
    assert numbers["longevity"] == 80.0
    assert numbers["sillage"] == 100.0
    assert numbers["long_lasting_ul_per_ml"] == 70.0
    assert numbers["vapour_4h_ppm"] == 30.0
    assert numbers["vapour_4h_over_peak"] == 30.0 / 500.0
    assert numbers["perceptible_4h"] == 30.0
    assert numbers["oil_left_4h"] == 0.8
    assert numbers["oil_left_2h"] is None  # no 2 h point in the series
    assert numbers["carles_base"] == 17.0
    assert numbers["fixative_loading"] == 0.275


def test_withheld_headspace_reads_as_missing_not_zero():
    entry = _entry()
    entry["time_windows"][4]["total_vapor_ppm"] = None
    entry["time_windows"][4]["perceptible_materials"] = None
    numbers = extract_performance_numbers(entry)
    assert numbers["vapour_4h_ppm"] is None
    assert numbers["vapour_4h_over_peak"] is None
    assert numbers["perceptible_4h"] is None


def test_perceptible_materials_given_as_a_list_counts_its_length():
    entry = _entry()
    entry["time_windows"][4]["perceptible_materials"] = ["a", "b", "c"]
    assert extract_performance_numbers(entry)["perceptible_4h"] == 3.0


def test_percentile_is_oriented_so_100_reads_longest_lasting():
    population = [1.0, 2.0, 3.0, 4.0]
    assert oriented_percentile(4.0, population, "higher") == 87.5
    assert oriented_percentile(4.0, population, "lower") == 12.5
    assert oriented_percentile(9.0, population, "higher") == 100.0


def test_separation_counts_ties_as_half():
    assert separation([5.0], [1.0, 2.0], "higher") == 1.0
    assert separation([5.0], [5.0], "higher") == 0.5
    assert separation([0.01], [0.2], "lower") == 1.0
    assert separation([], [1.0], "higher") is None


def test_spearman_needs_four_pairs():
    assert spearman([1, 2, 3], [1, 2, 3]) is None
    assert spearman([1, 2, 3, 4], [10, 20, 30, 40]) == 1.0
    assert spearman([1, 2, 3, 4], [4, 3, 2, 1]) == -1.0


def test_verdicts_saturated_missed_and_consistent():
    population = [
        extract_performance_numbers(
            _entry(formula_hash=f"p{i}", longevity=60.0 + i, ll_ul=40.0 + i, vapour_4h=10.0 + i)
        )
        for i in range(30)
    ]
    faint = Reading("faint-1", extract_performance_numbers(
        _entry(longevity=88.0, ll_ul=41.0, vapour_4h=11.0)), label=FAINT, bottle_id="b1")
    lasting = Reading("lasting-1", extract_performance_numbers(
        _entry(longevity=70.0, ll_ul=68.0, vapour_4h=38.0)), label=LASTING, bottle_id="b2")
    result = backtest([faint, lasting], population)
    by_key = {m["key"]: m for m in result["metrics"]}

    assert by_key["sillage"]["verdict"] == "saturated"
    assert by_key["longevity"]["verdict"] == "misses_faint_bottle"
    assert by_key["long_lasting_ul_per_ml"]["verdict"] == "consistent_so_far"
    assert by_key["vapour_4h_ppm"]["verdict"] == "consistent_so_far"
    assert by_key["long_lasting_ul_per_ml"]["separation"] == 1.0
    assert "sillage" in result["by_verdict"]["saturated"]
    assert result["evidence"]["faint_bottles"] == 1
    assert result["evidence"]["lasting_bottles"] == 1
    assert result["authority"] == "SCREENING_BACKTEST_NOT_CALIBRATION"


def test_misorders_when_a_faint_bottle_ties_or_beats_a_lasting_one_below_the_median():
    population = [
        extract_performance_numbers(_entry(formula_hash=f"p{i}", ll_ul=40.0 + i))
        for i in range(30)
    ]
    faint = Reading("f", extract_performance_numbers(_entry(ll_ul=45.0)), label=FAINT)
    lasting = Reading("l", extract_performance_numbers(_entry(ll_ul=43.0)), label=LASTING)
    metric = {m["key"]: m for m in backtest([faint, lasting], population)["metrics"]}
    assert metric["long_lasting_ul_per_ml"]["verdict"] == "misorders_bottles"


def test_candidate_cards_for_one_bottle_count_once():
    population = [extract_performance_numbers(_entry(formula_hash=f"p{i}")) for i in range(5)]
    readings = [
        Reading("card-a", extract_performance_numbers(_entry()), label=FAINT, bottle_id="b1"),
        Reading("card-b", extract_performance_numbers(_entry()), label=FAINT, bottle_id="b1"),
    ]
    evidence = backtest(readings, population)["evidence"]
    assert evidence["faint_bottles"] == 1
    assert evidence["readings"] == 2


def test_no_judged_bottles_and_no_data():
    population = [extract_performance_numbers(_entry(formula_hash=f"p{i}", ll_ul=40.0 + i))
                  for i in range(10)]
    unjudged = Reading("u", extract_performance_numbers(_entry()))
    metrics = {m["key"]: m for m in backtest([unjudged], population)["metrics"]}
    assert metrics["long_lasting_ul_per_ml"]["verdict"] == "no_judged_bottles"
    assert metrics["deep_pct"]["verdict"] == "saturated"  # all 8.0
    empty = {m["key"]: m for m in backtest([unjudged], [{}])["metrics"]}
    assert empty["longevity"]["verdict"] == "no_data"


def test_wear_ratings_give_median_strength_and_a_4h_label():
    wears = [
        {"bottle_id": "b1", "checks": {"m10": {"strength": 4}, "h4": {"strength": 1}}},
        {"bottle_id": "b1", "checks": {"h4": {"strength": 0}, "h8": {"strength": 9}}},
        {"bottle_id": "b2", "checks": {"h4": {"strength": 3}}},
        {"bottle_id": "", "checks": {"h4": {"strength": 3}}},
    ]
    strengths = strengths_from_wears(wears)
    assert strengths["b1"] == {"m10": 4.0, "h4": 0.5}  # 9 is off the 0-5 scale
    assert label_from_strengths(strengths["b1"]) == FAINT
    assert label_from_strengths(strengths["b2"]) == LASTING
    assert label_from_strengths({"h4": 2.0}) == UNKNOWN
    assert label_from_strengths({"h1": 0.0}) == UNKNOWN


def test_rating_correlation_is_reported_once_four_bottles_are_rated():
    population = [extract_performance_numbers(_entry(formula_hash=f"p{i}", ll_ul=40.0 + i))
                  for i in range(30)]
    readings = [
        Reading(f"r{i}", extract_performance_numbers(_entry(ll_ul=40.0 + 5 * i)),
                strengths={"h4": float(i)})
        for i in range(4)
    ]
    metric = {m["key"]: m for m in backtest(readings, population)["metrics"]}
    assert metric["long_lasting_ul_per_ml"]["rating_pairs_4h"] == 4
    assert metric["long_lasting_ul_per_ml"]["rating_rho_4h"] == 1.0
    assert metric["subliminal_4h"]["rating_rho_4h"] is None  # all equal, no rank order


def test_dedupe_population_by_formula_hash():
    reports = [{"formulas": [_entry(formula_hash="a")]}, {"formulas": [_entry(formula_hash="a")]},
               _entry(formula_hash="b")]
    assert len(dedupe_population(reports)) == 2


def test_label_aliases():
    assert normalise_label("weak") == FAINT
    assert normalise_label("good") == LASTING
    assert normalise_label(None) == UNKNOWN
    assert normalise_label("maybe") == UNKNOWN
