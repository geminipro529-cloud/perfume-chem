"""Crowd pleasantness prior: one -1..+1 table; zeros are unknown, not neutral."""

from __future__ import annotations

import json

import pytest

from engine import ingredient_intelligence as ii
from engine.formulation_intelligence import pleasantness_table as pt

HAND_DERIVED = ("hedonic_model_table", "profile_override", "profile_direct")


@pytest.fixture(scope="module")
def table() -> dict:
    return pt.load_crowd_table()


def test_header_labels_table_as_a_crowd_guess_without_oav(table):
    assert table["schema"] == "pleasantness_crowd_v1"
    assert "not a measurement" in table["label"]
    assert "doi:10.1186/s12868-016-0287-2" in table["source_citation"]
    assert sum(table["counts"].values()) == len(table["materials"])
    keys: list[str] = []

    def walk(node):
        if isinstance(node, dict):
            keys.extend(k.casefold() for k in node)
            for child in node.values():
                walk(child)

    walk({k: v for k, v in table.items() if k != "materials"})
    for entry in table["materials"].values():  # field names, not material names
        walk(entry)
    assert not [k for k in keys if "oav" in k]


def test_all_values_on_one_scale_and_zero_hand_values_are_unknown(table):
    for name, entry in table["materials"].items():
        if entry["value"] is None:
            assert entry["source"] == "unknown", name
            assert pt.crowd_pleasantness(name) is None
            continue
        assert -1.0 <= entry["value"] <= 1.0, name
        for point in (entry["dose_points"] or {}).values():
            assert -1.0 <= point <= 1.0, name
        if entry["source"] in HAND_DERIVED:
            assert entry["raw_value"] != 0, name
    # Profiles whose legacy override is exactly 0 must not appear as known neutral.
    zero_overrides = [
        n for n, v in ii._HEDONIC_OVERRIDES.items()
        if v == 0 and n in ii._PROFILES
        and ii._PROFILES[n]["evidence"]["hedonic"]["status"] == "HEURISTIC_OVERRIDE"
    ]
    assert zero_overrides
    for name in zero_overrides:
        assert table["materials"][name]["source"] in ("unknown", "keller_vosshall_2016"), name


def test_hand_values_follow_the_stored_calibration(table):
    cal = table["calibration"]
    assert cal["applied"] is True
    a, b = cal["pooled"]["a"], cal["pooled"]["b"]
    divisor = {s: pt.RAW_SCALES[s][1] for s in HAND_DERIVED}
    for name, entry in table["materials"].items():
        if entry["source"] in HAND_DERIVED:
            expected = max(-1.0, min(1.0, a + b * entry["raw_value"] / divisor[entry["source"]]))
            assert entry["value"] == pytest.approx(expected, abs=1e-4), name


def test_character_word_heuristic_values_are_unknown(table):
    """They ran r = -0.22 against the panel, so they are kept for audit only."""
    assert table["counts"].get("character_heuristic") is None
    assert "character_heuristic" not in table["calibration"]["applied_to"]
    heuristic = [n for n, e in table["materials"].items() if e.get("reason", "").startswith("character-word")]
    assert len(heuristic) == 91
    for name in heuristic:
        entry = table["materials"][name]
        assert entry["value"] is None and entry["source"] == "unknown", name
        assert entry["raw_value"] != 0, name
        assert pt.crowd_pleasantness(name) is None
    bergamot = table["materials"]["Bergamot EO"]
    assert bergamot["reason"] == "character-word heuristic; r = -0.22 against the panel, n = 18"
    assert bergamot["raw_value"] == pytest.approx(0.24)
    assert pt.crowd_pleasantness("Bergamot EO") is None


def test_vanillin_is_panel_sourced_and_beta_ionone_drops_when_strong(table):
    vanillin = pt.crowd_pleasantness("Vanillin")
    assert vanillin.source == "keller_vosshall_2016"
    assert vanillin.confidence == "panel"
    assert vanillin.value == pytest.approx(0.70, abs=0.01)
    points = table["materials"]["Beta Ionone"]["dose_points"]
    assert table["materials"]["Beta Ionone"]["source"] == "keller_vosshall_2016"
    assert points["strong"] < points["weak"]
    assert pt.crowd_pleasantness("beta-Ionone", 0.3).value < pt.crowd_pleasantness("beta-Ionone", 0.05).value


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Indole (10%)", "Indole"),  # inventory.txt line
        ("Eugenol 10% in DPG", "Eugenol"),
        ("Eugenol (10% in DPG)", "Eugenol"),
        ("eugenol", "Eugenol"),
        ("Vetiver EO (India)", "Vetiver EO (India)"),  # identity parenthetical kept
    ],
)
def test_inventory_style_names_resolve(raw, expected):
    value = pt.crowd_pleasantness(raw)
    assert value is not None
    assert value.material == expected


def test_inventory_line_of_a_now_unknown_material_still_resolves():
    # Cade's only value was a character-word heuristic, so it resolves but has no value.
    assert pt._resolve("Cade Oil Rectified (1% in DPG)") == "Cade Oil Rectified"  # inventory.txt line
    assert pt.crowd_pleasantness("Cade Oil Rectified (1% in DPG)") is None


def test_unknown_name_returns_none():
    assert pt.crowd_pleasantness("Not A Material 10% in DPG") is None


def test_flip_material_turns_unpleasant_when_strong(table):
    entry = table["materials"]["Indole"]
    assert entry["dose_source"] == "heuristic_unmeasured"
    strong = pt.crowd_pleasantness("Indole", strength_share=0.3)
    weak = pt.crowd_pleasantness("Indole", strength_share=0.05)
    assert strong.dose_dependent
    assert strong.value <= -0.4
    assert weak.value == pytest.approx(entry["value"])


def test_dose_rule_is_linear_between_thresholds(table):
    points = table["materials"]["Vanillin"]["dose_points"]
    mid = pt.crowd_pleasantness("Vanillin", strength_share=0.175).value
    assert mid == pytest.approx((points["weak"] + points["strong"]) / 2)
    assert pt.crowd_pleasantness("Vanillin", 0.10).value == pytest.approx(points["weak"])
    assert pt.crowd_pleasantness("Vanillin", 0.25).value == pytest.approx(points["strong"])
    # No dose points: the share is ignored.
    hedione = pt.crowd_pleasantness("Hedione", 0.9)
    assert not hedione.dose_dependent
    assert hedione.value == table["materials"]["Hedione"]["value"]


def test_build_matches_panel_by_cas_and_orders_dilutions(tmp_path):
    rows = [
        {"stimulus": "1", "cid": "1183", "name": "vanillin", "cas": "121-33-5",
         "concentration": "0.1", "ratio": "1/10", "solvent": "paraffin oil",
         "pleasantness_mean_0_100": 90.0, "intensity_mean_0_100": 70.0, "n_pleasant": 50},
        {"stimulus": "2", "cid": "1183", "name": "vanillin", "cas": "121-33-5",
         "concentration": "0.001", "ratio": "1/1000", "solvent": "paraffin oil",
         "pleasantness_mean_0_100": 60.0, "intensity_mean_0_100": 40.0, "n_pleasant": 50},
        # Name-less row carrying its CAS in cid (quirk of the source export).
        {"stimulus": "3", "cid": "120-72-9", "concentration": "0.01", "ratio": "1/100",
         "solvent": "paraffin oil", "pleasantness_mean_0_100": 20.0,
         "intensity_mean_0_100": 60.0, "n_pleasant": 50},
    ]
    path = tmp_path / "keller.json"
    path.write_text(json.dumps(rows), encoding="utf-8")
    built = pt.build_crowd_table(str(path))
    vanillin = built["materials"]["Vanillin"]
    assert vanillin["source"] == "keller_vosshall_2016"
    assert vanillin["keller"]["match_by"] == "cas"
    assert vanillin["dose_points"] == {"weak": 0.2, "strong": 0.8}
    assert vanillin["value"] == pytest.approx(0.5)
    assert built["calibration"]["applied"] is False  # too few panel pairs
    for entry in built["materials"].values():
        if entry["source"] in HAND_DERIVED:
            assert entry["raw_value"] != 0
