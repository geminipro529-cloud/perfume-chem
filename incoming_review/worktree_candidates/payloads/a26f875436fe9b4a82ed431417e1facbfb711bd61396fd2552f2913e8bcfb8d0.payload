from __future__ import annotations

import json
from dataclasses import replace

import pytest

import engine.perception.depth_family_adapters as depth_family_adapters
from engine.perception.depth_comparison import (
    DepthDimensionAlignment,
    compare_depth_profiles,
)
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
from engine.perception.depth_family_adapters import (
    adapt_floral_design_request,
    all_family_depth_templates,
    family_depth_template,
)
from engine.perception.floral_depth import (
    FloralDepthStrategy,
    FloralDesignRequestV1,
    FloralFacetClass,
    FloralFacetV1,
    FloralIdentityContractV1,
    FloralScope,
    FloralSourceClass,
    FloralSubjectRole,
    FloralSubjectV1,
    FloralTemporalContourV1,
    FloralTemporalWindowV1,
    FloralTrainingTrialV1,
    TrainingDomain,
)


def _probe(
    probe_id: str = "probe_identity_ablation",
    *,
    probe_type: DepthProbeType = DepthProbeType.ABLATION,
    time_windows: tuple[str, ...] = ("0_min", "30_min"),
    blinding_rule: str = "random three-digit codes conceal arm identity",
) -> DepthProbeV1:
    return DepthProbeV1(
        probe_id=probe_id,
        probe_type=probe_type,
        changed_factor="remove the declared identity anchor and replace its raw volume with carrier",
        arms=("complete architecture", "carrier-matched anchor omission"),
        constant_constraints=(
            "constant total raw volume",
            "same carrier and application mass",
        ),
        primary_endpoints=("named identity retention", "recognizer clarity"),
        failure_endpoints=("genericization", "identity substitution"),
        time_windows=time_windows,
        blinding_rule=blinding_rule,
        order_rule="balanced order with a repeated coded control",
        accept_rule="retain only if identity retention exceeds the omission repeatably",
        reject_rule="reject on identity drift or no repeatable target-linked difference",
        evidence_refs=("doi:10.1016/S0031-9384(00)00407-8",),
    )


def _mechanism(
    mechanism_id: str = "mechanism_identity_anchor",
    *,
    dimension: DepthDimension = DepthDimension.OBJECT_IDENTITY,
    probe_id: str = "probe_identity_ablation",
    participant_ids: tuple[str, ...] = ("module_named_object",),
) -> DepthMechanismV1:
    return DepthMechanismV1(
        mechanism_id=mechanism_id,
        dimension=dimension,
        kind=DepthMechanismKind.ANCHOR,
        target_link="the named object must remain recognizable without becoming generic",
        causal_hypothesis="the anchor supplies the minimum invariant recognizer set",
        participant_ids=participant_ids,
        expected_contribution="stable target identity across the declared time windows",
        failure_mode="a generic family smell replaces the named target",
        falsification_probe_id=probe_id,
        temporal_windows=("0_min", "30_min"),
        evidence_state=DepthEvidenceState.EXPERIMENT_DESIGN,
        evidence_refs=("doi:10.3758/BF03206052",),
    )


def _dimension(
    mechanism_id: str = "mechanism_identity_anchor",
    probe_id: str = "probe_identity_ablation",
) -> DepthDimensionContractV1:
    return DepthDimensionContractV1(
        dimension=DepthDimension.OBJECT_IDENTITY,
        target_definition="a coherent white-floral object with individually purposeful anatomy",
        required=True,
        mechanism_ids=(mechanism_id,),
        observable_endpoints=("named identity retention", "recognizer clarity"),
        failure_modes=("generic white-floral blur",),
        probe_ids=(probe_id,),
        evidence_refs=("doi:10.1016/S0031-9384(00)00407-8",),
    )


def _profile() -> DepthArchitectureProfileV1:
    probe = _probe()
    mechanism = _mechanism()
    return DepthArchitectureProfileV1(
        profile_id="profile_white_flower_reference",
        target_identity="White Flower Reliquary",
        family=PerfumeFamily.FLORAL,
        emotional_tone="radiant petals held inside a cool, solemn enclosure",
        realism_or_abstraction_target="recognizable living floral anatomy with deliberate abstraction",
        forbidden_drift=("generic white floral", "syrup", "woody amber takeover"),
        ideal_formula_ref="target://white-flower-reliquary/ideal/v1",
        current_inventory_build_ref="inventory://white-flower-reliquary/current/v1",
        dimension_contracts=(_dimension(),),
        mechanisms=(mechanism,),
        probes=(probe,),
        construction_row_count=64,
        source_refs=("design://white-flower-reliquary/v1",),
        claim_ceiling="COMPUTATIONAL_EXPERIMENT_DESIGN_ONLY",
    )


def _serialized_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {
            child
            for nested in value.values()
            for child in _serialized_keys(nested)
        }
    if isinstance(value, list):
        return {child for nested in value for child in _serialized_keys(nested)}
    return set()


def test_depth_profile_is_deterministic_and_has_no_sensory_authority() -> None:
    profile = _profile()

    assert profile.profile_sha256 == profile.profile_sha256
    assert len(profile.profile_sha256) == 64
    assert profile.formula_authority is False
    assert profile.sensory_authority is False
    assert profile.similarity_authority is False
    assert profile.hedonic_authority is False
    assert profile.performance_authority is False
    assert profile.safety_authority is False
    assert profile.stability_authority is False
    assert profile.release_authority is False

    payload = profile.as_dict()
    assert json.dumps(payload, sort_keys=True) == json.dumps(profile.as_dict(), sort_keys=True)
    forbidden_key_fragments = ("score", "winner", "rank", "better", "superior", "deeper")
    assert not {
        key
        for key in _serialized_keys(payload)
        if any(fragment in key.lower() for fragment in forbidden_key_fragments)
    }


@pytest.mark.parametrize(
    ("field_name", "value"),
    (
        ("target_identity", ""),
        ("emotional_tone", " "),
        ("realism_or_abstraction_target", ""),
        ("claim_ceiling", ""),
    ),
)
def test_depth_profile_rejects_empty_identity_fields(field_name: str, value: str) -> None:
    with pytest.raises(ValueError, match=field_name):
        replace(_profile(), **{field_name: value})


def test_depth_profile_requires_distinct_ideal_and_current_ledgers() -> None:
    profile = _profile()

    with pytest.raises(ValueError, match="TARGET/IDEAL.*CURRENT-INVENTORY"):
        replace(
            profile,
            current_inventory_build_ref=profile.ideal_formula_ref,
        )


def test_depth_profile_rejects_duplicate_contract_and_probe_ids() -> None:
    profile = _profile()

    with pytest.raises(ValueError, match="dimension contracts"):
        replace(profile, dimension_contracts=profile.dimension_contracts * 2)
    with pytest.raises(ValueError, match="probe IDs"):
        replace(profile, probes=profile.probes * 2)


def test_depth_mechanism_requires_real_participants() -> None:
    with pytest.raises(ValueError, match="participant_ids"):
        _mechanism(participant_ids=())


def test_depth_probe_requires_comparative_arms() -> None:
    with pytest.raises(ValueError, match="at least two controlled arms"):
        replace(_probe(), arms=("complete architecture",))


def test_construction_count_is_diagnostic_and_cannot_be_negative() -> None:
    assert _profile().as_dict()["construction_row_count"] == 64

    with pytest.raises(ValueError, match="construction_row_count"):
        replace(_profile(), construction_row_count=-1)


def _profile_for_dimension(
    dimension: DepthDimension,
    *,
    mechanism: DepthMechanismV1 | None = None,
    probe: DepthProbeV1 | None = None,
    required: bool = True,
) -> DepthArchitectureProfileV1:
    selected_probe = probe or _probe()
    selected_mechanism = mechanism or replace(
        _mechanism(),
        dimension=dimension,
    )
    contract = replace(
        _dimension(),
        dimension=dimension,
        target_definition=f"target-linked definition for {dimension.value.lower()}",
        required=required,
        mechanism_ids=(selected_mechanism.mechanism_id,),
        probe_ids=(selected_probe.probe_id,),
    )
    return replace(
        _profile(),
        dimension_contracts=(contract,),
        mechanisms=(selected_mechanism,),
        probes=(selected_probe,),
    )


def test_evaluator_accepts_a_closed_target_linked_design_without_granting_authority() -> None:
    result = evaluate_depth_profile(_profile())

    assert result.state is DepthDesignState.DESIGN_READY
    assert result.reason_codes == ("DESIGN_READY_EXPERIMENTS_SPECIFIED",)
    assert result.blockers == ()
    assert result.uncovered_dimensions == ()
    assert result.empirical_authority is False
    assert result.sensory_authority is False
    assert result.similarity_authority is False
    assert result.hedonic_authority is False
    assert result.performance_authority is False
    assert result.safety_authority is False
    assert result.stability_authority is False
    assert result.release_authority is False


def test_evaluator_holds_construction_count_as_the_only_depth_dimension() -> None:
    profile = _profile_for_dimension(
        DepthDimension.CONSTRUCTION_COMPLEXITY,
        mechanism=replace(
            _mechanism(),
            dimension=DepthDimension.CONSTRUCTION_COMPLEXITY,
            kind=DepthMechanismKind.PHYSICAL_CONSTRAINT,
            causal_hypothesis="the formula contains sixty-four counted odor rows",
            expected_contribution="construction burden is recorded without a sensory inference",
        ),
    )

    result = evaluate_depth_profile(profile)

    assert result.state is DepthDesignState.HOLD
    assert "HOLD_COUNT_ONLY_DEPTH" in result.reason_codes


def test_evaluator_holds_a_required_dimension_without_mechanism_or_probe() -> None:
    missing = replace(
        _profile(),
        dimension_contracts=(
            replace(
                _dimension(),
                dimension=DepthDimension.INTERNAL_ANATOMY,
                mechanism_ids=(),
                probe_ids=(),
            ),
        ),
        mechanisms=(),
        probes=(),
    )

    result = evaluate_depth_profile(missing)

    assert result.state is DepthDesignState.HOLD
    assert "HOLD_REQUIRED_DIMENSION" in result.reason_codes
    assert result.uncovered_dimensions == (DepthDimension.INTERNAL_ANATOMY,)


def test_evaluator_holds_mechanisms_without_existing_falsification_probe() -> None:
    mechanism = replace(
        _mechanism(),
        falsification_probe_id="probe_that_does_not_exist",
    )
    profile = replace(
        _profile(),
        mechanisms=(mechanism,),
    )

    result = evaluate_depth_profile(profile)

    assert result.state is DepthDesignState.HOLD
    assert "HOLD_UNBOUND_MECHANISM" in result.reason_codes
    assert result.unbound_mechanism_ids == (mechanism.mechanism_id,)


def test_evaluator_holds_unblinded_hedonic_architecture() -> None:
    probe = replace(
        _probe(probe_type=DepthProbeType.HEDONIC_PREFERENCE),
        primary_endpoints=("liking", "desire to re-smell"),
        blinding_rule="open labels reveal the complete and omission arms",
    )
    mechanism = replace(
        _mechanism(),
        dimension=DepthDimension.HEDONIC_ARCHITECTURE,
        kind=DepthMechanismKind.HEDONIC_TENSION_RELEASE,
        causal_hypothesis="controlled bitter shadow increases rewarding floral relief",
        expected_contribution="higher liking and re-smelling without identity loss",
    )
    profile = _profile_for_dimension(
        DepthDimension.HEDONIC_ARCHITECTURE,
        mechanism=mechanism,
        probe=probe,
    )

    result = evaluate_depth_profile(profile)

    assert result.state is DepthDesignState.HOLD
    assert "HOLD_HEDONIC_BLINDING" in result.reason_codes


def test_evaluator_holds_temporal_depth_with_only_one_window() -> None:
    probe = _probe(
        probe_type=DepthProbeType.TEMPORAL,
        time_windows=("0_min",),
    )
    mechanism = replace(
        _mechanism(),
        dimension=DepthDimension.TEMPORAL_ARCHITECTURE,
        kind=DepthMechanismKind.TEMPORAL_HANDOFF,
        temporal_windows=("0_min",),
    )
    profile = _profile_for_dimension(
        DepthDimension.TEMPORAL_ARCHITECTURE,
        mechanism=mechanism,
        probe=probe,
    )

    result = evaluate_depth_profile(profile)

    assert result.state is DepthDesignState.HOLD
    assert "HOLD_TEMPORAL_WINDOWS" in result.reason_codes


def test_evaluator_requires_five_temporal_windows_and_adaptation_control() -> None:
    four_windows = ("0_min", "5_min", "30_min", "2_hour")
    probe = _probe(
        probe_type=DepthProbeType.TEMPORAL,
        time_windows=four_windows,
    )
    mechanism = replace(
        _mechanism(),
        dimension=DepthDimension.TEMPORAL_ARCHITECTURE,
        kind=DepthMechanismKind.TEMPORAL_HANDOFF,
        temporal_windows=four_windows,
    )
    profile = _profile_for_dimension(
        DepthDimension.TEMPORAL_ARCHITECTURE,
        mechanism=mechanism,
        probe=probe,
    )

    result = evaluate_depth_profile(profile)

    assert result.state is DepthDesignState.HOLD
    assert "HOLD_TEMPORAL_WINDOWS" in result.reason_codes

    five_windows = (*four_windows, "4_hour")
    no_adaptation_control = replace(
        profile,
        mechanisms=(replace(mechanism, temporal_windows=five_windows),),
        probes=(replace(probe, time_windows=five_windows),),
    )

    result = evaluate_depth_profile(no_adaptation_control)

    assert result.state is DepthDesignState.HOLD
    assert "HOLD_TEMPORAL_ADAPTATION_CONTROL" in result.reason_codes

    controlled = replace(
        no_adaptation_control,
        probes=(
            replace(
                no_adaptation_control.probes[0],
                constant_constraints=(
                    *no_adaptation_control.probes[0].constant_constraints,
                    "fresh coded applications at each window control olfactory adaptation",
                ),
            ),
        ),
    )

    result = evaluate_depth_profile(controlled)

    assert result.state is DepthDesignState.DESIGN_READY
    assert "HOLD_TEMPORAL_WINDOWS" not in result.reason_codes
    assert "HOLD_TEMPORAL_ADAPTATION_CONTROL" not in result.reason_codes


def test_evaluator_separates_hedonic_valence_from_hedonic_architecture() -> None:
    liking_only_probe = replace(
        _probe(probe_type=DepthProbeType.HEDONIC_PREFERENCE),
        primary_endpoints=("liking", "preference"),
    )
    mechanism = replace(
        _mechanism(),
        dimension=DepthDimension.HEDONIC_ARCHITECTURE,
        kind=DepthMechanismKind.HEDONIC_TENSION_RELEASE,
        causal_hypothesis="controlled shadow creates a tension-and-relief path",
        expected_contribution="higher liking without identity loss",
    )
    profile = _profile_for_dimension(
        DepthDimension.HEDONIC_ARCHITECTURE,
        mechanism=mechanism,
        probe=liking_only_probe,
    )

    result = evaluate_depth_profile(profile)

    assert result.state is DepthDesignState.HOLD
    assert "HOLD_HEDONIC_ENDPOINT_SEPARATION" in result.reason_codes


def test_evaluator_blocks_oav_model_language_from_becoming_performance_truth() -> None:
    probe = _probe(probe_type=DepthProbeType.SPATIAL)
    mechanism = replace(
        _mechanism(),
        dimension=DepthDimension.SPATIAL_PERFORMANCE,
        kind=DepthMechanismKind.DIFFUSION_CARRIER,
        causal_hypothesis="modeled OAV establishes physical sillage and projection",
        expected_contribution="guaranteed performance from calculated headspace",
    )
    profile = _profile_for_dimension(
        DepthDimension.SPATIAL_PERFORMANCE,
        mechanism=mechanism,
        probe=probe,
    )

    result = evaluate_depth_profile(profile)

    assert result.state is DepthDesignState.HOLD
    assert "HOLD_MODELED_PERFORMANCE_CLAIM" in result.reason_codes


def test_evaluator_requires_constant_total_geometry_for_ablation() -> None:
    probe = replace(
        _probe(),
        constant_constraints=("same application mass",),
    )
    profile = _profile_for_dimension(
        DepthDimension.OBJECT_IDENTITY,
        probe=probe,
    )

    result = evaluate_depth_profile(profile)

    assert result.state is DepthDesignState.HOLD
    assert "HOLD_CONSTANT_TOTAL" in result.reason_codes


def test_evaluator_enforces_computational_claim_ceiling() -> None:
    profile = replace(_profile(), claim_ceiling="SENSORY_DEPTH_CONFIRMED")

    result = evaluate_depth_profile(profile)

    assert result.state is DepthDesignState.HOLD
    assert "HOLD_CLAIM_CEILING" in result.reason_codes


def test_same_family_comparison_reports_shared_and_unique_mechanisms_without_ranking() -> None:
    left = _profile()
    second_probe = _probe(
        "probe_identity_ratio",
        probe_type=DepthProbeType.RATIO_SWEEP,
    )
    second_mechanism = replace(
        _mechanism("mechanism_identity_contrast", probe_id=second_probe.probe_id),
        kind=DepthMechanismKind.CONTRAST,
        causal_hypothesis="a cool green edge increases relief around the white floral object",
        expected_contribution="clearer object boundary without green-family drift",
    )
    right = replace(
        left,
        profile_id="profile_white_flower_reference_with_contrast",
        dimension_contracts=(
            replace(
                left.dimension_contracts[0],
                mechanism_ids=(left.mechanisms[0].mechanism_id, second_mechanism.mechanism_id),
                probe_ids=(left.probes[0].probe_id, second_probe.probe_id),
            ),
        ),
        mechanisms=(*left.mechanisms, second_mechanism),
        probes=(*left.probes, second_probe),
    )

    result = compare_depth_profiles(left, right)

    assert result.same_family is True
    assert result.left_profile_sha256 == left.profile_sha256
    assert result.right_profile_sha256 == right.profile_sha256
    assert len(result.dimension_comparisons) == 1
    dimension = result.dimension_comparisons[0]
    assert dimension.alignment is DepthDimensionAlignment.TARGET_ALIGNED
    assert dimension.shared_mechanism_kinds == (DepthMechanismKind.ANCHOR,)
    assert dimension.left_only_mechanism_ids == ()
    assert dimension.right_only_mechanism_ids == (second_mechanism.mechanism_id,)
    assert result.sensory_similarity_authority is False
    assert result.sensory_preference_authority is False
    assert result.release_authority is False
    assert result.safety_authority is False
    assert result.stability_authority is False

    forbidden_key_fragments = ("score", "winner", "rank", "better", "superior", "deeper")
    assert not {
        key
        for key in _serialized_keys(result.as_dict())
        if any(fragment in key.lower() for fragment in forbidden_key_fragments)
    }


def test_cross_family_comparison_preserves_target_anatomy_and_abstains() -> None:
    floral = _profile()
    wood_probe = _probe("probe_wood_texture", probe_type=DepthProbeType.TEXTURE)
    wood_mechanism = replace(
        _mechanism("mechanism_wood_grain", probe_id=wood_probe.probe_id),
        dimension=DepthDimension.TEXTURE_MATERIALITY,
        kind=DepthMechanismKind.TEXTURE_MODULATION,
        target_link="the wood object requires polished grain over a yielding creamy interior",
        causal_hypothesis="dry grain and creamy body create a differentiated wood surface",
        participant_ids=("module_dry_grain", "module_creamy_body"),
        expected_contribution="resolved grain and body without generic woody-amber mass",
        failure_mode="flat woody-amber wall",
    )
    wood_contract = replace(
        _dimension(wood_mechanism.mechanism_id, wood_probe.probe_id),
        dimension=DepthDimension.TEXTURE_MATERIALITY,
        target_definition="polished dry grain enclosing a creamy and fibrous wood body",
        observable_endpoints=("grain clarity", "surface-to-body distinction"),
        failure_modes=("generic woody-amber wall",),
    )
    wood = replace(
        floral,
        profile_id="profile_polished_root_chamber",
        target_identity="Polished Root Chamber",
        family=PerfumeFamily.WOODY,
        emotional_tone="warm carved wood crossed by a cool mineral seam",
        realism_or_abstraction_target="recognizable wood materiality in an abstract architectural form",
        ideal_formula_ref="target://polished-root-chamber/ideal/v1",
        current_inventory_build_ref="inventory://polished-root-chamber/current/v1",
        dimension_contracts=(wood_contract,),
        mechanisms=(wood_mechanism,),
        probes=(wood_probe,),
    )

    result = compare_depth_profiles(floral, wood)

    assert result.same_family is False
    assert {item.dimension for item in result.dimension_comparisons} == {
        DepthDimension.OBJECT_IDENTITY,
        DepthDimension.TEXTURE_MATERIALITY,
    }
    assert {item.alignment for item in result.dimension_comparisons} == {
        DepthDimensionAlignment.LEFT_ONLY,
        DepthDimensionAlignment.RIGHT_ONLY,
    }
    assert result.target_incompatibilities
    assert any("cross-family" in item.lower() for item in result.abstentions)
    assert any("physical sensory evidence" in item.lower() for item in result.abstentions)


def test_comparison_hash_and_serialization_are_deterministic() -> None:
    result = compare_depth_profiles(_profile(), _profile())

    assert result.comparison_sha256 == result.comparison_sha256
    assert len(result.comparison_sha256) == 64
    assert result.as_dict() == compare_depth_profiles(_profile(), _profile()).as_dict()


def test_every_perfume_family_has_a_distinct_complete_depth_template() -> None:
    templates = all_family_depth_templates()

    assert tuple(item.family for item in templates) == tuple(PerfumeFamily)
    assert len(templates) == len(PerfumeFamily)
    signatures = set()
    for template in templates:
        assert template.identity_questions
        assert template.anatomy_axes
        assert template.relationship_mechanisms
        assert template.texture_vocabulary
        assert template.temporal_questions
        assert template.spatial_questions
        assert template.hedonic_questions
        assert template.collapse_risks
        assert DepthDimension.OBJECT_IDENTITY in template.required_dimensions
        assert DepthDimension.RELATIONAL_TOPOLOGY in template.required_dimensions
        assert DepthDimension.ROBUSTNESS_ANTI_COLLAPSE in template.required_dimensions
        assert len(template.template_sha256) == 64
        signatures.add((template.anatomy_axes, template.collapse_risks))
        assert family_depth_template(template.family) == template

    assert len(signatures) == len(PerfumeFamily)


def _minimal_floral_request() -> FloralDesignRequestV1:
    identity = FloralIdentityContractV1(
        target_identity="White Champi Under Glass",
        emotional_tone="cool lucid petals opening toward warm narcotic flesh",
        floral_subjects=(
            FloralSubjectV1(
                subject_id="white_champi",
                name="White Champi",
                role=FloralSubjectRole.LEAD,
            ),
        ),
        floral_scope=FloralScope.SOLIFLORE,
        realism_target="recognizable living white champi translated through glass-like abstraction",
        ideal_formula_ref="formula:white-champi:ideal:v1",
        current_inventory_build_ref="formula:white-champi:current:v1",
        allowed_source_classes=(
            FloralSourceClass.ESSENTIAL_OIL,
            FloralSourceClass.ABSOLUTE,
            FloralSourceClass.KNOWN_CHEMICAL,
        ),
        forbidden_drift=("generic white floral", "detergent musk"),
        evidence_refs=("source:white-champi-design",),
        claim_ceiling="COMPUTATIONAL_EXPERIMENT_DESIGN_ONLY",
    )
    facet = FloralFacetV1(
        facet_id="white_champi_petal",
        facet_class=FloralFacetClass.PETAL,
        target_function="cool luminous petal recognizer",
        subject_owner="white_champi",
        omission_loss="the flower loses its white champi petal identity",
        failure_mode="generic muguet-like white floral blur",
        required_temporal_windows=("OPENING", "30_MIN", "2_HOUR"),
        evidence_refs=("source:white-champi-design",),
        ideal_materials=("white_champi_eo",),
        current_build_bindings=("white_champi_eo",),
        controlled_comparison_ref="trial_white_champi_petal",
    )
    contour = FloralTemporalContourV1(
        windows=(
            FloralTemporalWindowV1(
                window_id="OPENING",
                required_recognizers=("WHITE_CHAMPI_PRESENT",),
                state_hypothesis="cool petal and humid air lead",
            ),
            FloralTemporalWindowV1(
                window_id="2_HOUR",
                required_recognizers=("WHITE_CHAMPI_PRESENT",),
                state_hypothesis="warm flesh and petal memory remain coupled",
            ),
        )
    )
    trial = FloralTrainingTrialV1(
        trial_id="trial_white_champi_petal",
        domain=TrainingDomain.FLORAL,
        stage_order=1,
        changed_factor="WHITE_CHAMPI_PETAL_RECOGNIZER",
        intervention_material_ids=("white_champi_eo",),
        controlled_arms=("FULL_TARGET", "CARRIER_MATCHED_PETAL_OMISSION"),
        primary_endpoints=("TARGET_IDENTITY", "PETAL_CLARITY"),
        failure_endpoints=("GENERIC_WHITE_FLORAL", "TARGET_DRIFT"),
        constant_constraints=("CONSTANT_TOTAL_RAW_VOLUME", "SAME_APPLICATION_MASS"),
        prerequisite_trial_ids=(),
        accept_rule="retain only for repeatable target identity with clearer petal anatomy",
        reject_rule="reject for no difference, blur, or target drift",
        blinding_rule="opaque three-digit codes conceal arm identity",
        order_rule="balanced order with a repeated coded control",
        time_windows=("OPENING", "30_MIN", "2_HOUR"),
        evidence_refs=("source:white-champi-design",),
    )
    return FloralDesignRequestV1(
        identity=identity,
        strategy=FloralDepthStrategy.ANATOMICAL_CONTINUUM,
        facets=(facet,),
        coupling=None,
        temporal_contour=contour,
        ideal_materials=(),
        current_build_materials=(),
        preparations=(),
        missing_chemical_impacts=(),
        wood_texture_contracts=(),
        training_trials=(trial,),
        passed_trial_ids=(),
        no_change_reason="no change only when no target-linked deficiency remains",
        architecture_contract=None,
    )


def test_floral_adapter_preserves_target_ledgers_controls_and_claim_ceiling() -> None:
    request = _minimal_floral_request()

    profile = adapt_floral_design_request(
        request,
        profile_id="depth:white-champi-under-glass:v1",
        evidence_refs=("adapter:test-receipt",),
    )

    assert profile.family is PerfumeFamily.FLORAL
    assert profile.target_identity == request.identity.target_identity
    assert profile.emotional_tone == request.identity.emotional_tone
    assert profile.realism_or_abstraction_target == request.identity.realism_target
    assert profile.ideal_formula_ref == request.identity.ideal_formula_ref
    assert profile.current_inventory_build_ref == request.identity.current_inventory_build_ref
    assert profile.forbidden_drift == request.identity.forbidden_drift
    assert profile.claim_ceiling == request.identity.claim_ceiling
    assert {probe.probe_id for probe in profile.probes} == {
        trial.trial_id for trial in request.training_trials
    }
    assert "adapter:test-receipt" in profile.source_refs
    assert {
        DepthDimension.OBJECT_IDENTITY,
        DepthDimension.INTERNAL_ANATOMY,
        DepthDimension.TEMPORAL_ARCHITECTURE,
        DepthDimension.ROBUSTNESS_ANTI_COLLAPSE,
    }.issubset({item.dimension for item in profile.dimension_contracts})
    assert any(
        "white_champi_eo" in mechanism.participant_ids
        for mechanism in profile.mechanisms
    )
    assert profile.construction_row_count == 0


def test_floral_adapter_is_deterministic_and_keeps_authority_false() -> None:
    request = _minimal_floral_request()
    left = adapt_floral_design_request(
        request,
        profile_id="depth:white-champi-under-glass:v1",
        evidence_refs=("adapter:test-receipt",),
    )
    right = adapt_floral_design_request(
        request,
        profile_id="depth:white-champi-under-glass:v1",
        evidence_refs=("adapter:test-receipt",),
    )

    assert left.as_dict() == right.as_dict()
    assert left.profile_sha256 == right.profile_sha256
    assert left.sensory_authority is False
    assert left.hedonic_authority is False
    assert left.performance_authority is False


def _formula_bound_pipeline_payload(material_names: tuple[str, ...]) -> dict[str, object]:
    materials = [
        {
            "name": name,
            "canonical_name": name.casefold(),
            "raw_ul": 20.0,
            "active_ul": 20.0,
            "oav": 1.0,
            "sources": {"oav_model": "heuristic:monomolecular_headspace"},
        }
        for name in material_names
    ]
    time_series = [
        {
            "label": label,
            "t_seconds": seconds,
            "temporal_authority": "HEURISTIC_UNCALIBRATED",
            "state": {
                "total_raw_ul": 20.0 * len(material_names),
                "total_active_ul": 20.0 * len(material_names),
                "headspace_basis": "MODELED_ACTIVE_CONCENTRATE_SCREEN",
                "materials": materials,
            },
        }
        for label, seconds in (
            ("opening", 0.0),
            ("top", 300.0),
            ("heart", 1800.0),
            ("late_heart", 7200.0),
            ("drydown", 14400.0),
        )
    ]
    return {
        "overall": "FAIL",
        "release_evidence_overall": "HOLD",
        "formulas": [
            {
                "name": "CURRENT-INVENTORY BUILD",
                "number": 1,
                "formula_hash": "b" * 64,
                "formula_state": {
                    "total_raw_ul": 20.0 * len(material_names),
                    "total_active_ul": 20.0 * len(material_names),
                    "headspace_basis": "MODELED_ACTIVE_CONCENTRATE_SCREEN",
                    "materials": materials,
                },
                "time_series": time_series,
            }
        ],
        "run_evidence_contract": {
            "formula_definitions": [
                {
                    "number": 1,
                    "name": "CURRENT-INVENTORY BUILD",
                    "sha256": "a" * 64,
                }
            ],
            "analysis_input_sha256": "c" * 64,
            "inventory_sha256": "d" * 64,
            "scientific_inputs_sha256": "e" * 64,
            "pipeline_source_sha256": "f" * 64,
        },
    }


def test_formula_bound_profile_uses_canonical_definition_hash_not_legacy_hash(
    tmp_path,
) -> None:
    formula_path = tmp_path / "canonical-bound-floral.md"
    formula_path.write_text(
        "# Canonical Bound Floral\n\n"
        "## CURRENT-INVENTORY BUILD\n\n"
        "| # | Material | Dilution | Amount (uL) | Active uL | Active ppm | Current-build function |\n"
        "|---:|---|---|---:|---:|---:|---|\n"
        "| 1 | Material A | neat | 20 | 20 | 500000 | R01 petal surface |\n"
        "| 2 | Material B | neat | 20 | 20 | 500000 | R02 warm flesh |\n\n"
        "## END\n",
        encoding="utf-8",
    )
    payload = _formula_bound_pipeline_payload(("Material A", "Material B"))

    profile = depth_family_adapters.adapt_floral_formula_depth_profile(
        _minimal_floral_request(),
        profile_id="depth:canonical-bound-floral:v1",
        evidence_refs=("adapter:canonical-formula-binding-test",),
        formula_path=formula_path,
        pipeline_payload=payload,
        current_build_heading="## CURRENT-INVENTORY BUILD",
    )

    assert profile.formula_evidence is not None
    assert profile.formula_evidence.formula_definition_sha256 == "a" * 64
    assert profile.formula_evidence.formula_definition_sha256 != "b" * 64


def test_formula_bound_floral_profile_uses_all_rows_and_all_universal_dimensions(
    tmp_path,
) -> None:
    formula_path = tmp_path / "bound_floral.md"
    formula_path.write_text(
        "# Bound Floral\n\n"
        "## CURRENT-INVENTORY BUILD\n\n"
        "| # | Material | Dilution | Amount (uL) | Active uL | Active ppm | Current-build function |\n"
        "|---:|---|---|---:|---:|---:|---|\n"
        "| 1 | Material A | neat | 20 | 20 | 333333.3333 | R01 petal surface |\n"
        "| 2 | Material B | neat | 20 | 20 | 333333.3333 | R02 warm flesh |\n"
        "| 3 | Material C | neat | 20 | 20 | 333333.3333 | R03 flower-linked wood echo |\n"
        "|  | **Total concentrate** |  | **60** | **60** | **1000000** | test total |\n\n"
        "## END\n",
        encoding="utf-8",
    )
    adapter = getattr(
        depth_family_adapters,
        "adapt_floral_formula_depth_profile",
        None,
    )
    assert callable(adapter), "formula-bound floral depth adapter is missing"

    profile = adapter(
        _minimal_floral_request(),
        profile_id="depth:bound-floral:v1",
        evidence_refs=("adapter:formula-binding-test",),
        formula_path=formula_path,
        pipeline_payload=_formula_bound_pipeline_payload(
            ("Material A", "Material B", "Material C")
        ),
        current_build_heading="## CURRENT-INVENTORY BUILD",
    )

    assert profile.construction_row_count == 3
    assert profile.formula_evidence is not None
    assert profile.formula_evidence.formula_row_count == 3
    assert profile.formula_evidence.role_ids == ("R01", "R02", "R03")
    assert profile.formula_evidence.material_names == (
        "Material A",
        "Material B",
        "Material C",
    )
    assert profile.formula_evidence.temporal_windows == (
        "opening",
        "top",
        "heart",
        "late_heart",
        "drydown",
    )
    dimensions = {contract.dimension for contract in profile.dimension_contracts}
    required = set(family_depth_template(PerfumeFamily.FLORAL).required_dimensions)
    assert required.issubset(dimensions)
    assert DepthDimension.CONSTRUCTION_COMPLEXITY in dimensions

    result = evaluate_depth_profile(profile)
    assert result.state is DepthDesignState.DESIGN_READY
    assert result.empirical_authority is False
    assert result.sensory_authority is False
    assert result.hedonic_authority is False
    assert result.performance_authority is False


def test_formula_bound_floral_profile_supports_standard_five_column_build(
    tmp_path,
) -> None:
    formula_path = tmp_path / "compact_bound_floral.md"
    formula_path.write_text(
        "# Compact Bound Floral\n\n"
        "## 3. TARGET / IDEAL FORMULA\n\n"
        "| # | Target material / stock | Raw uL | Role | Target-linked function |\n"
        "|---:|---|---:|---|---|\n"
        "| 1 | Ideal Material A, 10% | 20 | R01 | transparent petal surface |\n"
        "| 2 | Ideal Material B, 50% | 20 | R02 | warm flower-linked wood echo |\n\n"
        "## 4. CURRENT-INVENTORY BUILD - Compact Bound Floral\n\n"
        "| # | Material | Dilution | Amount (uL) | Role |\n"
        "|---:|---|---|---:|---|\n"
        "| 1 | Material A | 10% | 20 | R01 |\n"
        "| 2 | Material B | 50% | 20 | R02 |\n"
        "|  | **Total concentrate** |  | **40** | exact total |\n\n"
        "## END\n",
        encoding="utf-8",
    )
    payload = _formula_bound_pipeline_payload(("Material A", "Material B"))
    state = payload["formulas"][0]["formula_state"]
    state["materials"][0]["active_ul"] = 2.0
    state["materials"][1]["active_ul"] = 10.0
    state["total_active_ul"] = 12.0

    profile = depth_family_adapters.adapt_floral_formula_depth_profile(
        _minimal_floral_request(),
        profile_id="depth:compact-bound-floral:v1",
        evidence_refs=("adapter:compact-formula-binding-test",),
        formula_path=formula_path,
        pipeline_payload=payload,
        current_build_heading=(
            "## 4. CURRENT-INVENTORY BUILD - Compact Bound Floral"
        ),
    )

    assert profile.formula_evidence is not None
    assert tuple(
        (
            role.role_id,
            role.material_name,
            role.raw_ul,
            role.active_ul,
            role.active_ppm,
            role.target_function,
        )
        for role in profile.formula_evidence.roles
    ) == (
        (
            "R01",
            "Material A",
            20.0,
            2.0,
            50_000.0,
            "transparent petal surface",
        ),
        (
            "R02",
            "Material B",
            20.0,
            10.0,
            250_000.0,
            "warm flower-linked wood echo",
        ),
    )


def test_formula_bound_floral_profile_rejects_pipeline_material_mismatch(tmp_path) -> None:
    formula_path = tmp_path / "mismatch.md"
    formula_path.write_text(
        "# Mismatch\n\n"
        "## CURRENT-INVENTORY BUILD\n\n"
        "| # | Material | Dilution | Amount (uL) | Active uL | Active ppm | Current-build function |\n"
        "|---:|---|---|---:|---:|---:|---|\n"
        "| 1 | Material A | neat | 20 | 20 | 500000 | R01 petal surface |\n"
        "| 2 | Material B | neat | 20 | 20 | 500000 | R02 warm flesh |\n\n"
        "## END\n",
        encoding="utf-8",
    )
    adapter = getattr(
        depth_family_adapters,
        "adapt_floral_formula_depth_profile",
        None,
    )
    assert callable(adapter), "formula-bound floral depth adapter is missing"

    with pytest.raises(ValueError, match="pipeline material set"):
        adapter(
            _minimal_floral_request(),
            profile_id="depth:mismatch:v1",
            evidence_refs=("adapter:formula-binding-test",),
            formula_path=formula_path,
            pipeline_payload=_formula_bound_pipeline_payload(("Material A",)),
            current_build_heading="## CURRENT-INVENTORY BUILD",
        )


def test_bounded_reference_profile_supports_non_scalar_cross_family_comparison() -> None:
    builder = getattr(
        depth_family_adapters,
        "build_bounded_reference_depth_profile",
        None,
    )
    assert callable(builder), "bounded reference depth-profile builder is missing"

    reference = builder(
        profile_id="depth:dhp-2025-local-study:v1",
        target_identity="DHP 2025 local iris-sandalwood-amber study",
        family=PerfumeFamily.HYBRID_MULTIFAMILY,
        emotional_tone="transparent orris authority over sandalwood-amber warmth",
        realism_or_abstraction_target="abstract iris and tactile wood architecture",
        forbidden_drift=(
            "generic woody amber",
            "powder without iris identity",
            "sweet musk block",
        ),
        ideal_formula_ref="reference:dhp-2025:ideal:v1",
        current_inventory_build_ref="reference:dhp-2025:local-study:v1",
        construction_row_count=25,
        temporal_windows=("opening", "top", "heart", "late_heart", "drydown"),
        source_refs=("local-formula-sha256:" + "a" * 64,),
        claim_ceiling="COMPUTATIONAL_EXPERIMENT_DESIGN_ONLY",
    )

    evaluation = evaluate_depth_profile(reference)
    assert evaluation.state is DepthDesignState.DESIGN_READY
    assert set(family_depth_template(reference.family).required_dimensions).issubset(
        {contract.dimension for contract in reference.dimension_contracts}
    )
    assert reference.formula_evidence is None
    assert reference.sensory_authority is False
    assert reference.hedonic_authority is False
    assert reference.performance_authority is False

    floral = _profile()
    comparison = compare_depth_profiles(floral, reference)
    assert comparison.same_family is False
    assert comparison.hedonic_authority is False
    assert comparison.sensory_preference_authority is False
    assert comparison.performance_authority is False
    assert comparison.target_incompatibilities
    assert all(
        dimension.alignment
        is DepthDimensionAlignment.SAME_CONSTRUCT_DIFFERENT_TARGET
        or dimension.alignment in {
            DepthDimensionAlignment.LEFT_ONLY,
            DepthDimensionAlignment.RIGHT_ONLY,
        }
        for dimension in comparison.dimension_comparisons
    )
