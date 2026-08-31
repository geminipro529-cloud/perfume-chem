from __future__ import annotations

from engine.perception.architectural_delta import ArchitecturalDeltaState
from engine.perception.architecture_contracts import ArchitectureCompilationState
from engine.perception.cypress_harmonic_program import (
    build_default_cypress_harmonic_program,
)
from engine.perception.cypress_heart_frontier import CypressHeartFrontierState
from engine.perception.harmonic_synthesis import (
    HarmonicMaterialState,
    HarmonicModuleState,
    HarmonicSynthesisState,
)


def test_default_program_runs_all_design_modules_as_one_constraint_system() -> None:
    program = build_default_cypress_harmonic_program()

    assert program.frontier_result.state is CypressHeartFrontierState.THEORY_SELECTED
    assert program.architecture_result.state is ArchitectureCompilationState.NO_CHANGE
    assert program.delta_result.state is ArchitecturalDeltaState.NO_CHANGE
    assert program.synthesis_result.state is HarmonicSynthesisState.DESIGN_READY
    assert program.synthesis_result.tensions == ()

    expected_modules = (
        "material-capability-atlas",
        "cypress-heart-frontier",
        "family-depth",
        "architecture-compiler",
        "architectural-delta",
        "temporal-ledger",
        "hedonic-preference",
    )
    assert program.synthesis_request.required_module_ids == expected_modules
    assert tuple(report.module_id for report in program.module_reports) == expected_modules


def test_empirical_modules_remain_withheld_without_blocking_theory_design() -> None:
    program = build_default_cypress_harmonic_program()
    reports = {report.module_id: report for report in program.module_reports}

    assert reports["temporal-ledger"].state is HarmonicModuleState.WITHHELD
    assert reports["hedonic-preference"].state is HarmonicModuleState.WITHHELD
    assert program.synthesis_result.empirical_gaps == (
        "hedonic-preference:NO_SCOPED_BLINDED_PREFERENCE_DATA",
        "temporal-ledger:NO_BLINDED_TEMPORAL_OBSERVATIONS",
    )
    assert program.synthesis_result.claim_ceiling == (
        "COMPUTATIONAL_EXPERIMENT_DESIGN_ONLY"
    )


def test_selected_current_build_materials_all_resolve_through_same_atlas() -> None:
    program = build_default_cypress_harmonic_program()

    assert len(program.synthesis_result.material_dispositions) == 8
    assert all(
        item.state is HarmonicMaterialState.CURRENT_READY
        for item in program.synthesis_result.material_dispositions
    )
    assert {item.material_name for item in program.synthesis_result.material_dispositions} == {
        "Cypress EO",
        "Magnolia EO",
        "Alpha Irone",
        "Orris Liquid",
        "Hedione",
        "Florol",
        "Alpha Ionone",
        "Hexyl Salicylate",
    }


def test_harmonic_relations_preserve_subject_light_shadow_and_temporal_handoff() -> None:
    program = build_default_cypress_harmonic_program()
    relations = {item.relation_id: item for item in program.synthesis_result.retained_relations}

    assert set(relations) == {
        "cyp02_cypress_to_magnolia_relief",
        "cyp02_magnolia_to_orris_depth",
        "cyp02_orris_to_cypress_return",
    }
    assert "sole named subject" in relations[
        "cyp02_cypress_to_magnolia_relief"
    ].target_link
    assert relations["cyp02_magnolia_to_orris_depth"].relation_kind == (
        "CHIAROSCURO_VERTICAL_DEPTH"
    )
    assert relations["cyp02_orris_to_cypress_return"].temporal_windows == (
        "LATE_HEART",
        "DRYDOWN",
    )


def test_program_is_deterministic_and_never_grants_authority() -> None:
    first = build_default_cypress_harmonic_program()
    second = build_default_cypress_harmonic_program()

    assert first.record_sha256 == second.record_sha256
    assert first.synthesis_result.record_sha256 == second.synthesis_result.record_sha256
    for field_name in (
        "formula_mutation_authorized",
        "physical_execution_authorized",
        "compounding_authorized",
        "purchase_authority",
        "sensory_authority",
        "hedonic_authority",
        "similarity_authority",
        "performance_authority",
        "safety_authority",
        "stability_authority",
        "release_authority",
    ):
        assert getattr(first, field_name) is False


def test_program_does_not_smuggle_scalar_beauty_or_component_count_logic() -> None:
    program = build_default_cypress_harmonic_program()
    rendered = str(program.as_dict()).casefold()

    assert program.frontier_result.scalar_score_used is False
    assert program.synthesis_result.vote_counting_used is False
    assert "overall_score" not in rendered
    assert "beauty_score" not in rendered
    assert "hedonic_score" not in rendered
    assert program.architecture_request.component_count_used_as_complexity is False
    assert program.architecture_request.predicted_oav_used_as_perception is False
    assert program.architecture_request.composition_score_used_as_hedonic is False
