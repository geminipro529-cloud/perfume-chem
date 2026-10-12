"""Unit tests for engine.formulation_intelligence.yardstick (scorecard floors, scores, duel)."""
from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from engine.formulation_intelligence import yardstick as ys

ROOT = Path(__file__).resolve().parents[2]
R7 = ROOT / "formulas" / "Lavande_Ambre_Profond_R7_Ambrox_30mL_Parfum.md"

BRIEF = {
    "id": "lavender_neroli",
    "named_notes": [
        {"name": "lavender", "window": "opening", "materials": ["lavender", "linalool"]},
        {"name": "musk", "window": "drydown", "materials": ["ethylene brassylate"]},
    ],
}


def _row(material: str, amount: str, fraction: str = "1", unit: str = "uL", **extra) -> dict:
    return {"material": material, "amount": amount, "unit": unit, "active_fraction": fraction,
            **extra}


def _formula(neroli_ul: str = "10", extra_rows: tuple = (), parent: dict | None = None) -> dict:
    rows = [
        _row("Lavender EO (BONTAUX SAS)", "300", tier="top"),
        _row("Linalool", "100", tier="top"),
        _row("Hedione", "200", tier="heart"),
        _row("Iso E Super", "200", tier="base"),
        _row("Coumarin", "300", "0.1", fraction_basis="mass_fraction", carrier="DPG", tier="base"),
        _row("Ethylene Brassylate", "100", tier="base"),
        _row("Neroli EO", neroli_ul, tier="heart"),
        *extra_rows,
    ]
    return {"name": "test", "batch_volume_ml": 30.0, "rows": rows, "parent": parent}


@pytest.fixture(scope="module")
def base_card() -> dict:
    return ys.score_formula(_formula(), BRIEF)


def test_ten_ul_row_passes_pour_floor(base_card):
    assert base_card["floors"]["F5_pours"]["status"] == "PASS"


def test_nine_ul_row_fails_pour_floor_and_names_weaker_stock():
    card = ys.score_formula(_formula(neroli_ul="9"), BRIEF)
    f5 = card["floors"]["F5_pours"]
    assert f5["status"] == "FAIL"
    assert "Neroli EO 9 uL" in f5["detail"]
    assert "10%" in f5["detail"]  # owned Neroli EO 10% makes 9 uL neat a 90 uL pour
    assert card["disqualified"] is True


def test_tonalide_fails_musk_floor():
    card = ys.score_formula(_formula(extra_rows=(_row("Tonalide", "20"),)), BRIEF)
    assert card["floors"]["F6_musks"]["status"] == "FAIL"
    assert "Tonalide" in card["floors"]["F6_musks"]["detail"]


def test_pre_mix_guard_not_applicable_without_parent(base_card):
    assert base_card["floors"]["F3_pre_mix_guard"]["status"] == "NOT_APPLICABLE"


def test_stock_rebase_without_active_preservation_fails_pre_mix_guard():
    parent = _formula(neroli_ul="100")
    parent["rows"][-1]["active_fraction"] = "0.1"
    child = _formula(neroli_ul="100", parent=parent)  # neat now: 10x the active dose
    f3 = ys._f3_pre_mix(child, ys._gate_record(child))
    assert f3["status"] == "FAIL"
    assert "STOCK_REBASE_ACTIVE_EQUIVALENCE" in f3["codes"]
    preserved = _formula(neroli_ul="10", parent=parent)  # 10 uL neat = 100 uL of 10%
    assert ys._f3_pre_mix(preserved, ys._gate_record(preserved))["status"] == "PASS"


def test_every_floor_has_a_status_and_bottle_records_concentrate(base_card):
    assert set(base_card["floors"]) == set(ys.FLOOR_IDS)
    statuses = {"PASS", "FAIL", "HOLD", "NOT_APPLICABLE"}
    assert all(f["status"] in statuses for f in base_card["floors"].values())
    f4 = base_card["floors"]["F4_bottle"]
    assert f4["status"] == "PASS" and f4["concentrate_ul"] == 1210.0
    assert f4["concentrate_pct"] == pytest.approx(1210 / 300, abs=1e-3)


def test_renormalises_when_no_exclusions_or_family(base_card):
    parts = base_card["name_parts"]["parts"]
    assert parts["excluded_notes"] is None and parts["family_architecture"] is None
    assert base_card["name_score"] == pytest.approx(parts["named_notes"] * 100, abs=0.01)


def test_excluded_material_lowers_name_score(base_card):
    brief = {**BRIEF, "excluded_notes": [{"name": "neroli", "materials": ["neroli"]}]}
    card = ys.score_formula(_formula(), brief)
    assert card["name_parts"]["excluded_notes"][0]["matched"] == ["Neroli EO"]
    assert card["name_score"] < base_card["name_score"] or base_card["name_score"] == 0
    clean = {**BRIEF, "excluded_notes": [{"name": "rose", "materials": ["rhodinol"]}]}
    assert ys.score_formula(_formula(), clean)["name_score"] > card["name_score"]


def test_thresholds_match_release_gate_source():
    from engine.pipeline import gates

    master = inspect.getsource(gates._gate_master_perfumer)
    assert f"material_count < {ys.MATERIAL_COUNT_MIN}" in master
    assert f"material_count > {ys.MATERIAL_COUNT_MAX}" in master
    coty = inspect.getsource(gates._gate_coty_single_material_limit)
    assert f"pct > {ys.SINGLE_MATERIAL_LIMIT_PCT}" in coty


def _card(name=50.0, craft=50.0, valence=0.2, dq=False) -> dict:
    return {"formula": "x", "disqualified": dq, "name_score": name, "craft_score": craft,
            "liking": {"valence": valence}}


@pytest.mark.parametrize(
    ("engine", "reference", "verdict", "step"),
    [
        (_card(), None, "NO_REFERENCE", "1_reference"),
        (_card(dq=True), _card(dq=True), "BOTH_DISQUALIFIED", "2_floors"),
        (_card(dq=True), _card(name=0), "REFERENCE_WINS", "2_floors"),
        (_card(name=0), _card(dq=True), "ENGINE_WINS", "2_floors"),
        (_card(name=60), _card(name=55), "ENGINE_WINS", "3_name"),
        (_card(name=50, craft=90), _card(name=59), "REFERENCE_WINS", "3_name"),
        (_card(name=55, craft=40), _card(name=59, craft=45), "REFERENCE_WINS", "4_craft"),
        (_card(valence=0.30), _card(valence=0.25), "ENGINE_WINS", "5_liking"),
        (_card(valence=0.30), _card(valence=0.26), "TIE", "6_tie"),
        (_card(valence=None), _card(valence=0.9), "TIE", "6_tie"),
    ],
)
def test_duel_verdict_steps(engine, reference, verdict, step):
    v = ys.duel_verdict(engine, reference)
    assert (v["verdict"], v["deciding_step"]) == (verdict, step)


def test_json_round_trip(base_card):
    ref = _formula(neroli_ul="50")
    ref["rows"] = ref["rows"][:4] + [_row("Geraniol", "40", tier="heart")]
    near = ys.closeness(_formula(), ref)
    assert near["reference_top5_by_active_amount"][0]["material"] == "Lavender EO (BONTAUX SAS)"
    assert near["jaccard_by_tier"]["top"] == 1.0
    payload = {"card": base_card, "verdict": ys.duel_verdict(base_card, base_card),
               "closeness": near}
    assert json.loads(json.dumps(payload)) == payload
    assert payload["verdict"]["verdict"] == "TIE"


def test_smoke_lavande_r7():
    brief = {
        "id": "lavender_amber",
        "family": "aromatic fougere amber",
        "named_notes": [
            {"name": "lavender", "window": "opening", "materials": ["lavender", "linalyl acetate"]},
            {"name": "amber", "window": "drydown", "materials": ["ambrox", "labdanum"]},
        ],
        "excluded_notes": [{"name": "rose", "materials": ["rhodinol", "rose"]}],
        "family_core_groups": [["lavender"], ["coumarin"], ["ambrox", "labdanum"]],
    }
    card = ys.score_formula(ys.formula_from_markdown(R7), brief)
    statuses = {"PASS", "FAIL", "HOLD", "NOT_APPLICABLE"}
    assert set(card["floors"]) == set(ys.FLOOR_IDS)
    assert all(f["status"] in statuses and f["detail"] for f in card["floors"].values())
    assert card["floors"]["F3_pre_mix_guard"]["status"] == "NOT_APPLICABLE"
    assert 0 <= card["name_score"] <= 100 and 0 <= card["craft_score"] <= 100
    assert "screening_oav" not in json.dumps({k: v for k, v in card.items() if k != "diagnostics"})
