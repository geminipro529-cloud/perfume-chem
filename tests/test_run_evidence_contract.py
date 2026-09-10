from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from engine.calibration.hashing import (
    stable_formula_definition_hash,
    stable_formula_hash,
    stable_json_hash,
    stable_text_hash,
)
from engine.inventory_parser import (
    InventoryMaterial,
    parse_inventory,
    parse_stock_specification,
)
from engine.pipeline.formula_state import build_formula_state
from engine.pipeline.gates import (
    ReleaseGateConfig,
    _gate_architecture_concentration,
    _gate_carles_accord_ratio,
    _gate_coty_single_material_limit,
    _gate_perfume_knowledge,
    _safe_gate,
    gate_formula,
)
from engine.pipeline.preflight import (
    _dilution_consistency_check,
    _natural_composite_coverage_check,
    _quantitative_authority_check,
)
from engine.reference_contracts import (
    detect_reference_claim,
    evaluate_reference_contract,
)
from scripts.formula_release_gate import (
    _append_pipeline_analysis,
    _run_input_hashes,
    current_repository_evidence_hashes,
    validate_pipeline_analysis_artifact,
)
from scripts.formula_release_gate import (
    main as formula_release_main,
)
from scripts.verify_formula_workflow import (
    PIPELINE_ANALYSIS_START,
    parse_formula_markdown,
    parse_pipeline_analysis_manifest,
    split_generated_pipeline_analysis,
)


def _inventory_record(
    name: str,
    identity: str,
    fraction: float,
    *,
    basis: str,
    carrier: str = "",
) -> InventoryMaterial:
    return InventoryMaterial(
        name=name,
        identity_name=identity,
        dilution=fraction,
        category="floral",
        raw_name=f"{identity} ({fraction * 100:g}%)",
        status="owned",
        fraction_basis=basis,
        carrier=carrier,
    )


def _write_formula(path: Path, *, amount: float = 100.0) -> None:
    path.write_text(
        f"""# Bound Formula

| Material | Dilution | uL |
|---|---|---:|
| Hedione | 10% w/v in DPG | {amount:g} |
""",
        encoding="utf-8",
    )


def _persist_test_artifact(path: Path, analysis: str = "diagnostic analysis") -> None:
    formulas = parse_formula_markdown(path)
    config = ReleaseGateConfig(audit_enabled=False)
    manifest = {
        "schema": "perfume_pipeline_run_evidence_v1",
        **_run_input_hashes(formulas, config),
        "analysis_sha256": stable_text_hash(analysis),
    }
    manifest["artifact_sha256"] = stable_json_hash(manifest)
    _append_pipeline_analysis(path, analysis, manifest)


def test_stock_parser_preserves_fraction_basis_and_carrier():
    w_v = parse_stock_specification("33% w/v in DEP:EtOH")
    w_w = parse_stock_specification("10% w/w in DPG")
    neat = parse_stock_specification("neat")

    assert (w_v.fraction, w_v.fraction_basis, w_v.carrier) == (
        0.33,
        "mass_per_volume",
        "dep:etoh",
    )
    assert (w_w.fraction, w_w.fraction_basis, w_w.carrier) == (
        0.1,
        "mass_fraction",
        "dpg",
    )
    assert (neat.fraction, neat.fraction_basis, neat.declared) == (1.0, "neat", True)


@pytest.mark.parametrize("parent_mode", ["legacy_absent", "empty", "populated"])
@pytest.mark.parametrize("mutation", ["none", "remove", "alter"])
def test_bound_input_hash_preserves_parent_lineage(tmp_path, parent_mode, mutation):
    """Exercise the writer's exact input hash, including legacy field absence."""
    path = tmp_path / "binding.md"
    _write_formula(path)
    formulas = parse_formula_markdown(path)
    inputs = _run_input_hashes(
        formulas, ReleaseGateConfig(audit_enabled=False),
        parent_formulas=formulas if parent_mode == "populated" else [],
    )
    if parent_mode == "legacy_absent":
        inputs.pop("g15_parent_formula_definitions")
    manifest = {
        "schema": "perfume_pipeline_run_evidence_v1",
        "binding_schema": "formula-artifact-binding-v1",
        "renderer_version": "formula-release-gate-v1",
        **inputs,
        "analysis_input_sha256": stable_json_hash(inputs),
        "analysis_sha256": stable_text_hash("diagnostic analysis"),
        "generated_at_utc": "2026-09-09T00:00:00+00:00",
        "repository_commit": "UNAVAILABLE",
        "canonical_records": [{
            "record_id": "formula:1:bound-formula",
            "record_version": 1,
            "canonical_content_sha256": inputs["formula_definitions"][0]["sha256"],
        }],
    }
    if mutation == "remove":
        manifest.pop("g15_parent_formula_definitions", None)
    elif mutation == "alter":
        manifest["g15_parent_formula_definitions"] = [{
            "number": 1, "name": "Different parent", "sha256": "0" * 64,
        }]
    # Recompute the outer hash: the inner binding must still catch lineage edits.
    manifest["artifact_sha256"] = stable_json_hash(manifest)
    original = path.read_bytes()
    invalid = mutation == "alter" or (
        mutation == "remove" and parent_mode != "legacy_absent"
    )
    if invalid:
        with pytest.raises(RuntimeError, match="analysis_input_hash"):
            _append_pipeline_analysis(path, "diagnostic analysis", manifest)
        assert path.read_bytes() == original
    else:
        _append_pipeline_analysis(path, "diagnostic analysis", manifest)
        assert validate_pipeline_analysis_artifact(path)["status"] == "CURRENT"


def test_stock_parser_does_not_invent_carrier_from_preparation_volume():
    stock = parse_stock_specification("30% w/v, 3 g in 10 mL")

    assert stock.fraction == pytest.approx(0.30)
    assert stock.fraction_basis == "mass_per_volume"
    assert stock.carrier == ""


def test_inventory_comment_percentages_cannot_change_stock_fraction(tmp_path):
    inventory_path = tmp_path / "inventory.txt"
    inventory_path.write_text(
        """--- RESINS ---
- Olibanum Resinoid (viscous, 3 g)  # neat supplier form; about 30% carrier added during processing
""",
        encoding="utf-8",
    )

    record = parse_inventory(inventory_path)[0]

    assert record.name == "Olibanum Resinoid"
    assert record.dilution == 1.0
    assert record.fraction_basis == "neat"


def test_osmanthus_stock_substitution_is_hard_failed_and_reports_5_5x_impact(
    monkeypatch,
):
    inventory = [
        _inventory_record(
            "Osmanthus Absolute",
            "Osmanthus Absolute",
            0.1,
            basis="volume_fraction",
            carrier="dpg",
        ),
        _inventory_record(
            "Osmanthus Absolute",
            "Osmanthus Absolute (volume grade)",
            1.0,
            basis="neat",
        ),
    ]
    monkeypatch.setattr(
        "engine.pipeline.preflight.parse_current_inventory",
        lambda **_kwargs: inventory,
    )
    formula = {
        "ingredients_ul": {
            "Osmanthus Absolute": 300.0,
            "Osmanthus Absolute (volume grade)": 300.0,
        },
        "dilutions": {
            "Osmanthus Absolute": 0.1,
            "Osmanthus Absolute (volume grade)": 0.1,
        },
        "stock_specs": {
            "Osmanthus Absolute": {
                "fraction": 0.1,
                "fraction_basis": "volume_fraction",
                "carrier": "dpg",
                "declared": True,
            },
            "Osmanthus Absolute (volume grade)": {
                "fraction": 0.1,
                "fraction_basis": "volume_fraction",
                "carrier": "dpg",
                "declared": True,
            },
        },
    }

    check = _dilution_consistency_check(formula)

    assert check.status == "FAIL"
    mismatch = next(
        issue
        for issue in check.data["issues"]
        if issue["material"] == "Osmanthus Absolute (volume grade)"
    )
    assert mismatch["reason"] == "stock_fraction_mismatch"
    assert mismatch["active_multiplier_if_live_stock_used"] == [10.0]
    assert check.data["active_impact"] == {
        "declared_active_ul": 60.0,
        "live_projection_complete": True,
        "projected_live_active_ul": 330.0,
        "active_multiplier_if_live_stocks_used": 5.5,
    }
    assert check.data["active_impact_by_inventory_material"][
        "Osmanthus Absolute"
    ]["active_multiplier_if_live_stocks_used"] == 5.5


def test_incident_contracts_are_wired_into_the_release_gate(monkeypatch):
    inventory = [
        _inventory_record(
            "Osmanthus Absolute",
            "Osmanthus Absolute",
            0.1,
            basis="volume_fraction",
            carrier="dpg",
        ),
        _inventory_record(
            "Osmanthus Absolute",
            "Osmanthus Absolute (volume grade)",
            1.0,
            basis="neat",
        ),
    ]
    monkeypatch.setattr(
        "engine.pipeline.preflight.parse_current_inventory",
        lambda **_kwargs: inventory,
    )
    formula = {
        "number": 1,
        "name": "Osmanthus Explorer",
        "body": "Designed similar to Montblanc Explorer ratios.",
        "ingredients_ul": {
            "Osmanthus Absolute": 300.0,
            "Osmanthus Absolute (volume grade)": 300.0,
        },
        "dilutions": {
            "Osmanthus Absolute": 0.1,
            "Osmanthus Absolute (volume grade)": 0.1,
        },
        "stock_specs": {
            "Osmanthus Absolute": {
                "fraction": 0.1,
                "fraction_basis": "volume_fraction",
                "carrier": "dpg",
                "declared": True,
            },
            "Osmanthus Absolute (volume grade)": {
                "fraction": 0.1,
                "fraction_basis": "volume_fraction",
                "carrier": "dpg",
                "declared": True,
            },
        },
    }

    report = gate_formula(
        formula,
        ReleaseGateConfig(
            expected_concentrate_ul=600.0,
            brief="generic",
            audit_enabled=False,
        ),
    )
    gates = {gate.gate: gate for gate in report.gates}

    assert gates["inventory_stock_contract"].status == "FAIL"
    assert gates["quantitative_authority"].status == "FAIL"
    assert gates["reference_claim_contract"].status == "FAIL"
    assert report.status == "FAIL"


def test_missing_osmanthus_eo_cannot_be_satisfied_by_an_absolute(monkeypatch):
    inventory = [
        _inventory_record(
            "Osmanthus Absolute",
            "Osmanthus Absolute",
            0.1,
            basis="volume_fraction",
            carrier="dpg",
        )
    ]
    monkeypatch.setattr(
        "engine.pipeline.preflight.parse_current_inventory",
        lambda **_kwargs: inventory,
    )
    formula = {
        "ingredients_ul": {"Osmanthus EO": 100.0},
        "dilutions": {"Osmanthus EO": 1.0},
        "stock_specs": {
            "Osmanthus EO": {
                "fraction": 1.0,
                "fraction_basis": "neat",
                "carrier": "",
                "declared": True,
            }
        },
    }

    check = _dilution_consistency_check(formula)

    assert check.status == "FAIL"
    assert check.data["issues"] == [
        {"material": "Osmanthus EO", "reason": "not_in_inventory"}
    ]


def test_exact_ppm_requires_a_complete_physical_stock_chain():
    no_basis = build_formula_state(
        {"Hedione": 1000.0, "Iso E Super": 1000.0},
        {"Hedione": 1.0, "Iso E Super": 1.0},
    )
    exact = build_formula_state(
        {"Hedione": 1000.0, "Iso E Super": 1000.0},
        {"Hedione": 1.0, "Iso E Super": 1.0},
        stock_specs={
            "Hedione": {
                "fraction": 1.0,
                "fraction_basis": "mass_per_volume",
                "declared": True,
            },
            "Iso E Super": {
                "fraction": 1.0,
                "fraction_basis": "mass_per_volume",
                "declared": True,
            },
        },
    )

    assert no_basis.exact_mass_ppm_available is False
    assert (
        no_basis.quantitative_authority["headspace_oav"]
        == "MODELED_ACTIVE_CONCENTRATE_SCREEN"
    )
    assert _quantitative_authority_check(no_basis, require_exact_ppm=False).status == "WARN"
    assert _quantitative_authority_check(no_basis, require_exact_ppm=True).status == "FAIL"
    assert exact.exact_mass_ppm_available is True
    assert [m.active_concentrate_ppm_w_w for m in exact.materials] == [500_000.0, 500_000.0]


def test_natural_without_composite_decomposition_is_a_hard_failure():
    state = build_formula_state({"Imaginary Flower Absolute": 100.0})

    check = _natural_composite_coverage_check(state)

    assert check.status == "FAIL"
    assert check.data["materials"] == ["Imaginary Flower Absolute"]


def test_named_reference_prose_requires_explicit_versioned_contract():
    formula = {
        "name": "Osmanthus Explorer",
        "body": "Designed similar to Montblanc Explorer ratios.",
    }

    detection = detect_reference_claim(formula)

    assert detection.status == "FAIL"
    assert detection.scope == "quantitative_similarity"
    assert detection.quantitative_requested is True
    assert "without explicit" in detection.detail


def test_official_note_contract_authorizes_architecture_only():
    formula = {
        "name": "Explorer Architecture Study",
        "body": """**Claim mode:** named_reference
**Reference contract:** montblanc_explorer_official_notes_v1
**Reference scope:** architecture
""",
    }
    state = build_formula_state(
        {
            "Bergamot FCF": 100.0,
            "Pink Pepper EO": 50.0,
            "Vetiver EO": 100.0,
            "Javanol": 20.0,
            "Patchouli EO": 100.0,
            "Ambrox Super": 100.0,
        }
    )

    result = evaluate_reference_contract(formula, state)

    assert result["status"] == "PASS"
    assert result["data"]["evaluations"][0]["evidence_class"].endswith(
        "architecture_only"
    )

    formula["body"] = formula["body"].replace("architecture", "sensory_similarity")
    rejected = evaluate_reference_contract(formula, state)
    assert rejected["status"] == "FAIL"
    assert "cannot authorize sensory_similarity" in rejected["detail"]


def test_prada_lhomme_contract_requires_every_official_architecture_group():
    formula = {
        "name": "Prada L'Homme Architecture Control",
        "body": """**Claim mode:** named_reference
**Reference contract:** prada_lhomme_official_notes_v1
**Reference scope:** architecture
""",
    }
    complete = build_formula_state(
        {
            "Neroli EO": 50.0,
            "Alpha Ionone": 100.0,
            "Geranium EO": 50.0,
            "Black Pepper EO": 10.0,
            "Ambrofix": 100.0,
            "Cedarwood oil Virginia": 100.0,
            "Patchouli EO": 50.0,
        }
    )
    missing_patchouli = build_formula_state(
        {
            "Neroli EO": 50.0,
            "Alpha Ionone": 100.0,
            "Geranium EO": 50.0,
            "Black Pepper EO": 10.0,
            "Ambrofix": 100.0,
            "Cedarwood oil Virginia": 100.0,
        }
    )

    assert evaluate_reference_contract(formula, complete)["status"] == "PASS"
    rejected = evaluate_reference_contract(formula, missing_patchouli)
    assert rejected["status"] == "FAIL"
    assert "patchouli" in rejected["detail"]


def test_nonreference_use_of_explorer_word_remains_unclaimed():
    detection = detect_reference_claim(
        {"name": "Forest Explorer", "body": "A walk through wet cedar."}
    )

    assert detection.status == "PASS"
    assert detection.mode == "unclaimed"


def test_unclaimed_metadata_cannot_launder_named_ratio_prose():
    detection = detect_reference_claim(
        {
            "name": "Study",
            "body": """**Claim mode:** unclaimed
Designed similar to Montblanc Explorer ratios.
""",
        }
    )

    assert detection.status == "FAIL"
    assert "still makes" in detection.detail


def test_hard_gate_exceptions_fail_closed_while_aesthetic_exceptions_warn():
    def explode():
        raise RuntimeError("broken")

    assert _safe_gate(explode, "inventory_stock_contract").status == "FAIL"
    assert _safe_gate(explode, "ellena_legibility").status == "WARN"


def test_generic_brief_does_not_infer_a_named_family_from_layer_balance():
    state = build_formula_state(
        {"Iso E Super": 3000.0, "Ambrox Super": 2000.0, "Hedione": 1000.0}
    )

    gate = _gate_perfume_knowledge(state, ReleaseGateConfig(brief="generic"))

    assert gate.status == "WARN"
    assert gate.data["family"] == "generic"
    assert gate.data["family_source"] == "not_inferred"


def test_carles_ratio_uses_active_ppm_and_is_independent_of_oav():
    state = build_formula_state(
        {"Hedione": 1000.0, "Iso E Super": 100.0},
        {"Hedione": 1.0, "Iso E Super": 1.0},
        stock_specs={
            name: {
                "fraction": 1.0,
                "fraction_basis": "mass_per_volume",
                "declared": True,
            }
            for name in ("Hedione", "Iso E Super")
        },
    )
    altered = replace(
        state,
        materials=tuple(
            replace(material, oav=1e12 if index == 0 else 1e-12)
            for index, material in enumerate(state.materials)
        ),
    )

    original_gate = _gate_carles_accord_ratio(state, ReleaseGateConfig())
    altered_gate = _gate_carles_accord_ratio(altered, ReleaseGateConfig())

    assert original_gate.as_dict() == altered_gate.as_dict()
    assert original_gate.data["metric"] == "active_concentrate_ppm_w_w"
    assert "10:1" in original_gate.detail


def test_coty_share_uses_active_mass_not_raw_stock_volume():
    ingredients = {
        "Ambrox Super": 2400.0,
        "Hedione": 800.0,
        "Iso E Super": 800.0,
        "Ethylene Brassylate": 800.0,
    }
    dilutions = {
        "Ambrox Super": 0.33,
        "Hedione": 1.0,
        "Iso E Super": 1.0,
        "Ethylene Brassylate": 1.0,
    }
    state = build_formula_state(
        ingredients,
        dilutions,
        stock_specs={
            name: {
                "fraction": dilution,
                "fraction_basis": "mass_per_volume",
                "declared": True,
            }
            for name, dilution in dilutions.items()
        },
    )

    assert ingredients["Ambrox Super"] / sum(ingredients.values()) == 0.5
    assert state.active_mass_percentages()["Ambrox Super"] == pytest.approx(24.812, abs=0.001)
    assert _gate_coty_single_material_limit(state, ReleaseGateConfig()).status == "PASS"


def test_architecture_concentration_exposes_the_incident_top_five_share():
    state = build_formula_state(
        {
            "Hedione HC": 870.0,
            "Ambrox Super": 2400.0,
            "Iso E Super": 400.0,
            "Ethylene Brassylate": 360.0,
            "Zenolide": 300.0,
            "Clearwood": 120.0,
            "Dihydromyrcenol": 50.0,
            "Vetival": 50.0,
            "Osmanthus Absolute": 300.0,
            "Osmanthus Absolute (volume grade)": 300.0,
            "Bergamot FCF": 25.0,
            "Grapefruit FCF": 15.0,
            "Petitgrain EO Paraguay": 30.0,
            "Allyl Cyclohexyl Propionate": 80.0,
            "Dynascone": 15.0,
            "Javanol": 8.0,
            "Ambrettolide": 100.0,
            "Labdanum Resinoid": 100.0,
        },
        {
            "Ambrox Super": 0.33,
            "Osmanthus Absolute": 0.1,
            "Osmanthus Absolute (volume grade)": 0.1,
            "Allyl Cyclohexyl Propionate": 0.1,
            "Dynascone": 0.1,
            "Ambrettolide": 0.1,
            "Labdanum Resinoid": 0.1,
        },
    )

    gate = _gate_architecture_concentration(state)

    assert gate.status == "WARN"
    assert gate.data["basis"] == "estimated_active_volume_fraction"
    assert gate.data["top_5_pct"] == pytest.approx(87.538, abs=0.001)


def test_legacy_analysis_is_excluded_from_formula_definition(tmp_path):
    path = tmp_path / "legacy.md"
    path.write_text(
        """# Current Formula

| Material | Dilution | uL |
|---|---|---:|
| Hedione | neat | 100 |

## Pipeline Analysis (obsolete run)

| Material | Dilution | uL |
|---|---|---:|
| Iso E Super | neat | 9999 |
""",
        encoding="utf-8",
    )

    formula = parse_formula_markdown(path)[0]

    assert formula["ingredients_ul"] == {"Hedione": 100.0}
    assert "Pipeline Analysis" not in formula["body"]
    assert formula["embedded_analysis"]["format"] == "legacy_unbound"


def test_v1_calibration_hash_is_stable_but_v2_binds_semantics():
    base = {
        "number": 1,
        "name": "Calibration Formula",
        "body": "Original intent",
        "ingredients_ul": {"Hedione": 100.0, "Iso E Super": 200.0},
        "dilutions": {"Hedione": 1.0, "Iso E Super": 0.5},
        "stock_specs": {
            "Hedione": {
                "fraction": 1.0,
                "fraction_basis": "neat",
                "declared": True,
            },
            "Iso E Super": {
                "fraction": 0.5,
                "fraction_basis": "volume_fraction",
                "declared": True,
            },
        },
    }
    changed = {
        **base,
        "body": "Changed intent",
        "stock_specs": {
            **base["stock_specs"],
            "Iso E Super": {
                **base["stock_specs"]["Iso E Super"],
                "fraction_basis": "mass_fraction",
            },
        },
    }

    v1 = stable_formula_hash(base["name"], base["ingredients_ul"], base["dilutions"])

    assert v1 == "f72427844f0457dbd5b183745cf661012c74676b8e2edcc6ab56761de81e35dc"
    assert stable_formula_definition_hash(base) != stable_formula_definition_hash(changed)


def test_bound_analysis_replaces_legacy_once_and_detects_formula_staleness(tmp_path):
    path = tmp_path / "bound.md"
    _write_formula(path)
    path.write_text(
        path.read_text(encoding="utf-8")
        + "\n## Pipeline Analysis (old)\n\nobsolete\n",
        encoding="utf-8",
    )

    _persist_test_artifact(path)

    text = path.read_text(encoding="utf-8")
    assert text.count(PIPELINE_ANALYSIS_START) == 1
    assert "Pipeline Analysis (old)" not in text
    assert validate_pipeline_analysis_artifact(path)["status"] == "CURRENT"

    source, artifact = split_generated_pipeline_analysis(text)
    path.write_text(source.replace("| Hedione | 10% w/v in DPG | 100 |", "| Hedione | 10% w/v in DPG | 101 |") + "\n\n" + artifact, encoding="utf-8")

    result = validate_pipeline_analysis_artifact(path)
    assert result["status"] == "STALE"
    assert "formula_definition" in result["stale_issues"]


def test_bound_analysis_detects_content_tampering(tmp_path):
    path = tmp_path / "tampered.md"
    _write_formula(path)
    _persist_test_artifact(path)

    text = path.read_text(encoding="utf-8")
    path.write_text(
        text.replace("diagnostic analysis", "altered analysis"),
        encoding="utf-8",
    )

    result = validate_pipeline_analysis_artifact(path)
    assert result["status"] == "TAMPERED"
    assert "analysis_content_hash" in result["integrity_issues"]


def test_bound_analysis_becomes_stale_when_an_input_snapshot_changes(tmp_path):
    path = tmp_path / "inventory-stale.md"
    _write_formula(path)
    _persist_test_artifact(path)
    hashes = current_repository_evidence_hashes()
    hashes["inventory_sha256"] = "0" * 64

    result = validate_pipeline_analysis_artifact(path, repository_hashes=hashes)

    assert result["status"] == "STALE"
    assert "inventory" in result["stale_issues"]


def test_explicit_quarantine_is_nonblocking_but_never_current(tmp_path):
    path = tmp_path / "quarantined.md"
    _write_formula(path)
    _persist_test_artifact(path)
    source, artifact = split_generated_pipeline_analysis(
        path.read_text(encoding="utf-8")
    )
    source = source.replace(
        "# Bound Formula",
        "# Bound Formula\n\n"
        "**Status:** QUARANTINED — do not mix or release until repaired.",
    )
    path.write_text(source + "\n\n" + artifact, encoding="utf-8")

    result = validate_pipeline_analysis_artifact(path)

    assert result["status"] == "QUARANTINED"
    assert result["artifact_binding_status"] == "STALE"
    assert result["release_authority"] is False
    assert result["quarantine_explicit"] is True
    assert "formula_definition" in result["stale_issues"]


def test_explicit_quarantine_without_artifact_remains_nonpromoting(tmp_path):
    path = tmp_path / "quarantined-no-artifact.md"
    path.write_text(
        "# Quarantined\n\n"
        "**Status**: QUARANTINED — do not mix or release pending repair.\n",
        encoding="utf-8",
    )

    result = validate_pipeline_analysis_artifact(path)

    assert result == {
        "status": "QUARANTINED",
        "artifact_binding_status": "NONE",
        "issues": [],
        "release_authority": False,
        "quarantine_explicit": True,
    }


def test_quarantine_cannot_hide_artifact_tampering(tmp_path):
    path = tmp_path / "quarantined-tampered.md"
    _write_formula(path)
    _persist_test_artifact(path)
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        "# Bound Formula",
        "# Bound Formula\n\n"
        "**Status:** QUARANTINED — do not mix or release until repaired.",
    )
    path.write_text(
        text.replace("diagnostic analysis", "altered analysis"),
        encoding="utf-8",
    )

    result = validate_pipeline_analysis_artifact(path)

    assert result["status"] == "TAMPERED"
    assert result["artifact_binding_status"] == "TAMPERED"
    assert "analysis_content_hash" in result["integrity_issues"]


@pytest.mark.parametrize("line_ending", [b"\n", b"\r\n"])
def test_failed_post_write_verification_rolls_formula_back(tmp_path, monkeypatch, line_ending):
    path = tmp_path / "rollback.md"
    _write_formula(path)
    original = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", line_ending)
    path.write_bytes(original)
    formulas = parse_formula_markdown(path)
    manifest = {
        "schema": "perfume_pipeline_run_evidence_v1",
        **_run_input_hashes(formulas, ReleaseGateConfig(audit_enabled=False)),
        "analysis_sha256": stable_text_hash("diagnostic analysis"),
    }
    manifest["artifact_sha256"] = stable_json_hash(manifest)
    monkeypatch.setattr(
        "scripts.formula_release_gate.validate_pipeline_analysis_artifact",
        lambda _path: {"status": "STALE", "issues": ["forced"]},
    )

    with pytest.raises(RuntimeError, match="not current"):
        _append_pipeline_analysis(path, "diagnostic analysis", manifest)

    assert path.read_bytes() == original


def test_release_cli_persists_a_verified_artifact_by_default(tmp_path, capsys):
    path = tmp_path / "cli.md"
    path.write_text(
        """# CLI Formula

| Material | Dilution | uL |
|---|---|---:|
| Hedione | neat | 100 |
""",
        encoding="utf-8",
    )

    rc = formula_release_main(
        [
            "--formula-file",
            str(path),
            "--expected-concentrate-ul",
            "100",
            "--brief",
            "generic",
            "--no-audit",
            "--json",
        ]
    )
    capsys.readouterr()

    assert rc in {0, 1}
    validation = validate_pipeline_analysis_artifact(path)
    assert validation["status"] == "CURRENT"
    persisted = path.read_text(encoding="utf-8")
    assert persisted.count(PIPELINE_ANALYSIS_START) == 1
    _source, artifact = split_generated_pipeline_analysis(persisted)
    manifest = parse_pipeline_analysis_manifest(artifact)
    assert manifest is not None
    assert manifest["binding_schema"] == "formula-artifact-binding-v1"
    assert manifest["renderer_version"] == "formula-release-gate-v1"
    assert len(manifest["analysis_input_sha256"]) == 64
    assert manifest["repository_commit"]
    assert manifest["canonical_records"][0]["canonical_content_sha256"]
