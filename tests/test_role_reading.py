"""Row roles over time: a detection diagnostic, never a verdict or a depth measure.

Unit tests use synthetic frames only; studio formulas stay out of the repo.
"""

from __future__ import annotations

import contextlib
import io
import json
import math
from types import SimpleNamespace

import pytest

import scripts.formula_release_gate as release_cli
from engine.perception.role_reading import build_role_reading, role_reading_text_lines
from engine.pipeline.simulator import DEFAULT_WINDOWS, SimulationFrame

ABSENT = object()  # the row is missing from that frame


def _material(name, oav, family, texture="smooth"):
    intensity = None if oav is None or oav <= 0 else 1.0 + math.log10(max(oav, 1e-9))
    return SimpleNamespace(
        name=name,
        screening_oav=oav,
        oav=oav,
        screening_intensity=intensity,
        intensity=intensity,
        screening_vapor_ppm=None,
        family=family,
        texture=texture,
        physics_status="SCREENING_SENSITIVITY_ONLY" if oav is not None else "WITHHELD",
        physics_blockers=() if oav is not None else ("missing_odt",),
        missing_fields=() if oav is not None else ("odt",),
    )


def _frames(rows):
    """rows: name -> (family, texture, five OAVs in window order; ABSENT drops the row)."""
    frames = []
    for index, (label, seconds) in enumerate(DEFAULT_WINDOWS):
        materials = tuple(
            _material(name, values[index], family, texture)
            for name, (family, texture, values) in rows.items()
            if values[index] is not ABSENT
        )
        frames.append(
            SimulationFrame(
                label=label,
                t_seconds=seconds,
                state=SimpleNamespace(materials=materials),
            )
        )
    return frames


def _codes(reading):
    return [flag["code"] for flag in reading["flags"]]


def _flag(reading, code):
    return next(flag for flag in reading["flags"] if flag["code"] == code)


def _row(reading, name):
    return next(row for row in reading["rows"] if row["name"] == name)


# Five loud rows that fill every window's top 5, so test rows rank below them.
LEADS = {f"Lead{i}": ("citrus", "sparkling", (100.0 - i,) * 5) for i in range(5)}


# One lavender object with a fresh crowd; ten index "shadows" mostly are not.
R3_SHAPED = {
    "Lav": ("lavender", "airy", (1000, 2000, 5000, 4000, 3000)),
    "Lin": ("lavender", "airy", (500, 900, 2000, 1500, 1000)),
    "LinAc": ("lavender", "smooth", (300, 600, 1500, 1200, 900)),
    "Berg": ("citrus", "sparkling", (800, 1200, 1800, 400, 100)),
    "Musk": ("musk", "soft", (4, 10, 50, 80, 90)),
    # index shadows that stay shadows over time
    "S1": ("floral", "powdery", (0.05, 0.1, 0.4, 0.6, 0.7)),
    "S2": ("woody", "dry", (0.04, 0.08, 0.3, 0.5, 0.6)),
    "S3": ("floral", "powdery", (0.03, 0.06, 0.2, 0.3, 0.35)),
    # index shadows that become ordinary notes
    "U1": ("musk", "soft", (0.1, 0.2, 1.2, 1.5, 1.6)),
    "U2": ("woody", "dry", (0.2, 0.4, 1.4, 1.8, 2.0)),
    "U3": ("amber", "warm", (0.3, 0.5, 2.0, 2.5, 3.0)),
    "U4": ("green", "crisp", (0.4, 0.8, 1.1, 1.0, 0.9)),
    # index shadows that sit far below 0.1
    "Q1": ("floral", "powdery", (0.001, 0.002, 0.01, 0.02, 0.03)),
    "Q2": ("woody", "dry", (0.002, 0.003, 0.02, 0.03, 0.04)),
    "Q3": ("amber", "warm", (0.001, 0.001, 0.005, 0.008, 0.009)),
    "NoOdt": ("woody", "dry", (None, None, None, None, None)),
}
R3_INDEX_ROWS = [
    {"name": "Lav", "oav": 900.0},
    {"name": "Lin", "oav": 400.0},
    {"name": "LinAc", "oav": 250.0},
    {"name": "Berg", "oav": 700.0},
    {"name": "Musk", "oav": 3.0},
    {"name": "S1", "oav": 0.1},  # band edge, counted
    {"name": "S2", "oav": 0.5},
    {"name": "S3", "oav": 0.3},
    {"name": "U1", "oav": 1.0},  # band edge, counted
    {"name": "U2", "oav": 0.6},
    {"name": "U3", "oav": 0.7},
    {"name": "U4", "oav": 0.9},
    {"name": "Q1", "oav": 0.2},
    {"name": "Q2", "oav": 0.4},
    {"name": "Q3", "oav": 0.15},
    {"name": "NoOdt", "oav": None},
]


def test_r3_shaped_formula_names_the_index_mistake_and_silent_rows():
    reading = build_role_reading(_frames(R3_SHAPED), R3_INDEX_ROWS)

    assert reading["schema"] == "role_reading_v1"
    assert reading["status"] == "OK"
    assert reading["verdict_effect"] == "NONE"
    assert reading["class_counts"] == {
        "lead": 5,
        "support": 4,
        "shadow": 3,
        "silent": 3,
        "unknown": 1,
    }
    index = reading["index_shadows"]
    assert index["count"] == 10
    assert index["stay_shadows"] == ["S1", "S2", "S3"]
    assert index["become_notes"] == ["U1", "U2", "U3", "U4"]
    assert index["never_reach_0_1"] == ["Q1", "Q2", "Q3"]
    assert _codes(reading) == ["INDEX_SHADOWS_NOT_SHADOWS", "SILENT_ROWS"]
    assert _flag(reading, "INDEX_SHADOWS_NOT_SHADOWS")["message"] == (
        "The luxury index counts 10 rows as sub-threshold shadows; over the gate's time "
        "windows 3 stay shadows (peak OAV from 0.1 to below 1). Become notes (OAV >= 1): "
        "U1, U2, U3, U4. Never reach 0.1: Q1, Q2, Q3."
    )
    assert _flag(reading, "SILENT_ROWS")["rows"] == ["Q1", "Q2", "Q3"]
    # heart and drydown top 5 overlap is a fact, never a flag
    assert reading["heart_drydown_top5"]["shared"] == 5
    # no intensity-weight reading of any kind
    text_json = json.dumps(reading)
    for gone in ("family_weights", "effective_family", "top_family", "SAME_TOP_FAMILY"):
        assert gone not in text_json
    heart = reading["windows"][2]
    assert heart["time"] == "30 min"
    assert heart["rows_oav_ge_1"] == 9
    assert heart["detectable_families"] == {
        "lavender": 3,
        "musk": 2,
        "amber": 1,
        "citrus": 1,
        "green": 1,
        "woody": 1,
    }
    assert heart["detectable_textures"] == {
        "airy": 2,
        "soft": 2,
        "crisp": 1,
        "dry": 1,
        "smooth": 1,
        "sparkling": 1,
        "warm": 1,
    }
    assert heart["detectable_rows_without_family"] == 0
    assert heart["detectable_rows_without_texture"] == 0


def test_index_band_is_score_luxury_band():
    index_rows = [
        {"name": "S1", "oav": 0.0999},  # below band: index treats it as silent
        {"name": "S2", "oav": 1.0001},  # above band: index treats it as a note
        {"name": "S3", "oav": 1.0},
        {"name": "U1", "oav": 0.1},
    ]
    index = build_role_reading(_frames(R3_SHAPED), index_rows)["index_shadows"]
    assert [row["name"] for row in index["rows"]] == ["S3", "U1"]


def test_oav_exactly_1_is_support_and_counts_as_detectable():
    rows = dict(LEADS)
    rows["AtOne"] = ("woody", "dry", (0.2, 0.5, 1.0, 0.7, 0.4))
    rows["JustBelow"] = ("floral", "powdery", (0.2, 0.5, 0.9999, 0.7, 0.4))
    reading = build_role_reading(_frames(rows))

    assert _row(reading, "AtOne")["class"] == "support"
    assert _row(reading, "JustBelow")["class"] == "shadow"
    heart = reading["windows"][2]
    assert heart["rows_oav_ge_1"] == 6
    assert heart["detectable_families"] == {"citrus": 5, "woody": 1}
    assert reading["windows"][1]["rows_oav_ge_1"] == 5


def test_oav_exactly_0_1_is_shadow_and_just_below_is_silent():
    rows = dict(LEADS)
    rows["AtFloor"] = ("woody", "dry", (0.01, 0.05, 0.1, 0.08, 0.02))
    rows["JustUnder"] = ("floral", "powdery", (0.01, 0.05, 0.0999, 0.08, 0.02))
    reading = build_role_reading(_frames(rows))

    assert _row(reading, "AtFloor")["class"] == "shadow"
    assert _row(reading, "JustUnder")["class"] == "silent"
    assert _codes(reading) == ["SILENT_ROWS"]
    assert _flag(reading, "SILENT_ROWS")["message"] == (
        "1 row never reaches OAV 0.1 in any window that has an OAV: JustUnder."
    )


def test_exactly_one_failed_index_shadow_raises_the_flag():
    rows = dict(LEADS)
    rows["Stays1"] = ("floral", "powdery", (0.1, 0.2, 0.5, 0.6, 0.4))
    rows["Stays2"] = ("woody", "dry", (0.1, 0.3, 0.9, 0.8, 0.7))
    rows["OneNote"] = ("amber", "warm", (0.2, 0.4, 0.9, 1.5, 1.2))
    index_rows = [
        {"name": "Lead0", "oav": 80.0},
        {"name": "Stays1", "oav": 0.3},
        {"name": "Stays2", "oav": 0.5},
        {"name": "OneNote", "oav": 0.6},
    ]
    reading = build_role_reading(_frames(rows), index_rows)

    assert _codes(reading) == ["INDEX_SHADOWS_NOT_SHADOWS"]
    flag = _flag(reading, "INDEX_SHADOWS_NOT_SHADOWS")
    assert flag["become_notes"] == ["OneNote"]
    assert flag["message"] == (
        "The luxury index counts 3 rows as sub-threshold shadows; over the gate's time "
        "windows 2 stay shadows (peak OAV from 0.1 to below 1). Become notes (OAV >= 1): "
        "OneNote."
    )


def test_index_shadows_that_stay_shadows_raise_nothing():
    rows = dict(LEADS)
    rows["Stays1"] = ("floral", "powdery", (0.05, 0.2, 0.5, 0.6, 0.4))
    rows["Stays2"] = ("woody", "dry", (0.1, 0.3, 0.9999, 0.8, 0.7))
    index_rows = [{"name": "Stays1", "oav": 0.3}, {"name": "Stays2", "oav": 0.5}]
    reading = build_role_reading(_frames(rows), index_rows)

    assert reading["flags"] == []
    assert reading["index_shadows"]["count"] == 2
    assert reading["index_shadows"]["not_shadow_over_time"] == 0
    assert reading["index_shadows"]["stay_shadows"] == ["Stays1", "Stays2"]


def test_silent_rows_reads_max_oav_even_for_a_top5_row_in_a_tiny_formula():
    rows = {
        "Loud": ("citrus", "sparkling", (5.0, 4.0, 3.0, 2.0, 1.5)),
        "Mid": ("woody", "dry", (2.0, 2.0, 1.5, 1.2, 1.1)),
        "Tiny": ("musk", "soft", (0.01, 0.02, 0.05, 0.04, 0.03)),
    }
    reading = build_role_reading(_frames(rows))

    assert _row(reading, "Tiny")["class"] == "lead"  # ranks in a three-row top 5
    assert _codes(reading) == ["SILENT_ROWS"]
    assert _flag(reading, "SILENT_ROWS")["rows"] == ["Tiny"]


def test_missing_frame_rows_and_unmatched_index_rows_do_not_raise():
    rows = dict(LEADS)
    rows["Late"] = ("amber", "warm", (ABSENT, ABSENT, 0.4, 1.2, 2.0))
    rows["Gone"] = ("citrus", "sparkling", (2.0, 1.5, 0.5, ABSENT, ABSENT))
    index_rows = [
        {"name": "Late", "oav": 0.5},
        {"name": "Ghost", "oav": 0.5},  # in the index, in no frame
    ]
    reading = build_role_reading(_frames(rows), index_rows)

    late = _row(reading, "Late")
    assert late["oav_by_window"]["opening"] is None
    assert late["absent_from_windows"] == ["opening", "top"]
    assert late["class"] == "support"
    assert late["peak_time"] == "4 h"
    gone = _row(reading, "Gone")
    assert gone["absent_from_windows"] == ["late_heart", "drydown"]
    assert gone["bridge"] is False
    index = reading["index_shadows"]
    assert index["unmatched"] == [{"name": "Ghost", "concentrate_oav": 0.5}]
    assert index["count"] == 2
    assert index["become_notes"] == ["Late"]
    flag = _flag(reading, "INDEX_SHADOWS_NOT_SHADOWS")
    assert flag["unmatched"] == ["Ghost"]
    assert flag["message"] == (
        "The luxury index counts 2 rows as sub-threshold shadows; over the gate's time "
        "windows 0 stay shadows (peak OAV from 0.1 to below 1). Become notes (OAV >= 1): "
        "Late. Not in the frames: Ghost."
    )
    json.dumps(reading)

    # an unmatched row alone is a data gap, listed but not flagged
    only_ghost = build_role_reading(_frames(rows), [{"name": "Ghost", "oav": 0.5}])
    assert only_ghost["index_shadows"]["unmatched"] == [{"name": "Ghost", "concentrate_oav": 0.5}]
    assert "INDEX_SHADOWS_NOT_SHADOWS" not in _codes(only_ghost)


def test_unknown_oav_rows_are_listed_not_silent_and_not_flagged():
    rows = dict(LEADS)
    rows["NoOdt"] = ("woody", "dry", (None, None, None, None, None))
    rows["PartlyKnownQuiet"] = ("musk", "soft", (None, 0.01, 0.05, None, 0.02))
    reading = build_role_reading(_frames(rows))

    no_odt = _row(reading, "NoOdt")
    assert no_odt["class"] == "unknown"
    assert no_odt["max_oav"] is None
    assert no_odt["unknown_reason"]["missing_fields"] == ["odt"]
    assert reading["unknown_rows"] == [
        {"name": "NoOdt", "reason": no_odt["unknown_reason"]},
    ]
    assert _row(reading, "PartlyKnownQuiet")["class"] == "silent"
    assert _row(reading, "PartlyKnownQuiet")["peak_window"] == "heart"
    assert _codes(reading) == ["SILENT_ROWS"]
    assert _flag(reading, "SILENT_ROWS")["rows"] == ["PartlyKnownQuiet"]
    assert reading["index_shadows"]["status"] == "NOT_SUPPLIED"


def test_bridge_needs_oav_ge_1_by_30_min_and_at_2_h_or_later():
    rows = {
        "EarlyOnly": ("citrus", "sparkling", (500, 300, 2, 0.5, 0.1)),
        "LateOnly": ("musk", "soft", (0.2, 0.5, 0.9, 3, 6)),
        "HeartToLate": ("floral", "velvety", (0.3, 0.6, 1.0, 1.0, 0.8)),
        "OpeningAndDrydown": ("woody", "dry", (1.2, 0.8, 0.7, 0.9, 1.1)),
        "NeverOne": ("amber", "warm", (0.5, 0.6, 0.99, 0.99, 0.99)),
    }
    reading = build_role_reading(_frames(rows))
    bridge = {row["name"]: row["bridge"] for row in reading["rows"]}

    assert bridge == {
        "EarlyOnly": False,
        "LateOnly": False,
        "HeartToLate": True,
        "OpeningAndDrydown": True,
        "NeverOne": False,
    }
    assert reading["bridge_count"] == 2


def test_lead_support_shadow_follow_top5_and_max_oav():
    rows = dict(LEADS)
    rows["SupportNotTop"] = ("woody", "dry", (2, 2, 2, 2, 2))
    rows["Shadow"] = ("floral", "powdery", (0.5, 0.5, 0.5, 0.5, 0.5))
    reading = build_role_reading(_frames(rows))

    assert {_row(reading, f"Lead{i}")["class"] for i in range(5)} == {"lead"}
    assert _row(reading, "SupportNotTop")["class"] == "support"
    assert _row(reading, "Shadow")["class"] == "shadow"
    # the window top 5 is the gate's own dominant_oav ranking
    frames = _frames(rows)
    assert [r["material"] for r in reading["windows"][0]["top5"]] == [
        r["material"] for r in frames[0].dominant_oav(limit=5)
    ]


def test_text_section_reads_for_a_perfumer():
    lines = role_reading_text_lines(build_role_reading(_frames(R3_SHAPED), R3_INDEX_ROWS))
    text = "\n".join(lines)

    assert len(lines) <= 12
    assert lines[0].startswith("  Row roles over time (detection diagnostic, AGENTS.md Rule 1")
    assert "does not measure depth, objects, textures, strength or beauty" in text
    assert "Kenny's nose decides" in text
    window_lines = [line.strip() for line in lines[2:7]]
    assert [line.split(":")[0] for line in window_lines] == ["0 s", "5 min", "30 min", "2 h", "4 h"]
    assert window_lines[2] == (
        "30 min: 9 rows at OAV >= 1; top 5: Lav 5000, Lin 2000, Berg 1800, LinAc 1500, Musk 50"
    )
    for label in ("opening", "late_heart", "drydown"):
        assert label not in text
    assert "%" not in text and "weight" not in text
    assert (
        "Roles: lead 5, support 4, shadow 3 (S1, S2, S3), silent 3 (Q1, Q2, Q3), "
        "unknown 1 (NoOdt: missing odt)"
    ) in text
    assert "9 bridge rows = detectable both early (by 30 min) and late (2 h or later)" in text
    assert "Top 5 at 30 min and 4 h share 5: Lav, Lin, Berg, LinAc, Musk" in text
    assert "INDEX_SHADOWS_NOT_SHADOWS: The luxury index counts 10 rows" in text
    assert "SILENT_ROWS: 3 rows never reach OAV 0.1" in text


def test_text_section_reports_error_and_unavailable_in_one_line():
    error = {"status": "ERROR", "error": "KeyError: 'x'"}
    assert role_reading_text_lines(error) == ["  Row roles over time: ERROR (KeyError: 'x')"]
    assert role_reading_text_lines(build_role_reading([])) == [
        "  Row roles over time: UNAVAILABLE (no simulation frames)"
    ]


TRIAL_FORMULA = """# Trial Fougere

| # | Material | Dilution | Amount (uL) | Amount (mL) |
|---:|---|---:|---:|---:|
| 1 | Cedrat FCF oil Sicilian | neat | 1200 | 1.200 |
| 2 | Lavender EO (BONTAUX SAS) | neat | 700 | 0.700 |
| 3 | Linalyl Acetate | neat | 600 | 0.600 |
| 4 | Hedione | neat | 900 | 0.900 |
| 5 | Coumarin | 30% | 300 | 0.300 |
| 6 | Evernyl | 20% | 10 | 0.010 |
| 7 | Iso E Super | neat | 1500 | 1.500 |
| 8 | Cedarwood oil Virginia | neat | 300 | 0.300 |
| 9 | Zenolide | neat | 490 | 0.490 |
"""


def _verdicts(payload):
    return {
        "overall": payload["overall"],
        "formulas": [
            {
                "status": report["status"],
                "commercial_readiness": report["commercial_readiness"],
                "gates": [(gate["gate"], gate["status"]) for gate in report["gates"]],
                "scores": report["scores"],
                "ranking": report["ranking"],
                "oav_authority": report["oav_authority"],
            }
            for report in payload["formulas"]
        ],
    }


def _run_gate(argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = release_cli.main(argv)
    return rc, out.getvalue()


@pytest.fixture(scope="module")
def trial_argv(tmp_path_factory):
    path = tmp_path_factory.mktemp("role_reading") / "trial.md"
    path.write_text(TRIAL_FORMULA, encoding="utf-8")
    return [
        "--formula-file",
        str(path),
        "--brief",
        "aromatic_fougere",
        "--no-audit",
        "--no-append-analysis",
    ]


@pytest.fixture(scope="module")
def trial_run(trial_argv):
    rc, out = _run_gate([*trial_argv, "--json"])
    return rc, json.loads(out)


def test_release_gate_carries_role_reading_without_changing_verdicts(
    trial_argv, trial_run, monkeypatch
):
    rc, payload = trial_run
    report = payload["formulas"][0]
    reading = report["role_reading"]
    assert "depth_reading" not in report
    assert reading["schema"] == "role_reading_v1"
    assert reading["status"] == "OK"
    assert reading["verdict_effect"] == "NONE"
    assert [w["label"] for w in reading["windows"]] == [w["label"] for w in report["time_windows"]]
    for window, gate_window in zip(reading["windows"], report["time_windows"]):
        assert [r["material"] for r in window["top5"]] == [
            r["material"] for r in gate_window["dominant_leaders"]
        ]
    assert reading["index_shadows"]["status"] == "AVAILABLE"
    assert {row["name"] for row in reading["rows"]} == {row["name"] for row in report["oav_table"]}

    monkeypatch.setattr(
        release_cli,
        "build_role_reading",
        lambda frames, index_rows=None: {"status": "DISABLED", "reason": "test"},
    )
    rc_without, out = _run_gate([*trial_argv, "--json"])
    without = json.loads(out)
    assert without["formulas"][0]["role_reading"]["status"] == "DISABLED"
    assert rc == rc_without == 1
    assert _verdicts(payload) == _verdicts(without)
    # the existing CLI test's expectations for this formula still hold
    assert payload["overall"] == "FAIL"
    monkeypatch.undo()

    _, text = _run_gate(trial_argv)
    assert "Overall: FAIL" in text
    assert "  Row roles over time (detection diagnostic" in text
    assert "    30 min: " in text
    assert "    Roles: lead " in text


def test_release_gate_finishes_when_the_role_reading_raises(trial_argv, trial_run, monkeypatch):
    rc, payload = trial_run

    def boom(frames, index_rows=None):
        raise RuntimeError("synthetic reader failure")

    monkeypatch.setattr(release_cli, "build_role_reading", boom)
    rc_error, out = _run_gate([*trial_argv, "--json"])
    failed = json.loads(out)

    assert failed["formulas"][0]["role_reading"] == {
        "status": "ERROR",
        "error": "RuntimeError: synthetic reader failure",
    }
    assert rc_error == rc
    assert failed["overall"] == payload["overall"]
    assert _verdicts(failed) == _verdicts(payload)

    _, text = _run_gate(trial_argv)
    assert "Overall: FAIL" in text
    assert "  Row roles over time: ERROR (RuntimeError: synthetic reader failure)" in text
