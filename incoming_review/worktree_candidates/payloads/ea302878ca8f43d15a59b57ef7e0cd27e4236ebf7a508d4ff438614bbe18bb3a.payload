from __future__ import annotations

from dataclasses import replace

import pytest

from engine.hedonic_evidence import (
    EvaluationSubstrate,
    HedonicEvidenceRequest,
    HedonicEvidenceState,
    HedonicScope,
    PreferenceEvidenceAdequacyContract,
    PreferenceItemEvidenceBinding,
    SensoryEvaluationContext,
    bind_preference_fit_evidence,
    bind_preference_fit_evidence_v2,
    bind_preference_fit_evidence_v3,
    evaluate_hedonic_evidence,
)
from engine.pipeline.release_evidence import EvidenceAxisState, release_axis_from_hedonic
from engine.preference import PairwisePreference, PreferenceFitRequest, fit_preference_model
from engine.preference_davidson import DavidsonFitConfig, fit_davidson
from engine.preference_validation import (
    ClusterBootstrapConfig,
    HeldoutValidationConfig,
    NextPairConstraints,
    OrderCarryoverConfig,
    TransitivityConfig,
)

FORMULA_A = "a" * 64
FORMULA_B = "b" * 64
FORMULA_C = "c" * 64
SAMPLE_A = "d" * 64
SAMPLE_B = "e" * 64
SAMPLE_C = "f" * 64
PROTOCOL_SHA = "1" * 64
SCHEDULE_SHA = "2" * 64


def _context(*, substrate: EvaluationSubstrate = EvaluationSubstrate.BLOTTER):
    skin = substrate is EvaluationSubstrate.SKIN
    return SensoryEvaluationContext(
        context_id="ctx-owner-wear" if skin else "ctx-blotter",
        substrate=substrate,
        application_protocol_sha256="3" * 64,
        environment_sha256="4" * 64,
        maturation_state_sha256="5" * 64,
        carryover_control_sha256="6" * 64,
        carryover_qualified=True,
        apparatus_sha256="7" * 64 if not skin else None,
        wearer_id="owner-pseudonym" if skin else None,
        body_odor_context_sha256="8" * 64 if skin else None,
    )


def _bindings() -> tuple[PreferenceItemEvidenceBinding, ...]:
    return (
        PreferenceItemEvidenceBinding(
            item_id="A",
            build_sha256=FORMULA_A,
            sample_sha256=SAMPLE_A,
            provenance_manifest_sha256="9" * 64,
            sampling_or_dose_receipt_sha256="a" * 64,
            batch_id="batch-A",
        ),
        PreferenceItemEvidenceBinding(
            item_id="B",
            build_sha256=FORMULA_B,
            sample_sha256=SAMPLE_B,
            provenance_manifest_sha256="b" * 64,
            sampling_or_dose_receipt_sha256="c" * 64,
            batch_id="batch-B",
        ),
        PreferenceItemEvidenceBinding(
            item_id="C",
            build_sha256=FORMULA_C,
            sample_sha256=SAMPLE_C,
            provenance_manifest_sha256="d" * 64,
            sampling_or_dose_receipt_sha256="e" * 64,
            batch_id="batch-C",
        ),
    )


def _row(
    comparison_id: str,
    assessor: str,
    left: str,
    right: str,
    winner: str,
    first: str,
    partition: str,
    context: SensoryEvaluationContext,
) -> PairwisePreference:
    samples = {"A": SAMPLE_A, "B": SAMPLE_B, "C": SAMPLE_C}
    return PairwisePreference(
        left,
        right,
        winner,
        comparison_id=comparison_id,
        assessor_id=assessor,
        protocol_id="liking-v3",
        criterion_id="LIKING",
        time_seconds=300,
        first_presented_item=first,
        session_id=f"session-{comparison_id}",
        matrix_id="matrix-v3",
        time_window_id="heart",
        position_in_session=1,
        protocol_sha256=PROTOCOL_SHA,
        sample_sha256=samples[left],
        left_sample_sha256=samples[left],
        right_sample_sha256=samples[right],
        evaluation_context_sha256=context.record_sha256,
        partition=partition,
    )


def _rows(
    assessors: tuple[str, ...],
    partition: str,
    context: SensoryEvaluationContext,
) -> tuple[PairwisePreference, ...]:
    rows: list[PairwisePreference] = []
    winners = {("A", "B"): "A", ("A", "C"): "A", ("B", "C"): "B"}
    for assessor in assessors:
        for left, right in winners:
            winner = winners[(left, right)]
            rows.append(
                _row(
                    f"{partition}-{assessor}-{left}{right}-1",
                    assessor,
                    left,
                    right,
                    winner,
                    left,
                    partition,
                    context,
                )
            )
            rows.append(
                _row(
                    f"{partition}-{assessor}-{left}{right}-2",
                    assessor,
                    left,
                    right,
                    winner,
                    right,
                    partition,
                    context,
                )
            )
    return tuple(rows)


def _evidence(*, heldout_bootstrap: int = 100, order_confounded: bool = False):
    context = _context()
    training = _rows(("p1", "p2"), "TRAINING", context)
    heldout = _rows(("p3", "p4"), "HELDOUT", context)
    if order_confounded:
        training = tuple(replace(row, first_presented_item=row.preferred_item) for row in training)
        heldout = tuple(replace(row, first_presented_item=row.preferred_item) for row in heldout)
    request = PreferenceFitRequest(
        training=training,
        heldout=heldout,
        minimum_comparisons=12,
        minimum_heldout_comparisons=6,
        declared_baseline_accuracy=0.5,
        criterion_id="LIKING",
        bootstrap_replicates=20,
        bootstrap_seed=31,
        require_scoped_validation=True,
    )
    result = fit_preference_model(request)
    repeat_map = {
        row.comparison_id or "": "repeat-1" for row in training + heldout
    }
    parent = bind_preference_fit_evidence(
        request,
        result,
        scope=HedonicScope.TRAINED_PANEL,
        formula_build_sha256=FORMULA_A,
        sample_sha256=(SAMPLE_A, SAMPLE_B, SAMPLE_C),
        protocol_sha256=PROTOCOL_SHA,
        assessor_ids=("p1", "p2", "p3", "p4"),
        repeat_ids=("repeat-1",),
        comparison_repeat_ids=repeat_map,
        time_seconds=300,
        schedule_sha256=SCHEDULE_SHA,
    )
    davidson = fit_davidson(
        items=("A", "B", "C"),
        comparisons=training,
        config=DavidsonFitConfig(
            regularization=request.regularization,
            maximum_iterations=request.maximum_iterations,
        ),
    )
    v2 = bind_preference_fit_evidence_v2(
        parent,
        davidson_fit=davidson,
        construct_registry_sha256="f" * 64,
        criterion_wording_sha256="0" * 64,
        source_transfer_sha256="1" * 64,
        source_transfer_state="DIRECT",
        bootstrap_config=ClusterBootstrapConfig(replicates=100, seed=31),
        heldout_config=HeldoutValidationConfig(
            split_unit="ASSESSOR",
            practical_margin=0.0,
            bootstrap_replicates=heldout_bootstrap,
            seed=31,
        ),
        transitivity_config=TransitivityConfig(),
        eligible_next_pairs=(("A", "B"), ("A", "C"), ("B", "C")),
        next_pair_constraints=NextPairConstraints(decision_resolved=True),
    )
    v3 = bind_preference_fit_evidence_v3(
        v2,
        focal_item_id="A",
        item_bindings=_bindings(),
        evaluation_context=context,
        adequacy_contract=PreferenceEvidenceAdequacyContract(
            analysis_plan_sha256="2" * 64,
            sampling_frame_sha256="3" * 64,
            minimum_assessors=4,
            minimum_directional_training_comparisons=12,
            minimum_heldout_groups=2,
            minimum_heldout_comparisons=6,
            minimum_cluster_bootstrap_replicates=100,
            minimum_heldout_bootstrap_replicates=100,
        ),
        order_carryover_config=OrderCarryoverConfig(
            maximum_pair_order_count_difference=0,
            maximum_absolute_first_position_effect=0.25,
            require_qualified_carryover=True,
        ),
    )
    return context, v2, v3


def _request(context: SensoryEvaluationContext, receipt) -> HedonicEvidenceRequest:
    return HedonicEvidenceRequest(
        criterion_id="LIKING",
        scope=HedonicScope.TRAINED_PANEL,
        formula_build_sha256=FORMULA_A,
        sample_sha256=(SAMPLE_A, SAMPLE_B, SAMPLE_C),
        protocol_sha256=PROTOCOL_SHA,
        assessor_ids=("p1", "p2", "p3", "p4"),
        repeat_ids=("repeat-1",),
        time_seconds=300,
        schedule_sha256=SCHEDULE_SHA,
        fit_receipt=receipt,
        focal_item_id="A",
        evaluation_context_sha256=context.record_sha256,
    )


def test_v2_receipt_is_compatibility_provenance_not_promotable_liking() -> None:
    context, v2, _ = _evidence()
    result = evaluate_hedonic_evidence(_request(context, v2))
    assert result.state is HedonicEvidenceState.DIAGNOSTIC
    assert "V3_ITEM_CONTEXT_BINDING_REQUIRED" in result.limitations


def test_fully_bound_v3_can_validate_only_the_exact_liking_scope() -> None:
    context, _, v3 = _evidence()
    result = evaluate_hedonic_evidence(_request(context, v3))
    assert result.state is HedonicEvidenceState.VALIDATED_EXACT_SCOPE
    assert result.evidence_schema_version == "preference_fit_evidence_v3"
    assert result.focal_item_id == "A"
    assert result.evaluation_context_sha256 == context.record_sha256
    assert result.item_bindings_sha256 == v3.item_bindings_sha256
    assert result.release_authority is False
    assert release_axis_from_hedonic(result).state is EvidenceAxisState.PASS


def test_item_label_to_sample_swap_is_rejected() -> None:
    context, v2, _ = _evidence()
    swapped = tuple(
        replace(row, left_sample_sha256=SAMPLE_B)
        if row.left_item == "A"
        else row
        for row in v2.fit_request.training
    )
    mutated_request = replace(v2.fit_request, training=swapped)
    mutated_result = fit_preference_model(mutated_request)
    parent = bind_preference_fit_evidence(
        mutated_request,
        mutated_result,
        scope=HedonicScope.TRAINED_PANEL,
        formula_build_sha256=FORMULA_A,
        sample_sha256=(SAMPLE_A, SAMPLE_B, SAMPLE_C),
        protocol_sha256=PROTOCOL_SHA,
        assessor_ids=("p1", "p2", "p3", "p4"),
        repeat_ids=("repeat-1",),
        comparison_repeat_ids={
            row.comparison_id or "": "repeat-1"
            for row in mutated_request.training + mutated_request.heldout
        },
        time_seconds=300,
        schedule_sha256=SCHEDULE_SHA,
    )
    davidson = fit_davidson(
        items=("A", "B", "C"),
        comparisons=swapped,
        config=DavidsonFitConfig(maximum_iterations=2000),
    )
    mutated_v2 = replace(v2, parent_v1=parent, davidson_fit=davidson)
    with pytest.raises(ValueError, match="left sample hash"):
        bind_preference_fit_evidence_v3(
            mutated_v2,
            focal_item_id="A",
            item_bindings=_bindings(),
            evaluation_context=context,
            adequacy_contract=PreferenceEvidenceAdequacyContract(
                analysis_plan_sha256="2" * 64,
                sampling_frame_sha256="3" * 64,
                minimum_assessors=1,
                minimum_directional_training_comparisons=1,
                minimum_heldout_groups=1,
                minimum_heldout_comparisons=1,
                minimum_cluster_bootstrap_replicates=1,
                minimum_heldout_bootstrap_replicates=1,
            ),
            order_carryover_config=OrderCarryoverConfig(),
        )


def test_legacy_sample_hash_must_name_one_item_in_its_comparison() -> None:
    context, v2, _ = _evidence()
    changed_training = tuple(
        replace(row, sample_sha256=SAMPLE_C)
        if row.left_item == "A" and row.right_item == "B"
        else row
        for row in v2.fit_request.training
    )
    changed_request = replace(v2.fit_request, training=changed_training)
    changed_parent = replace(v2.parent_v1, fit_request=changed_request)
    changed_v2 = replace(v2, parent_v1=changed_parent)

    with pytest.raises(ValueError, match="legacy sample hash"):
        bind_preference_fit_evidence_v3(
            changed_v2,
            focal_item_id="A",
            item_bindings=_bindings(),
            evaluation_context=context,
            adequacy_contract=PreferenceEvidenceAdequacyContract(
                analysis_plan_sha256="2" * 64,
                sampling_frame_sha256="3" * 64,
                minimum_assessors=1,
                minimum_directional_training_comparisons=1,
                minimum_heldout_groups=1,
                minimum_heldout_comparisons=1,
                minimum_cluster_bootstrap_replicates=1,
                minimum_heldout_bootstrap_replicates=1,
            ),
            order_carryover_config=OrderCarryoverConfig(),
        )


def test_item_bindings_must_cover_compared_items_exactly() -> None:
    context, v2, _ = _evidence()
    adequacy = PreferenceEvidenceAdequacyContract(
        analysis_plan_sha256="2" * 64,
        sampling_frame_sha256="3" * 64,
        minimum_assessors=1,
        minimum_directional_training_comparisons=1,
        minimum_heldout_groups=1,
        minimum_heldout_comparisons=1,
        minimum_cluster_bootstrap_replicates=1,
        minimum_heldout_bootstrap_replicates=1,
    )
    with pytest.raises(ValueError, match="exactly cover"):
        bind_preference_fit_evidence_v3(
            v2,
            focal_item_id="A",
            item_bindings=_bindings()[:-1],
            evaluation_context=context,
            adequacy_contract=adequacy,
            order_carryover_config=OrderCarryoverConfig(),
        )
    extra = PreferenceItemEvidenceBinding(
        "D", "4" * 64, "5" * 64, "6" * 64, "7" * 64, "batch-D"
    )
    with pytest.raises(ValueError, match="exactly cover"):
        bind_preference_fit_evidence_v3(
            v2,
            focal_item_id="A",
            item_bindings=(*_bindings(), extra),
            evaluation_context=context,
            adequacy_contract=adequacy,
            order_carryover_config=OrderCarryoverConfig(),
        )


def test_item_binding_samples_must_equal_parent_sample_set_without_duplicates() -> None:
    context, v2, _ = _evidence()
    adequacy = PreferenceEvidenceAdequacyContract(
        analysis_plan_sha256="2" * 64,
        sampling_frame_sha256="3" * 64,
        minimum_assessors=1,
        minimum_directional_training_comparisons=1,
        minimum_heldout_groups=1,
        minimum_heldout_comparisons=1,
        minimum_cluster_bootstrap_replicates=1,
        minimum_heldout_bootstrap_replicates=1,
    )
    duplicate_sample_bindings = (
        _bindings()[0],
        replace(_bindings()[1], sample_sha256=SAMPLE_A),
        _bindings()[2],
    )
    with pytest.raises(ValueError, match="distinct sample"):
        bind_preference_fit_evidence_v3(
            v2,
            focal_item_id="A",
            item_bindings=duplicate_sample_bindings,
            evaluation_context=context,
            adequacy_contract=adequacy,
            order_carryover_config=OrderCarryoverConfig(),
        )

    changed_parent = replace(
        v2.parent_v1,
        sample_sha256=(SAMPLE_A, SAMPLE_B, "9" * 64),
    )
    changed_v2 = replace(v2, parent_v1=changed_parent)
    with pytest.raises(ValueError, match="exactly match the parent sample set"):
        bind_preference_fit_evidence_v3(
            changed_v2,
            focal_item_id="A",
            item_bindings=_bindings(),
            evaluation_context=context,
            adequacy_contract=adequacy,
            order_carryover_config=OrderCarryoverConfig(),
        )


def test_skin_context_requires_wearer_and_body_odor_binding() -> None:
    with pytest.raises(ValueError, match="wearer_id"):
        SensoryEvaluationContext(
            context_id="skin",
            substrate=EvaluationSubstrate.SKIN,
            application_protocol_sha256="3" * 64,
            environment_sha256="4" * 64,
            maturation_state_sha256="5" * 64,
            carryover_control_sha256="6" * 64,
            carryover_qualified=True,
        )


def test_context_mismatch_invalidates_v3() -> None:
    context, _, v3 = _evidence()
    request = replace(_request(context, v3), evaluation_context_sha256="9" * 64)
    result = evaluate_hedonic_evidence(request)
    assert result.state is HedonicEvidenceState.INVALID_OR_CONFOUNDED
    assert "evaluation_context_sha256" in " ".join(result.blockers)


def test_zero_heldout_bootstrap_cannot_promote() -> None:
    context, _, v3 = _evidence(heldout_bootstrap=0)
    result = evaluate_hedonic_evidence(_request(context, v3))
    assert result.state is HedonicEvidenceState.INSUFFICIENT_EVIDENCE
    assert "HELDOUT_BOOTSTRAP_REPLICATES_INSUFFICIENT" in result.limitations


def test_only_completed_cluster_bootstrap_replicates_count_toward_adequacy() -> None:
    context, v2, _ = _evidence()
    shortened = replace(
        v2.cluster_bootstrap,
        completed_replicates=99,
        failed_replicates=1,
    )
    shortened_v2 = replace(v2, cluster_bootstrap=shortened)
    v3 = bind_preference_fit_evidence_v3(
        shortened_v2,
        focal_item_id="A",
        item_bindings=_bindings(),
        evaluation_context=context,
        adequacy_contract=PreferenceEvidenceAdequacyContract(
            analysis_plan_sha256="2" * 64,
            sampling_frame_sha256="3" * 64,
            minimum_assessors=4,
            minimum_directional_training_comparisons=12,
            minimum_heldout_groups=2,
            minimum_heldout_comparisons=6,
            minimum_cluster_bootstrap_replicates=100,
            minimum_heldout_bootstrap_replicates=100,
        ),
        order_carryover_config=OrderCarryoverConfig(
            maximum_pair_order_count_difference=0,
        ),
    )
    result = evaluate_hedonic_evidence(_request(context, v3))
    assert result.state is HedonicEvidenceState.INSUFFICIENT_EVIDENCE
    assert "CLUSTER_BOOTSTRAP_REPLICATES_INSUFFICIENT" in result.limitations


def test_order_confounding_is_invalid_not_a_liking_result() -> None:
    context, _, v3 = _evidence(order_confounded=True)
    result = evaluate_hedonic_evidence(_request(context, v3))
    assert result.state is HedonicEvidenceState.INVALID_OR_CONFOUNDED
    assert "ORDER" in " ".join(result.blockers)
