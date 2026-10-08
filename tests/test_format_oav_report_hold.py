"""The OAV report lists HOLD gates (data missing) apart from FAIL and WARN."""

import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "format_oav_report.py"


def test_hold_gates_get_their_own_section_between_fail_and_warn(tmp_path):
    report = {
        "formulas": [
            {
                "formula_state": {
                    "materials": [],
                    "note_distribution": {"top": 30, "heart": 40, "base": 30},
                },
                "time_series": [],
                "gates": [
                    {"gate": "exact_subtotal", "status": "FAIL", "detail": "13380 uL parsed"},
                    {
                        "gate": "phase_compatibility",
                        "status": "HOLD",
                        "detail": "needs the density of its w/w stock",
                    },
                    {"gate": "oav_legibility", "status": "WARN", "detail": "threshold missing"},
                ],
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

    hold_at = out.index("GATES — HOLD")
    warn_at = out.index("GATES — WARN")
    assert out.index("GATES — FAIL") < hold_at < warn_at
    assert "phase_compatibility" in out[hold_at:warn_at]
    assert "phase_compatibility" not in out[warn_at:]
