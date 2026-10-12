"""The personal liking fit with single-material (blotter) ratings."""

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.services.personal_liking import CrowdTable, fit_personal_liking

NOW = datetime(2026, 10, 10, tzinfo=timezone.utc)
CROWD = CrowdTable(
    {
        "Iso E Super": {"value": 0.9, "family": "woody"},
        "Hedione": {"value": 0.1, "family": "floral"},
    }
)


def mat(material, liking):
    return SimpleNamespace(material=material, liking=liking)


def formula(liking, shares, guess=None):
    return SimpleNamespace(liking=liking, material_shares=shares, crowd_guess=guess)


def test_one_known_crowd_rating_gives_evidence_one_and_no_deviation_from_its_own_offset():
    # y = (8 - 5.5) / 4.5 = 0.5556; b = y - 0.9 is this same gap, so the residual is 0.
    fit = fit_personal_liking([], [], CROWD, material_ratings=[mat("Iso E Super", 8)], now=NOW)
    row = fit["materials"]["Iso E Super"]
    assert row["evidence"] == 1.0 and row["direct_n"] == 1 and row["n"] == 1
    assert row["deviation"] == pytest.approx(0.0)
    assert row["personal"] == pytest.approx(0.9)
    assert fit["material_ratings_used"] == 1
    assert fit["schema"] == "personal_liking_v1"


def test_two_known_materials_get_half_their_residual():
    # y: 10 -> 1.0, 2 -> -0.7778; gaps 0.1 and -0.8778; b = -0.3889.
    # residuals: 1.0 - 0.9 + 0.3889 = 0.4889 and -0.7778 - 0.1 + 0.3889 = -0.4889; halved.
    fit = fit_personal_liking(
        [], [], CROWD, material_ratings=[mat("Iso E Super", 10), mat("Hedione", 2)], now=NOW
    )
    assert fit["offset_b"] == pytest.approx(-0.38889, abs=1e-4)
    iso, hed = fit["materials"]["Iso E Super"], fit["materials"]["Hedione"]
    assert iso["deviation"] == pytest.approx(0.24444, abs=1e-4)
    assert hed["deviation"] == pytest.approx(-0.24444, abs=1e-4)
    assert iso["personal"] == pytest.approx(1.0)  # 0.9 + 0.2444 clipped to 1
    assert hed["personal"] == pytest.approx(-0.14444, abs=1e-4)


def test_unknown_material_uses_the_typical_prior():
    # typical = median(0.9, 0.1) = 0.5; b = 0 (no known gap); y = 0.5556.
    fit = fit_personal_liking([], [], CROWD, material_ratings=[mat("Mystery Resin", 8)], now=NOW)
    row = fit["materials"]["Mystery Resin"]
    assert row["prior_source"] == "typical" and row["crowd"] is None
    assert row["prior"] == pytest.approx(0.5)
    assert row["deviation"] == pytest.approx((0.55556 - 0.5) / 2, abs=1e-4)
    assert row["direct_n"] == 1


def test_direct_ratings_list_the_material_as_liked_or_disliked():
    fit = fit_personal_liking(
        [], [], CROWD, material_ratings=[mat("Iso E Super", 10), mat("Hedione", 2)], now=NOW
    )
    assert fit["liked"] == ["Iso E Super"]
    assert fit["disliked"] == ["Hedione"]


def test_formula_only_fit_is_unchanged_when_there_are_no_material_ratings():
    ratings = [formula(9, {"Iso E Super": 0.5, "Hedione": 0.25}, 0.4), formula(3, {"Hedione": 0.5})]
    plain = fit_personal_liking(ratings, [], CROWD, now=NOW)
    explicit = fit_personal_liking(ratings, [], CROWD, material_ratings=[], now=NOW)
    assert plain == explicit
    assert plain["material_ratings_used"] == 0
    assert all(row["direct_n"] == 0 for row in plain["materials"].values())
    assert plain["ratings_used"] == 2


def test_material_rating_and_formula_rating_share_one_offset():
    ratings = [formula(9, {"Hedione": 0.5}, 0.4)]  # y = 0.7778, gap 0.3778
    fit = fit_personal_liking(
        ratings, [], CROWD, material_ratings=[mat("Iso E Super", 8)], now=NOW
    )  # gap 0.5556 - 0.9 = -0.3444
    assert fit["offset_b"] == pytest.approx((0.37778 - 0.34444) / 2, abs=1e-4)
