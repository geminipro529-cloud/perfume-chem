from pathlib import Path

import engine.pipeline.gates as gates_module
from engine.optimizer.models import FormulaVector
from engine.optimizer.oav_guard import OAVCheck
from engine.optimizer.scoring import FormulaScorer
from engine.pipeline.gates import ReleaseGateConfig, gate_formula
from scripts.formula_release_gate import main as release_gate_main
from scripts.verify_formula_workflow import parse_formula_markdown


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _formula(
    ingredients, *, name="Trial Formula", body="aromatic fougere", dilutions=None
):
    total = sum(ingredients.values()) or 1.0
    return {
        "number": 1,
        "name": name,
        "body": body,
        "ingredients_ul": dict(ingredients),
        "dilutions": dilutions or {},
        "ingredients_pct": {k: v / total * 100.0 for k, v in ingredients.items()},
    }


def _trial_fougere():
    return _formula(
        {
            "Bergamot FCF": 1200.0,
            "Lavender EO": 700.0,
            "Linalyl Acetate": 600.0,
            "Hedione": 900.0,
            "Coumarin": 300.0,
            "Evernyl": 10.0,
            "Iso E Super": 1500.0,
            "Vetiver EO": 300.0,
            "Habanolide": 490.0,
        }
    )


class _LowConfidence:
    def score(self, _ingredients):
        return {
            "data_confidence": 30.0,
            "pairing_confidence": 30.0,
            "prediction_confidence": 30.0,
            "overall_confidence": 30.0,
            "confidence_grade": "LOW",
            "per_material": {},
        }


def test_commercial_trial_low_confidence_warns_not_blocks(monkeypatch):
    monkeypatch.setattr(gates_module, "ConfidenceScorer", lambda: _LowConfidence())
    report = gate_formula(
        _trial_fougere(),
        ReleaseGateConfig(
            brief="aromatic_fougere",
            commercial_mode=True,
            commercial_confidence_policy="warn",
            audit_enabled=False,
        ),
    )
    gate_map = {gate.gate: gate for gate in report.gates}

    assert report.status == "WARN"
    assert gate_map["confidence_minimum"].status == "WARN"
    assert report.commercial_readiness == "COMMERCIAL_TRIAL_READY_LOW_CONFIDENCE"


def test_strict_commercial_low_confidence_blocks(monkeypatch):
    monkeypatch.setattr(gates_module, "ConfidenceScorer", lambda: _LowConfidence())
    report = gate_formula(
        _trial_fougere(),
        ReleaseGateConfig(
            brief="aromatic_fougere",
            commercial_mode=True,
            commercial_confidence_policy="block",
            audit_enabled=False,
        ),
    )
    gate_map = {gate.gate: gate for gate in report.gates}

    assert report.status == "FAIL"
    assert gate_map["confidence_minimum"].status == "FAIL"
    assert report.commercial_readiness == "NOT_RELEASE_READY"


def test_oav_scaling_guard_blocks_proportional_trace_floor():
    formula = _formula({"Hedione": 5998.5, "Geosmin": 1.5}, body="generic")
    report = gate_formula(
        formula,
        ReleaseGateConfig(
            brief="generic",
            batch_scaling_targets_ml=(15.0,),
            audit_enabled=False,
        ),
    )
    gate_map = {gate.gate: gate for gate in report.gates}

    assert gate_map["oav_scaling_guard"].status == "FAIL"
    assert gate_map["oav_scaling_guard"].data["findings"][0]["material"] == "Geosmin"


def test_oav_scaling_guard_passes_stable_formula():
    report = gate_formula(
        _trial_fougere(),
        ReleaseGateConfig(
            brief="aromatic_fougere",
            batch_scaling_targets_ml=(15.0,),
            audit_enabled=False,
        ),
    )
    gate_map = {gate.gate: gate for gate in report.gates}

    assert gate_map["oav_scaling_guard"].status == "PASS"


def test_commercial_trial_upgrades_scaling_warning_to_blocker(monkeypatch):
    def fake_scaling(*_args, **_kwargs):
        return [
            OAVCheck(
                material="Hedione",
                source_conc_ppm=1.0,
                target_conc_ppm=1.0,
                odt_ppm=0.1,
                source_oav=10.0,
                target_oav=10.0,
                severity="warn",
                message="synthetic scaling warning",
            )
        ]

    monkeypatch.setattr(gates_module, "check_proportional_scaling", fake_scaling)

    technical = gate_formula(
        _trial_fougere(),
        ReleaseGateConfig(
            brief="aromatic_fougere",
            batch_scaling_targets_ml=(15.0,),
            audit_enabled=False,
        ),
    )
    trial = gate_formula(
        _trial_fougere(),
        ReleaseGateConfig(
            brief="aromatic_fougere",
            commercial_mode=True,
            commercial_confidence_policy="warn",
            batch_scaling_targets_ml=(15.0,),
            audit_enabled=False,
        ),
    )

    assert {gate.gate: gate for gate in technical.gates}[
        "oav_scaling_guard"
    ].status == "WARN"
    assert {gate.gate: gate for gate in trial.gates}[
        "oav_scaling_guard"
    ].status == "FAIL"


def test_unknown_material_fails_gate_and_legacy_scorer_penalizes():
    formula = _formula({"Hedione": 5900.0, "Mysteryonium X": 100.0}, body="generic")
    report = gate_formula(
        formula, ReleaseGateConfig(brief="generic", audit_enabled=False)
    )
    gate_map = {gate.gate: gate for gate in report.gates}

    scores = FormulaScorer().score(
        FormulaVector(ingredients={"Hedione": 98.0, "Mysteryonium X": 2.0})
    )

    assert gate_map["material_spine_coverage"].status == "FAIL"
    assert scores["_unknown_materials"] == ["Mysteryonium X"]
    assert scores["total"] <= 5.0


def test_formula_release_gate_cli_accepts_commercial_trial_and_scaling_target(
    tmp_path, capsys
):
    formula_path = tmp_path / "trial.md"
    formula_path.write_text(
        """# Trial Fougere

| # | Material | Dilution | Amount (uL) | Amount (mL) |
|---:|---|---:|---:|---:|
| 1 | Bergamot FCF | neat | 1200 | 1.200 |
| 2 | Lavender EO | neat | 700 | 0.700 |
| 3 | Linalyl Acetate | neat | 600 | 0.600 |
| 4 | Hedione | neat | 900 | 0.900 |
| 5 | Coumarin | neat | 300 | 0.300 |
| 6 | Evernyl | neat | 10 | 0.010 |
| 7 | Iso E Super | neat | 1500 | 1.500 |
| 8 | Vetiver EO | neat | 300 | 0.300 |
| 9 | Habanolide | neat | 490 | 0.490 |
""",
        encoding="utf-8",
    )

    status = release_gate_main(
        [
            "--formula-file",
            str(formula_path),
            "--brief",
            "aromatic_fougere",
            "--commercial-trial",
            "--scaling-target-ml",
            "15",
            "--no-audit",
        ]
    )
    captured = capsys.readouterr()

    assert status == 0
    assert "oav_scaling_guard" in captured.out


def test_regenerated_thai_markdown_is_commercial_trial_safe():
    path = (
        PROJECT_ROOT
        / "formulas"
        / "collections"
        / "Thai_Aromatic_Fougere_3_Optimized.md"
    )
    text = path.read_text(encoding="utf-8")
    formulas = parse_formula_markdown(path)

    assert "COMMERCIAL_TRIAL_READY_LOW_CONFIDENCE" in text
    assert "not sellable until calibrated" in text
    assert "### Release Gate Audit" in text
    assert "### Gate Time-Series OAV Leaders" in text
    assert "Audit event" in text
    for formula in formulas:
        assert formula["ingredients_ul"].get("Evernyl", 0.0) < 24.0


def test_regenerated_layton_markdown_is_transparent_trial_output():
    path = (
        PROJECT_ROOT
        / "formulas"
        / "collections"
        / "Layton_DNA_Mass_Market_3_Optimized.md"
    )
    text = path.read_text(encoding="utf-8")
    formulas = parse_formula_markdown(path)

    assert "Layton DNA-inspired" in text
    assert "not sellable until calibrated" in text
    assert "proprietary cardamom-base fidelity is intentionally sacrificed" in text
    assert "### Release Gate Audit" in text
    assert "### Gate Time-Series OAV Leaders" in text
    assert "Audit event" in text
    for formula in formulas:
        for material in formula["ingredients_ul"]:
            lower = material.lower()
            assert "ftec" not in lower
            assert "fleuressence" not in lower
            assert " accord" not in f" {lower}"
            assert " base" not in f" {lower}"
            assert not lower.endswith(" fo")
