"""Composed formulas carry a diagnostic voice summary; it never changes a row."""

import copy
from types import SimpleNamespace

from engine.formulation_intelligence.formula_design_runtime import design_formula
from engine.formulation_intelligence.voice_summary import (
    LATE_WINDOWS,
    ONE_NOTE_MAX_EFFECTIVE_VOICES,
    ONE_NOTE_MIN_TOP_SHARE,
    SCREENING_NOTE,
    attach_complexity_summary,
    complexity_summary,
)
from engine.research.contracts import stable_payload_hash

WINDOWS = ("opening", "top", "heart", "late_heart", "drydown")


def _material(name: str, oav: float, intensity: float) -> SimpleNamespace:
    return SimpleNamespace(name=name, oav=oav, intensity=intensity, is_known=True, is_opaque_preblend=False)


def _simulation(materials: list[SimpleNamespace]) -> tuple[SimpleNamespace, tuple[SimpleNamespace, ...]]:
    state = SimpleNamespace(materials=tuple(materials))
    frames = tuple(
        SimpleNamespace(label=label, t_seconds=float(index * 600), state=state)
        for index, label in enumerate(WINDOWS)
    )
    return state, frames


def _rows(names: list[str], *, character: str | None = None) -> list[dict]:
    return [
        {
            "identity_name": name,
            "material": name,
            "amount_decimal": "100",
            "amount_unit": "uL",
            "stock_fraction_decimal": "1",
            "role": "character" if name == character else "structure",
            "note": "heart",
            "slot": f"slot_{index}",
        }
        for index, name in enumerate(names)
    ]


DOMINANT = [_material("Rhodinol", 5000.0, 9.0), _material("Cedarwood", 40.0, 3.0), _material("Musk", 20.0, 2.5)]
BALANCED = [_material(f"M{index}", 100.0, 5.0) for index in range(5)]
CROWDED = [_material(f"C{index}", 50.0, 4.0) for index in range(12)]


def _flags(summary: dict) -> set[str]:
    return {flag["flag"] for flag in summary["flags"]}


def test_one_material_holding_the_odour_activity_is_flagged_one_note() -> None:
    summary = complexity_summary(_rows(["Rhodinol", "Cedarwood", "Musk"]), simulation=_simulation(DOMINANT))

    assert summary["status"] == "AVAILABLE"
    assert [window["label"] for window in summary["windows"]] == list(WINDOWS)
    assert summary["windows"][2]["odour_activity_lead"] == "Rhodinol"
    assert "one_note" in _flags(summary)
    one_note = next(flag for flag in summary["flags"] if flag["flag"] == "one_note")
    assert one_note["material"] == "Rhodinol"
    assert one_note["message"].startswith("one-note risk: smell-check.")


def test_a_balanced_formula_is_neither_one_note_nor_crowded() -> None:
    summary = complexity_summary(_rows([m.name for m in BALANCED]), simulation=_simulation(BALANCED))

    assert summary["windows"][2]["effective_voices"] == 5.0
    assert summary["windows"][2]["detectable_components"] == 5
    assert _flags(summary) == set()


def test_many_near_equal_voices_with_no_foreground_are_flagged_crowded() -> None:
    summary = complexity_summary(_rows([m.name for m in CROWDED]), simulation=_simulation(CROWDED))

    assert _flags(summary) == {"crowded"}
    crowded = summary["flags"][0]
    assert crowded["message"].startswith("crowded: smell-check.")
    assert "olfactory white" in crowded["source"]


def test_summary_is_a_screening_note_with_no_score_and_keeps_the_module_boundaries() -> None:
    rows = _rows(["Rhodinol", "Cedarwood", "Musk"], character="Rhodinol")
    rows.append({**rows[0], "identity_name": "Ambrox Crystals", "material": "Ambrox Crystals", "amount_unit": "mg"})
    summary = complexity_summary(rows, simulation=_simulation(DOMINANT))

    assert summary["note"] == SCREENING_NOTE
    assert "not a beauty or quality score" in summary["note"]
    assert summary["overall_score"] is None
    assert summary["limitations"] and summary["forbidden_claims"]
    assert summary["skipped_rows"][0]["material"] == "Ambrox Crystals"
    assert summary["foreground_materials"] == ["Rhodinol"]
    assert summary["foreground_background"][0]["foreground_share"] > 0.5


def test_attach_covers_main_and_variants_marks_near_twins_and_recomputes_the_hash() -> None:
    main = {"rows": _rows([m.name for m in BALANCED])}
    twin = {"rows": _rows([m.name for m in BALANCED])}
    other = {"rows": _rows(["Rhodinol", "Cedarwood", "Musk"])}
    report = {
        "formula_name": "Test",
        "optimized_formula": main,
        "design_variants": [{"formula": main}, {"formula": twin}, {"formula": other}],
        "design_sha256": "stale",
    }
    before = copy.deepcopy(report)
    simulations = {id(main): _simulation(BALANCED), id(twin): _simulation(BALANCED), id(other): _simulation(DOMINANT)}

    enhanced = attach_complexity_summary(report, simulations=simulations)

    assert enhanced["complexity_summary"]["status"] == "AVAILABLE"
    assert [_flags(v["complexity_summary"]) for v in enhanced["design_variants"]] == [
        {"similar_to_variant_2"}, {"similar_to_variant_1"}, {"one_note"},
    ]
    assert _flags(enhanced["complexity_summary"]) == set()
    assert [v["formula"] for v in enhanced["design_variants"]] == [v["formula"] for v in before["design_variants"]]
    assert enhanced["optimized_formula"] == before["optimized_formula"]
    assert enhanced["design_sha256"] == stable_payload_hash(
        {key: value for key, value in enhanced.items() if key != "design_sha256"}
    )
    assert enhanced["design_sha256"] != "stale"


def _one_note_expected(summary: dict) -> bool:
    late = [window for window in summary["windows"] if window["label"] in LATE_WINDOWS]
    few_voices = bool(late) and all(
        (window["effective_voices"] or 0.0) < ONE_NOTE_MAX_EFFECTIVE_VOICES for window in late
    )
    leads = {window["odour_activity_lead"] for window in late}
    one_lead = (
        bool(late)
        and len(leads) == 1
        and None not in leads
        and all((window["odour_activity_lead_share"] or 0.0) >= ONE_NOTE_MIN_TOP_SHARE for window in late)
    )
    return few_voices or one_lead


def test_design_formula_one_note_flag_matches_its_windows_and_the_amber_is_not_one_note() -> None:
    # The rose chypre stopped being one-note once master's material-data and
    # composer fixes landed (7 effective voices at drydown), so the real-brief
    # check is that the flag agrees with the numbers it is computed from; the
    # synthetic Rhodinol case above pins that a one-note formula is flagged.
    chypre = design_formula(idea="rose chypre with patchouli and oakmoss depth")
    amber = design_formula(idea="warm amber with an iris heart and a smoky shadow")

    for report in (chypre, amber):
        summary = report["complexity_summary"]
        assert ("one_note" in _flags(summary)) == _one_note_expected(summary)
    assert "one_note" not in _flags(amber["complexity_summary"])
    for report in (chypre, amber):
        assert report["design_variants"]
        for variant in report["design_variants"]:
            assert variant["complexity_summary"]["status"] == "AVAILABLE"


def test_every_deep_compose_variant_carries_its_own_summary() -> None:
    report = design_formula(idea="warm amber with an iris heart and a smoky shadow", design_mode="DEEP_COMPOSE")

    assert len(report["design_variants"]) > 1
    for variant in report["design_variants"]:
        windows = variant["complexity_summary"]["windows"]
        assert [window["label"] for window in windows] == list(WINDOWS)
        assert all(window["effective_voices"] is not None for window in windows)
