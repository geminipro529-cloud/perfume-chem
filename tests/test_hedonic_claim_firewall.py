from __future__ import annotations

import hashlib
import json
from pathlib import Path

import engine.pipeline.gates as gates_module
from engine.optimizer.scoring import FormulaScorer
from engine.orchestration import methodology as active_methodology
from engine.orchestration.iec_loop import IECHyperparameters
from engine.orchestration.pipeline import AtelierConfig, stage2_methodology
from engine.pipeline.formula_state import build_formula_state
from engine.pipeline.gates import ReleaseGateConfig, gate_formula
from engine.pipeline.oav_authority import OAVAuthorityRequest, analyze_oav_authority
from engine.pipeline.release_scoring import compute_unified_release_scores
from scripts import evaluate_formula as formula_evaluator

ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "data" / "governance" / "hedonic_active_path_audit_v1.json"
AUDIT_SIDECAR = AUDIT_PATH.with_suffix(".sha256")


def _canonical_text_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _formula() -> dict[str, object]:
    return {
        "number": 1,
        "name": "Hedonic Firewall Probe",
        "ingredients_ul": {
            "Lavender EO": 700.0,
            "Hedione": 900.0,
            "Coumarin": 300.0,
            "Iso E Super": 1500.0,
        },
        "dilutions": {
            "Lavender EO": 1.0,
            "Hedione": 1.0,
            "Coumarin": 0.2,
            "Iso E Super": 1.0,
        },
    }


def _release_payload(*, scorer: FormulaScorer | None = None) -> dict[str, object]:
    formula = _formula()
    authority = analyze_oav_authority(
        OAVAuthorityRequest(
            formula_name=str(formula["name"]),
            ingredients_ul=formula["ingredients_ul"],
            dilutions=formula["dilutions"],
            batch_volume_ml=30.0,
        )
    )
    gates = gate_formula(formula, ReleaseGateConfig(audit_enabled=False)).as_dict()
    return compute_unified_release_scores(
        formula, authority, gates, scorer=scorer
    ).as_dict()


def test_release_scoring_never_calls_legacy_replay(monkeypatch) -> None:
    def forbidden(*args, **kwargs):
        raise AssertionError("legacy replay entered active release scoring")

    monkeypatch.setattr(FormulaScorer, "score_legacy_replay", forbidden)
    payload = _release_payload()

    assert "hedonic" not in payload["scores"]
    assert payload["scores"]["_hedonic_evidence"]["state"] == "NOT_TESTED"


def test_release_scoring_reports_liking_not_tested_without_exact_scope_receipt() -> None:
    payload = _release_payload()

    assert "hedonic" not in payload["scores"]
    assert payload["scores"]["_hedonic_evidence"] == {
        "state": "NOT_TESTED",
        "basis": "No exact-scope blinded LIKING receipt supplied to FormulaScorer.",
        "legacy_heuristic_available_for_replay": True,
    }
    authority = payload["provenance"]["score_contract"]["axis_authority"]
    assert "hedonic" not in authority


def test_formula_evaluator_withholds_numeric_hedonic_output(tmp_path, capsys) -> None:
    formula_path = tmp_path / "probe.md"
    formula_path.write_text(
        """# Probe

| # | Material | Dilution | Amount (uL) |
|---:|---|---:|---:|
| 1 | Hedione | neat | 1000 |
| 2 | Iso E Super | neat | 1000 |
""",
        encoding="utf-8",
    )

    result = formula_evaluator.evaluate_formula(str(formula_path))
    formula_evaluator.print_report(result)
    rendered = capsys.readouterr().out

    assert result.hedonic_score is None
    assert result.hedonic_state == "NOT_TESTED"
    assert "HEDONIC SCORE" not in rendered
    assert "LIKING EVIDENCE: NOT_TESTED" in rendered


def test_formula_batch_export_contains_state_not_numeric_hedonic_score(
    tmp_path, capsys
) -> None:
    formula_path = tmp_path / "probe.md"
    formula_path.write_text(
        """# Probe

| # | Material | Dilution | Amount (uL) |
|---:|---|---:|---:|
| 1 | Hedione | neat | 1000 |
| 2 | Iso E Super | neat | 1000 |
""",
        encoding="utf-8",
    )
    output = tmp_path / "results.jsonl"

    formula_evaluator.evaluate_batch(str(tmp_path), str(output))
    capsys.readouterr()
    record = json.loads(output.read_text(encoding="utf-8").splitlines()[0])

    assert "hedonic_score" not in record
    assert record["hedonic_evidence"] == {"state": "NOT_TESTED"}


def test_balance_gate_withholds_synthetic_hedonic_contrast_axis() -> None:
    state = build_formula_state(
        {"Hedione": 350.0, "Iso E Super": 250.0, "Romandolide": 635.0},
        batch_volume_ml=30.0,
    )
    result = gates_module._gate_balance_axes(
        state, ReleaseGateConfig(audit_enabled=False)
    )

    assert "hedonic_contrast" not in result.data["axes"]
    assert result.data["hedonic_evidence"] == {
        "state": "NOT_TESTED",
        "reason": "No exact-scope blinded LIKING evidence entered this gate.",
    }


def test_active_methodology_api_does_not_export_legacy_hedonic_objectives() -> None:
    forbidden = {
        "HEDONIC_TARGETS",
        "HEDONIC_WEIGHTS",
        "HedonicMaterialTarget",
        "HedonicCategory",
        "MarketSegment",
        "check_hedonic_distribution",
        "compute_hedonic_objective",
    }

    assert forbidden.isdisjoint(active_methodology.__all__)
    assert all(not hasattr(active_methodology, name) for name in forbidden)


def test_active_atelier_cannot_select_a_legacy_hedonic_methodology() -> None:
    assert all(
        "hedonic" not in f"{spec.name} {spec.philosophy}".casefold()
        for spec in active_methodology.METHODOLOGY_SPECS
    )
    selected = stage2_methodology(
        AtelierConfig(name="probe"),
        {"elements": ["hedonic", "computational"]},
    )

    assert "hedonic" not in selected["selected_method"].casefold()
    cost_selected = stage2_methodology(
        AtelierConfig(name="cost probe"),
        {"elements": ["cost", "commercial"]},
    )
    assert "Cost-Optimized Construction" in {
        cost_selected["selected_method"],
        *cost_selected["alternatives"],
    }


def test_active_iec_contract_has_no_composition_derived_hedonic_weight() -> None:
    assert not hasattr(IECHyperparameters(), "hedonic_weight")


def test_construction_gate_does_not_import_legacy_hedonic_distribution() -> None:
    source = (ROOT / "engine" / "pipeline" / "gates.py").read_text(encoding="utf-8")

    assert "check_hedonic_distribution" not in source


def test_active_oav_intelligence_exports_no_legacy_zone_hedonic_value() -> None:
    source = (ROOT / "engine" / "pipeline" / "oav_intelligence.py").read_text(
        encoding="utf-8"
    )

    assert "zone_hedonic" not in source
    assert "zone.hedonic" not in source
    assert "future_modules.family_hedonic_optimizer" not in source


def test_active_report_adapters_do_not_request_numeric_hedonic_scores() -> None:
    for relative in (
        "scripts/format_oav_report.py",
        "scripts/oav_headspace_analyze.py",
    ):
        source = (ROOT / relative).read_text(encoding="utf-8")
        assert "scores.get('hedonic'" not in source
        assert '"hedonic",' not in source


def test_active_data_spine_migration_does_not_ingest_legacy_valence() -> None:
    source = (ROOT / "engine" / "data_spine" / "migrate.py").read_text(
        encoding="utf-8"
    )

    assert "from engine.hedonic_model import HEDONIC_VALENCE" not in source
    assert "_ingest_hedonic(reg)" not in source


def test_legacy_call_surfaces_are_closed_to_historical_replay() -> None:
    replay_callers = []
    hedonic_callers = []
    for base_name in ("engine", "scripts"):
        for path in (ROOT / base_name).rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            relative = path.relative_to(ROOT).as_posix()
            if ".score_legacy_replay(" in text:
                replay_callers.append(relative)
            if "score_hedonic(" in text:
                hedonic_callers.append(relative)

    assert sorted(replay_callers) == [
        "scripts/verify_c0_physical_model_inventory.py"
    ]
    assert sorted(hedonic_callers) == [
        "engine/hedonic_model.py",
        "engine/optimizer/scoring.py",
        "scripts/verify_c0_physical_model_inventory.py",
    ]


def test_frozen_active_path_audit_receipt_matches_current_files() -> None:
    payload = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    observed = hashlib.sha256(AUDIT_PATH.read_bytes()).hexdigest()

    assert AUDIT_SIDECAR.read_text(encoding="ascii").strip() == observed
    assert payload["schema_version"] == "hedonic_active_path_audit_v1"
    assert payload["status"] == "PASS_ACTIVE_PATHS_CLOSED"
    assert payload["legacy_replay_classification"] == "LEGACY_REPLAY_ONLY"
    assert payload["liking_without_exact_scope_receipt"] == "NOT_TESTED"
    assert payload["source_hash_basis"] == "SHA256_LF_NORMALIZED_TEXT"
    assert all(value is False for value in payload["authority_flags"].values())
    assert payload["unresolved_compatibility_surfaces"]
    for relative, expected in payload["file_sha256"].items():
        assert _canonical_text_sha256(ROOT / relative) == expected
