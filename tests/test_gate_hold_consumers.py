"""HOLD is a blocking gate status: every consumer of release-gate rows and
report statuses must block on it, count it and display it, never treat it as
passing. Each test feeds a synthetic report holding a HOLD gate and no FAIL."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

from engine.pipeline import gates as gates_module
from engine.pipeline.audit_log import gate_report_event
from engine.pipeline.gates import GateResult, ReleaseGateConfig
from engine.pipeline.interventions import build_intervention_contract, diagnose_gates
from scripts import batch_gate_all_formulas as batch
from scripts import pipeline_audit
from scripts.format_pipeline_analysis import build_gate_summary

ROOT = Path(__file__).resolve().parents[1]

HOLD_GATE = {"gate": "concentration_basis", "status": "HOLD", "detail": "stock basis undeclared"}
PASS_GATE = {"gate": "exact_subtotal", "status": "PASS", "detail": ""}
WARN_GATE = {"gate": "robustness_perturbation", "status": "WARN", "detail": "fragile"}


def _gate_results() -> list[GateResult]:
    return [GateResult(**row, data={}) for row in (PASS_GATE, WARN_GATE, HOLD_GATE)]


def test_commercial_readiness_is_never_ready_for_hold_report() -> None:
    confident = {"combined_confidence": 95.0}
    gates = _gate_results()
    for config in (
        ReleaseGateConfig(),
        ReleaseGateConfig(commercial_mode=True),
        ReleaseGateConfig(commercial_mode=True, commercial_confidence_policy="warn"),
    ):
        readiness = gates_module._commercial_readiness("HOLD", gates, confident, config)
        assert readiness == "NOT_RELEASE_READY_HOLD"
        assert "READY_FOR_TRIAL" not in readiness and "TRIAL_READY" not in readiness
    # FAIL keeps its own verdict.
    assert (
        gates_module._commercial_readiness("FAIL", gates, confident, ReleaseGateConfig())
        == "NOT_RELEASE_READY"
    )


def test_gate_summary_renders_and_counts_hold() -> None:
    lines = build_gate_summary({"gates": [PASS_GATE, WARN_GATE, HOLD_GATE]})
    text = "\n".join(lines)
    assert "**1 PASS** / **1 WARN** / **1 HOLD** / **0 FAIL**" in text
    assert "  HOLD concentration_basis: stock basis undeclared" in text


def test_batch_classifies_and_collects_hold() -> None:
    output = {"overall": "HOLD", "formulas": [{"gates": [PASS_GATE, HOLD_GATE]}]}
    assert batch.classify_overall(output) == "HOLD"
    assert batch.collect_failed_gates(output) == ["concentration_basis"]


def test_batch_main_tallies_one_hold(tmp_path: Path, monkeypatch, capsys) -> None:
    formulas_dir = tmp_path / "formulas"
    output_dir = tmp_path / "results"
    formulas_dir.mkdir()
    output_dir.mkdir()
    formula = formulas_dir / "held.md"
    formula.write_text("no metadata\n", encoding="utf-8")

    monkeypatch.setattr(batch, "ROOT", tmp_path)
    monkeypatch.setattr(batch, "FORMULAS_DIR", formulas_dir)
    monkeypatch.setattr(batch, "OUTPUT_DIR", output_dir)
    monkeypatch.setattr(batch, "discover_formula_files", lambda: ([formula], []))
    monkeypatch.setattr(
        batch,
        "run_gate",
        lambda *args: {"overall": "HOLD", "formulas": [{"gates": [HOLD_GATE]}]},
    )

    assert batch.main(["--workers", "1", "--execution-mode", "isolated"]) == 0

    (run_dir,) = [path for path in output_dir.iterdir() if path.is_dir()]
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["held"] == 1
    assert summary["errors"] == 0
    assert summary["passed"] == summary["warned"] == summary["failed"] == 0
    assert [row["status"] for row in summary["formulas"]] == ["HOLD"]
    assert "  HOLD:       1" in capsys.readouterr().out


def test_pipeline_audit_scan_lists_hold_gates(tmp_path: Path, monkeypatch, capsys) -> None:
    import engine.formula_metadata as formula_metadata

    path = tmp_path / "formulas" / "held.md"
    path.parent.mkdir()
    path.write_text("x\n", encoding="utf-8")
    report = SimpleNamespace(
        number=1,
        name="Held",
        status="HOLD",
        commercial_readiness="NOT_RELEASE_READY_HOLD",
        audit_event_id="",
        gates=tuple(_gate_results()),
    )
    monkeypatch.setattr(pipeline_audit, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(pipeline_audit, "_matching_formula_paths", lambda *a, **k: [path])
    monkeypatch.setattr(pipeline_audit, "parse_formula_markdown", lambda _path: [{}])
    monkeypatch.setattr(pipeline_audit, "gate_formula", lambda *a, **k: report)
    monkeypatch.setattr(
        formula_metadata,
        "pipeline_preflight_guard",
        lambda *a, **k: SimpleNamespace(ok=lambda: True),
    )

    assert pipeline_audit.main(["scan-formulas", "--no-audit"]) == 0
    out = capsys.readouterr().out
    assert "Held: HOLD (NOT_RELEASE_READY_HOLD)" in out
    assert "  HOLD: concentration_basis" in out

    assert pipeline_audit.main(["scan-formulas", "--no-audit", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    row = payload["results"][0]["formulas"][0]
    assert row["hold_gates"] == ["concentration_basis"]
    assert row["failed_gates"] == []


def test_interventions_treat_hold_as_release_blocking() -> None:
    (issue,) = [row for row in diagnose_gates([PASS_GATE, HOLD_GATE])]
    assert issue["status"] == "HOLD"
    assert issue["blocks_release"] is True
    assert issue["severity"] == "HIGH"

    report = {"status": "HOLD", "gates": [PASS_GATE, WARN_GATE, HOLD_GATE]}
    contract = build_intervention_contract({}, report)
    assert [row["gate"] for row in contract["blocking_issues"]] == ["concentration_basis"]
    assert contract["deterministic_repairs"] == []
    assert contract["confidence"]["repairability"] == "data_required"


def test_audit_event_lists_hold_gates() -> None:
    report = SimpleNamespace(name="Held", status="HOLD", gates=_gate_results())
    event = gate_report_event(report, ReleaseGateConfig(audit_enabled=False))
    assert event["hold_gates"] == ["concentration_basis"]
    assert event["failed_gates"] == []


def test_check_gates_script_counts_hold(tmp_path: Path) -> None:
    payload = tmp_path / "pipeline.json"
    payload.write_text(
        json.dumps({"formulas": [{"gates": [PASS_GATE, WARN_GATE, HOLD_GATE]}]}),
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_gates.py"), str(payload)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "1 PASS | 1 WARN | 1 HOLD | 0 FAIL" in result.stdout
    assert "  HOLD concentration_basis" in result.stdout
