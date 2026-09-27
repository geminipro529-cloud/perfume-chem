"""Regression coverage for the preliminary formula inventory warning."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from engine import formula_metadata as formula_metadata_module
from engine.formula_metadata import _load_inventory_names, pipeline_preflight_guard
from engine.name_utils import normalize_name

ROOT = Path(__file__).resolve().parents[1]
FORMULA = ROOT / "formulas" / "Gin_Vetiver_Cypress_Air_Haitian_Grapefruit100_AddOnly_20260910.md"


def test_default_inventory_names_come_from_current_authority_overlay() -> None:
    normalized = {normalize_name(name) for name in _load_inventory_names()}

    assert normalize_name("Vetiver EO (Haiti)") in normalized
    assert normalize_name("Cedarwood Virginia") in normalized
    assert normalize_name("Coriander Essential Oil") in normalized
    assert normalize_name("Cinnamyl Alcohol") in normalized


def test_current_gin_vetiver_candidate_has_no_false_inventory_warning() -> None:
    result = pipeline_preflight_guard(str(FORMULA), brief="vetiver_woody")

    assert not any(
        warning.startswith("INVENTORY_MISSING:") for warning in result.warnings
    )


def _write_formula(path: Path, *, quantitative: bool = False) -> None:
    metadata = (
        "**Claim mode:** named_reference\n"
        "**Reference scope:** quantitative_similarity\n"
        if quantitative
        else ""
    )
    path.write_text(
        f"{metadata}\n# Test Formula\n\n"
        "| Material | Dilution | uL |\n"
        "|---|---:|---:|\n"
        "| Hedione | neat | 100 |\n",
        encoding="utf-8",
    )


def test_pipeline_preflight_default_still_checks_inventory_membership(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    formula_path = tmp_path / "formula.md"
    _write_formula(formula_path)
    calls: list[str] = []

    def load_inventory(path: str = "inventory.txt") -> set[str]:
        calls.append(path)
        return {"Hedione"}

    monkeypatch.setattr(formula_metadata_module, "_load_inventory_names", load_inventory)

    result = pipeline_preflight_guard(str(formula_path))

    assert calls == ["inventory.txt"]
    assert not any(warning.startswith("INVENTORY_MISSING:") for warning in result.warnings)


def test_pipeline_preflight_can_skip_only_legacy_inventory_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    formula_path = tmp_path / "formula.md"
    _write_formula(formula_path, quantitative=True)

    def fail_if_loaded(*args: object, **kwargs: object) -> set[str]:
        raise AssertionError("legacy inventory loader must be skipped")

    monkeypatch.setattr(formula_metadata_module, "_load_inventory_names", fail_if_loaded)

    result = pipeline_preflight_guard(
        str(formula_path),
        check_inventory_membership=False,
    )

    assert any(block.startswith("QUANTITATIVE_AUTHORITY:") for block in result.hard_blocks)
    assert not any(warning.startswith("INVENTORY_MISSING:") for warning in result.warnings)
    assert any(warning.startswith("COST_TICKER:") for warning in result.warnings)
    assert any(warning.startswith("EU_1545_WARN:") for warning in result.warnings)


def test_release_cli_skips_legacy_loader_and_keeps_authoritative_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    formula_path = tmp_path / "formula.md"
    _write_formula(formula_path)
    calls: list[dict[str, object]] = []
    real_guard = formula_metadata_module.pipeline_preflight_guard

    def guard_spy(*args: object, **kwargs: object):
        calls.append(dict(kwargs))
        return real_guard(*args, **kwargs)

    monkeypatch.setattr(formula_metadata_module, "pipeline_preflight_guard", guard_spy)
    monkeypatch.setattr(
        formula_metadata_module,
        "_load_inventory_names",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("release CLI called the legacy inventory loader")
        ),
    )

    import scripts.formula_release_gate as release_module

    state = SimpleNamespace(
        matrix_components_moles=(),
        matrix_mass_g=0.0,
        matrix_source="omitted",
        materials=(),
        total_vapor_ppm=0.0,
        headspace_basis="MODELED_ACTIVE_CONCENTRATE_SCREEN",
    )
    config_summary = {"family_archetype": "generic"}
    gate_list = [
        {
            "gate": "inventory_stock_contract",
            "status": "PASS",
            "detail": "authoritative stock contract",
        },
        {"gate": "quantitative_authority", "status": "PASS", "detail": ""},
        {"gate": "reference_claim_contract", "status": "PASS", "detail": ""},
        {
            "gate": "g15_oav_firewall",
            "status": "PASS",
            "detail": "",
            "data": {"pre_mix_guard": {"status": "PASS"}},
        },
    ]
    gate_result = SimpleNamespace(
        config_summary=config_summary,
        formula_state=state,
        as_dict=lambda: {
            "number": 1,
            "name": "Test Formula",
            "status": "PASS",
            "formula_hash": "a" * 64,
            "gates": gate_list,
            "confidence": {},
            "calibration_summary": {},
            "commercial_readiness": "LABORATORY_BETA",
            "preflight": {},
            "config_summary": config_summary,
            "formula_state": {"headspace_basis": state.headspace_basis},
            "time_series": [],
        },
    )
    oav_result = SimpleNamespace(
        primary_status="PASS",
        authority_rank_score=1.0,
        authoritative_rank_score=1.0,
        authority_rank_status="PASS",
        screening_diagnostic_score=1.0,
        perceptible_material_count=0,
        known_perceptible_material_count=0,
        subliminal_mass_ratio=0.0,
        known_subliminal_mass_ratio_lower_bound=0.0,
        top_family_drift=0.0,
        screening_top_family_drift=0.0,
        screening_oav_coverage={},
        canonical_oav_coverage={},
        unknown_screening_oav_materials=(),
        incomplete_canonical_physics_materials=(),
        state=state,
        material_rows=(),
        time_windows=(),
    )
    scores = SimpleNamespace(
        as_dict=lambda: {"scores": {}, "industry_10": {}, "provenance": {}}
    )
    oav_requests = []

    def analyze_oav(request, *args, **kwargs):
        oav_requests.append(request)
        return oav_result

    monkeypatch.setattr(release_module, "gate_formula", lambda *args, **kwargs: gate_result)
    monkeypatch.setattr(release_module, "analyze_oav_authority", analyze_oav)
    monkeypatch.setattr(release_module, "compute_unified_release_scores", lambda *args, **kwargs: scores)
    monkeypatch.setattr(release_module, "build_intervention_contract", lambda *args, **kwargs: {})
    monkeypatch.setattr(release_module, "render_pipeline_analysis", lambda payload: "analysis")

    rc = release_module.main(
        [
            "--formula-file",
            str(formula_path),
            "--expected-concentrate-ul",
            "100",
            "--brief",
            "generic",
            "--scaling-target-ml",
            "15",
            "--no-audit",
            "--no-append-analysis",
            "--json",
        ]
    )
    output = capsys.readouterr().out
    payload = json.loads(output)

    assert rc == 0
    assert calls == [{"brief": "generic", "check_inventory_membership": False}]
    assert oav_requests[0].batch_scaling_targets_ml == (15.0,)
    gates = payload["formulas"][0]["gates"]
    authoritative = next(gate for gate in gates if gate["gate"] == "inventory_stock_contract")
    assert authoritative["status"] == "PASS"
    runtime = payload["runtime_observability"]
    assert runtime["schema"] == "perfume_pipeline_runtime_observability_v1"
    assert runtime["authority"] == "NONDETERMINISTIC_OPERATIONAL_DIAGNOSTIC_ONLY"
    assert runtime["scientific_authority"] is False
    assert runtime["included_in_run_evidence_contract"] is False
    assert runtime["included_in_analysis_artifact"] is False
    assert runtime["included_in_audit_event"] is False
    assert runtime["formula_count"] == 1
    assert runtime["total_pre_output_ms"] >= 0
    assert set(runtime["stage_ms"]) == {
        "parse_formula_inputs",
        "metadata_preflight",
        "evidence_snapshot",
        "gate_formula",
        "oav_authority",
        "release_scoring",
        "intervention_contract",
        "compounding_protocol",
        "analysis_render",
        "manifest_binding",
        "artifact_persist_validate",
        "audit_append",
    }
    assert all(value >= 0 for value in runtime["stage_ms"].values())
    assert runtime["stage_ms"]["artifact_persist_validate"] == 0.0
    assert runtime["stage_ms"]["audit_append"] == 0.0

    manifest = payload["run_evidence_contract"]
    assert "runtime_observability" not in manifest
    assert "runtime_observability" not in payload["analysis_markdown"]
    assert payload["formulas"][0]["compounding"]["compounding_authority"] == (
        "WITHHELD"
    )
    unhashed_manifest = dict(manifest)
    artifact_hash = unhashed_manifest.pop("artifact_sha256")
    assert artifact_hash == release_module.stable_json_hash(unhashed_manifest)
