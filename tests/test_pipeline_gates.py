from dataclasses import replace

import pytest

import engine.pipeline.gates as gates_module
from engine.knowledge.perfume_knowledge import evaluate_pyramid_balance
from engine.name_utils import normalize_name
from engine.optimizer.perfumer_logic import evaluate_perfumer_logic
from engine.pipeline.formula_state import build_formula_state
from engine.pipeline.gates import (
    ReleaseGateConfig,
    _apply_guideline_policy,
    _gate_concentration_basis,
    _result,
    _status_from_gates,
    gate_formula,
)


def _formula(ingredients, dilutions=None, name="Test Formula"):
    total = sum(ingredients.values()) or 1.0
    return {
        "number": 1,
        "name": name,
        "ingredients_ul": ingredients,
        "dilutions": dilutions or {},
        "ingredients_pct": {k: v / total * 100 for k, v in ingredients.items()},
        "body": name,
    }


def _exact_w_v_stock_specs(*names: str) -> dict[str, dict[str, object]]:
    return {
        name: {
            "fraction": 1.0,
            "fraction_basis": "mass_per_volume",
            "carrier": "",
            "declared": True,
        }
        for name in names
    }


def test_guideline_policy_demotes_advisory_failures_to_warnings():
    gate = _result("literature_compliance", "FAIL", "too strict")
    normalized = _apply_guideline_policy(gate)

    assert normalized.status == "WARN"
    assert normalized.data["original_status"] == "FAIL"
    assert _status_from_gates([normalized]) == "WARN"


def test_perfumer_logic_routes_registered_nonlegacy_brief_to_its_archetype():
    formula = _formula(
        {
            "Iso E Super": 1800.0,
            "Hedione": 900.0,
            "Ethylene Brassylate": 600.0,
            "Dihydro Beta Ionone": 300.0,
        },
        name="Woody Floral Musk",
    )

    report = evaluate_perfumer_logic(formula, brief="woody_floral_musk")

    assert report.brief == "woody_floral_musk.classic"
    assert all(check.name != "perfumer_logic_brief" for check in report.checks)


def test_jellinek_classification_spells_ambrettolide_correctly():
    assert gates_module._JELLINEK_CLASSES["ambrettolide"] == "erogenic"


def test_guideline_policy_keeps_hard_blockers_failing():
    gate = _result("safety_ifra_allergen", "FAIL", "unsafe")
    normalized = _apply_guideline_policy(gate)

    assert normalized.status == "FAIL"
    assert _status_from_gates([normalized]) == "FAIL"


@pytest.mark.parametrize(
    "gate_name",
    ["weber_fechner_contrast", "guerlain_vanillin_coumarin", "fougere_skeleton"],
)
def test_screening_oav_failures_are_diagnostic_without_action_authority(gate_name):
    normalized = _apply_guideline_policy(_result(gate_name, "FAIL", "screening flag"))

    assert normalized.status == "WARN"
    assert normalized.data["original_status"] == "FAIL"
    assert normalized.data["evidence_role"] == "HEURISTIC_SCREENING_ONLY"
    assert normalized.data["formula_optimization_authority"] is False
    assert normalized.data["compounding_action_authority"] is False
    assert normalized.data["repair_authority"] is False
    assert normalized.data["release_authority"] is False
    assert normalized.data["sensory_endpoint_authority"] is False
    assert "NOT_PHYSICS_SENSORY_LIKING" in normalized.data["claim_ceiling"]


def test_concentration_basis_gate_reads_bound_stock_fraction_basis():
    state = build_formula_state(
        {"Hedione": 100.0},
        {"Hedione": 1.0},
        stock_specs={
            "Hedione": {
                "fraction": 1.0,
                "fraction_basis": "neat",
                "carrier": "",
                "declared": True,
            }
        },
    )

    check = _gate_concentration_basis(state, ReleaseGateConfig())

    assert check.status == "PASS"


def test_concentration_basis_gate_fails_closed_on_unspecified_basis():
    state = build_formula_state(
        {"Hedione": 100.0},
        {"Hedione": 1.0},
        stock_specs={
            "Hedione": {
                "fraction": 1.0,
                "fraction_basis": "unspecified",
                "carrier": "",
                "declared": True,
            }
        },
    )

    check = _gate_concentration_basis(state, ReleaseGateConfig())

    assert check.status == "FAIL"
    assert "Hedione" in check.detail


def test_concentration_basis_gate_fails_closed_on_unsupported_basis():
    state = build_formula_state(
        {"Hedione": 100.0},
        {"Hedione": 1.0},
        stock_specs={
            "Hedione": {
                "fraction": 1.0,
                "fraction_basis": "banana",
                "carrier": "mystery",
                "declared": True,
            }
        },
    )

    check = _gate_concentration_basis(state, ReleaseGateConfig())

    assert check.status == "FAIL"
    assert "banana" in check.detail


def test_gate_blocks_opaque_preblend_by_default():
    formula = _formula(
        {"Hedione": 3000.0, "Iso E Super": 2000.0, "Cardamom FTEC": 1000.0},
        name="Aromatic Fougere",
    )
    report = gate_formula(
        formula,
        ReleaseGateConfig(expected_concentrate_ul=6000.0, brief="generic"),
    )

    gates = {g.gate: g for g in report.gates}
    assert gates["opaque_preblends"].status == "FAIL"
    assert report.status == "FAIL"


def test_gate_allows_preblend_with_explicit_waiver():
    formula = _formula(
        {"Hedione": 3000.0, "Iso E Super": 2000.0, "Cardamom FTEC": 1000.0},
        name="Aromatic Fougere",
    )
    report = gate_formula(
        formula,
        ReleaseGateConfig(
            expected_concentrate_ul=6000.0,
            brief="generic",
            allow_preblends=True,
        ),
    )

    gates = {g.gate: g for g in report.gates}
    assert gates["opaque_preblends"].status == "WARN"


def test_gate_blocks_neat_trace_below_floor():
    formula = _formula(
        {"Hedione": 5999.0, "Geosmin": 1.0},
        name="Trace Test",
    )
    report = gate_formula(
        formula,
        ReleaseGateConfig(expected_concentrate_ul=6000.0, brief="generic"),
    )

    gates = {g.gate: g for g in report.gates}
    assert gates["pipette_floor_neat_traces"].status == "FAIL"


def test_gate_warns_when_top_carrier_relies_on_low_authority_odt():
    formula = _formula(
        {"Bergamot": 3000.0, "Hedione": 2000.0, "Iso E Super": 1000.0},
        name="ODT Authority Test",
    )
    report = gate_formula(
        formula,
        ReleaseGateConfig(
            expected_concentrate_ul=6000.0, brief="generic", audit_enabled=False
        ),
    )

    gates = {g.gate: g for g in report.gates}
    assert gates["odt_coverage"].status == "WARN"
    assert any(
        row["material"] == "Bergamot"
        for row in gates["odt_coverage"].data["low_authority_materials"]
    )


def test_gamma_gate_reports_source_authority_and_ideal_scenario_leverage():
    state = build_formula_state(
        {"Iso E Super": 200.0, "Hedione": 100.0},
        {"Iso E Super": 1.0, "Hedione": 1.0},
        matrix_moles={"Ethanol": 0.4},
        matrix_mass_g=18.4,
        matrix_source="explicit",
    )

    gate = gates_module._gate_oav_physics_gamma(
        state,
        ReleaseGateConfig(audit_enabled=False),
    )

    assert gate.status == "WARN"
    assert gate.data["release_authority"] is False
    assert gate.data["comparison_scenario"]["authority"] == (
        "COMPARISON_SCENARIO_ONLY"
    )
    iso_e = next(
        row for row in gate.data["materials"]
        if row["material"] == "Iso E Super"
    )
    modeled = next(
        material for material in state.materials
        if material.name == "Iso E Super"
    )
    assert iso_e["authority"] in {
        "HEURISTIC_HANSEN_DISTANCE",
        "HEURISTIC_PROFILE_CONSTANT",
    }
    assert iso_e["ideal_gamma_scenario_oav"] == pytest.approx(
        modeled.oav / modeled.gamma,
        rel=1e-5,
    )
    assert iso_e["modeled_to_ideal_oav_ratio"] == pytest.approx(
        modeled.gamma,
        rel=1e-5,
    )
    assert "non-unity" not in gate.detail


def test_solvent_matrix_gate_uses_stock_carrier_evidence_without_inventing_matrix():
    state = build_formula_state(
        {"Neroli EO": 300.0, "Ambrofix": 250.0},
        {"Neroli EO": 0.1, "Ambrofix": 0.3},
        stock_specs={
            "Neroli EO": {
                "fraction_basis": "unspecified",
                "carrier": "DPG",
                "declared": True,
            },
            "Ambrofix": {
                "fraction_basis": "mass_per_volume",
                "carrier": "",
                "declared": True,
            },
        },
        matrix_moles={"Ethanol": 0.4, "Water": 0.05},
        matrix_mass_g=19.3,
        matrix_source="incomplete_stock_carrier",
    )

    gate = gates_module._gate_solvent_matrix(
        state,
        ReleaseGateConfig(audit_enabled=False),
    )

    assert gate.status == "WARN"
    assert gate.data["authority"] == "PARTIAL_UNRESOLVED"
    assert gate.data["known_stock_carriers_ul"]["DPG"] == pytest.approx(270.0)
    assert gate.data["unresolved_carrier_proxy_ul"] == pytest.approx(175.0)
    assert gate.data["bulk_matrix_components_ul"]["ETHANOL"] == pytest.approx(
        0.4 * 46.0684 / 0.785 * 1000.0,
        rel=1e-6,
    )
    assert gate.data["bulk_matrix_components_ul"]["WATER"] == pytest.approx(
        0.05 * 18.01528 / 0.997 * 1000.0,
        rel=1e-6,
    )
    assert gate.data["headspace_stock_carrier_inclusion"] == (
        "NOT_INCLUDED_PENDING_RECONCILIATION"
    )
    assert "30 mL" not in gate.detail


def test_chemistry_stability_fails_aldehyde_amine_contact():
    formula = _formula(
        {"Aldehyde C12 MNA": 2000.0, "Indole": 1000.0, "Hedione": 3000.0},
        name="Reactive Jasmine",
    )
    formula["stock_specs"] = _exact_w_v_stock_specs(*formula["ingredients_ul"])
    report = gate_formula(
        formula,
        ReleaseGateConfig(
            expected_concentrate_ul=6000.0, brief="generic", audit_enabled=False
        ),
    )

    gates = {g.gate: g for g in report.gates}
    assert gates["chemistry_stability"].status == "FAIL"
    assert "Schiff-base risk" in gates["chemistry_stability"].detail


def test_chemistry_stability_warns_for_citrus_heavy_oxidation_risk():
    formula = _formula(
        {
            "D-Limonene": 1500.0,
            "Linalool": 300.0,
            "Hedione": 1200.0,
            "Iso E Super": 3000.0,
        },
        name="Citrus Stress Test",
    )
    formula["stock_specs"] = _exact_w_v_stock_specs(*formula["ingredients_ul"])
    technical = gate_formula(
        formula,
        ReleaseGateConfig(
            expected_concentrate_ul=6000.0, brief="generic", audit_enabled=False
        ),
    )
    commercial = gate_formula(
        formula,
        ReleaseGateConfig(
            expected_concentrate_ul=6000.0,
            brief="generic",
            commercial_mode=True,
            audit_enabled=False,
        ),
    )

    technical_gates = {g.gate: g for g in technical.gates}
    commercial_gates = {g.gate: g for g in commercial.gates}
    assert technical_gates["chemistry_stability"].status == "WARN"
    assert commercial_gates["chemistry_stability"].status == "FAIL"


def test_chemistry_stability_passes_stable_woody_floral_formula():
    formula = _formula(
        {"Hedione": 2500.0, "Iso E Super": 2500.0, "Habanolide": 1000.0},
        name="Stable Woods Floral",
    )
    formula["stock_specs"] = _exact_w_v_stock_specs(*formula["ingredients_ul"])
    report = gate_formula(
        formula,
        ReleaseGateConfig(
            expected_concentrate_ul=6000.0, brief="generic", audit_enabled=False
        ),
    )

    gates = {g.gate: g for g in report.gates}
    assert gates["chemistry_stability"].status == "PASS"


def test_phase_compatibility_fails_hsp_incompatible_blend():
    formula = _formula(
        {
            "Vanillin": 1800.0,
            "D-Limonene": 1800.0,
            "Galaxolide": 1800.0,
            "Hedione": 600.0,
        },
        name="Phase Clash",
    )
    formula["stock_specs"] = _exact_w_v_stock_specs(*formula["ingredients_ul"])
    report = gate_formula(
        formula,
        ReleaseGateConfig(
            expected_concentrate_ul=6000.0, brief="generic", audit_enabled=False
        ),
    )

    gates = {g.gate: g for g in report.gates}
    assert gates["phase_compatibility"].status == "FAIL"


def test_phase_compatibility_warns_when_hsp_coverage_is_thin():
    formula = _formula(
        {"Lavender EO": 3000.0, "Habanolide": 2000.0, "Vetiver EO": 1000.0},
        name="Sparse HSP Coverage",
    )
    formula["stock_specs"] = _exact_w_v_stock_specs(*formula["ingredients_ul"])
    report = gate_formula(
        formula,
        ReleaseGateConfig(
            expected_concentrate_ul=6000.0, brief="generic", audit_enabled=False
        ),
    )

    gates = {g.gate: g for g in report.gates}
    assert gates["phase_compatibility"].status == "WARN"


def test_physical_mass_gates_fail_unknown_instead_of_using_proxy_active_mass():
    state = build_formula_state(
        {"D-Limonene": 75.0, "Hedione": 25.0},
        {"D-Limonene": 0.25, "Hedione": 0.25},
        stock_specs={
            name: {
                "fraction_basis": "mass_fraction",
                "carrier": "dpg",
                "declared": True,
            }
            for name in ("D-Limonene", "Hedione")
        },
    )

    chemistry = gates_module._gate_chemistry_stability(
        state, ReleaseGateConfig(audit_enabled=False)
    )
    phase = gates_module._gate_phase_compatibility(state)

    for result in (chemistry, phase):
        assert result.status == "FAIL"
        assert result.data["assessment"] == "UNKNOWN"
        assert result.data["active_mass_basis"] == "authoritative_active_g"
        assert result.data["proxy_active_g_ignored"] is True
        assert result.data["missing_authoritative_active_mass_materials"]
        assert "UNKNOWN" in result.detail


def test_eu_allergen_declaration_uses_finished_product_mass_not_oav():
    state = build_formula_state(
        {"Geraniol": 100.0},
        {"Geraniol": 1.0},
        stock_specs=_exact_w_v_stock_specs("Geraniol"),
        matrix_moles={"Ethanol": 0.43},
        matrix_mass_g=20.0,
        matrix_source="explicit",
    )
    row = state.materials[0]
    assert row.active_finished_product_ppm_w_w is not None
    assert row.active_finished_product_ppm_w_w > 10.0
    state = replace(
        state,
        materials=(
            replace(
                row,
                oav=0.0,
                screening_oav=0.0,
                canonical_oav=None,
            ),
        ),
    )

    result = gates_module._gate_eu_allergen_declaration(
        state, ReleaseGateConfig(audit_enabled=False)
    )

    assert result.status == "WARN"
    assert result.data["oav_used"] is False
    assert result.data["perceptibility_filter_applied"] is False
    assert result.data["concentration_basis"] == "active_finished_product_ppm_w_w"
    assert result.data["declaration_candidates"][0]["allergen"] == "geraniol"


def test_pyramid_balance_uses_normalized_note_map_keys():
    result = evaluate_pyramid_balance(
        {"Cedrat FCF oil Sicilian": 100.0},
        family="citrus",
        note_map={normalize_name("Cedrat FCF Sicilian"): "top"},
    )

    assert result.actual_top == 100.0
    assert result.actual_heart == 0.0
    assert result.actual_base == 0.0


def test_mode_gate_blocks_physical_commit_during_reconstruction():
    result = gates_module._gate_mode_protection(
        None,
        ReleaseGateConfig(
            mode="RECONSTRUCTION",
            action="ATOMIC_COMMIT",
            audit_enabled=False,
        ),
    )

    assert result.status == "FAIL"
    assert result.data["reasons"] == ["ACTION_NOT_ALLOWED_IN_MODE"]


def test_mode_gate_allows_atomic_commit_only_in_live_batch():
    result = gates_module._gate_mode_protection(
        None,
        ReleaseGateConfig(
            mode="LIVE_BATCH",
            action="ATOMIC_COMMIT",
            audit_enabled=False,
        ),
    )

    assert result.status == "PASS"
    assert result.data["mode"] == "LIVE_BATCH"
    assert result.data["action"] == "ATOMIC_COMMIT"
