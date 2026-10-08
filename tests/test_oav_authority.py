import json
import re
import subprocess
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path

import pytest

from engine.pipeline.formula_state import build_formula_state
from engine.pipeline.gates import GateReport, GateResult
from engine.pipeline.natural_absolute_decomposition import get_composite_metadata
from engine.pipeline.oav_authority import OAVAuthorityRequest, analyze_oav_authority
from engine.pipeline.simulator import simulate_formula


def _request(ingredients, **overrides):
    payload = dict(
        formula_name="Authority Test Formula",
        ingredients_ul=ingredients,
        batch_volume_ml=30.0,
        temperature_K=305.0,
    )
    payload.update(overrides)
    return OAVAuthorityRequest(**payload)


def _bound_gate_report(request, *gates):
    state = build_formula_state(
        request.ingredients_ul,
        request.dilutions,
        batch_volume_ml=request.batch_volume_ml,
        temperature_K=request.temperature_K,
        context=request.context,
        matrix_moles=request.matrix_moles,
        matrix_mass_g=request.matrix_mass_g,
        matrix_source=request.matrix_source,
    )
    simulation = tuple(
        simulate_formula(
            request.ingredients_ul,
            request.dilutions,
            batch_volume_ml=request.batch_volume_ml,
            temperature_K=request.temperature_K,
            context=request.context,
            windows=request.target_windows,
            initial_state=state,
        )
    )
    return GateReport(
        number=1,
        name=request.formula_name,
        status="PASS",
        gates=tuple(gates),
        formula_state=state,
        simulation=simulation,
        confidence={},
        formula_hash="test",
        calibration_summary={},
        commercial_readiness="NOT_READY",
        config_summary={
            "batch_volume_ml": request.batch_volume_ml,
            "temperature_K": request.temperature_K,
            "matrix_components_moles": [
                [name, value] for name, value in sorted(request.matrix_moles.items())
            ],
            "matrix_mass_g": request.matrix_mass_g,
            "matrix_source": request.matrix_source,
            "batch_scaling_targets_ml": list(request.batch_scaling_targets_ml),
        },
    )


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


def test_oav_authority_unknowns_remain_unknown_in_aggregates_and_rank():
    result = analyze_oav_authority(
        _request(
            {
                "Mystery Molecule": 3000.0,
                "Hedione": 1500.0,
                "Iso E Super": 1500.0,
            }
        )
    )
    mystery = next(row for row in result.state.materials if row.name == "Mystery Molecule")
    mystery_family = mystery.family or mystery.canonical_name

    assert result.screening_oav_coverage["status"] == "INCOMPLETE"
    assert result.unknown_screening_oav_materials == ("Mystery Molecule",)
    assert result.perceptible_material_count is None
    assert result.known_perceptible_material_count == 2
    assert result.subliminal_mass_ratio is None
    assert result.known_subliminal_mass_ratio_lower_bound == 0.0
    assert result.top_family_drift is None
    assert result.authoritative_rank_score is None
    assert result.authority_rank_status.startswith("WITHHELD")
    assert isinstance(result.screening_diagnostic_score, float)

    opening = result.time_windows[0]
    assert mystery_family not in opening.family_envelope
    assert opening.family_envelope_coverage[mystery_family]["status"] == "INCOMPLETE"
    assert opening.family_envelope_coverage[mystery_family]["unknown_materials"] == [
        "Mystery Molecule"
    ]
    assert opening.perceptible_material_count is None
    assert opening.subliminal_mass_ratio is None
    assert opening.unknown_screening_oav_materials == ("Mystery Molecule",)

    summary = result.authority_verdict_summary
    assert summary["authority_rank_score"] is None
    assert summary["screening_diagnostic_score"] == pytest.approx(
        result.screening_diagnostic_score
    )
    assert summary["rank_semantics"].endswith("NOT_BEAUTY_OR_PLEASANTNESS_AUTHORITY")
    assert summary["eligible_as_measured_evaluator_authority"] is False
    assert summary["beauty_authorized"] is False
    assert summary["pleasantness_authorized"] is False
    assert summary["liking_authorized"] is False


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


def test_oav_authority_reuses_canonical_scaling_gate_without_recomputing(monkeypatch):
    request = _request(
        {"Hedione": 5999.0, "Geosmin": 1.0},
        batch_scaling_targets_ml=(15.0,),
    )
    provided_scaling = GateResult(
        gate="oav_scaling_guard",
        status="PASS",
        detail="provided scaling result",
        data={"findings": [{"source": "gate_report"}]},
    )
    report = _bound_gate_report(request, provided_scaling)
    calls = 0

    def fail_if_recomputed(*args, **kwargs):
        nonlocal calls
        calls += 1
        raise AssertionError("scaling gate was recomputed despite a supplied gate report")

    monkeypatch.setattr(
        "engine.pipeline.oav_authority._gate_oav_scaling",
        fail_if_recomputed,
    )

    result = analyze_oav_authority(request, gate_report=report)

    assert calls == 0
    assert result.scaling_risk == provided_scaling.as_dict()


def test_oav_authority_rejects_gate_report_binding_mismatches():
    request = _request(
        {"Hedione": 5999.0, "Geosmin": 1.0},
        dilutions={"Hedione": 1.0, "Geosmin": 0.01},
        batch_scaling_targets_ml=(15.0,),
        context="skin",
        matrix_moles={"ethanol": 1.0},
        matrix_mass_g=10.0,
        matrix_source="explicit",
    )
    report = _bound_gate_report(request)
    mismatches = (
        (
            "dilutions",
            replace(request, dilutions={"Hedione": 1.0, "Geosmin": 0.02}),
        ),
        ("batch volume", replace(request, batch_volume_ml=31.0)),
        ("temperature", replace(request, temperature_K=304.0)),
        ("context", replace(request, context="blotter")),
        ("matrix components", replace(request, matrix_moles={"ethanol": 2.0})),
        ("matrix mass", replace(request, matrix_mass_g=11.0)),
        ("matrix source", replace(request, matrix_source="estimated")),
        ("scaling targets", replace(request, batch_scaling_targets_ml=(20.0,))),
    )

    for message, mismatched_request in mismatches:
        with pytest.raises(ValueError, match=message):
            analyze_oav_authority(mismatched_request, gate_report=report)


def test_oav_authority_rejects_legacy_gate_report_without_explicit_binding():
    request = _request({"Hedione": 5999.0, "Geosmin": 1.0})
    report = replace(_bound_gate_report(request), config_summary={})

    with pytest.raises(ValueError, match="lacks explicit reuse binding"):
        analyze_oav_authority(request, gate_report=report)


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


def test_odt_source_sections_have_no_duplicate_textual_keys():
    text = Path("engine/odor_thresholds.py").read_text(encoding="utf-8")
    odt_data_start = text.index("ODT_DATA: dict[str, dict] = ")
    odt_verification_start = text.index("ODT_VERIFICATION: dict[str, dict] = ")

    def extract_dict_literal(source: str, assignment_start: int) -> str:
        brace_start = source.index("{", assignment_start)
        depth = 0
        for idx in range(brace_start, len(source)):
            char = source[idx]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return source[brace_start : idx + 1]
        raise AssertionError("Unclosed dict literal in odor_thresholds.py")

    odt_data_block = extract_dict_literal(text, odt_data_start)
    odt_verification_block = extract_dict_literal(text, odt_verification_start)

    def duplicate_keys(block: str) -> dict[str, int]:
        keys = re.findall(r'^\s*"([^"]+)"\s*:\s*\{', block, flags=re.M)
        counts = Counter(keys)
        return {key: count for key, count in counts.items() if count > 1}

    assert duplicate_keys(odt_data_block) == {}
    assert duplicate_keys(odt_verification_block) == {}


def test_uncovered_naturals_and_opaque_preblends_never_use_monomolecular_oav():
    state = build_formula_state(
        {
            "Anise EO": 100.0,
            "Jasmine FO": 100.0,
            "Lavender EO": 100.0,
        },
        batch_volume_ml=10.0,
    )
    rows = {row.name: row for row in state.materials}

    for name in ("Anise EO", "Jasmine FO"):
        assert rows[name].oav is None
        assert rows[name].intensity is None
        assert rows[name].sources["oav_model"] == (
            "unknown:composite_decomposition_missing"
        )

    assert rows["Lavender EO"].oav is not None
    assert rows["Lavender EO"].sources["oav_model"] == (
        "modeled:natural_constituent_composite"
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
        "modeled:natural_constituent_composite"
    )
    for name in ("Cocoa Absolute", "Cocoa CO2 Extract"):
        assert rows[name].oav is not None
        assert rows[name].oav > 0
        assert rows[name].sources["oav_model"] == (
            "modeled:natural_constituent_composite"
        )
    assert rows["Cocoa Absolute"].oav > rows["Cocoa CO2 Extract"].oav
    assert rows["Cocoa Absolute"].canonical_name == "cocoa absolute"
    assert rows["Cocoa Absolute"].dilution == 1.0
    assert rows["Cocoa Absolute"].active_ul == 100.0
    assert rows["Cocoa CO2 Extract"].canonical_name == "cocoa co2 extract"
    assert rows["Cocoa CO2 Extract"].dilution == 0.077
    assert rows["Cocoa CO2 Extract"].active_ul == 19.25


def test_resin_tinctures_use_generic_literature_composites_for_screening_only():
    fractions = {
        "Turkish Storax Liquidambar orientalis resin ethanol tincture": 0.20,
        "Vietnamese Benzoin Styrax tonkinensis resin ethanol tincture": 0.40,
        "Kenyan Myrrh resin ethanol tincture": 0.20,
        "Oman Frankincense resin ethanol tincture": 0.33,
    }
    state = build_formula_state(
        {name: 100.0 for name in fractions},
        fractions,
        batch_volume_ml=30.0,
    )
    rows = {row.name: row for row in state.materials}
    expected_coverage = {
        "Turkish Storax Liquidambar orientalis resin ethanol tincture": 0.1566,
        "Vietnamese Benzoin Styrax tonkinensis resin ethanol tincture": 0.6,
        "Kenyan Myrrh resin ethanol tincture": 0.0013,
        "Oman Frankincense resin ethanol tincture": 0.021485,
    }

    for name, coverage in expected_coverage.items():
        row = rows[name]
        metadata = get_composite_metadata(name)
        assert metadata is not None
        assert metadata.resolution == "literature_proxy"
        assert metadata.composition_authority == "LITERATURE_PARTIAL_PROXY"
        assert metadata.batch_specific is False
        assert metadata.characterized_fraction == coverage
        assert any("starting charge" in limit for limit in metadata.limitations)
        assert metadata.sources
        assert row.is_known is True
        assert row.oav is not None and row.oav > 0
        assert row.screening_oav == row.oav
        assert row.canonical_oav is None
        assert row.physics_status == "SCREENING_SENSITIVITY_ONLY"
        assert "NATURAL_COMPOSITE_PARTIAL" in row.physics_blockers
        assert row.sources["oav_model"] == "modeled:natural_constituent_composite"
        assert row.authoritative_active_g is None
        assert row.active_concentrate_ppm_w_w is None


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
