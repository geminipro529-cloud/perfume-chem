"""DHI-11 V3.1: V3 Smooth rebuilt on the stocks Kenny owns on 2026-10-08."""
from __future__ import annotations

from pathlib import Path

import pytest

from engine.pipeline.formula_state import build_formula_state
from engine.pipeline.preflight import _dilution_consistency_check
from scripts.verify_formula_workflow import parse_formula_markdown

ROOT = Path(__file__).resolve().parents[1]
FORMULA_PATH = ROOT / "formulas" / "DHI-11_Velours_d_Iris_05443A_30mL_20pct_V3_1_Current_Stock.md"
PARENT_PATH = ROOT / "formulas" / "DHI-11_Velours_d_Iris_05443A_30mL_20pct_V3_Smooth.md"

# Rows that change name or raw volume against V3 Smooth; every other row is identical.
SWAPS = {
    "Ambrettolide": (1600.0, 160.0),  # 10% w/w in DPG -> neat (Kenny 2026-10-08), same nominal active
    "Vetiver EO (India)": (140.0, None),
    "Vetiver EO (Haiti)": (None, 140.0),
    "Lavender EO High Altitude": (110.0, None),
    "Lavender EO (BONTAUX SAS)": (None, 110.0),
}
STRUCTURAL_ONLY = {
    "Benzyl Benzoate",
    "Benzyl Salicylate",
    "Carrot Seed EO",
    "Dihydro Beta Ionone",
    "Irotyl",
    "Sandalore",
    "Ultralia",
}


@pytest.fixture(scope="module")
def formula():
    parsed = parse_formula_markdown(FORMULA_PATH)
    assert len(parsed) == 1
    return parsed[0]


def test_v31_keeps_v3_smooth_doses_except_the_named_stock_swaps(formula):
    parent = parse_formula_markdown(PARENT_PATH)[0]["ingredients_ul"]
    child = formula["ingredients_ul"]
    assert len(child) == 30
    assert sum(child.values()) == pytest.approx(4560.0)
    assert formula["family_archetype"] == "iris_coumarin_amber.dhi2011"
    for name, (before, after) in SWAPS.items():
        assert parent.get(name) == before, name
        assert child.get(name) == after, name
    unchanged = set(parent) - set(SWAPS)
    assert {name: child[name] for name in unchanged} == {name: parent[name] for name in unchanged}
    active = sum(amount * formula["dilutions"][name] for name, amount in child.items())
    assert active == pytest.approx(4010.05)


def test_v31_only_preflight_blocker_is_the_mimosa_receipt_hold(formula):
    result = _dilution_consistency_check(formula)
    issues = {item["material"]: item["reason"] for item in result.data["issues"]}
    assert issues == {"Mimosa Absolute": "inventory_stock_non_executable"}
    assert len(result.data["matched_stocks"]) == 29


def test_v31_recognizers_still_model_at_oav_one_or_more(formula):
    state = build_formula_state(
        formula["ingredients_ul"],
        formula["dilutions"],
        stock_specs=formula["stock_specs"],
        batch_volume_ml=30.0,
        temperature_K=305.0,
        matrix_moles=formula["matrix_moles"],
        matrix_mass_g=formula["matrix_mass_g"],
        matrix_source=formula["matrix_source"],
    )
    rows = {material.name: material for material in state.materials}
    recognizers = set(formula["ingredients_ul"]) - STRUCTURAL_ONLY
    low = {name: rows[name].oav for name in recognizers if (rows[name].oav or 0.0) < 1.0}
    assert low == {}
