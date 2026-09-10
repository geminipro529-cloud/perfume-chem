from __future__ import annotations

from dataclasses import replace

import pytest

from engine.perception.depth_contracts import (
    DepthArchitectureProfileV1,
    DepthDesignState,
    DepthDimension,
    DepthDimensionContractV1,
    DepthEvidenceState,
    DepthMechanismKind,
    DepthMechanismV1,
    DepthProbeType,
    DepthProbeV1,
    PerfumeFamily,
)
from engine.perception.depth_evaluation import evaluate_depth_profile
from engine.perception.depth_family_adapters import all_family_depth_templates


def _probe(
    *,
    probe_type: DepthProbeType = DepthProbeType.ABLATION,
    endpoints: tuple[str, ...] = ("target identity", "recognizer clarity"),
    windows: tuple[str, ...] = ("0_min", "30_min"),
    constraints: tuple[str, ...] = (
        "constant total raw volume",
        "same carrier and application mass",
    ),
) -> DepthProbeV1:
    return DepthProbeV1(
        probe_id="probe_target_relation",
        probe_type=probe_type,
        changed_factor="remove only the declared target-linked relation",
        arms=("complete architecture", "carrier-matched relation omission"),
        constant_constraints=constraints,
        primary_endpoints=endpoints,
        failure_endpoints=("genericization", "target drift"),
        time_windows=windows,
        blinding_rule="opaque three-digit codes conceal arm identity",
        order_rule="counterbalanced order with repeated coded control",
        accept_rule="retain only a repeatable target-linked effect",
        reject_rule="reject on target drift, ties, or no repeatable effect",
        evidence_refs=("design://family-architecture/compiler-v1",),
    )


def _profile(
    dimension: DepthDimension = DepthDimension.OBJECT_IDENTITY,
    *,
    probe: DepthProbeV1 | None = None,
    mechanism_kind: DepthMechanismKind = DepthMechanismKind.ANCHOR,
) -> DepthArchitectureProfileV1:
    selected_probe = probe or _probe()
    mechanism = DepthMechanismV1(
        mechanism_id="mechanism_target_relation",
        dimension=dimension,
        kind=mechanism_kind,
        target_link="the named target must remain recognizable without becoming generic",
        causal_hypothesis="the declared relation preserves one target-specific invariant",
        participant_ids=("named_target_module",),
        expected_contribution="target-specific coherence without family-wide substitution",
        failure_mode="a generic family smell replaces the named target",
        falsification_probe_id=selected_probe.probe_id,
        temporal_windows=selected_probe.time_windows,
        evidence_state=DepthEvidenceState.EXPERIMENT_DESIGN,
        evidence_refs=("design://family-architecture/compiler-v1",),
    )
    contract = DepthDimensionContractV1(
        dimension=dimension,
        target_definition="one target-specific dimension, never an ingredient-count proxy",
        required=True,
        mechanism_ids=(mechanism.mechanism_id,),
        observable_endpoints=selected_probe.primary_endpoints,
        failure_modes=(mechanism.failure_mode,),
        probe_ids=(selected_probe.probe_id,),
        evidence_refs=("design://family-architecture/compiler-v1",),
    )
    return DepthArchitectureProfileV1(
        profile_id="profile_family_compiler_test",
        target_identity="Named target architecture",
        family=PerfumeFamily.FLORAL,
        emotional_tone="rich, lucid, and internally contrasted",
        realism_or_abstraction_target="recognizable subject with deliberate abstraction",
        forbidden_drift=("generic family smell", "material-count padding"),
        ideal_formula_ref="target://family-compiler/ideal/v1",
        current_inventory_build_ref="inventory://family-compiler/current/v1",
        dimension_contracts=(contract,),
        mechanisms=(mechanism,),
        probes=(selected_probe,),
        construction_row_count=64,
        source_refs=("design://family-architecture/compiler-v1",),
        claim_ceiling="COMPUTATIONAL_EXPERIMENT_DESIGN_ONLY",
    )


def test_all_eighteen_family_templates_keep_full_noncount_depth_surface() -> None:
    templates = all_family_depth_templates()
    expected_dimensions = tuple(
        dimension
        for dimension in DepthDimension
        if dimension is not DepthDimension.CONSTRUCTION_COMPLEXITY
    )

    assert len(templates) == len(PerfumeFamily) == 18
    assert tuple(template.family for template in templates) == tuple(PerfumeFamily)
    assert len({template.template_sha256 for template in templates}) == 18
    for template in templates:
        assert template.required_dimensions == expected_dimensions
        assert template.identity_questions
        assert template.anatomy_axes
        assert template.relationship_mechanisms
        assert template.texture_vocabulary
        assert template.temporal_questions
        assert template.spatial_questions
        assert template.hedonic_questions
        assert template.collapse_risks
        assert "cannot establish" in template.claim_boundary


def test_family_anatomy_is_target_specific_not_a_shared_material_recipe() -> None:
    templates = {template.family: template for template in all_family_depth_templates()}
    floral = templates[PerfumeFamily.FLORAL]
    woody = templates[PerfumeFamily.WOODY]
    amber = templates[PerfumeFamily.AMBER_RESINOUS]

    assert floral.anatomy_axes != woody.anatomy_axes
    assert woody.relationship_mechanisms != amber.relationship_mechanisms
    assert floral.collapse_risks != amber.collapse_risks
    assert not any("must use" in item.casefold() for item in floral.anatomy_axes)


def test_ingredient_count_alone_cannot_be_promoted_to_depth() -> None:
    profile = _profile(
        DepthDimension.CONSTRUCTION_COMPLEXITY,
        mechanism_kind=DepthMechanismKind.PHYSICAL_CONSTRAINT,
    )

    result = evaluate_depth_profile(profile)

    assert result.state is DepthDesignState.HOLD
    assert "HOLD_COUNT_ONLY_DEPTH" in result.reason_codes


def test_hedonic_architecture_requires_liking_and_nonliking_relational_endpoints() -> None:
    liking_only = _probe(
        probe_type=DepthProbeType.HEDONIC_PREFERENCE,
        endpoints=("liking", "preference"),
    )
    profile = _profile(
        DepthDimension.HEDONIC_ARCHITECTURE,
        probe=liking_only,
        mechanism_kind=DepthMechanismKind.HEDONIC_TENSION_RELEASE,
    )

    result = evaluate_depth_profile(profile)

    assert result.state is DepthDesignState.HOLD
    assert "HOLD_HEDONIC_ENDPOINT_SEPARATION" in result.reason_codes


def test_temporal_architecture_requires_five_windows_and_adaptation_control() -> None:
    windows = ("0_min", "5_min", "30_min", "2_hour", "4_hour")
    uncontrolled = _probe(probe_type=DepthProbeType.TEMPORAL, windows=windows)
    profile = _profile(
        DepthDimension.TEMPORAL_ARCHITECTURE,
        probe=uncontrolled,
        mechanism_kind=DepthMechanismKind.TEMPORAL_HANDOFF,
    )

    result = evaluate_depth_profile(profile)
    assert result.state is DepthDesignState.HOLD
    assert "HOLD_TEMPORAL_ADAPTATION_CONTROL" in result.reason_codes

    controlled_probe = replace(
        uncontrolled,
        constant_constraints=(
            *uncontrolled.constant_constraints,
            "fresh coded applications at each window control olfactory adaptation",
        ),
    )
    controlled = _profile(
        DepthDimension.TEMPORAL_ARCHITECTURE,
        probe=controlled_probe,
        mechanism_kind=DepthMechanismKind.TEMPORAL_HANDOFF,
    )
    accepted = evaluate_depth_profile(controlled)
    assert accepted.state is DepthDesignState.DESIGN_READY


def test_target_ideal_and_current_inventory_ledgers_cannot_collapse() -> None:
    profile = _profile()

    with pytest.raises(ValueError, match="TARGET/IDEAL.*CURRENT-INVENTORY"):
        replace(profile, current_inventory_build_ref=profile.ideal_formula_ref)


def test_compiler_and_evaluation_never_grant_empirical_authority() -> None:
    profile = _profile()
    result = evaluate_depth_profile(profile)

    assert result.state is DepthDesignState.DESIGN_READY
    for field_name in (
        "formula_authority",
        "sensory_authority",
        "similarity_authority",
        "hedonic_authority",
        "performance_authority",
        "safety_authority",
        "stability_authority",
        "release_authority",
    ):
        assert getattr(profile, field_name) is False
    for field_name in (
        "empirical_authority",
        "formula_mutation_authorized",
        "physical_execution_authorized",
        "purchase_authority",
        "sensory_authority",
        "similarity_authority",
        "hedonic_authority",
        "performance_authority",
        "safety_authority",
        "stability_authority",
        "release_authority",
    ):
        assert getattr(result, field_name) is False
