"""The crowd guess check and the weight it earns in the personal liking fit."""

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.services.personal_liking import CrowdTable, fit_personal_liking

NOW = datetime(2026, 10, 10, tzinfo=timezone.utc)
CROWD = CrowdTable({"Iso E Super": {"value": 0.8, "family": "woody"}})


def rated(guess, y):
    """A bottle rating whose y = (liking - 5.5) / 4.5 equals the given value."""

    return SimpleNamespace(liking=y * 4.5 + 5.5, material_shares={"Hedione": 1.0}, crowd_guess=guess)


def guesses(count):
    return [(-1 + 2 * i / (count - 1)) for i in range(count)]


def fit(ratings, **kwargs):
    return fit_personal_liking(ratings, [], CROWD, now=NOW, **kwargs)


def test_nine_ratings_are_too_few_but_still_report_r():
    result = fit([rated(g, g) for g in guesses(9)])
    assert result["crowd_check"]["verdict"] == "too_few"
    assert result["crowd_check"]["n"] == 9
    assert result["crowd_check"]["r"] == pytest.approx(1.0)
    assert result["crowd_weight"] == 1.0


def test_ten_ratings_on_a_perfect_line_predict():
    result = fit([rated(g, g) for g in guesses(10)])
    check = result["crowd_check"]
    assert check["r"] == pytest.approx(1.0) and check["slope"] == pytest.approx(1.0)
    assert check["rmse"] == pytest.approx(0.0, abs=1e-9)
    assert check["verdict"] == "predicts"
    assert result["crowd_weight"] == pytest.approx(1.0)


def test_ten_anti_correlated_ratings_halve_the_weight():
    result = fit([rated(g, -g) for g in guesses(10)])
    assert result["crowd_check"]["slope"] == pytest.approx(-1.0)
    assert result["crowd_check"]["verdict"] == "none"
    assert result["crowd_weight"] == pytest.approx(0.5)


def test_thirty_anti_correlated_ratings_give_a_quarter():
    result = fit([rated(g, -g) for g in guesses(30)])
    assert result["crowd_weight"] == pytest.approx(0.25)


def test_constant_guesses_have_no_r_and_count_as_none():
    result = fit([rated(0.3, y) for y in guesses(10)])
    check = result["crowd_check"]
    assert check["r"] is None and check["slope"] is None
    assert check["verdict"] == "none"
    assert result["crowd_weight"] == pytest.approx(0.5)


def test_weak_correlation_verdict():
    ratings = [rated(g, 0.3 * g + (0.5 if i % 2 else -0.5)) for i, g in enumerate(guesses(12))]
    check = fit(ratings)["crowd_check"]
    assert 0.2 <= check["r"] < 0.5 and check["verdict"] == "weak"


def test_known_material_prior_is_weighted_by_the_crowd_weight():
    ratings = [rated(g, -g) for g in guesses(10)]
    ratings.append(SimpleNamespace(liking=8, material_shares={"Iso E Super": 1.0}, crowd_guess=None))
    result = fit(ratings)
    w = result["crowd_weight"]
    assert w < 1
    row = result["materials"]["Iso E Super"]
    assert row["crowd"] == 0.8
    assert row["prior"] == pytest.approx(w * 0.8)


def test_empty_fit_still_writes_the_check():
    result = fit([])
    assert result["crowd_check"] == {"n": 0, "r": None, "slope": None, "rmse": None, "verdict": "too_few"}
    assert result["crowd_weight"] == 1.0
