from pathlib import Path

import engine.pipeline.gates as gates_module
from engine.optimizer.models import FormulaVector
from engine.optimizer.oav_guard import OAVCheck
from engine.optimizer.scoring import FormulaScorer
from engine.pipeline.formula_state import build_formula_state
from engine.pipeline.gates import ReleaseGateConfig, gate_formula
from future_modules.edge_cases import MUSK_CLASS_COVERAGE, check_musk_class_coverage
from scripts.formula_release_gate import main as release_gate_main
from scripts.verify_formula_workflow import parse_formula_markdown

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_osmanthus_dark_crystal_uses_both_distinct_cocoa_stocks():
    formulas = parse_formula_markdown(
        PROJECT_ROOT / "formulas" / "Osmanthus_Dark_Crystal_30mL_EdP.md"
    )

    assert len(formulas) == 1
    formula = formulas[0]
    assert formula["ingredients_ul"]["Cocoa Absolute"] == 40.0
    assert formula["dilutions"]["Cocoa Absolute"] == 1.0
    assert formula["ingredients_ul"]["Cocoa CO2 Extract"] == 250.0
    assert formula["dilutions"]["Cocoa CO2 Extract"] == 0.077
    assert "Cocoa CO2 Absolute" not in formula["ingredients_ul"]
    assert sum(formula["ingredients_ul"].values()) == 5240.0


def test_future_module_gates_accept_unknown_oav_and_current_api_contracts():
    state = build_formula_state(
        {
            "Hedione": 350.0,
            "Iso E Super": 250.0,
            "Romandolide": 635.0,
            "Cocoa CO2 Extract": 250.0,
        },
        {"Cocoa CO2 Extract": 0.077},
        batch_volume_ml=30.0,
    )
    config = ReleaseGateConfig(audit_enabled=False)

    balance = gates_module._gate_balance_axes(state, config)
    character = gates_module._gate_character_shifts(state, config)
    musk = gates_module._gate_musk_intelligence(state, config)

    assert balance.status == "PASS"
    assert "skipped" not in balance.detail.lower()
    assert character.status in {"PASS", "WARN"}
    assert "api mismatch" not in character.detail.lower()
    assert musk.status == "PASS"
    assert "api mismatch" not in musk.detail.lower()


def test_balance_axes_does_not_route_screening_oav_as_hedonic_evidence(monkeypatch):
    import future_modules.balance_axes as balance_axes

    captured = {}
    original = balance_axes.evaluate_all_balances

    def capture_evaluate_all_balances(*args, **kwargs):
        captured["hedonic_data"] = args[4]
        return original(*args, **kwargs)

    monkeypatch.setattr(
        balance_axes,
        "evaluate_all_balances",
        capture_evaluate_all_balances,
    )
    state = build_formula_state(
        {"Hedione": 350.0, "Iso E Super": 250.0},
        batch_volume_ml=30.0,
    )

    result = gates_module._gate_balance_axes(
        state, ReleaseGateConfig(audit_enabled=False)
    )

    assert result.status == "PASS"
    assert captured["hedonic_data"] == {}
    assert result.data["hedonic_evaluation_status"] == "NOT_EVALUATED"
    assert result.data["hedonic_endpoint_authority"] is False


def test_edge_case_gate_uses_formula_specific_temperature_factors():
    state = build_formula_state(
        {
            "Zenolide": 400.0,
            "Ethylene Brassylate": 520.0,
            "Ambrettolide": 100.0,
            "Ambrox Super": 200.0,
        },
        {"Ambrettolide": 0.10, "Ambrox Super": 0.33},
        batch_volume_ml=30.0,
        temperature_K=305.0,
    )

    result = gates_module._gate_edge_cases(
        state,
        ReleaseGateConfig(temperature_K=305.0, audit_enabled=False),
    )

    temperature = result.data["vp_temperature_factor"]
    assert temperature["reference_temperature_K"] == 298.15
    assert temperature["formula_temperature_K"] == 305.0
    assert temperature["material_count"] == 4
    assert 1.0 < temperature["min"] <= temperature["median"] <= temperature["max"]
    assert "cc_factor" not in result.data
    assert "Bangkok VP" not in result.detail
    assert "formula VP factor" in result.detail
    assert result.data["musk_coverage_pct"] > 90.0
    assert "Musk coverage: 100%" in result.detail


def test_musk_structural_classes_match_supplier_and_chemical_families():
    assert "Ethylene Brassylate" in MUSK_CLASS_COVERAGE["macrocyclic"]
    assert "Zenolide" in MUSK_CLASS_COVERAGE["macrocyclic"]
    assert "Exaltolide" in MUSK_CLASS_COVERAGE["macrocyclic"]
    assert "Romandolide" in MUSK_CLASS_COVERAGE["alicyclic"]
    assert "Romandolide" not in MUSK_CLASS_COVERAGE["macrocyclic"]


def test_missing_musk_classes_have_deterministic_order():
    adequate, missing = check_musk_class_coverage(["Ambrox Super"])

    assert adequate is False
    assert missing == ["macrocyclic", "polycyclic"]


def test_low_hedione_is_not_mislabeled_as_olfactory_fatigue():
    state = build_formula_state(
        {"Hedione": 350.0, "Dipropylene Glycol": 5650.0},
        batch_volume_ml=30.0,
    )

    result = gates_module._gate_olfactory_fatigue(
        state,
        ReleaseGateConfig(audit_enabled=False),
    )

    assert result.status == "PASS"
    assert "minimum for radiance" not in result.detail


def test_high_modeled_oav_is_advisory_not_an_overdose_verdict():
    state = build_formula_state(
        {"Beta Ionone": 6000.0},
        batch_volume_ml=30.0,
    )
    config = ReleaseGateConfig(audit_enabled=False)

    overdose = gates_module._gate_oav_overdose_blocker(state, config)
    fatigue = gates_module._gate_olfactory_fatigue(state, config)

    assert overdose.status == "WARN"
    assert overdose.data["release_authority"] is False
    assert overdose.data["evidence_class"] == "MODELED_SCREENING_ONLY"
    assert "use 1%" not in overdose.detail.lower()
    assert fatigue.status != "FAIL"
    assert "overdose" not in fatigue.detail.lower()


def test_adaptation_tier_uses_material_family_for_named_citrus_oils():
    state = build_formula_state(
        {"Bergamot FCF": 100.0, "Hedione": 100.0, "Iso E Super": 100.0},
        batch_volume_ml=30.0,
    )
    rows = {material.name: material for material in state.materials}

    assert gates_module._adaptation_tier(rows["Bergamot FCF"]) == "fast"
    assert gates_module._adaptation_tier(rows["Hedione"]) == "medium"
    assert gates_module._adaptation_tier(rows["Iso E Super"]) == "slow"


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
    ingredients = {
        "Cedrat FCF oil Sicilian": 1200.0,
        "Lavender EO (BONTAUX SAS)": 700.0,
        "Linalyl Acetate": 600.0,
        "Hedione": 900.0,
        "Coumarin": 300.0,
        "Evernyl": 10.0,
        "Iso E Super": 1500.0,
        "Cedarwood oil Virginia": 300.0,
        "Zenolide": 490.0,
    }
    return _formula(
        ingredients,
        dilutions={
            material: (
                0.3
                if material == "Coumarin"
                else 0.2
                if material == "Evernyl"
                else 1.0
            )
            for material in ingredients
        },
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


def test_noncommercial_low_confidence_is_diagnostic_not_blocking(monkeypatch):
    monkeypatch.setattr(gates_module, "ConfidenceScorer", lambda: _LowConfidence())
    report = gate_formula(
        _trial_fougere(),
        ReleaseGateConfig(
            brief="aromatic_fougere",
            min_confidence_score=50.0,
            commercial_mode=False,
            audit_enabled=False,
        ),
    )
    gate_map = {gate.gate: gate for gate in report.gates}

    assert gate_map["confidence_minimum"].status == "WARN"
    assert "below 50.0" in gate_map["confidence_minimum"].detail


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
    | 1 | Cedrat FCF oil Sicilian | neat | 1200 | 1.200 |
    | 2 | Lavender EO (BONTAUX SAS) | neat | 700 | 0.700 |
    | 3 | Linalyl Acetate | neat | 600 | 0.600 |
    | 4 | Hedione | neat | 900 | 0.900 |
    | 5 | Coumarin | 30% | 300 | 0.300 |
    | 6 | Evernyl | 20% | 10 | 0.010 |
| 7 | Iso E Super | neat | 1500 | 1.500 |
    | 8 | Cedarwood oil Virginia | neat | 300 | 0.300 |
| 9 | Zenolide | neat | 490 | 0.490 |
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
