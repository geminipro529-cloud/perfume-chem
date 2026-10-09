"""Crowd-guess pleasantness: strength-weighted per window, no contrast penalty."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from engine.formulation_intelligence import pleasantness as pl
from engine.formulation_intelligence import pleasantness_table as pt
from engine.hedonic_model import score_hedonic

FAKE_VALUES = {"Sweet": 0.8, "Sour": -0.4, "Even A": 0.5, "Even B": 0.5, "High": 0.9, "Low": 0.1}


@pytest.fixture
def fake_table(monkeypatch):
    def fake(name, strength_share=None):
        if name not in FAKE_VALUES:
            return None
        return pt.CrowdValue(name, FAKE_VALUES[name], "test", "hand", False, None)

    monkeypatch.setattr(pl, "crowd_pleasantness", fake)
    monkeypatch.setattr(pt, "crowd_pleasantness", fake)  # score_hedonic reads it from the table module
    return fake


def _material(name, intensity, oav=10.0):
    return SimpleNamespace(name=name, oav=oav, intensity=intensity)


def _frames(*windows):
    labels = (("opening", 0.0), ("top", 300.0), ("heart", 1800.0), ("late_heart", 7200.0), ("drydown", 14400.0))
    frames = tuple(
        SimpleNamespace(label=label, t_seconds=t, state=SimpleNamespace(materials=tuple(materials)))
        for (label, t), materials in zip(labels, windows)
    )
    return (None, frames)


def _score(*windows):
    return pl.score_pleasantness([], simulation=_frames(*windows))


def test_window_weights_are_modelled_strength_not_equal(fake_table):
    result = _score([_material("Sweet", 3.0), _material("Sour", 1.0)])
    window = result["windows"][0]
    assert window["strength_shares"] == {"Sweet": 0.75, "Sour": 0.25}
    expected = 0.75 * 0.8 + 0.25 * -0.4
    assert window["pleasantness"] == pytest.approx(expected, abs=1e-3)
    assert window["score_0_100"] == round((expected + 1) * 50)
    assert window["coverage"] == 1.0
    assert window["status"] == "CROWD_GUESS"
    assert [c["material"] for c in window["contributors"]] == ["Sweet", "Sour"]


def test_unknown_materials_are_excluded_not_neutral_and_cut_coverage(fake_table):
    result = _score([_material("Sweet", 1.0), _material("Sour", 1.0), _material("Mystery", 2.0)])
    window = result["windows"][0]
    assert window["pleasantness"] == pytest.approx((0.8 - 0.4) / 2, abs=1e-3)  # not (0.2 + 0) / ...
    assert window["coverage"] == 0.5
    assert window["unrated"] == ["Mystery"]
    assert window["strength_shares"]["Mystery"] == 0.5
    low = _score([_material("Sweet", 1.0), _material("Mystery", 3.0)])["windows"][0]
    assert low["status"] == "LOW_COVERAGE"
    assert low["pleasantness"] == pytest.approx(0.8)


def test_only_detectable_materials_carry_weight(fake_table):
    window = _score([_material("Sweet", 1.0), _material("Sour", 5.0, oav=0.9)])["windows"][0]
    assert window["strength_shares"] == {"Sweet": 1.0}
    assert window["pleasantness"] == pytest.approx(0.8)
    empty = _score([_material("Sweet", 1.0, oav=0.2)])
    assert empty["windows"][0]["status"] == "NO_DETECTABLE_MATERIALS"
    assert empty["windows"][0]["pleasantness"] is None
    assert empty["state"] == "NOT_ESTABLISHED"
    assert empty["overall"] is None


def test_contrast_is_not_penalised(fake_table):
    even = _score([_material("Even A", 1.0), _material("Even B", 1.0)])["windows"][0]
    spread = _score([_material("High", 1.0), _material("Low", 1.0)])["windows"][0]
    assert even["pleasantness"] == spread["pleasantness"] == pytest.approx(0.5)
    assert even["score_0_100"] == spread["score_0_100"] == 75


def test_a_strong_indole_share_lowers_the_window():
    hedione = pt.crowd_pleasantness("Hedione")
    assert hedione is not None and not hedione.dose_dependent
    trace = _score([_material("Hedione", 9.0), _material("Indole", 1.0)])["windows"][0]
    strong = _score([_material("Hedione", 6.0), _material("Indole", 4.0)])["windows"][0]
    assert strong["pleasantness"] < trace["pleasantness"]
    adjusted = {item["material"]: item for item in strong["dose_adjusted"]}
    assert "Indole" in adjusted and "Indole" not in {i["material"] for i in trace["dose_adjusted"]}
    assert set(adjusted["Indole"]) == {"material", "base", "used", "dose_source"}
    assert adjusted["Indole"]["used"] <= -0.4
    assert adjusted["Indole"]["dose_source"] == "heuristic_unmeasured"
    indole = next(c for c in strong["contributors"] if c["material"] == "Indole")
    assert indole["value"] <= -0.4
    base = pt.crowd_pleasantness("Indole").value
    assert strong["pleasantness"] < 0.6 * hedione.value + 0.4 * base  # below the share-blind mean


def test_dose_adjusted_lists_only_material_changes_of_005_or_more():
    keller = pt.load_crowd_table()["materials"]["Vanillin"]
    assert keller["dose_source"] == "keller"
    base = pt.crowd_pleasantness("Vanillin").value
    near = pt.crowd_pleasantness("Vanillin", strength_share=0.17).value
    assert abs(near - base) < 0.05  # premise: a Keller material at 0.17 is within tolerance
    window = _score([_material("Vanillin", 83.0), _material("Indole", 30.0), _material("Hedione", 53.0)])
    mix = pl._score_mix({"Vanillin": 0.17, "Indole": 0.3, "Hedione": 0.53})
    listed = [item["material"] for item in mix["dose_adjusted"]]
    assert "Vanillin" not in listed
    assert "Indole" in listed
    assert window["windows"][0]["dose_adjusted"] is not None


def test_top_level_labels_overall_and_rating_windows(fake_table):
    result = _score(
        [_material("Sweet", 1.0)],
        [_material("Sweet", 1.0)],
        [_material("Sweet", 1.0), _material("Sour", 1.0)],
        [_material("Sour", 1.0)],
        [_material("Mystery", 1.0)],
    )
    assert result["state"] == "CROWD_GUESS"
    assert result["optimization_authority"] is False
    assert result["label"].startswith("Crowd guess:") and "Not a measurement" in result["label"]
    assert "Ma, Tang, Thomas-Danguin & Xu (2020)" in result["method"]
    assert "a power law of each material's odour activity value (OAV)" in result["method"]
    assert "a model, not measured intensity; materials below OAV 1 are left out" in result["method"]
    assert "only as that detection floor" not in result["method"]
    assert result["table_schema"] == "pleasantness_crowd_v1"
    assert [w["window"] for w in result["windows"]] == ["opening", "top", "heart", "late_heart", "drydown"]
    assert result["windows"][4]["status"] == "NO_RATED_MATERIALS"
    # Mean of the four CROWD_GUESS windows: 0.8, 0.8, 0.2, -0.4.
    assert result["overall"] == pytest.approx(0.35, abs=1e-3)
    one_hour = result["rating_windows"]["1h"]
    assert one_hour["material_shares"] == {"Sour": 0.75, "Sweet": 0.25}
    assert one_hour["crowd_guess"] == pytest.approx(0.25 * 0.8 + 0.75 * -0.4, abs=1e-3)
    assert result["rating_windows"]["opening"]["material_shares"] == {"Sweet": 1.0}
    assert result["rating_windows"]["4h"]["crowd_guess"] is None


def test_legacy_score_no_longer_penalises_contrast(fake_table):
    even = score_hedonic({"Even A": 100.0, "Even B": 100.0})
    spread = score_hedonic({"High": 100.0, "Low": 100.0})
    assert spread.hedonic_contrast > 0.3
    assert even.score == spread.score == 75.0
    assert not any("⚠" in line for line in spread.diagnostics)
    with_unknown = score_hedonic({"Even A": 100.0, "Mystery": 100.0})
    assert with_unknown.score == 75.0  # unknown excluded, not averaged in as neutral
    assert with_unknown.coverage_status == "PARTIAL_TABLE_COVERAGE"
    assert with_unknown.unrated_materials == ["Mystery"]


def test_design_report_carries_the_estimate_on_primary_and_variants():
    from engine.formulation_intelligence.formula_design_runtime import design_formula

    report = design_formula(idea="rose chypre with oakmoss and patchouli")
    estimate = report["scientific_overlays"]["pleasantness"]
    assert estimate["state"] in ("CROWD_GUESS", "LOW_COVERAGE")
    assert estimate["optimization_authority"] is False
    assert [w["window"] for w in estimate["windows"]] == ["opening", "top", "heart", "late_heart", "drydown"]
    for key in ("opening", "1h", "4h"):
        shares = estimate["rating_windows"][key]["material_shares"]
        assert sum(shares.values()) == pytest.approx(1.0, abs=0.001)
    assert report["design_variants"]
    for variant in report["design_variants"]:
        assert variant["scientific_overlays"]["pleasantness"]["schema"] == "pleasantness_estimate_v1"
    assert report["scientific_overlays"]["personal_liking"] == {"state": "NOT_TESTED"}
    assert report["pleasantness"] is None  # the top-level liking-style field stays unset
