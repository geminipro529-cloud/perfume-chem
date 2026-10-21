"""Depth reading: structure over the gate's windows, never a verdict.

Unit tests use synthetic frames only; studio formulas stay out of the repo.
"""

from __future__ import annotations

import json
import math
from types import SimpleNamespace

import scripts.formula_release_gate as release_cli
from engine.perception.depth_reading import build_depth_reading, depth_reading_text_lines
from engine.pipeline.simulator import DEFAULT_WINDOWS, SimulationFrame


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
    """rows: name -> (family, texture, five OAVs in window order)."""
    frames = []
    for index, (label, seconds) in enumerate(DEFAULT_WINDOWS):
        materials = tuple(
            _material(name, values[index], family, texture)
            for name, (family, texture, values) in rows.items()
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


def test_r3_shaped_formula_raises_the_four_flags():
    reading = build_depth_reading(_frames(R3_SHAPED), R3_INDEX_ROWS)

    assert reading["verdict_effect"] == "NONE"
    assert reading["class_counts"] == {
        "lead": 5, "support": 4, "shadow": 3, "silent": 3, "unknown": 1
    }
    index = reading["index_shadows"]
    assert index["count"] == 10
    assert index["by_class"] == {
        "lead": 0, "support": 4, "shadow": 3, "silent": 3, "unknown": 0
    }
    assert index["not_shadow_over_time"] == 7
    assert reading["drydown_change"]["top5_shared"] == 5
    assert reading["drydown_change"]["heart_top_family"] == "lavender"
    assert reading["drydown_change"]["drydown_top_family"] == "lavender"
    assert _codes(reading) == [
        "INDEX_SHADOWS_NOT_SHADOWS",
        "SILENT_ROWS",
        "SAME_TOP_FAMILY",
        "NO_DRYDOWN_CHANGE",
    ]
    silent = next(f for f in reading["flags"] if f["code"] == "SILENT_ROWS")
    assert silent["rows"] == ["Q1", "Q2", "Q3"]
    for window in reading["windows"][1:]:
        assert window["family_weights"]["top_family"] == "lavender"
    json.dumps(reading)  # JSON-serialisable
    text = "\n".join(depth_reading_text_lines(reading))
    assert "Row classes: lead 5, support 4, shadow 3, silent 3, unknown 1" in text
    assert "NO_DRYDOWN_CHANGE" in text


def test_index_band_is_score_luxury_band():
    rows = dict(R3_SHAPED)
    index_rows = [
        {"name": "S1", "oav": 0.0999},  # below band: index treats it as silent
        {"name": "S2", "oav": 1.0001},  # above band: index treats it as a note
        {"name": "S3", "oav": 1.0},
        {"name": "U1", "oav": 0.1},
    ]
    index = build_depth_reading(_frames(rows), index_rows)["index_shadows"]
    assert [row["name"] for row in index["rows"]] == ["S3", "U1"]


# Several objects per window, the drydown turns to amber, the shadows stay shadows.
DEEPER = {
    "Berg": ("citrus", "sparkling", (3000, 4000, 1000, 50, 10)),
    "Lav": ("lavender", "airy", (1000, 2000, 3000, 800, 100)),
    "Rose": ("floral", "velvety", (200, 400, 2500, 1500, 400)),
    "Cedar": ("woody", "dry", (50, 100, 800, 2000, 1500)),
    "Amber": ("amber", "warm", (10, 20, 300, 1500, 3000)),
    "Musk": ("musk", "soft", (5, 10, 200, 1200, 2500)),
    "IrisShadow": ("floral", "powdery", (0.05, 0.1, 0.4, 0.5, 0.6)),
    "MossShadow": ("mossy", "damp", (0.04, 0.08, 0.3, 0.35, 0.4)),
    "SpiceShadow": ("spicy", "grainy", (0.1, 0.2, 0.3, 0.2, 0.15)),
}
DEEPER_INDEX_ROWS = [
    {"name": "Berg", "oav": 2500.0},
    {"name": "Lav", "oav": 900.0},
    {"name": "Rose", "oav": 150.0},
    {"name": "Cedar", "oav": 40.0},
    {"name": "Amber", "oav": 8.0},
    {"name": "Musk", "oav": 4.0},
    {"name": "IrisShadow", "oav": 0.2},
    {"name": "MossShadow", "oav": 0.15},
    {"name": "SpiceShadow", "oav": 0.25},
]


def test_deeper_formula_raises_no_flag():
    reading = build_depth_reading(_frames(DEEPER), DEEPER_INDEX_ROWS)

    assert reading["flags"] == []
    assert reading["index_shadows"]["by_class"]["shadow"] == 3
    assert reading["index_shadows"]["not_shadow_over_time"] == 0
    tops = [w["family_weights"]["top_family"] for w in reading["windows"]]
    assert tops == ["citrus", "citrus", "lavender", "woody", "amber"]
    drydown = reading["drydown_change"]
    # four rows shared, but the top family changes: not a "no change" drydown
    assert drydown["top5_shared"] == 4
    assert drydown["top_family_unchanged"] is False
    heart = next(w for w in reading["windows"] if w["label"] == "heart")
    assert heart["assigned_family_count"] == 6
    assert heart["family_weights"]["effective_family_count"] > 5.0


def test_unknown_oav_rows_are_unknown_not_silent():
    # five louder rows fill every top 5, so the quiet row cannot rank as a lead
    rows = {f"Lead{i}": ("citrus", "sparkling", (100 - i,) * 5) for i in range(5)}
    rows |= {
        "NoOdt": ("woody", "dry", (None, None, None, None, None)),
        "PartlyKnownQuiet": ("musk", "soft", (None, 0.01, 0.05, None, 0.02)),
    }
    reading = build_depth_reading(_frames(rows))
    by_name = {row["name"]: row for row in reading["rows"]}

    assert by_name["NoOdt"]["class"] == "unknown"
    assert by_name["NoOdt"]["max_oav"] is None
    assert by_name["NoOdt"]["unknown_reason"]["missing_fields"] == ["odt"]
    assert by_name["PartlyKnownQuiet"]["class"] == "silent"
    assert by_name["PartlyKnownQuiet"]["peak_window"] == "heart"
    silent = next(f for f in reading["flags"] if f["code"] == "SILENT_ROWS")
    assert silent["rows"] == ["PartlyKnownQuiet"]
    assert reading["index_shadows"]["status"] == "NOT_SUPPLIED"


def test_bridge_needs_oav_ge_1_early_and_late():
    rows = {
        "EarlyOnly": ("citrus", "sparkling", (500, 300, 2, 0.5, 0.1)),
        "LateOnly": ("musk", "soft", (0.2, 0.5, 0.9, 3, 6)),
        "HeartToLate": ("floral", "velvety", (0.3, 0.6, 1.0, 1.0, 0.8)),
        "OpeningAndDrydown": ("woody", "dry", (1.2, 0.8, 0.7, 0.9, 1.1)),
        "NeverOne": ("amber", "warm", (0.5, 0.6, 0.99, 0.99, 0.99)),
    }
    reading = build_depth_reading(_frames(rows))
    bridge = {row["name"]: row["bridge"] for row in reading["rows"]}

    assert bridge == {
        "EarlyOnly": False,
        "LateOnly": False,
        "HeartToLate": True,
        "OpeningAndDrydown": True,
        "NeverOne": False,
    }
    assert reading["bridge_count"] == 2


def test_same_top_family_reads_from_5_min_and_needs_an_assigned_family():
    rows = {
        "Berg": ("citrus", "sparkling", (5000, 100, 50, 10, 5)),
        "Lemon": ("citrus", "sparkling", (3000, 50, 20, 5, 2)),
        "Lav": ("lavender", "airy", (100, 3000, 4000, 3000, 2000)),
        "Lin": ("lavender", "airy", (50, 1000, 2000, 1500, 1000)),
        "Musk": ("musk", "soft", (2, 5, 10, 20, 30)),
        "Wood": ("woody", "dry", (1, 2, 5, 10, 20)),
    }
    reading = build_depth_reading(_frames(rows))
    assert reading["windows"][0]["family_weights"]["top_family"] == "citrus"
    flag = next(f for f in reading["flags"] if f["code"] == "SAME_TOP_FAMILY")
    assert flag["family"] == "lavender"
    assert flag["windows"] == 4

    for name in ("Lav", "Lin"):
        rows[name] = (None, "airy", rows[name][2])
    reading = build_depth_reading(_frames(rows))
    assert reading["windows"][2]["family_weights"]["top_family"] == "unassigned"
    assert "SAME_TOP_FAMILY" not in _codes(reading)


def test_lead_support_shadow_follow_top5_and_max_oav():
    rows = {f"L{i}": ("citrus", "sparkling", (100 - i,) * 5) for i in range(5)}
    rows["SupportNotTop"] = ("woody", "dry", (2, 2, 2, 2, 2))
    rows["Shadow"] = ("floral", "powdery", (0.5, 0.5, 0.5, 0.5, 0.5))
    reading = build_depth_reading(_frames(rows))
    by_name = {row["name"]: row for row in reading["rows"]}

    assert {by_name[f"L{i}"]["class"] for i in range(5)} == {"lead"}
    assert by_name["SupportNotTop"]["class"] == "support"
    assert by_name["Shadow"]["class"] == "shadow"
    # the window top 5 is the gate's own dominant_oav ranking
    frames = _frames(rows)
    assert [r["material"] for r in reading["windows"][0]["top5"]] == [
        r["material"] for r in frames[0].dominant_oav(limit=5)
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


def test_release_gate_carries_depth_reading_without_changing_verdicts(
    tmp_path, capsys, monkeypatch
):
    path = tmp_path / "trial.md"
    path.write_text(TRIAL_FORMULA, encoding="utf-8")
    argv = [
        "--formula-file", str(path),
        "--brief", "aromatic_fougere",
        "--no-audit", "--no-append-analysis",
    ]

    rc = release_cli.main([*argv, "--json"])
    payload = json.loads(capsys.readouterr().out)
    report = payload["formulas"][0]
    reading = report["depth_reading"]
    assert reading["schema"] == "depth_reading_v1"
    assert reading["verdict_effect"] == "NONE"
    assert [w["label"] for w in reading["windows"]] == [
        w["label"] for w in report["time_windows"]
    ]
    for window, gate_window in zip(reading["windows"], report["time_windows"]):
        assert [r["material"] for r in window["top5"]] == [
            r["material"] for r in gate_window["dominant_leaders"]
        ]
    assert reading["index_shadows"]["status"] == "AVAILABLE"
    assert {row["name"] for row in reading["rows"]} == {
        row["name"] for row in report["oav_table"]
    }

    monkeypatch.setattr(
        release_cli,
        "build_depth_reading",
        lambda frames, index_rows=None: {"status": "DISABLED", "reason": "test"},
    )
    rc_without = release_cli.main([*argv, "--json"])
    without = json.loads(capsys.readouterr().out)
    assert without["formulas"][0]["depth_reading"]["status"] == "DISABLED"
    assert rc == rc_without == 1
    assert _verdicts(payload) == _verdicts(without)
    # the existing CLI test's expectations for this formula still hold
    assert payload["overall"] == "FAIL"
    monkeypatch.undo()

    release_cli.main(argv)
    text = capsys.readouterr().out
    assert "Overall: FAIL" in text
    assert "Depth reading (screening diagnostic" in text
    assert "Row classes: lead" in text
