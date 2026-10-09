"""OAV text stays numeric: no loudness words (AGENTS.md Rule 1), and Hedione is a style warning."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import engine.pipeline.gates as gates_module
from engine.pipeline.formula_state import build_formula_state
from engine.pipeline.gates import ReleaseGateConfig
from scripts.format_pipeline_analysis import OAV_BRACKETS, build_oav_structural, oav_label

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "format_oav_report.py"
OAVS = [25000.0, 4000.0, 500.0, 70.0, 20.0, 7.0, 2.0, 0.5]
# "Perceptible: n/m" (OAV >= 1, a detection count) is allowed; loudness ladders are not.
LOUDNESS = re.compile(
    r"massive|very strong|v\.strong|moderate|at threshold|overload|fatigue",
    re.IGNORECASE,
)


def _materials() -> list[dict]:
    notes = ["top", "top", "heart", "heart", "heart", "base", "base", "base"]
    return [
        {"name": f"Material {i}", "note": note, "family": "woody", "oav": oav}
        for i, (oav, note) in enumerate(zip(OAVS, notes))
    ]


def test_oav_labels_are_numeric_ranges() -> None:
    labels = [oav_label(oav) for oav in OAVS]
    assert labels[0] == "OAV >= 10,000"
    assert labels[-1] == "OAV < 1"
    assert all(label.startswith("OAV") for _threshold, label in OAV_BRACKETS)
    assert not any(LOUDNESS.search(label) for label in labels)


def test_structural_oav_section_makes_no_loudness_claims() -> None:
    rendered = "\n".join(
        build_oav_structural(_materials(), {"formula_state": {"batch_volume_ml": 30.0}})
    )
    assert "### OAV Tiers" in rendered
    assert "**OAV >= 1000** (2)" in rendered
    assert LOUDNESS.search(rendered) is None


def test_oav_report_ranking_shows_ranges_not_loudness(tmp_path: Path) -> None:
    report = {
        "formulas": [
            {
                "formula_state": {
                    "materials": _materials(),
                    "note_distribution": {"top": 30, "heart": 40, "base": 30},
                },
                "time_series": [],
                "gates": [],
            }
        ]
    }
    path = tmp_path / "out.json"
    path.write_text(json.dumps(report), encoding="utf-8")

    out = subprocess.run(
        [sys.executable, str(SCRIPT), str(path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        check=True,
    ).stdout

    ranking = out[out.index("OAV RANKING") : out.index("TIME RELEASE")]
    assert "Range" in ranking and "> 1,000" in ranking and "1-5" in ranking
    assert LOUDNESS.search(ranking) is None


def test_hedione_share_warning_is_a_style_warning_not_a_rule() -> None:
    rows = {"Hedione": 20.0, "Linalool": 80.0}  # 20% of fragrance-active uL
    state = build_formula_state(rows, {name: 1.0 for name in rows})
    formula = {"name": "Test Formula", "ingredients_ul": rows, "dilutions": {k: 1.0 for k in rows}}
    result = gates_module._gate_hedione_share(
        formula, state, ReleaseGateConfig(brief="generic", audit_enabled=False)
    )

    assert result.status == "WARN"
    assert "style warning level" in result.detail
    assert "lower-Hedione control" in result.detail
    assert "becomes the perfume" not in result.detail
    assert "not a safety limit" in result.data["source"]
