from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, replace

import pytest

from engine.formulation_intelligence.contracts import (
    AssessmentScope,
    AuthorityCeiling,
    PlaneAssessment,
    PlaneId,
)
from engine.formulation_intelligence.experiment_selector import (
    DecisionNeed,
    DecisionSourceKind,
    DecisionSourceRef,
    DesignRecordKind,
    DesignVersionRecord,
    ExperimentProtocol,
    LineageSourceKind,
    LineageSourceRef,
    MissingnessRule,
    MissingOutcome,
    ProtocolBindings,
    ProtocolKind,
    ProtocolQuestion,
    ProtocolReadiness,
    RealizedOrder,
    SequenceMethod,
    SourceReadiness,
    StoppingCondition,
    protocol_to_plane_assessment,
    select_experiment,
)

_HASH_A = "a" * 64
_HASH_B = "b" * 64
_HASH_C = "c" * 64
_HASH_D = "d" * 64
_HASH_E = "e" * 64


def _scope(target_id: str = "target:exact") -> AssessmentScope:
    return AssessmentScope(target_id, "all_windows", "target_ideal")


def _question(
    question_id: str,
    decision_need: DecisionNeed,
    *,
    candidate_ids: tuple[str, ...] = (),
    component_ids: tuple[str, ...] = (),
    sweep_levels: tuple[str, ...] = (),
    temporal_windows: tuple[str, ...] = (),
    target_id: str = "target:exact",
    inventory_readiness: SourceReadiness = SourceReadiness.CLEAR,
    decision_source_id: str = "unknown:target-fidelity",
    decision_source_hash: str = _HASH_E,
) -> ProtocolQuestion:
    scope = _scope(target_id)
    design_records = tuple(
        DesignVersionRecord(
            record_id=record_id,
            record_kind=record_kind,
            design_version_id="design:v3",
            record_sha256=_HASH_D,
            semantic_target_id=target_id,
            scope=scope,
        )
        for record_kind, record_ids in (
            (DesignRecordKind.CANDIDATE, candidate_ids),
            (DesignRecordKind.COMPONENT, component_ids),
        )
        for record_id in record_ids
    )
    if decision_need is DecisionNeed.NO_UNRESOLVED_DECISION:
        return ProtocolQuestion(
            question_id=question_id,
            decision_need=decision_need,
            candidate_ids=candidate_ids,
            component_ids=component_ids,
            sweep_levels=sweep_levels,
            temporal_windows=temporal_windows,
        )
    return ProtocolQuestion(
        question_id=question_id,
        decision_need=decision_need,
        semantic_target_id=target_id,
        semantic_target_receipt_sha256=_HASH_A,
        lineage_sources=(
            LineageSourceRef(
                source_kind=LineageSourceKind.PLANE_SYNTHESIS,
                source_id="plane-synthesis:exact",
                artifact_sha256=_HASH_A,
                scopes=(scope,),
                readiness=SourceReadiness.CLEAR,
            ),
            LineageSourceRef(
                source_kind=LineageSourceKind.CANDIDATE_ASSEMBLY,
                source_id="candidate-assembly:exact",
                artifact_sha256=_HASH_B,
                scopes=(scope,),
                readiness=SourceReadiness.CLEAR,
            ),
            LineageSourceRef(
                source_kind=LineageSourceKind.INVENTORY_PROJECTION,
                source_id="inventory-projection:exact",
                artifact_sha256=_HASH_C,
                scopes=(scope,),
                readiness=inventory_readiness,
            ),
        ),
        decision_source_refs=(
            DecisionSourceRef(
                source_kind=DecisionSourceKind.UNKNOWN_FACT,
                source_id=decision_source_id,
                record_sha256=decision_source_hash,
                scope=scope,
            ),
        ),
        design_records=design_records,
        candidate_ids=candidate_ids,
        component_ids=component_ids,
        sweep_levels=sweep_levels,
        temporal_windows=temporal_windows,
    )


def _stop() -> StoppingCondition:
    return StoppingCondition(
        condition_id="stop:decision-resolved",
        criterion_id="target_fidelity",
        rule="stop only after the preregistered contrast is decision-resolving",
        minimum_complete_blocks=2,
        maximum_complete_blocks=6,
    )


def _bindings(
    *,
    stopping_conditions: tuple[StoppingCondition, ...] | None = None,
    realized_orders: tuple[RealizedOrder, ...] = (),
) -> ProtocolBindings:
    return ProtocolBindings(
        total_basis="constant 1.00 g evaluation aliquot",
        carrier_composition="ethanol/DEP carrier fractions locked by mass",
        washout_seconds=900,
        repeat_count=2,
        independent_preparation_count=2,
        assessor_count=4,
        stopping_conditions=(
            (_stop(),) if stopping_conditions is None else stopping_conditions
        ),
        realized_orders=realized_orders,
    )


@pytest.mark.parametrize(
    ("question", "expected_kind"),
    (
        (
            _question("q:none", DecisionNeed.NO_UNRESOLVED_DECISION),
            ProtocolKind.ZERO_INTERVENTION,
        ),
        (
            _question(
                "q:ab",
                DecisionNeed.CANDIDATE_DIFFERENCE,
                candidate_ids=("candidate-a", "candidate-b"),
            ),
            ProtocolKind.CARRIER_MATCHED_AB,
        ),
        (
            _question(
                "q:omission",
                DecisionNeed.COMPONENT_NECESSITY,
                candidate_ids=("complete-system",),
                component_ids=("facet-shadow",),
            ),
            ProtocolKind.COMPLETE_OMISSION,
        ),
        (
            _question(
                "q:recombination",
                DecisionNeed.RECONSTRUCTION_SUFFICIENCY,
                candidate_ids=("native-reference", "full-recombination"),
            ),
            ProtocolKind.FULL_RECOMBINATION,
        ),
        (
            _question(
                "q:sweep",
                DecisionNeed.RATIO_OR_LOAD,
                candidate_ids=("candidate-system",),
                sweep_levels=("low", "center", "high"),
            ),
            ProtocolKind.RATIO_LOAD_SWEEP,
        ),
        (
            _question(
                "q:temporal",
                DecisionNeed.TIME_LOCAL_EFFECT,
                candidate_ids=("candidate-system",),
                temporal_windows=("opening", "30 min", "4 h"),
            ),
            ProtocolKind.TEMPORAL_OBSERVATION,
        ),
        (
            _question(
                "q:preparation",
                DecisionNeed.PREPARATION_REPRODUCIBILITY,
                candidate_ids=("candidate-system",),
            ),
            ProtocolKind.INDEPENDENT_PREPARATION,
        ),
        (
            _question(
                "q:assessors",
                DecisionNeed.ASSESSOR_HETEROGENEITY,
                candidate_ids=("candidate-a", "candidate-b"),
            ),
            ProtocolKind.ASSESSOR_REPLICATION,
        ),
    ),
)
def test_each_decision_need_selects_one_minimum_protocol_family(
    question: ProtocolQuestion,
    expected_kind: ProtocolKind,
) -> None:
    protocol = select_experiment(question, _bindings())

    assert protocol.kind is expected_kind
    assert protocol.decision_need is question.decision_need
    assert protocol.selection_basis
    assert "score" not in protocol.selection_basis.casefold()
    if expected_kind is ProtocolKind.ZERO_INTERVENTION:
        assert protocol.readiness is ProtocolReadiness.NO_EXPERIMENT_REQUIRED
        assert protocol.arms == ()
    else:
        assert protocol.readiness is ProtocolReadiness.PROTOCOL_DESIGN_COMPLETE


def test_ab_protocol_preserves_every_control_without_execution_authority() -> None:
    stopping = (
        _stop(),
        StoppingCondition(
            condition_id="stop:maximum-burden",
            criterion_id="complete_blocks",
            rule="stop at the preregistered maximum even if the contrast remains unresolved",
            minimum_complete_blocks=2,
            maximum_complete_blocks=6,
        ),
    )
    protocol = select_experiment(
        _question(
            "q:controlled-ab",
            DecisionNeed.CANDIDATE_DIFFERENCE,
            candidate_ids=("candidate-a", "candidate-b"),
        ),
        _bindings(stopping_conditions=stopping),
    )

    assert protocol.controls.constant_total_required is True
    assert protocol.controls.total_basis == "constant 1.00 g evaluation aliquot"
    assert protocol.controls.carrier_match_required is True
    assert protocol.controls.carrier_displacement_required is True
    assert protocol.controls.carrier_composition == (
        "ethanol/DEP carrier fractions locked by mass"
    )
    assert protocol.blinding.coded_samples_required is True
    assert protocol.blinding.assessor_blinded is True
    assert protocol.blinding.code_key_separation_required is True
    assert protocol.order.method is SequenceMethod.AB_BA
    assert protocol.order.planned_sequences == (
        (protocol.arms[0].coded_sample_id, protocol.arms[1].coded_sample_id),
        (protocol.arms[1].coded_sample_id, protocol.arms[0].coded_sample_id),
    )
    assert protocol.order.realized_order_required is True
    assert protocol.washout.planned_seconds == 900
    assert protocol.washout.realized_seconds_required is True
    assert protocol.repeats.planned_repeat_count == 2
    assert protocol.repeats.independent_preparation_count == 2
    assert protocol.repeats.assessor_count == 4
    assert protocol.stopping_conditions == stopping
    assert protocol.missingness.rule is MissingnessRule.PRESERVE_NO_IMPUTATION
    assert set(protocol.missingness.distinct_outcomes) == set(MissingOutcome)
    assert protocol.missingness.imputation_authorized is False
    assert protocol.authority_ceiling is AuthorityCeiling.DESIGN_ONLY
    assert protocol.formula_generation_authorized is False
    assert protocol.sample_preparation_authorized is False
    assert protocol.physical_execution_authorized is False
    assert protocol.assessor_allocation_authorized is False
    assert protocol.sensory_inference_authority is False
    assert protocol.safety_authority is False
    assert protocol.release_authority is False


def test_three_arm_sweep_uses_williams_sequences_without_allocating_assessors() -> None:
    protocol = select_experiment(
        _question(
            "q:williams",
            DecisionNeed.RATIO_OR_LOAD,
            candidate_ids=("candidate-system",),
            sweep_levels=("low", "center", "high"),
        ),
        _bindings(),
    )

    codes = {arm.coded_sample_id for arm in protocol.arms}
    assert protocol.order.method is SequenceMethod.WILLIAMS_FIRST_ORDER_BALANCED
    assert len(protocol.order.planned_sequences) == 6
    assert all(set(sequence) == codes for sequence in protocol.order.planned_sequences)
    assert protocol.assessor_allocation_authorized is False


def test_missing_bindings_hold_instead_of_inventing_protocol_values() -> None:
    protocol = select_experiment(
        _question(
            "q:held",
            DecisionNeed.CANDIDATE_DIFFERENCE,
            candidate_ids=("candidate-a", "candidate-b"),
        ),
        ProtocolBindings(),
    )

    assert protocol.kind is ProtocolKind.CARRIER_MATCHED_AB
    assert protocol.readiness is ProtocolReadiness.HOLD_MISSING_BINDINGS
    assert protocol.controls.total_basis is None
    assert protocol.controls.carrier_composition is None
    assert protocol.washout.planned_seconds is None
    assert protocol.repeats.planned_repeat_count is None
    assert protocol.stopping_conditions == ()
    assert {
        "total basis is unbound",
        "carrier composition is unbound",
        "washout duration is unbound",
        "repeat count is unbound",
        "stopping conditions are unbound",
    }.issubset(set(protocol.hold_reasons))
    assert protocol.physical_execution_authorized is False


def test_question_specific_missingness_is_held_not_promoted() -> None:
    sweep = select_experiment(
        _question(
            "q:missing-levels",
            DecisionNeed.RATIO_OR_LOAD,
            candidate_ids=("candidate-system",),
            sweep_levels=("low", "high"),
        ),
        _bindings(),
    )
    temporal = select_experiment(
        _question(
            "q:missing-time",
            DecisionNeed.TIME_LOCAL_EFFECT,
            candidate_ids=("candidate-system",),
            temporal_windows=("30 min",),
        ),
        _bindings(),
    )

    assert sweep.readiness is ProtocolReadiness.HOLD_MISSING_BINDINGS
    assert "at least three ratio/load levels are required" in sweep.hold_reasons
    assert temporal.readiness is ProtocolReadiness.HOLD_MISSING_BINDINGS
    assert "at least two temporal windows are required" in temporal.hold_reasons


def test_realized_order_washout_repeat_and_missing_cells_round_trip() -> None:
    question = _question(
        "q:realized",
        DecisionNeed.CANDIDATE_DIFFERENCE,
        candidate_ids=("candidate-a", "candidate-b"),
    )
    planned = select_experiment(question, _bindings())
    realized = RealizedOrder(
        block_id="block-2",
        participant_id="participant-7",
        repeat_index=2,
        sample_order=tuple(arm.coded_sample_id for arm in reversed(planned.arms)),
        predecessor_sample_id="coded-warmup",
        realized_washout_seconds=840,
        missing_sample_ids=(planned.arms[0].coded_sample_id,),
    )
    protocol = select_experiment(
        question,
        _bindings(realized_orders=(realized,)),
    )
    restored = ExperimentProtocol.from_dict(protocol.as_dict())

    assert protocol.order.realized_orders == (realized,)
    assert restored == protocol
    assert restored.as_dict() == protocol.as_dict()
    assert restored.content_sha256 == protocol.content_sha256
    assert len(protocol.content_sha256) == 64


def test_temporal_windows_are_measurement_keys_not_interpolated_scores() -> None:
    windows = ("opening", "5 min", "30 min", "2 h", "4 h")
    protocol = select_experiment(
        _question(
            "q:temporal-keys",
            DecisionNeed.TIME_LOCAL_EFFECT,
            candidate_ids=("candidate-system",),
            temporal_windows=windows,
        ),
        _bindings(),
    )

    assert protocol.temporal_windows == windows
    assert protocol.burden.temporal_window_count == len(windows)
    assert protocol.missingness.imputation_authorized is False


def test_selection_is_non_scalar_and_records_native_burdens_separately() -> None:
    protocol = select_experiment(
        _question(
            "q:non-scalar",
            DecisionNeed.CANDIDATE_DIFFERENCE,
            candidate_ids=("candidate-a", "candidate-b"),
        ),
        _bindings(),
    )

    protocol_fields = {item.name for item in fields(protocol)}
    burden_fields = {item.name for item in fields(protocol.burden)}
    assert not {"score", "utility", "rank", "weighted_total"} & protocol_fields
    assert burden_fields == {
        "condition_count",
        "planned_repeat_count",
        "independent_preparation_count",
        "assessor_count",
        "temporal_window_count",
        "intervention_required",
    }
    with pytest.raises(FrozenInstanceError):
        protocol.kind = ProtocolKind.ZERO_INTERVENTION  # type: ignore[misc]


def test_selected_protocol_binds_exact_target_sources_and_unresolved_records() -> None:
    question = _question(
        "q:lineage",
        DecisionNeed.CANDIDATE_DIFFERENCE,
        candidate_ids=("candidate-a", "candidate-b"),
    )
    scope = _scope()
    question = replace(
        question,
        decision_source_refs=(
            DecisionSourceRef(
                DecisionSourceKind.UNKNOWN_FACT,
                "unknown:target-fidelity",
                _HASH_C,
                scope,
            ),
            DecisionSourceRef(
                DecisionSourceKind.CONFLICT,
                "conflict:opening-shape",
                _HASH_D,
                scope,
            ),
            DecisionSourceRef(
                DecisionSourceKind.PRIOR_EXPERIMENT,
                "experiment:blind-ab-v2",
                _HASH_E,
                scope,
            ),
        ),
    )

    protocol = select_experiment(question, _bindings())
    restored = ExperimentProtocol.from_dict(protocol.as_dict())

    assert protocol.readiness is ProtocolReadiness.PROTOCOL_DESIGN_COMPLETE
    assert protocol.semantic_target_id == "target:exact"
    assert protocol.semantic_target_receipt_sha256 == _HASH_A
    assert {source.source_kind for source in protocol.lineage_sources} == set(
        LineageSourceKind
    )
    assert protocol.decision_source_refs == question.decision_source_refs
    assert protocol.design_records == question.design_records
    assert protocol.source_unknown_resolved is False
    assert protocol.source_conflict_resolved is False
    assert protocol.source_experiment_observed is False
    assert restored == protocol


def test_unrelated_design_records_and_source_scopes_cannot_be_design_complete() -> None:
    question = _question(
        "q:unrelated",
        DecisionNeed.CANDIDATE_DIFFERENCE,
        candidate_ids=("candidate-a", "candidate-b"),
    )
    unrelated_scope = _scope("target:unrelated")
    question = replace(
        question,
        lineage_sources=tuple(
            replace(source, scopes=(unrelated_scope,))
            if source.source_kind is LineageSourceKind.PLANE_SYNTHESIS
            else source
            for source in question.lineage_sources
        ),
        design_records=(
            question.design_records[0],
            replace(
                question.design_records[1],
                semantic_target_id="target:unrelated",
                scope=unrelated_scope,
            ),
        ),
    )

    protocol = select_experiment(question, _bindings())

    assert protocol.readiness is ProtocolReadiness.HOLD_MISSING_BINDINGS
    assert "plane_synthesis source scopes do not bind the semantic target" in (
        protocol.hold_reasons
    )
    assert "candidate candidate-b design record does not bind the semantic target" in (
        protocol.hold_reasons
    )


def test_missing_lineage_and_inventory_hold_are_preserved_as_holds() -> None:
    missing = ProtocolQuestion(
        question_id="q:missing-lineage",
        decision_need=DecisionNeed.CANDIDATE_DIFFERENCE,
        candidate_ids=("candidate-a", "candidate-b"),
    )
    inventory_held = _question(
        "q:inventory-hold",
        DecisionNeed.CANDIDATE_DIFFERENCE,
        candidate_ids=("candidate-a", "candidate-b"),
        inventory_readiness=SourceReadiness.HOLD,
    )

    missing_protocol = select_experiment(missing, _bindings())
    held_protocol = select_experiment(inventory_held, _bindings())

    assert missing_protocol.readiness is ProtocolReadiness.HOLD_MISSING_BINDINGS
    assert "semantic target ID is unbound" in missing_protocol.hold_reasons
    assert "semantic target receipt hash is unbound" in missing_protocol.hold_reasons
    assert "source lineage is incomplete" in missing_protocol.hold_reasons
    assert held_protocol.readiness is ProtocolReadiness.HOLD_MISSING_BINDINGS
    assert "source inventory projection remains HOLD" in held_protocol.hold_reasons
    assert held_protocol.physical_execution_authorized is False


def test_lineage_schemas_are_closed_and_source_resolution_flags_are_hard_false() -> None:
    protocol = select_experiment(
        _question(
            "q:closed-lineage",
            DecisionNeed.COMPONENT_NECESSITY,
            candidate_ids=("complete-system",),
            component_ids=("facet-shadow",),
        ),
        _bindings(),
    )
    payload = protocol.as_dict()

    payload["source_unknown_resolved"] = True
    with pytest.raises(ValueError, match="source_unknown_resolved"):
        ExperimentProtocol.from_dict(payload)

    source_payload = protocol.lineage_sources[0].as_dict()
    source_payload["unexpected"] = "field"
    with pytest.raises(ValueError, match="closed schema"):
        LineageSourceRef.from_dict(source_payload)


def test_protocol_adapter_preserves_exact_experiment_plane_lineage_and_unknowns() -> None:
    scope = _scope()
    question = _question(
        "q:plane-adapter",
        DecisionNeed.CANDIDATE_DIFFERENCE,
        candidate_ids=("candidate-a", "candidate-b"),
    )
    question = replace(
        question,
        decision_source_refs=(
            DecisionSourceRef(
                DecisionSourceKind.UNKNOWN_FACT,
                "unknown:target-fidelity",
                _HASH_C,
                scope,
            ),
            DecisionSourceRef(
                DecisionSourceKind.CONFLICT,
                "conflict:opening-shape",
                _HASH_D,
                scope,
            ),
            DecisionSourceRef(
                DecisionSourceKind.PRIOR_EXPERIMENT,
                "experiment:blind-ab-v2",
                _HASH_E,
                scope,
            ),
        ),
    )
    protocol = select_experiment(question, _bindings())

    assessment = protocol_to_plane_assessment(protocol, scope)
    restored = PlaneAssessment.from_dict(assessment.as_dict())

    assert assessment.plane_id is PlaneId.EXPERIMENT
    assert assessment.scope == scope
    assert assessment.scope.target_scope == protocol.semantic_target_id
    assert assessment.proposed_experiments == (protocol.protocol_id,)
    assert {_HASH_B, _HASH_C}.issubset(set(assessment.freshness_hashes))
    assert {unknown.unknown_id for unknown in assessment.unknowns} == {
        "unknown:target-fidelity",
        "conflict:opening-shape",
        "experiment:blind-ab-v2",
    }
    assert {
        (claim.claim_key, claim.claim_value) for claim in assessment.claims
    }.issuperset(
        {
            ("physical_execution_state", "not_authorized"),
            ("source_observation_state", "not_observed"),
        }
    )
    assert assessment.authority_ceiling is AuthorityCeiling.DESIGN_ONLY
    assert restored == assessment

    with pytest.raises(ValueError, match="semantic target"):
        protocol_to_plane_assessment(protocol, _scope("target:unrelated"))
