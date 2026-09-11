import json
import subprocess
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path

import pytest

from engine.pipeline.formula_state import build_formula_state
from engine.pipeline.gates import GateResult, ReleaseGateConfig, gate_formula
from engine.pipeline.oav_authority import OAVAuthorityRequest, analyze_oav_authority


def _request(ingredients, **overrides):
    payload = dict(
        formula_name="Authority Test Formula",
        ingredients_ul=ingredients,
        batch_volume_ml=30.0,
        temperature_K=305.0,
    )
    payload.update(overrides)
    return OAVAuthorityRequest(**payload)


@pytest.fixture(scope="module", params=[False, True])
def receipt_gate(request):
    formula = {
        "name": "Receipt identity regression", "number": 1,
        "ingredients_ul": {"Javanol": 14.0}, "dilutions": {"Javanol": 0.2},
    }
    report = gate_formula(formula, ReleaseGateConfig(
        audit_enabled=False, deep_plane_diagnostics_enabled=request.param,
    ))
    oav_request = _request(
        formula["ingredients_ul"], formula_name=formula["name"],
        dilutions=formula["dilutions"], dose_receipt_sha256=report.dose_receipt.receipt_sha256,
    )
    return oav_request, report


def test_exact_receipt_identity_does_not_promote_strict_oav(receipt_gate):
    request, report = receipt_gate
    assert report.dose_receipt.status == "BOUND"
    result = analyze_oav_authority(request, gate_report=report)
    assert result.receipt_binding_status == "BOUND_GATE_RECEIPT"
    assert result.dose_receipt_sha256 == report.dose_receipt.receipt_sha256
    assert result.strict_oav_status == "ABSTAINED"
    assert result.as_dict()["authority_verdict_summary"]["release_authority"] is False
    assert report.as_dict()["dose_receipt"] == report.dose_receipt.as_dict()
    assert report.preflight["status"] != "PASS"
    plain = analyze_oav_authority(replace(request, dose_receipt_sha256=None))
    assert result.material_rows == plain.material_rows
    assert result.time_windows == plain.time_windows


@pytest.mark.parametrize("enabled", [False, True])
def test_abstained_stock_receipt_can_bind_identity_but_not_authority(enabled):
    formula = {
        "name": "Unresolved stock regression", "number": 1,
        "ingredients_ul": {"Javanol": 14.0}, "dilutions": {"Javanol": 0.1},
    }
    report = gate_formula(formula, ReleaseGateConfig(
        audit_enabled=False, deep_plane_diagnostics_enabled=enabled,
    ))
    assert report.dose_receipt.status == "ABSTAINED"
    request = _request(
        formula["ingredients_ul"], formula_name=formula["name"],
        dilutions=formula["dilutions"], dose_receipt_sha256=report.dose_receipt.receipt_sha256,
    )
    result = analyze_oav_authority(request, gate_report=report)
    assert result.receipt_binding_status == "BOUND_GATE_RECEIPT"
    assert result.strict_oav_status == "ABSTAINED"
    assert report.preflight["status"] == "FAIL"
    assert report.commercial_readiness == "NOT_RELEASE_READY"
    assert result.as_dict()["authority_verdict_summary"]["release_authority"] is False


@pytest.mark.parametrize("status", ["PASS", "FAIL"])
def test_bound_receipt_does_not_trust_cached_policy_outcomes(receipt_gate, status):
    request, report = receipt_gate
    clean = analyze_oav_authority(request, gate_report=report)
    poisoned = replace(report, gates=tuple(
        GateResult(name, status, "Fabricated cached policy", {})
        for name in ("odt_coverage", "oav_legibility", "oav_scaling",
                     "robustness_perturbation", "oav_intelligence")
    ))
    assert analyze_oav_authority(request, gate_report=poisoned).as_dict() == clean.as_dict()


def test_bound_receipt_recomputes_changed_scaling_policy(receipt_gate):
    request, report = receipt_gate
    changed = replace(request, batch_scaling_targets_ml=(1.0,))
    bound = analyze_oav_authority(changed, gate_report=report)
    plain = analyze_oav_authority(replace(changed, dose_receipt_sha256=None))
    assert bound.scaling_risk == plain.scaling_risk
    assert bound.primary_status == plain.primary_status


def test_unrequested_binding_remains_unbound(receipt_gate):
    request, report = receipt_gate
    result = analyze_oav_authority(replace(request, dose_receipt_sha256=None), gate_report=report)
    assert result.dose_receipt_sha256 is None
    assert result.receipt_binding_status == "UNBOUND"


@pytest.mark.parametrize("change", [
    {"formula_name": "Other formula"}, {"formula_uid": "Other UID"},
    {"dilutions": {"Javanol": 0.1}}, {"dilutions": {"Javanol": 0.0}},
    {"dilutions": {}}, {"ingredients_ul": {"Javanol": 14.1}},
    {"stock_specs": {"Javanol": {"carrier": "dep"}}},
    {"stock_specs": {"Javanol": {"fraction_basis": "mass_fraction"}}},
    {"stock_specs": {"Javanol": {"stock_id": "other"}}},
    {"temperature_K": 298.15}, {"batch_volume_ml": 40.0}, {"context": "blotter"},
    {"matrix_moles": {"ethanol": 0.1}, "matrix_source": "explicit", "matrix_mass_g": 4.6},
    {"dose_receipt_sha256": "0" * 64},
])
def test_bound_receipt_rejects_changed_request(receipt_gate, change):
    request, report = receipt_gate
    with pytest.raises(ValueError):
        analyze_oav_authority(replace(request, **change), gate_report=report)


@pytest.mark.parametrize("kind", [
    "missing_receipt", "receipt_inventory", "report_name", "report_hash",
    "state_receipt", "state_status", "extra_material", "state_values",
    "frame_values", "frame_checksum", "frame_origin", "missing_frame", "reordered_frames",
])
def test_bound_receipt_rejects_changed_report(receipt_gate, kind):
    request, report = receipt_gate
    state = report.formula_state
    if kind == "missing_receipt":
        report = replace(report, dose_receipt=None)
    elif kind == "receipt_inventory":
        report = replace(report, dose_receipt=replace(
            report.dose_receipt, inventory_snapshot_sha256="0" * 64,
        ))
        request = replace(request, dose_receipt_sha256=report.dose_receipt.receipt_sha256)
    elif kind == "report_name":
        report = replace(report, name="Other report")
    elif kind == "report_hash":
        report = replace(report, formula_hash="0" * 64)
    elif kind == "state_receipt":
        report = replace(report, formula_state=replace(state, dose_receipt_sha256="0" * 64))
    elif kind == "state_status":
        report = replace(report, formula_state=replace(state, dose_receipt_status="OTHER"))
    elif kind == "extra_material":
        report = replace(report, formula_state=replace(state, materials=state.materials * 2))
    elif kind == "state_values":
        report = replace(report, formula_state=replace(state, total_raw_ul=1.0))
    elif kind == "missing_frame":
        report = replace(report, simulation=report.simulation[:-1])
    elif kind == "reordered_frames":
        report = replace(report, simulation=tuple(reversed(report.simulation)))
    else:
        frame = report.simulation[-1]
        if kind == "frame_values":
            frame = replace(frame, state=replace(frame.state, total_raw_ul=123.0))
        elif kind == "frame_checksum":
            frame = replace(frame, frame_content_sha256="0" * 64)
        else:
            frame = replace(frame, source_state_sha256="0" * 64)
        report = replace(report, simulation=(*report.simulation[:-1], frame))
    with pytest.raises(ValueError):
        analyze_oav_authority(request, gate_report=report)


def test_expected_receipt_requires_report(receipt_gate):
    request, _ = receipt_gate
    with pytest.raises(ValueError, match="requires its gate report"):
        analyze_oav_authority(request)


@pytest.mark.parametrize("digest", ["", "A" * 64, "g" * 64, "0" * 63, 7])
def test_receipt_request_rejects_malformed_digest(digest):
    with pytest.raises(ValueError, match="lowercase SHA-256"):
        _request({"Javanol": 14.0}, dose_receipt_sha256=digest)


def test_oav_authority_contract_shape_and_material_rows():
    result = analyze_oav_authority(
        _request(
            {
                "Bergamot FCF": 1200.0,
                "Lavender EO": 700.0,
                "Linalyl Acetate": 600.0,
                "Hedione": 900.0,
                "Coumarin": 300.0,
                "Evernyl": 20.0,
                "Iso E Super": 1500.0,
                "Vetiver EO": 300.0,
                "Habanolide": 480.0,
            },
            family_archetype="aromatic_fougere",
        )
    )

    payload = result.as_dict()

    assert set(payload) == {
        "request_summary",
        "current_batch_assumptions",
        "material_oav_table",
        "family_envelope_table",
        "dominant_oav_leaders_by_window",
        "oav_intelligence",
        "authority_verdict_summary",
        "downstream_integration",
    }
    assert payload["request_summary"]["formula_name"] == "Authority Test Formula"
    assert payload["current_batch_assumptions"]["backend"] == "engine.pipeline.formula_state + engine.pipeline.simulator"
    assert payload["material_oav_table"]
    assert payload["material_oav_table"][0]["oav"] >= payload["material_oav_table"][-1]["oav"]
    assert payload["oav_intelligence"]["intelligence_status"] in {"PASS", "WARN", "FAIL"}
    assert {
        "name",
        "canonical_name",
        "family",
        "note",
        "raw_ul",
        "dilution",
        "active_ul",
        "vapor_ppm",
        "odt_air_ppm",
        "odt_source",
        "oav",
        "intensity",
    } <= set(payload["material_oav_table"][0])
    assert result.primary_status in {"PASS", "WARN", "FAIL"}


def test_oav_authority_family_envelopes_and_time_windows():
    result = analyze_oav_authority(
        _request(
            {
                "Bergamot FCF": 2500.0,
                "Iso E Super": 2500.0,
                "Habanolide": 1000.0,
            }
        )
    )

    labels = [window.label for window in result.time_windows]
    assert labels == ["opening", "top", "heart", "late_heart", "drydown"]
    assert all(window.family_envelope for window in result.time_windows)
    assert all(isinstance(window.dominant_oav, list) for window in result.time_windows)
    assert result.top_family_drift >= 0.0
    # Bergamot opens as the leader, then the bounded-step temporal screen lets
    # Iso E Super overtake it as the volatile citrus pool declines.
    assert result.dominant_leaders_changed is True
    assert result.time_windows[0].dominant_oav[0]["material"] == "Bergamot FCF"
    assert result.time_windows[-1].dominant_oav[0]["material"] == "Iso E Super"


def test_oav_authority_missing_odt_blocks():
    result = analyze_oav_authority(
        _request(
            {
                "Mystery Molecule": 3000.0,
                "Hedione": 1500.0,
                "Iso E Super": 1500.0,
            }
        )
    )

    assert result.primary_status == "FAIL"
    assert "Mystery Molecule" in result.missing_odt_materials
    assert result.odt_coverage["status"] == "FAIL"
    assert result.blocking_reasons


def test_oav_authority_low_legibility_blocks():
    result = analyze_oav_authority(
        _request(
            {
                "Vanillin": 3000.0,
                "Coumarin": 2000.0,
                "Benzyl Salicylate": 1000.0,
            }
        )
    )

    assert result.primary_status == "FAIL"
    assert result.oav_legibility["status"] == "PASS"
    assert result.downstream_integration["perceptible_material_count"] == 3
    assert result.intelligence_blocking_reasons


def test_oav_authority_high_subliminal_mass_warns():
    result = analyze_oav_authority(
        _request(
            {
                "Hedione": 1000.0,
                "Iso E Super": 1000.0,
                "Linalyl Acetate": 1000.0,
                "Dipropylene Glycol": 3000.0,
            }
        )
    )

    assert result.primary_status == "WARN"
    assert result.oav_legibility["status"] == "WARN"
    assert result.subliminal_mass_ratio > 0.45
    assert result.warning_reasons


def test_oav_authority_scaling_blocker_is_reflected():
    result = analyze_oav_authority(
        _request(
            {
                "Hedione": 5999.0,
                "Geosmin": 1.0,
            },
            batch_scaling_targets_ml=(15.0,),
        )
    )

    assert result.primary_status == "FAIL"
    assert result.scaling_risk["status"] == "FAIL"
    assert result.scaling_risk["data"]["findings"]


def test_oav_authority_json_serialization_is_deterministic():
    result = analyze_oav_authority(
        _request(
            {
                "Bergamot FCF": 1200.0,
                "Lavender EO": 700.0,
                "Linalyl Acetate": 600.0,
                "Hedione": 900.0,
                "Coumarin": 300.0,
                "Evernyl": 20.0,
                "Iso E Super": 1500.0,
                "Vetiver EO": 300.0,
                "Habanolide": 480.0,
            }
        )
    )

    first = json.dumps(result.as_dict(), sort_keys=True)
    second = json.dumps(result.as_dict(), sort_keys=True)

    assert first == second


def test_odt_data_sources_have_no_duplicate_keys():
    """ODT data now lives in data/engine_data/*.json; guard against duplicate keys."""
    from engine.material_data_loader import engine_data_path

    duplicates: dict[str, int] = {}

    def _collect_duplicates(pairs):
        counts = Counter(key for key, _ in pairs)
        for key, count in counts.items():
            if count > 1:
                duplicates[key] = count
        return dict(pairs)

    json.loads(
        engine_data_path("odor_thresholds").read_text(encoding="utf-8"),
        object_pairs_hook=_collect_duplicates,
    )
    assert duplicates == {}


def test_uncovered_naturals_and_opaque_preblends_never_use_monomolecular_oav():
    state = build_formula_state(
        {
            "Spike Lavender EO": 100.0,
            "Jasmine FO": 100.0,
            "Lavender EO": 100.0,
        },
        batch_volume_ml=10.0,
    )
    rows = {row.name: row for row in state.materials}

    for name in ("Spike Lavender EO", "Jasmine FO"):
        assert rows[name].oav is None
        assert rows[name].intensity is None
        assert rows[name].sources["oav_model"] == (
            "unknown:composite_decomposition_missing"
        )

    assert rows["Lavender EO"].oav is not None
    assert rows["Lavender EO"].sources["oav_model"] == (
        "literature:natural_composite_gc_o"
    )


def test_natural_oav_models_keep_absolute_and_co2_extract_distinct_and_resolved():
    state = build_formula_state(
        {
            "Lime Distilled EO": 140.0,
            "Cocoa Absolute": 100.0,
            "Cocoa CO2 Extract": 250.0,
        },
        {"Cocoa CO2 Extract": 0.077},
        batch_volume_ml=30.0,
    )
    rows = {row.name: row for row in state.materials}

    assert rows["Lime Distilled EO"].oav is not None
    assert rows["Lime Distilled EO"].oav > 0
    assert rows["Lime Distilled EO"].sources["oav_model"] == (
        "literature:natural_composite_gc_o"
    )
    for name in ("Cocoa Absolute", "Cocoa CO2 Extract"):
        assert rows[name].oav is not None
        assert rows[name].oav > 0
        assert rows[name].sources["oav_model"] == (
            "literature:natural_composite_gc_o"
        )
    assert rows["Cocoa Absolute"].oav > rows["Cocoa CO2 Extract"].oav
    assert rows["Cocoa Absolute"].canonical_name == "cocoa absolute"
    assert rows["Cocoa Absolute"].dilution == 1.0
    assert rows["Cocoa Absolute"].active_ul == 100.0
    assert rows["Cocoa CO2 Extract"].canonical_name == "cocoa co2 extract"
    assert rows["Cocoa CO2 Extract"].dilution == 0.077
    assert rows["Cocoa CO2 Extract"].active_ul == 19.25


def test_pipeline_analysis_prints_unknown_oav_without_calling_it_subthreshold(
    tmp_path: Path,
):
    diagnostic_sentinel = "END-OF-DIAGNOSTIC-DETAIL"
    payload = {
        "formulas": [
            {
                "gates": [
                    {
                        "gate": "diagnostic",
                        "status": "WARN",
                        "detail": "x" * 180 + diagnostic_sentinel,
                    }
                ],
                "time_series": [],
                "formula_state": {
                    "batch_volume_ml": 30.0,
                    "total_active_ul": 119.25,
                    "note_distribution": {"top": 83.9, "heart": 0.0, "base": 16.1},
                    "materials": [
                        {
                            "name": "Linalool",
                            "oav": 12.0,
                            "note": "top",
                            "family": "citrus",
                            "vp_pure_pa": 21.3,
                            "vapor_ppm": 0.018,
                            "odt_air_ppm": 0.0015,
                            "active_g": 0.1,
                            "active_ul": 100.0,
                            "mole_fraction": 0.01,
                            "profile_name": "Linalool",
                            "ifra_limit_pct": 10.0,
                        },
                        {
                            "name": "Cocoa CO2 Extract",
                            "oav": None,
                            "note": "base",
                            "family": "gourmand",
                            "vp_pure_pa": 0.01,
                            "vapor_ppm": 0.0003,
                            "odt_air_ppm": 0.003,
                            "active_g": 0.01925,
                            "active_ul": 19.25,
                            "mole_fraction": 0.001,
                            "profile_name": "Cocoa CO2 Extract",
                        },
                    ],
                },
            }
        ]
    }
    input_path = tmp_path / "pipeline.json"
    input_path.write_text(json.dumps(payload), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/format_pipeline_analysis.py",
            "--input",
            str(input_path),
        ],
        cwd=Path(__file__).resolve().parents[1],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert "Cocoa CO2 Extract" in result.stdout
    assert "UNKNOWN" in result.stdout
    assert "SUB: Cocoa CO2 Extract" not in result.stdout
    assert "IFRA: Linalool" not in result.stdout
    assert diagnostic_sentinel in result.stdout


def test_pipeline_analysis_labels_distribution_and_longevity_as_proxies(
    tmp_path: Path,
):
    materials = [
        {
            "name": "Aromatic Leader",
            "oav": 1000.0,
            "note": "top",
            "family": "aromatic",
            "vp_pure_pa": 10.0,
            "vapor_ppm": 8.0,
            "odt_air_ppm": 0.008,
            "active_g": 0.5,
            "active_ul": 500.0,
            "mole_fraction": 0.05,
            "profile_name": "Aromatic Leader",
        },
        {
            "name": "Base Wood",
            "oav": 10.0,
            "note": "base",
            "family": "woody",
            "vp_pure_pa": 0.01,
            "vapor_ppm": 0.01,
            "odt_air_ppm": 0.001,
            "active_g": 0.5,
            "active_ul": 500.0,
            "mole_fraction": 0.05,
            "profile_name": "Base Wood",
        },
    ]
    labels = ("opening", "top", "heart", "late_heart", "drydown")
    seconds = (0.0, 300.0, 1800.0, 7200.0, 14400.0)
    time_series = []
    for index, (label, t_seconds) in enumerate(zip(labels, seconds)):
        state_materials = [dict(material) for material in materials]
        state_materials[0]["oav"] = 1000.0 - index * 100.0
        state_materials[1]["oav"] = 10.0
        time_series.append(
            {
                "label": label,
                "t_seconds": t_seconds,
                "dominant_oav": [
                    {
                        "material": state_materials[0]["name"],
                        "oav": state_materials[0]["oav"],
                    }
                ],
                "state": {
                    "materials": state_materials,
                    "note_distribution": {"top": 50.0, "heart": 0.0, "base": 50.0},
                    "total_raw_ul": 1000.0 - index * 25.0,
                    "total_vapor_ppm": 10.0 - index,
                },
            }
        )

    payload = {
        "formulas": [
            {
                "gates": [],
                "time_series": time_series,
                "formula_state": {
                    "batch_volume_ml": 30.0,
                    "total_active_ul": 1000.0,
                    "note_distribution": {"top": 50.0, "heart": 0.0, "base": 50.0},
                    "materials": materials,
                },
            }
        ]
    }
    input_path = tmp_path / "pipeline.json"
    input_path.write_text(json.dumps(payload), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/format_pipeline_analysis.py",
            "--input",
            str(input_path),
        ],
        cwd=Path(__file__).resolve().parents[1],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert "active note distribution" in result.stdout
    assert "of headspace" not in result.stdout
    assert "Heuristic, unvalidated skin-life proxy" not in result.stdout
    assert "Uncalibrated loss index" in result.stdout
    assert "Absolute skin life: unavailable" in result.stdout
    assert "remaining index is not measured evaporation" in result.stdout
    assert "citrus (OAV" not in result.stdout
    assert "Aromatic Leader leads at OAV" in result.stdout
    assert "authentic for vetiver" not in result.stdout
