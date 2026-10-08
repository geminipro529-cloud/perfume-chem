"""Suggestions name, and are scored with, the exact owned stock Kenny would pour."""

from __future__ import annotations

import pytest

import engine.formula_recommendations as fr
from engine.formula_recommendations import (
    format_recommendations,
    generate_recommendations,
    load_inventory,
)
from engine.optimizer.scoring import FormulaVector

_BASELINE = {
    "longevity": 10.0,
    "sillage": 90.0,
    "texture": 90.0,
    "synergy": 90.0,
    "hedonic": 90.0,
    "geometric_total": 50.0,
}


class _RecordingScorer:
    """Accepts every candidate and records the formula each one is scored with."""

    def __init__(self) -> None:
        self.scored: list[FormulaVector] = []

    def identity_signature(self, fv, scores):
        return {}

    def score_axis(self, fv, axis):
        self.scored.append(fv)
        return 99.0

    def score(self, fv):
        return {**_BASELINE, "longevity": 99.0, "geometric_total": 60.0}

    def identity_preservation(self, *args, **kwargs):
        return {"score": 100.0}


def _stock(name: str, dilution: float) -> dict:
    return {"name": name, "dilution": dilution, "category": "test", "catalog": None}


def _recommend(
    monkeypatch,
    inventory,
    dose,
    *,
    mode="pre_mix",
    batch_volume_ml=None,
    candidate="beta ionone",
    fv=None,
):
    monkeypatch.setattr(fr, "AXIS_CANDIDATES", {"longevity": [(candidate, dose, "test")]})
    monkeypatch.setattr(fr, "_creative_profile_candidates", lambda **_: [])
    monkeypatch.setattr(fr.GapDetector, "suggest_synergistic_fillers", lambda self, names: [])
    scorer = _RecordingScorer()
    if fv is None:
        fv = FormulaVector(ingredients={"Hedione": 100.0}, dilutions={"Hedione": 1.0})
    recs = generate_recommendations(
        fv,
        dict(_BASELINE),
        inventory=inventory,
        mode=mode,
        batch_volume_ml=batch_volume_ml,
        scorer=scorer,
        include_unvalidated_advisory=True,
    )
    assert len(recs) == 1 and len(scorer.scored) == 1
    return recs[0], scorer.scored[0]


THREE_STOCKS = [_stock("Beta Ionone", 1.0), _stock("Beta Ionone", 0.1), _stock("Beta Ionone", 0.001)]


def test_load_inventory_keeps_every_owned_stock():
    inventory = load_inventory()
    for name in ("Beta Ionone", "Ethyl 2-Methylbutyrate", "Geosmin"):
        strengths = sorted(item["dilution"] for item in inventory if item["name"] == name)
        assert len(strengths) > 1, (name, strengths)
    beta = {item["dilution"] for item in inventory if item["name"] == "Beta Ionone"}
    assert {1.0, 0.001} <= beta


def test_small_active_dose_picks_the_strongest_stock_that_pipettes_20_ul(monkeypatch):
    # 0.1% of a 10 mL concentrate neat is 10 µL; the same active as the 10% stock is 100 µL.
    rec, scored = _recommend(monkeypatch, THREE_STOCKS, 0.1)
    assert rec.material == "Beta Ionone 10%"
    assert rec.dose_pct == pytest.approx(1.0)
    assert scored.dilutions["Beta Ionone"] == 0.1
    assert scored.ingredients["Beta Ionone"] == pytest.approx(1.0 * 100.0 / 101.0)
    assert scored.ingredients["Beta Ionone"] * 0.1 == pytest.approx(0.1 * 100.0 / 101.0)


def test_tiny_active_dose_picks_the_dilute_stock(monkeypatch):
    stocks = [_stock("Beta Ionone", 1.0), _stock("Beta Ionone", 0.001)]
    rec, scored = _recommend(monkeypatch, stocks, 0.004)
    assert rec.material == "Beta Ionone 0.1%"
    assert rec.dose_pct == pytest.approx(4.0)
    assert scored.dilutions["Beta Ionone"] == 0.001
    assert scored.ingredients["Beta Ionone"] == pytest.approx(4.0 * 100.0 / 104.0)


def test_large_active_dose_keeps_the_strongest_stock(monkeypatch):
    rec, scored = _recommend(monkeypatch, list(reversed(THREE_STOCKS)), 2.0)
    assert rec.material == "Beta Ionone, neat"
    assert rec.dose_pct == pytest.approx(2.0)
    assert scored.dilutions["Beta Ionone"] == 1.0
    assert scored.ingredients["Beta Ionone"] == pytest.approx(2.0 * 100.0 / 102.0)


def test_post_mix_uses_the_batch_volume_and_names_the_poured_stock(monkeypatch):
    # 1.0 x 0.35 = 0.35% of a 5 mL bottle neat is 17.5 µL; the 10% stock is 175 µL.
    rec, scored = _recommend(monkeypatch, THREE_STOCKS, 1.0, mode="post_mix", batch_volume_ml=5.0)
    assert rec.material == "Beta Ionone 10%"
    assert rec.dose_pct == pytest.approx(3.5)
    assert rec.dose_ul == 175
    assert scored.dilutions["Beta Ionone"] == 0.1


def test_no_stock_reaching_20_ul_falls_back_to_the_most_dilute():
    stocks = [_stock("Beta Ionone", 1.0), _stock("Beta Ionone", 0.5)]
    chosen, raw_pct = fr._choose_stock(stocks[0], stocks, 0.5, 1000.0)
    assert chosen["dilution"] == 0.5
    assert raw_pct == pytest.approx(1.0)


def test_single_stock_material_scores_exactly_as_before(monkeypatch):
    rec, scored = _recommend(monkeypatch, [_stock("Beta Ionone", 0.01)], 0.04)
    scale = 100.0 / (100.0 + 0.04)  # the renormalization the candidate loop applies
    assert scored.ingredients == {"Hedione": 100.0 * scale, "Beta Ionone": 0.04 * scale}
    assert scored.dilutions == {"Hedione": 1.0, "Beta Ionone": 0.01}
    assert rec.material == "Beta Ionone 1%"


def test_display_shows_strength_and_small_doses(monkeypatch):
    rec, _ = _recommend(monkeypatch, [_stock("Beta Ionone", 0.01)], 0.04)
    assert rec.dose_pct == pytest.approx(0.04)
    assert isinstance(rec.dose_pct, float)
    text = format_recommendations("Test", [rec], dict(_BASELINE))
    assert "0.04" in text
    assert " 0.0 " not in text

    neat, _ = _recommend(monkeypatch, [_stock("Beta Ionone", 1.0)], 2.0)
    assert neat.material == "Beta Ionone, neat"
    dilute, _ = _recommend(monkeypatch, [_stock("Beta Ionone", 0.001)], 2.0)
    assert dilute.material == "Beta Ionone 0.1%"


def test_dilute_stock_that_would_flood_the_formula_is_not_chosen():
    # Neat gives 5 µL; the 0.1% stock would need 5,000 µL, half the concentrate.
    stocks = [_stock("Beta Ionone", 1.0), _stock("Beta Ionone", 0.001)]
    chosen, raw_pct = fr._choose_stock(stocks[0], stocks, 0.05, 10000.0)
    assert chosen["dilution"] == 1.0
    assert raw_pct == pytest.approx(0.05)


def test_every_stock_over_the_cap_uses_the_strongest():
    # Neat is 200 µL and the 10% stock 2,000 µL; both exceed 10% of a 1 mL basis.
    stocks = [_stock("Beta Ionone", 0.1), _stock("Beta Ionone", 1.0)]
    chosen, raw_pct = fr._choose_stock(stocks[0], stocks, 20.0, 1000.0)
    assert chosen["dilution"] == 1.0
    assert raw_pct == pytest.approx(20.0)


_INVENTORY_TEXT = """\
--- FLORAL ---
- Helional 10% v/v in ethanol  # first row, as in the real inventory
- Osmanthus Absolute (volume grade)  # lower-cost grade
- Osmanthus Absolute (10% in DPG)
- Rose Oxide (1%)
- Rose Oxide (10%)
- Helional
--- WOODY ---
- Beta Ionone
- Beta Ionone (0.1% in TEC)
"""


@pytest.fixture
def parsed_inventory(tmp_path, monkeypatch):
    path = tmp_path / "inventory.txt"
    path.write_text(_INVENTORY_TEXT, encoding="utf-8")
    monkeypatch.setattr(fr, "_INVENTORY_PATH", path)
    return load_inventory()


def test_stocks_written_without_parentheses_form_one_group(parsed_inventory):
    first = fr._material_in_inventory("helional", parsed_inventory)
    assert first["name"] == "Helional 10% v/v in ethanol"
    assert [s["dilution"] for s in fr._owned_stocks(first, parsed_inventory)] == [1.0, 0.1]


def test_helional_dose_is_kept_in_the_neat_stock(monkeypatch, parsed_inventory):
    # 1.5% of a 10 mL concentrate neat is 150 µL; the 10% stock would be 10x too weak.
    rec, scored = _recommend(monkeypatch, parsed_inventory, 1.5, candidate="helional")
    assert rec.material == "Helional, neat"
    assert scored.dilutions["Helional 10% v/v in ethanol"] == 1.0


def test_grades_stay_separate_and_the_label_keeps_the_grade(monkeypatch, parsed_inventory):
    volume, premium = parsed_inventory[1], parsed_inventory[2]
    assert volume["identity_name"] == "Osmanthus Absolute (volume grade)"
    assert premium["identity_name"] == "Osmanthus Absolute"
    assert fr._owned_stocks(volume, parsed_inventory) == [volume]
    assert fr._owned_stocks(premium, parsed_inventory) == [premium]
    # 0.05% neat is 5 µL; pooling would switch to the premium 10% stock (50 µL).
    rec, scored = _recommend(monkeypatch, parsed_inventory, 0.05, candidate="osmanthus absolute")
    assert rec.material == "Osmanthus Absolute (volume grade), neat"
    assert scored.dilutions["Osmanthus Absolute"] == 1.0


def test_labels_name_real_name_strength_basis_and_solvent_once(parsed_inventory):
    labels = {fr._owned_stock_label(stock) for stock in parsed_inventory}
    assert labels == {
        "Helional 10% v/v in ethanol",
        "Helional, neat",
        "Osmanthus Absolute (volume grade), neat",
        "Osmanthus Absolute 10% in DPG",
        "Rose Oxide 1%",
        "Rose Oxide 10%",
        "Beta Ionone, neat",
        "Beta Ionone 0.1% in TEC",
    }
    for label in labels:
        assert label.count("%") + label.count("neat") == 1, label


def test_existing_row_without_a_dilution_is_shown_neat(monkeypatch, parsed_inventory):
    fv = FormulaVector(
        ingredients={"Hedione": 90.0, "Rose Oxide": 10.0}, dilutions={"Hedione": 1.0}
    )
    rec, scored = _recommend(monkeypatch, parsed_inventory, 0.5, candidate="rose oxide", fv=fv)
    assert "Rose Oxide" not in scored.dilutions  # scored neat by FormulaVector.effective_pct
    assert rec.material == "Rose Oxide, neat"

    fv.dilutions["Rose Oxide"] = 0.1
    rec, _ = _recommend(monkeypatch, parsed_inventory, 0.5, candidate="rose oxide", fv=fv)
    assert rec.material == "Rose Oxide 10%"


def test_warnings_still_key_on_the_material_name(monkeypatch, parsed_inventory):
    rec, _ = _recommend(monkeypatch, parsed_inventory, 2.0)
    assert rec.material == "Beta Ionone, neat"
    assert any("ANOSMIA" in warning and "Beta Ionone" in warning for warning in rec.warnings)
