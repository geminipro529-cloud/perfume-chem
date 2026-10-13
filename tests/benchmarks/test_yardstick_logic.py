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


_VETIVER = {"name": "vetiver", "window": "drydown", "materials": ["vetiver"]}


def test_a_note_only_a_natural_carries_is_held_not_missed(base_card):
    """Natural oils lack per-constituent physics, so their note can't be judged (Rule 4)."""
    vetiver = _formula(extra_rows=(_row("Vetiver EO (Haiti)", "200", tier="base"),))
    card = ys.score_formula(vetiver, {**BRIEF, "named_notes": [*BRIEF["named_notes"], _VETIVER]})

    assert card["name_parts"]["named_notes"][-1]["status"] == "unknown_physics"
    assert card["name_parts"]["named_notes"][-1]["score"] is None
    assert {"source": "named_note", "detail": "vetiver (drydown)"} in card["holds"]
    assert card["name_status"] == "PARTIAL_HOLD"
    assert card["name_coverage"] == {"named_notes": 3, "judged": 2, "held": ["vetiver"]}
    assert card["name_score"] == base_card["name_score"]
    assert base_card["name_status"] == "SCORED"


def test_a_brief_whose_every_note_is_held_has_no_name_number():
    vetiver = _formula(extra_rows=(_row("Vetiver EO (Haiti)", "200", tier="base"),))
    card = ys.score_formula(vetiver, {"id": "vetiver", "named_notes": [_VETIVER]})

    assert card["name_score"] is None
    assert card["name_status"] == "HOLD"
    assert card["name_coverage"] == {"named_notes": 1, "judged": 0, "held": ["vetiver"]}
    assert json.loads(json.dumps(card))["name_score"] is None


def test_thresholds_match_release_gate_source():
    from engine.pipeline import gates

    master = inspect.getsource(gates._gate_master_perfumer)
    assert f"material_count < {ys.MATERIAL_COUNT_MIN}" in master
    assert f"material_count > {ys.MATERIAL_COUNT_MAX}" in master
    coty = inspect.getsource(gates._gate_coty_single_material_limit)
    assert f"pct > {ys.SINGLE_MATERIAL_LIMIT_PCT}" in coty


def _card(name=50.0, craft=50.0, valence=0.2, dq=False, held=()) -> dict:
    floors = {fid: {"status": "HOLD" if fid in held else "PASS", "detail": "-"}
              for fid in ys.FLOOR_IDS}
    return {"formula": "x", "disqualified": dq, "name_score": name, "craft_score": craft,
            "liking": {"valence": valence}, "floors": floors}


@pytest.mark.parametrize(
    ("engine", "reference", "verdict", "step"),
    [
        # Reviewer's case: engine holds a floor, reference clean, engine ahead on name.
        (_card(name=90, held=("F1_owned_stock",)), _card(name=50), "ENGINE_AHEAD_HELD",
         "3_name"),
        (_card(name=50), _card(name=90, held=("F2_ifra",)), "REFERENCE_AHEAD_HELD", "3_name"),
        (_card(held=("F3_pre_mix_guard",)), _card(), "REFERENCE_WINS", "2_floor_holds"),
        (_card(name=50, held=("F1_owned_stock",)), _card(name=90), "REFERENCE_WINS", "3_name"),
        # A held side never wins, even when the other side holds too or fails a floor.
        (_card(name=90, held=("F1_owned_stock",)), _card(name=50, held=("F2_ifra",)),
         "ENGINE_AHEAD_HELD", "3_name"),
        (_card(name=90, held=("F1_owned_stock",)), _card(dq=True), "ENGINE_AHEAD_HELD",
         "2_floors"),
        (_card(dq=True), _card(held=("F1_owned_stock",)), "REFERENCE_AHEAD_HELD", "2_floors"),
        (_card(held=("F1_owned_stock",)), _card(held=("F2_ifra",)), "TIE", "6_tie"),
    ],
)
def test_a_side_holding_a_floor_never_wins(engine, reference, verdict, step):
    v = ys.duel_verdict(engine, reference)
    assert (v["verdict"], v["deciding_step"]) == (verdict, step)


def test_both_sides_holding_lists_both_holds():
    v = ys.duel_verdict(_card(name=90, held=("F1_owned_stock",)), _card(held=("F2_ifra",)))
    assert "F1_owned_stock" in v["detail"] and "F2_ifra" in v["detail"]


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
        # A held name is not a low name: craft and liking never decide past it.
        (_card(name=None, craft=90), _card(name=90, craft=40), "NAME_HELD", "3_name"),
        (_card(name=90), _card(name=None), "NAME_HELD", "3_name"),
        (_card(name=None, craft=90), _card(name=None, craft=40), "NAME_HELD", "3_name"),
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


class _Contract:
    """Stand-in for the release gate's stock contract result (status, detail, issues)."""

    def __init__(self, issues: list[dict]) -> None:
        self.data = {"issues": issues}

    def as_dict(self) -> dict:
        return {"status": "FAIL", "detail": "stock contract failed", "data": self.data}


DESIGN_ONLY = "inventory:text-design-only:"  # engine/personal_inventory.py _live_design_stock


def _unbound(material: str) -> dict:
    return {"material": material, "reason": "stock_id_not_in_current_inventory",
            "stock_id": f"{DESIGN_ONLY}abc123"}


# inventory.txt: "Damascol (10%)", "Leather FO" (neat), "Nutmeg EO (neat / as supplied)".
RECORD = {"dilutions": {"Damascol": 0.1, "Leather FO": 1.0, "Nutmeg EO": 0.1, "X": 1.0}}


def test_stock_only_on_inventory_txt_is_a_hold_not_a_fail() -> None:
    floor = ys._f1_stock(_Contract([_unbound("Damascol"), _unbound("Leather FO")]), RECORD)

    assert floor["status"] == "HOLD"
    assert "Damascol" in floor["detail"] and "Stock page" in floor["detail"]


def test_a_dilution_of_an_owned_stronger_stock_holds() -> None:
    # Nutmeg EO at 10% while only the neat oil is owned: one bench dilution away.
    preparable = {"material": "Nutmeg EO", "reason": "stock_fraction_mismatch"}

    floor = ys._f1_stock(_Contract([_unbound("Damascol"), preparable]), RECORD)

    assert floor["status"] == "HOLD" and "dilution prepared" in floor["detail"]


def test_any_other_stock_problem_still_fails() -> None:
    stronger_than_owned = {"material": "Damascol", "reason": "stock_fraction_mismatch"}
    unknown_id = {"material": "X", "reason": "stock_id_not_in_current_inventory",
                  "stock_id": "inventory:v5:missing"}
    defect = {"material": "Damascol", "reason": "conflicting_stock_rows"}

    assert ys._f1_stock(_Contract([stronger_than_owned]), {"dilutions": {"Damascol": 0.5}})[
        "status"] == "FAIL"  # only the 10% is owned; 50% can't be made from it
    assert ys._f1_stock(_Contract([unknown_id]), RECORD)["status"] == "FAIL"
    assert ys._f1_stock(_Contract([defect]), RECORD)["status"] == "FAIL"


def _real_f1(row: dict) -> dict:
    from engine.pipeline.preflight import resolve_inventory_stock_contract

    record = ys._gate_record({"name": "t", "rows": [row]})
    return ys._f1_stock(resolve_inventory_stock_contract(record), record)


def test_same_inventory_txt_material_holds_alike_from_engine_and_reference_rows() -> None:
    engine_row = _row("Leather FO", "50", stock_id=f"{DESIGN_ONLY}0123456789abcdef0123")
    reference_row = _row("Leather FO", "50")

    engine_f1, reference_f1 = _real_f1(engine_row), _real_f1(reference_row)

    assert engine_f1["status"] == reference_f1["status"] == "HOLD", (engine_f1, reference_f1)
    # A strength above every owned stock can't be prepared: hard on both sides.
    assert _real_f1(_row("Damascol", "50", "0.5"))["status"] == "FAIL"


# inventory.txt: Adoxal 10% DPG, Calone 1% DPG, Methyl Pamplemousse 10% w/w ethanol,
# Ambrox Super 25% w/w and Ambrox Super Crystals (neat solid), Heliotropal neat (the gate's
# list records Heliotropal 10% w/w DPG as preparation_required).
@pytest.mark.parametrize(
    ("row", "status"),
    [
        # Another carrier or basis than the owned stock's is a stock the user lacks.
        (_row("Adoxal", "30", "0.1", carrier="ethanol"), "FAIL"),
        (_row("Calone", "30", "0.01", carrier="ethanol"), "FAIL"),
        (_row("Methyl Pamplemousse", "30", "0.1", fraction_basis="volume_fraction",
              carrier="ethanol"), "FAIL"),
        # Diluting the DPG stock with ethanol gives a mixed carrier, not the row's.
        (_row("Adoxal", "30", "0.05", carrier="ethanol"), "FAIL"),
        (_row("Adoxal", "30", "0.05", carrier="DPG"), "HOLD"),
        (_row("Adoxal", "30", "0.05"), "HOLD"),
        # A neat oil dilutes into any carrier on any basis (Lavande R7's pepper row).
        (_row("Nutmeg EO", "30", "0.2", fraction_basis="volume_fraction", carrier="ethanol"),
         "HOLD"),
        # Crystals dissolve only so far: nothing above the strongest owned dilution.
        (_row("Ambrox Super", "30", "0.5", fraction_basis="mass_fraction"), "FAIL"),
        (_row("Ambrox Super", "30", "0.1", fraction_basis="mass_fraction"), "HOLD"),
        # Spelling: "cis-3-Hexenyl" is inventory.txt's "Cis-3 Hexenyl"; a strength in the
        # name is the row's own fraction (inventory.txt owns neat Cocoa Absolute).
        (_row("cis-3-Hexenyl Acetate", "30"), "HOLD"),
        (_row("Cocoa Absolute 10%", "30", "0.1", fraction_basis="mass_fraction",
              carrier="DPG"), "HOLD"),
        (_row("Orris Givco 204", "30"), "FAIL"),  # on neither stock list
        # The gate's own list says this stock is prepared at the bench.
        (_row("Heliotropal", "30", "0.1", fraction_basis="mass_fraction", carrier="DPG"),
         "HOLD"),
    ],
)
def test_stock_holds_respect_carrier_basis_and_solids(row: dict, status: str) -> None:
    assert _real_f1(row)["status"] == status


def test_unreadable_rows_hold_the_stock_floor_and_are_named() -> None:
    formula = {**_formula(), "row_parse_blockers": ["line 12: '| Tonal?de | 2O uL |' unread"]}
    f1 = ys.score_formula(formula, BRIEF)["floors"]["F1_owned_stock"]

    assert f1["status"] == "HOLD" and "Tonal?de" in f1["detail"]
    assert f1["blocked_rows"] == formula["row_parse_blockers"]
    assert ys.score_formula(_formula(), BRIEF)["floors"]["F1_owned_stock"].get(
        "blocked_rows") is None


def test_revision_dose_change_is_authorised_but_stock_rebase_is_not() -> None:
    parent = _formula(neroli_ul="10")
    child = _formula(neroli_ul="40", parent=parent)  # same stock, 4x active dose
    f3 = ys._f3_pre_mix(child, ys._gate_record(child))

    assert f3["status"] == "PASS" and "AUTHORIZED_ACTIVE_DOSE_CHANGE" in f3["detail"]


def test_missing_parent_file_holds_the_revision_floor(tmp_path) -> None:
    ref = ys.formula_from_markdown(R7, parent_path=tmp_path / "gone.md")
    card = ys.score_formula(ref, BRIEF)

    assert card["floors"]["F3_pre_mix_guard"]["status"] == "HOLD"
    assert "gone.md" in card["floors"]["F3_pre_mix_guard"]["detail"]


def test_file_batch_is_read_and_a_non_30_ml_batch_fails_the_bottle_floor(tmp_path) -> None:
    lines = R7.read_text(encoding="utf-8").splitlines()
    lines[0] = lines[0].replace("30 mL", "50 mL")
    fifty = tmp_path / "Lavande_50mL_Parfum.md"
    fifty.write_text("\n".join(lines) + "\n", encoding="utf-8")

    assert ys.formula_from_markdown(R7)["batch_volume_ml"] == 30.0
    formula = ys.formula_from_markdown(fifty)
    assert formula["batch_volume_ml"] == 50.0
    assert ys._f4_bottle(formula)["status"] == "FAIL"


def test_mg_rows_count_toward_the_bottle_but_not_the_pour_floor() -> None:
    formula = _formula(extra_rows=(_row("Ambrox Super", "5", unit="mg"),))
    assert ys._f4_bottle(formula)["concentrate_ul"] == 1215.0
    assert ys._f5_pours(formula)["status"] == "PASS"


class _M:
    """Stand-in for a simulator MaterialState row."""

    def __init__(self, name: str, oav: float | None, composite: bool = False) -> None:
        self.name, self.screening_oav = name, oav
        self.odt_air_ppm = None if oav is None else 0.01
        self.missing_fields: tuple = ()
        self.has_constituent_resolved_oav = composite


@pytest.mark.parametrize(
    ("mats", "status"),
    [
        ([_M("Orris Butter", 50.0, composite=True)], "unknown_physics"),  # sum: no verdict
        ([_M("Irone", 0.2), _M("Orris Butter", 50.0, composite=True)], "unknown_physics"),
        ([_M("Irone", 0.2), _M("Orris Concrete", None)], "unknown_physics"),
        ([_M("Irone", 2.0), _M("Orris Concrete", None)], "detectable"),
        ([_M("Irone", 0.2)], "below_threshold"),
        ([], "absent"),
    ],
)
def test_note_detection_never_reads_a_summed_natural(mats, status) -> None:
    names = {m.name for m in mats}
    assert ys._note_status(mats, names, ["irone", "orris"]) == status


def test_a_withheld_composer_result_is_disqualified_not_a_crash() -> None:
    withheld = ys.formula_from_composer(
        {"optimized_formula": None, "initial_formula": None,
         "assistant_message": "The brief contains a hard contradiction."}
    )
    card = ys.score_formula(withheld, BRIEF)

    assert card["disqualified"] is True
    assert card["name_score"] == 0.0
    assert "hard contradiction" in card["floors"]["F1_owned_stock"]["detail"]
    json.dumps(card)
