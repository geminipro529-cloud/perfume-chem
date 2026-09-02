from __future__ import annotations

import ast
import json
from dataclasses import replace
from pathlib import Path

import pytest

from engine.formulation_intelligence.contracts import (
    AssessmentScope,
    AuthorityCeiling,
    EvidenceClass,
    PlaneAssessment,
    PlaneId,
    ProvenanceRef,
    SupportMeasure,
    UnitInterval,
    ValueState,
)
from engine.formulation_intelligence.hedonic_platform import (
    AggregatePreferenceView,
    AggregationMethod,
    AssessorContext,
    BlindingState,
    CandidateCriterionValue,
    CarryoverState,
    ClusterStability,
    ComparisonCondition,
    CriterionPreferenceView,
    DecisionCandidate,
    DecisionEvidenceBasis,
    ExpertiseLevel,
    HedonicCriterion,
    HedonicEvidencePlatform,
    HedonicPlatformPlaneAdapter,
    InteractionResidualView,
    MaterialPriorView,
    MissingnessKind,
    MixtureExpectationMethod,
    MixtureExpectationView,
    NumericEstimate,
    NumericInterval,
    OutcomeCount,
    ParetoDecisionState,
    PopulationPreferenceView,
    PreferenceOutcome,
    PriorBasis,
    SensitivityState,
    TemporalPreferenceObservation,
    assess_hedonic_platform,
    build_aggregate_preference_view,
    build_criterion_preference_view,
    derive_interaction_residual,
    derive_pareto_decision,
)
from engine.formulation_intelligence.plane_synthesis import PlaneAssessmentAdapter


def _scope() -> AssessmentScope:
    return AssessmentScope(
        target_scope="target:blind-pair-study-v1",
        temporal_scope="30 min",
        matrix_scope="0.80% w/w in ethanol carrier; coded blotter context",
    )


def _provenance(
    provenance_id: str,
    *,
    evidence_class: EvidenceClass = EvidenceClass.DIRECT_OBSERVATION,
) -> ProvenanceRef:
    return ProvenanceRef(
        provenance_id=provenance_id,
        source_ref=f"receipt://{provenance_id}",
        evidence_class=evidence_class,
        independence_key=f"receipt:{provenance_id}",
    )


def _condition(
    *,
    endpoint: HedonicCriterion = HedonicCriterion.LIKING,
    matrix: str = "0.80% w/w in ethanol carrier",
    temporal_window: str = "30 min",
) -> ComparisonCondition:
    return ComparisonCondition(
        condition_id=f"condition:{endpoint.value}:30m",
        sample_a_id="coded-arm-a",
        sample_b_id="coded-arm-b",
        concentration_a="0.80% w/w",
        concentration_b="0.80% w/w",
        matrix=matrix,
        temporal_window=temporal_window,
        endpoint=endpoint,
        context="coded blotter evaluation under controlled room conditions",
    )


def _single_condition() -> ComparisonCondition:
    return ComparisonCondition(
        condition_id="condition:single-material-prior",
        sample_a_id="material-system-x",
        sample_b_id=None,
        concentration_a="0.10% w/w",
        concentration_b=None,
        matrix="ethanol carrier",
        temporal_window="5 min",
        endpoint=HedonicCriterion.LIKING,
        context="isolated material prior context",
    )


def _assessor(
    participant_id: str,
    *,
    assessor_id: str = "assessor-03",
    cluster_id: str | None = "cluster-1",
    order: tuple[str, ...] = ("coded-arm-b", "coded-arm-a"),
    predecessor: str | None = "coded-warmup",
    carryover: CarryoverState = CarryoverState.POSSIBLE,
) -> AssessorContext:
    return AssessorContext(
        participant_id=participant_id,
        assessor_id=assessor_id,
        cluster_id=cluster_id,
        expertise=ExpertiseLevel.TRAINED,
        sensitivity=SensitivityState.SCREENED_TYPICAL,
        sensitivity_detail="screened within protocol range",
        blinding=BlindingState.DOUBLE_BLIND,
        blinding_protocol_id="blind-protocol-db-2026-08-31",
        session_id="session-2026-08-31-pm",
        day_id="day-2",
        order_sequence_id="order-sequence-ba-02",
        realized_order=order,
        predecessor_sample_id=predecessor,
        carryover=carryover,
        repeat_index=2,
        context="warm humid room followed by neutral-air reset",
    )


def _observation(
    observation_id: str,
    *,
    participant_id: str,
    outcome: PreferenceOutcome,
    condition: ComparisonCondition | None = None,
    cluster_id: str | None = "cluster-1",
    rating_a: NumericEstimate | None = None,
    rating_b: NumericEstimate | None = None,
    provenance: ProvenanceRef | None = None,
    support: UnitInterval = UnitInterval(0.8, 0.95),
) -> TemporalPreferenceObservation:
    missing = outcome in {
        PreferenceOutcome.CANNOT_JUDGE,
        PreferenceOutcome.PROTOCOL_ABORT,
        PreferenceOutcome.MISSING,
    }
    missingness = {
        PreferenceOutcome.CANNOT_JUDGE: MissingnessKind.CANNOT_JUDGE,
        PreferenceOutcome.PROTOCOL_ABORT: MissingnessKind.PROTOCOL_ABORT,
        PreferenceOutcome.MISSING: MissingnessKind.ITEM_NONRESPONSE,
    }.get(outcome, MissingnessKind.NONE)
    return TemporalPreferenceObservation(
        view_id=observation_id,
        condition=condition or _condition(),
        assessor=_assessor(participant_id, cluster_id=cluster_id),
        outcome=outcome,
        missingness=missingness,
        missingness_reason=(
            f"protocol outcome recorded as {outcome.value}" if missing else None
        ),
        rating_a=rating_a
        or (
            NumericEstimate.unknown("no valid rating", unit="normalized criterion scale")
            if missing
            else NumericEstimate.known(
                0.50,
                unit="normalized criterion scale",
                lower=0.45,
                upper=0.55,
            )
            if outcome.is_tie
            else NumericEstimate.known(
                0.7,
                unit="normalized criterion scale",
                lower=0.65,
                upper=0.75,
            )
        ),
        rating_b=rating_b
        or (
            NumericEstimate.unknown("no valid rating", unit="normalized criterion scale")
            if missing
            else NumericEstimate.known(
                0.52,
                unit="normalized criterion scale",
                lower=0.47,
                upper=0.57,
            )
            if outcome.is_tie
            else NumericEstimate.known(
                0.4,
                unit="normalized criterion scale",
                lower=0.35,
                upper=0.45,
            )
        ),
        support=support,
        provenance_refs=(provenance or _provenance(f"prov:{observation_id}"),),
    )


def test_outcome_and_native_criterion_vocabularies_are_explicit() -> None:
    assert set(PreferenceOutcome) == {
        PreferenceOutcome.PREFER_A,
        PreferenceOutcome.PREFER_B,
        PreferenceOutcome.NO_PREFERENCE,
        PreferenceOutcome.NO_PERCEPTIBLE_DIFFERENCE,
        PreferenceOutcome.CANNOT_JUDGE,
        PreferenceOutcome.PROTOCOL_ABORT,
        PreferenceOutcome.MISSING,
    }
    assert set(HedonicCriterion) == {
        HedonicCriterion.LIKING,
        HedonicCriterion.COMFORT,
        HedonicCriterion.SENSUALITY,
        HedonicCriterion.ELEGANCE,
        HedonicCriterion.INTEREST,
        HedonicCriterion.NATURALNESS,
        HedonicCriterion.TARGET_FIDELITY,
        HedonicCriterion.DEPTH,
        HedonicCriterion.RICHNESS,
        HedonicCriterion.COHERENCE,
        HedonicCriterion.AVERSION,
        HedonicCriterion.DEFECT_INTENSITY,
    }

    for prohibited in ("hedonic_score", "beauty", "overall_score", "aggregate_score"):
        with pytest.raises(ValueError):
            HedonicCriterion(prohibited)


def test_condition_and_assessor_context_preserve_protocol_dimensions_and_order() -> None:
    condition = _condition()
    assessor = _assessor("participant-07")
    restored_condition = ComparisonCondition.from_dict(condition.as_dict())
    restored_assessor = AssessorContext.from_dict(assessor.as_dict())

    assert restored_condition == condition
    assert restored_assessor == assessor
    assert assessor.realized_order == ("coded-arm-b", "coded-arm-a")
    assert assessor.predecessor_sample_id == "coded-warmup"
    assert assessor.carryover is CarryoverState.POSSIBLE
    assert assessor.repeat_index == 2
    assert assessor.cluster_id == "cluster-1"
    assert assessor.assessor_id == "assessor-03"
    assert assessor.blinding is BlindingState.DOUBLE_BLIND
    assert assessor.blinding_protocol_id == "blind-protocol-db-2026-08-31"
    assert assessor.order_sequence_id == "order-sequence-ba-02"
    assert condition.endpoint is HedonicCriterion.LIKING
    assert condition.concentration_a == "0.80% w/w"
    assert condition.matrix == "0.80% w/w in ethanol carrier"


def test_closed_schema_rejects_missing_extra_and_wrong_version_fields() -> None:
    payload = _assessor("participant-schema").as_dict()

    extra = dict(payload)
    extra["implicit_score"] = 0.9
    with pytest.raises(ValueError, match="closed schema"):
        AssessorContext.from_dict(extra)

    missing = dict(payload)
    missing.pop("blinding")
    with pytest.raises(ValueError, match="closed schema"):
        AssessorContext.from_dict(missing)

    wrong_version = dict(payload)
    wrong_version["schema_version"] = "hedonic_assessor_context_v1"
    with pytest.raises(ValueError, match="schema_version"):
        AssessorContext.from_dict(wrong_version)


def test_missingness_is_typed_reasoned_and_never_coerced_to_zero() -> None:
    missing = _observation(
        "observation:typed-missingness",
        participant_id="participant-missingness",
        outcome=PreferenceOutcome.MISSING,
    )
    restored = TemporalPreferenceObservation.from_dict(missing.as_dict())

    assert restored.missingness is MissingnessKind.ITEM_NONRESPONSE
    assert restored.missingness_reason == "protocol outcome recorded as missing"
    assert restored.rating_a.value.state is ValueState.UNKNOWN
    assert restored.rating_a.value.value is None

    incompatible = missing.as_dict()
    incompatible["missingness"] = MissingnessKind.NONE.value
    incompatible["missingness_reason"] = None
    with pytest.raises(ValueError, match="incompatible"):
        TemporalPreferenceObservation.from_dict(incompatible)


def test_material_prior_and_predicted_expectation_cannot_become_human_observation() -> None:
    computational = _provenance(
        "prov:computational-prior",
        evidence_class=EvidenceClass.COMPUTATIONAL_MODEL,
    )
    prior = MaterialPriorView(
        view_id="prior:material-x",
        subject_id="material-system-x",
        condition=_single_condition(),
        basis=PriorBasis.COMPUTATIONAL_PRIOR,
        estimate=NumericEstimate.known(
            0.55,
            unit="normalized prior scale",
            lower=0.3,
            upper=0.7,
        ),
        support=UnitInterval(0.2, 0.5),
        provenance_refs=(computational,),
    )
    expectation = MixtureExpectationView(
        view_id="expectation:a-vs-b",
        condition=_condition(),
        method=MixtureExpectationMethod.INTENSITY_WEIGHTED,
        expected_difference=NumericEstimate.known(
            0.1,
            unit="normalized criterion scale",
            lower=0.05,
            upper=0.15,
        ),
        support=UnitInterval(0.25, 0.55),
        provenance_refs=(computational,),
    )

    packet = HedonicEvidencePlatform(
        material_priors=(prior,),
        mixture_expectations=(expectation,),
    )
    assessment = assess_hedonic_platform(packet, scope=_scope())

    assert assessment.authority_ceiling is AuthorityCeiling.HYPOTHESIS_ONLY
    assert any("predicted prior" in claim.claim_value.casefold() for claim in assessment.claims)
    assert any("predicted expectation" in claim.claim_value.casefold() for claim in assessment.claims)

    with pytest.raises(ValueError, match="human observation provenance"):
        _observation(
            "observation:invalid-computational",
            participant_id="participant-01",
            outcome=PreferenceOutcome.PREFER_A,
            provenance=computational,
        )


@pytest.mark.parametrize(
    "basis",
    (PriorBasis.OAV_DIAGNOSTIC, PriorBasis.SUPPLIER_PROSE, PriorBasis.UNKNOWN),
)
def test_non_hedonic_prior_basis_cannot_carry_known_numeric_liking(
    basis: PriorBasis,
) -> None:
    with pytest.raises(ValueError, match="known numeric hedonic estimate"):
        MaterialPriorView(
            view_id=f"prior:{basis.value}",
            subject_id="material-system-x",
            condition=_single_condition(),
            basis=basis,
            estimate=NumericEstimate.known(
                0.8,
                unit="unauthorized liking scale",
            ),
            support=UnitInterval(0.1, 0.3),
            provenance_refs=(
                _provenance(
                    f"prov:{basis.value}",
                    evidence_class=EvidenceClass.HEURISTIC,
                ),
            ),
        )


def test_supplier_prose_unknown_remains_hypothesis_only_and_not_tested() -> None:
    prior = MaterialPriorView(
        view_id="prior:supplier-prose-unknown",
        subject_id="material-system-x",
        condition=_single_condition(),
        basis=PriorBasis.SUPPLIER_PROSE,
        estimate=NumericEstimate.unknown(
            "Supplier odor prose is not participant liking evidence",
            unit="not tested",
        ),
        support=UnitInterval(0.0, 0.2),
        provenance_refs=(
            _provenance(
                "prov:supplier-prose-unknown",
                evidence_class=EvidenceClass.OFFICIAL_RECORD,
            ),
        ),
    )
    assessment = assess_hedonic_platform(
        HedonicEvidencePlatform(material_priors=(prior,)),
        scope=_scope(),
    )

    assert prior.estimate.value.state is ValueState.UNKNOWN
    assert prior.estimate.value.value is None
    assert assessment.authority_ceiling.is_no_stronger_than(
        AuthorityCeiling.HYPOTHESIS_ONLY
    )
    assert all(
        criterion.value.state is ValueState.UNKNOWN
        for criterion in assessment.native_criteria
    )
    assert any(
        claim.claim_key == "hedonic.authority_hold.liking_generalization"
        for claim in assessment.claims
    )


def test_interaction_residual_is_exact_condition_bound_and_unknown_safe() -> None:
    expectation = MixtureExpectationView(
        view_id="expectation:a-vs-b",
        condition=_condition(),
        method=MixtureExpectationMethod.INTENSITY_WEIGHTED,
        expected_difference=NumericEstimate.known(
            0.1,
            unit="normalized criterion scale",
            lower=0.05,
            upper=0.15,
        ),
        support=UnitInterval(0.3, 0.6),
        provenance_refs=(
            _provenance("prov:expectation", evidence_class=EvidenceClass.COMPUTATIONAL_MODEL),
        ),
    )
    observation = _observation(
        "observation:residual",
        participant_id="participant-02",
        outcome=PreferenceOutcome.PREFER_A,
    )

    residual = derive_interaction_residual(
        "residual:a-vs-b",
        expectation,
        observation,
    )

    assert isinstance(residual, InteractionResidualView)
    assert residual.residual.value.value == pytest.approx(0.2)
    assert residual.residual.uncertainty == NumericInterval(0.05, 0.35)
    assert residual.condition == expectation.condition == observation.condition

    mismatched = _observation(
        "observation:mismatch",
        participant_id="participant-03",
        outcome=PreferenceOutcome.PREFER_A,
        condition=_condition(matrix="oil matrix"),
    )
    with pytest.raises(ValueError, match="exact condition"):
        derive_interaction_residual("residual:mismatch", expectation, mismatched)

    missing = _observation(
        "observation:missing-residual",
        participant_id="participant-04",
        outcome=PreferenceOutcome.MISSING,
    )
    unknown_residual = derive_interaction_residual(
        "residual:unknown",
        expectation,
        missing,
    )
    assert unknown_residual.residual.value.state is ValueState.UNKNOWN
    assert unknown_residual.residual.value.value is None


def test_ties_abstentions_and_missing_outcomes_survive_criterion_view() -> None:
    observations = (
        _observation(
            "observation:tie",
            participant_id="participant-01",
            outcome=PreferenceOutcome.NO_PREFERENCE,
        ),
        _observation(
            "observation:no-difference",
            participant_id="participant-02",
            outcome=PreferenceOutcome.NO_PERCEPTIBLE_DIFFERENCE,
        ),
        _observation(
            "observation:cannot",
            participant_id="participant-03",
            outcome=PreferenceOutcome.CANNOT_JUDGE,
        ),
        _observation(
            "observation:abort",
            participant_id="participant-04",
            outcome=PreferenceOutcome.PROTOCOL_ABORT,
        ),
        _observation(
            "observation:missing",
            participant_id="participant-05",
            outcome=PreferenceOutcome.MISSING,
        ),
    )

    view = build_criterion_preference_view("criterion-view:liking", observations)
    restored = CriterionPreferenceView.from_dict(view.as_dict())

    assert restored == view
    assert {item.outcome for item in view.outcomes} == {
        PreferenceOutcome.NO_PREFERENCE,
        PreferenceOutcome.NO_PERCEPTIBLE_DIFFERENCE,
        PreferenceOutcome.CANNOT_JUDGE,
        PreferenceOutcome.PROTOCOL_ABORT,
        PreferenceOutcome.MISSING,
    }
    assert {item.observation_id for item in view.ties} == {
        "observation:no-difference",
        "observation:tie",
    }
    assert {item.observation_id for item in view.abstentions} == {
        "observation:abort",
        "observation:cannot",
        "observation:missing",
    }


def test_aggregate_view_retains_categorical_counts_and_cluster_strata_without_winner() -> None:
    observations = (
        _observation(
            "observation:aggregate-a",
            participant_id="participant-01",
            cluster_id="cluster-a",
            outcome=PreferenceOutcome.PREFER_A,
        ),
        _observation(
            "observation:aggregate-tie",
            participant_id="participant-02",
            cluster_id="cluster-b",
            outcome=PreferenceOutcome.NO_PREFERENCE,
        ),
        _observation(
            "observation:aggregate-missing",
            participant_id="participant-03",
            cluster_id="cluster-b",
            outcome=PreferenceOutcome.MISSING,
        ),
    )
    aggregate = build_aggregate_preference_view(
        "aggregate:categorical-only",
        observations,
    )
    restored = AggregatePreferenceView.from_dict(aggregate.as_dict())

    assert restored == aggregate
    assert aggregate.aggregation_method is AggregationMethod.STRATIFIED_CATEGORICAL_COUNTS
    assert aggregate.cluster_ids == ("cluster-a", "cluster-b")
    assert all(isinstance(item, OutcomeCount) for item in aggregate.outcome_counts)
    assert {item.outcome: item.count for item in aggregate.outcome_counts} == {
        PreferenceOutcome.PREFER_A: 1,
        PreferenceOutcome.NO_PREFERENCE: 1,
        PreferenceOutcome.MISSING: 1,
    }
    assert not hasattr(aggregate, "winner")
    assert not hasattr(aggregate, "score")

    assessment = assess_hedonic_platform(
        HedonicEvidencePlatform(
            temporal_observations=observations,
            aggregate_views=(aggregate,),
        ),
        scope=_scope(),
    )
    aggregate_claim = next(
        claim for claim in assessment.claims if claim.claim_key.startswith("hedonic.aggregate.")
    )
    assert "no pooled winner or scalar utility" in aggregate_claim.claim_value


def test_derived_views_preserve_separate_support_atoms_without_min_min_synthesis() -> None:
    first = _observation(
        "observation:support-first",
        participant_id="participant-support-first",
        outcome=PreferenceOutcome.PREFER_A,
        support=UnitInterval(0.2, 0.9),
    )
    second = _observation(
        "observation:support-second",
        participant_id="participant-support-second",
        outcome=PreferenceOutcome.NO_PREFERENCE,
        support=UnitInterval(0.6, 0.7),
    )
    criterion_view = build_criterion_preference_view(
        "criterion-view:atomic-support",
        (first, second),
    )
    aggregate_view = build_aggregate_preference_view(
        "aggregate:atomic-support",
        (first, second),
    )
    expectation = MixtureExpectationView(
        view_id="expectation:atomic-support",
        condition=_condition(),
        method=MixtureExpectationMethod.HEURISTIC,
        expected_difference=NumericEstimate.known(
            0.1,
            unit="normalized criterion scale",
        ),
        support=UnitInterval(0.1, 0.4),
        provenance_refs=(
            _provenance(
                "prov:expectation-atomic-support",
                evidence_class=EvidenceClass.COMPUTATIONAL_MODEL,
            ),
        ),
    )
    residual_view = derive_interaction_residual(
        "residual:atomic-support",
        expectation,
        first,
    )
    assessment = assess_hedonic_platform(
        HedonicEvidencePlatform(
            mixture_expectations=(expectation,),
            temporal_observations=(first, second),
            interaction_residuals=(residual_view,),
            criterion_preferences=(criterion_view,),
            aggregate_views=(aggregate_view,),
        ),
        scope=_scope(),
    )

    expected_by_prefix = {
        "hedonic.criterion_preference.": {
            UnitInterval(0.2, 0.9),
            UnitInterval(0.6, 0.7),
        },
        "hedonic.aggregate.": {
            UnitInterval(0.2, 0.9),
            UnitInterval(0.6, 0.7),
        },
        "hedonic.interaction_residual.": {
            UnitInterval(0.1, 0.4),
            UnitInterval(0.2, 0.9),
        },
    }
    for prefix, expected_bounds in expected_by_prefix.items():
        claim = next(item for item in assessment.claims if item.claim_key.startswith(prefix))
        intervals = tuple(
            item
            for item in assessment.support_intervals
            if item.claim_id == claim.claim_id
        )
        assert {item.bounds for item in intervals} == expected_bounds
        assert all(
            item.support_measure is SupportMeasure.EVIDENCE_SUPPORT
            for item in intervals
        )

    assert not hasattr(criterion_view, "support")
    assert not hasattr(aggregate_view, "support")
    assert not hasattr(residual_view, "support")


def test_exact_duplicates_canonicalize_but_conflicting_ids_are_retained() -> None:
    prefer_a = _observation(
        "observation:duplicate-cell",
        participant_id="participant-01",
        outcome=PreferenceOutcome.PREFER_A,
    )
    prefer_b = _observation(
        "observation:duplicate-cell",
        participant_id="participant-01",
        outcome=PreferenceOutcome.PREFER_B,
        rating_a=NumericEstimate.known(0.3, unit="normalized criterion scale"),
        rating_b=NumericEstimate.known(0.7, unit="normalized criterion scale"),
    )
    packet = HedonicEvidencePlatform(
        temporal_observations=(prefer_a, prefer_a, prefer_b),
    )

    assessment = assess_hedonic_platform(packet, scope=_scope())

    assert len(packet.temporal_observations) == 2
    assert len(assessment.conflicts) == 1
    assert assessment.conflicts[0].claim_key == "hedonic.duplicate.observation-duplicate-cell"
    assert "discordant duplicate" in assessment.conflicts[0].reason.casefold()


def test_stable_opposed_clusters_are_retained_without_pooling() -> None:
    condition = _condition(endpoint=HedonicCriterion.TARGET_FIDELITY)
    cluster_a = PopulationPreferenceView(
        view_id="population:cluster-a",
        condition=condition,
        cluster_id="cluster-a",
        participant_ids=("participant-01", "participant-03"),
        stability=ClusterStability.STABLE,
        outcome=PreferenceOutcome.PREFER_A,
        support=UnitInterval(0.65, 0.85),
        provenance_refs=(_provenance("prov:cluster-a"),),
    )
    cluster_b = PopulationPreferenceView(
        view_id="population:cluster-b",
        condition=condition,
        cluster_id="cluster-b",
        participant_ids=("participant-02", "participant-04"),
        stability=ClusterStability.STABLE,
        outcome=PreferenceOutcome.PREFER_B,
        support=UnitInterval(0.62, 0.82),
        provenance_refs=(_provenance("prov:cluster-b"),),
    )
    packet = HedonicEvidencePlatform(population_views=(cluster_b, cluster_a))

    assessment = assess_hedonic_platform(packet, scope=_scope())

    assert len(packet.population_views) == 2
    assert any("cluster-a" in claim.claim_value for claim in assessment.claims)
    assert any("cluster-b" in claim.claim_value for claim in assessment.claims)
    assert any(
        conflict.claim_key == "hedonic.population.opposed-clusters"
        for conflict in assessment.conflicts
    )
    assert any(
        unknown.field_key == "hedonic.population_generalization"
        for unknown in assessment.unknowns
    )


def test_realized_order_predecessor_carryover_and_repeat_survive_assessment() -> None:
    observation = _observation(
        "observation:order-carryover",
        participant_id="participant-09",
        outcome=PreferenceOutcome.PREFER_A,
    )
    assessment = assess_hedonic_platform(
        HedonicEvidencePlatform(temporal_observations=(observation,)),
        scope=_scope(),
    )
    observation_claim = next(
        claim for claim in assessment.claims if "order-carryover" in claim.claim_key
    )

    assert "coded-arm-b -> coded-arm-a" in observation_claim.claim_value
    assert "coded-warmup" in observation_claim.claim_value
    assert "possible" in observation_claim.claim_value
    assert "repeat 2" in observation_claim.claim_value
    assert "day-2" in observation_claim.claim_value
    assert "session-2026-08-31-pm" in observation_claim.claim_value


def _rating(value: float) -> NumericEstimate:
    return NumericEstimate.known(
        value,
        unit="normalized criterion scale",
        lower=value - 0.02,
        upper=value + 0.02,
    )


def _paired_decision_inputs(
    *,
    include_unknown_depth: bool = False,
    candidate_a_dominates: bool = False,
) -> tuple[
    tuple[DecisionCandidate, DecisionCandidate],
    tuple[TemporalPreferenceObservation, ...],
]:
    pairs = (
        (HedonicCriterion.LIKING, 0.9, 0.4),
        (
            HedonicCriterion.COMFORT,
            0.8 if candidate_a_dominates else 0.3,
            0.4 if candidate_a_dominates else 0.8,
        ),
    )
    observations: list[TemporalPreferenceObservation] = [
        _observation(
            f"observation:paired:{criterion.value}",
            participant_id="participant-paired",
            outcome=(
                PreferenceOutcome.PREFER_A
                if rating_a > rating_b
                else PreferenceOutcome.PREFER_B
            ),
            condition=_condition(endpoint=criterion),
            rating_a=_rating(rating_a),
            rating_b=_rating(rating_b),
        )
        for criterion, rating_a, rating_b in pairs
    ]
    if include_unknown_depth:
        observations.append(
            _observation(
                "observation:paired:depth",
                participant_id="participant-paired",
                outcome=PreferenceOutcome.CANNOT_JUDGE,
                condition=_condition(endpoint=HedonicCriterion.DEPTH),
            )
        )

    def candidate_for_arm(candidate_id: str, arm: str) -> DecisionCandidate:
        return DecisionCandidate(
            candidate_id=candidate_id,
            criteria=tuple(
                CandidateCriterionValue(
                    criterion=observation.condition.endpoint,
                    estimate=(
                        observation.rating_a if arm == "a" else observation.rating_b
                    ),
                    evidence_basis=DecisionEvidenceBasis.HUMAN_OBSERVATION,
                    source_view_ids=(observation.view_id,),
                )
                for observation in observations
            ),
        )

    return (
        (
            candidate_for_arm("coded-arm-a", "a"),
            candidate_for_arm("coded-arm-b", "b"),
        ),
        tuple(observations),
    )


@pytest.mark.parametrize(
    "basis",
    (DecisionEvidenceBasis.PREDICTED, DecisionEvidenceBasis.GENERIC_SCORE),
)
def test_known_predicted_or_generic_candidate_criterion_is_rejected_before_pareto(
    basis: DecisionEvidenceBasis,
) -> None:
    with pytest.raises(
        ValueError,
        match="known decision criteria require linked HUMAN_OBSERVATION evidence",
    ):
        CandidateCriterionValue(
            criterion=HedonicCriterion.LIKING,
            estimate=_rating(0.8),
            evidence_basis=basis,
            source_view_ids=("prediction:unbound",),
        )


def test_pareto_decision_is_noncompensatory_and_unknowns_do_not_become_zero() -> None:
    candidates, observations = _paired_decision_inputs(include_unknown_depth=True)
    decision = derive_pareto_decision(
        "decision:noncompensatory",
        candidates=candidates,
        linked_observations=observations,
    )
    restored = ParetoDecisionState.from_dict(decision.as_dict())

    assert restored == decision
    assert decision.pareto_front_ids == ("coded-arm-a", "coded-arm-b")
    assert decision.dominated_ids == ()
    assert decision.unresolved_ids == ("coded-arm-a", "coded-arm-b")
    assert (
        candidates[0]
        .criteria_by_id[HedonicCriterion.DEPTH]
        .estimate.value.value
        is None
    )
    assert not hasattr(decision, "score")
    assert not hasattr(decision, "weights")


def test_lossless_paired_observations_can_authorize_exact_scope_decision() -> None:
    candidates, observations = _paired_decision_inputs(candidate_a_dominates=True)
    decision = derive_pareto_decision(
        "decision:linked-human",
        candidates=candidates,
        linked_observations=observations,
    )
    platform = HedonicEvidencePlatform(
        temporal_observations=observations,
        decision_states=(decision,),
    )
    assessment = assess_hedonic_platform(platform, scope=_scope())

    assert decision.pareto_front_ids == ("coded-arm-a",)
    assert decision.dominated_ids == ("coded-arm-b",)
    assert decision.unresolved_ids == ()
    assert decision.condition_scope_id.startswith("hedonic-condition-scope:")
    assert {item.provenance_id for item in decision.provenance_refs} == {
        "prov:observation:paired:comfort",
        "prov:observation:paired:liking",
    }
    decision_claim = next(
        claim
        for claim in assessment.claims
        if claim.claim_key.startswith("hedonic.pareto_decision.")
    )
    assert decision_claim.authority_ceiling is AuthorityCeiling.EVIDENCE_LIMITED
    decision_support = tuple(
        interval
        for interval in assessment.support_intervals
        if interval.claim_id == decision_claim.claim_id
    )
    assert {item.support_measure for item in decision_support} == {
        SupportMeasure.DECLARATION_PRESENCE,
        SupportMeasure.EVIDENCE_SUPPORT,
    }


def test_decision_rejects_candidate_or_scalar_not_equal_to_observed_arm() -> None:
    candidates, observations = _paired_decision_inputs()
    wrong_id = replace(candidates[0], candidate_id="candidate-not-in-pair")
    with pytest.raises(ValueError, match="sample arm"):
        derive_pareto_decision(
            "decision:wrong-id",
            candidates=(wrong_id, candidates[1]),
            linked_observations=observations,
        )

    liking = candidates[0].criteria_by_id[HedonicCriterion.LIKING]
    wrong_value = replace(liking, estimate=_rating(0.1))
    wrong_scalar = replace(
        candidates[0],
        criteria=tuple(
            wrong_value if item.criterion is HedonicCriterion.LIKING else item
            for item in candidates[0].criteria
        ),
    )
    with pytest.raises(ValueError, match="exact linked observation arm rating"):
        derive_pareto_decision(
            "decision:wrong-scalar",
            candidates=(wrong_scalar, candidates[1]),
            linked_observations=observations,
        )


def test_two_candidate_cells_must_share_one_paired_observation() -> None:
    candidates, observations = _paired_decision_inputs()
    liking_observation = next(
        item
        for item in observations
        if item.condition.endpoint is HedonicCriterion.LIKING
    )
    split_observation = replace(
        liking_observation,
        view_id="observation:paired:liking:split",
    )
    b_liking = candidates[1].criteria_by_id[HedonicCriterion.LIKING]
    split_b = replace(
        candidates[1],
        criteria=tuple(
            replace(b_liking, source_view_ids=(split_observation.view_id,))
            if item.criterion is HedonicCriterion.LIKING
            else item
            for item in candidates[1].criteria
        ),
    )
    with pytest.raises(ValueError, match="share one paired observation"):
        derive_pareto_decision(
            "decision:split-pair",
            candidates=(candidates[0], split_b),
            linked_observations=(*observations, split_observation),
        )


def test_platform_from_dict_rejects_forged_decision_partition() -> None:
    candidates, observations = _paired_decision_inputs(candidate_a_dominates=True)
    decision = derive_pareto_decision(
        "decision:forgery-check",
        candidates=candidates,
        linked_observations=observations,
    )
    payload = HedonicEvidencePlatform(
        temporal_observations=observations,
        decision_states=(decision,),
    ).as_dict()
    payload["decision_states"][0]["pareto_front_ids"] = ["coded-arm-b"]
    payload["decision_states"][0]["dominated_ids"] = ["coded-arm-a"]

    with pytest.raises(ValueError, match="partitions must be recomputed"):
        HedonicEvidencePlatform.from_dict(payload)


def test_three_candidate_numeric_decision_requires_a_future_typed_aggregate() -> None:
    candidates, observations = _paired_decision_inputs()
    third = replace(candidates[0], candidate_id="coded-arm-c")

    with pytest.raises(ValueError, match="exactly two candidates"):
        derive_pareto_decision(
            "decision:three-candidate",
            candidates=(*candidates, third),
            linked_observations=observations,
        )


@pytest.mark.parametrize(
    ("assessor_field", "replacement"),
    (
        ("participant_id", "participant-other"),
        ("session_id", "session-other"),
        ("repeat_index", 3),
        ("blinding_protocol_id", "blind-protocol-other"),
    ),
)
def test_decision_rejects_cross_criterion_assessor_or_protocol_stitching(
    assessor_field: str,
    replacement: str | int,
) -> None:
    candidates, observations = _paired_decision_inputs()
    liking, comfort = observations
    altered_assessor = replace(
        comfort.assessor,
        **{assessor_field: replacement},
    )
    altered_comfort = replace(comfort, assessor=altered_assessor)

    with pytest.raises(ValueError, match="assessor/protocol scope"):
        derive_pareto_decision(
            "decision:mixed-assessor-scope",
            candidates=candidates,
            linked_observations=(liking, altered_comfort),
        )


def test_categorical_outcome_must_agree_with_directional_rating_intervals() -> None:
    with pytest.raises(ValueError, match="prefer_a outcome contradicts"):
        _observation(
            "observation:contradict-maximize",
            participant_id="participant-contradict",
            outcome=PreferenceOutcome.PREFER_A,
            rating_a=_rating(0.2),
            rating_b=_rating(0.8),
        )

    with pytest.raises(ValueError, match="prefer_b outcome contradicts"):
        _observation(
            "observation:contradict-minimize",
            participant_id="participant-contradict",
            outcome=PreferenceOutcome.PREFER_B,
            condition=_condition(endpoint=HedonicCriterion.AVERSION),
            rating_a=_rating(0.2),
            rating_b=_rating(0.8),
        )

    with pytest.raises(ValueError, match="tie outcome contradicts"):
        _observation(
            "observation:false-tie",
            participant_id="participant-contradict",
            outcome=PreferenceOutcome.NO_PREFERENCE,
            rating_a=_rating(0.8),
            rating_b=_rating(0.2),
        )

    overlapping = _observation(
        "observation:bounded-tie",
        participant_id="participant-tie",
        outcome=PreferenceOutcome.NO_PERCEPTIBLE_DIFFERENCE,
        rating_a=NumericEstimate.known(
            0.50,
            unit="normalized criterion scale",
            lower=0.45,
            upper=0.55,
        ),
        rating_b=NumericEstimate.known(
            0.52,
            unit="normalized criterion scale",
            lower=0.47,
            upper=0.57,
        ),
    )
    assert overlapping.outcome is PreferenceOutcome.NO_PERCEPTIBLE_DIFFERENCE


def test_platform_decision_round_trip_binds_observations_and_provenance() -> None:
    candidates, observations = _paired_decision_inputs(candidate_a_dominates=True)
    decision = derive_pareto_decision(
        "decision:positive-round-trip",
        candidates=candidates,
        linked_observations=observations,
    )
    platform = HedonicEvidencePlatform(
        temporal_observations=observations,
        decision_states=(decision,),
    )

    restored = HedonicEvidencePlatform.from_dict(platform.as_dict())

    assert restored == platform
    assert restored.content_sha256 == platform.content_sha256

    missing = platform.as_dict()
    missing["temporal_observations"] = missing["temporal_observations"][:-1]
    with pytest.raises(ValueError, match="resolve one unique temporal observation"):
        HedonicEvidencePlatform.from_dict(missing)

    forged_provenance = platform.as_dict()
    forged_provenance["decision_states"][0]["provenance_refs"] = [
        _provenance("prov:unrelated-human-receipt").as_dict()
    ]
    with pytest.raises(ValueError, match="provenance is not derived"):
        HedonicEvidencePlatform.from_dict(forged_provenance)


def test_standalone_decision_cannot_call_an_unresolved_candidate_dominated() -> None:
    candidates, observations = _paired_decision_inputs(include_unknown_depth=True)
    decision = derive_pareto_decision(
        "decision:standalone-unresolved",
        candidates=candidates,
        linked_observations=observations,
    )
    payload = decision.as_dict()
    payload["pareto_front_ids"] = ["coded-arm-a"]
    payload["dominated_ids"] = ["coded-arm-b"]
    payload["unresolved_ids"] = ["coded-arm-b"]

    with pytest.raises(ValueError, match="unresolved candidates cannot be declared dominated"):
        ParetoDecisionState.from_dict(payload)


def test_all_native_criteria_remain_separate_and_authority_is_bounded() -> None:
    observation = _observation(
        "observation:evidence-limited",
        participant_id="participant-08",
        outcome=PreferenceOutcome.PREFER_A,
    )
    assessment = assess_hedonic_platform(
        HedonicEvidencePlatform(temporal_observations=(observation,)),
        scope=_scope(),
    )

    assert assessment.plane_id is PlaneId.HEDONIC
    assert assessment.authority_ceiling is AuthorityCeiling.EVIDENCE_LIMITED
    assert {criterion.criterion_id for criterion in assessment.native_criteria} == {
        f"hedonic.{criterion.value}" for criterion in HedonicCriterion
    }
    assert all(
        criterion.value.state is ValueState.UNKNOWN
        for criterion in assessment.native_criteria
    )
    assert all(
        criterion.authority_ceiling.is_no_stronger_than(
            AuthorityCeiling.EVIDENCE_LIMITED
        )
        for criterion in assessment.native_criteria
    )
    hold_keys = {
        claim.claim_key
        for claim in assessment.claims
        if claim.claim_key.startswith("hedonic.authority_hold.")
    }
    assert hold_keys == {
        "hedonic.authority_hold.compounding",
        "hedonic.authority_hold.liking_generalization",
        "hedonic.authority_hold.observed_smell",
        "hedonic.authority_hold.physical_performance",
        "hedonic.authority_hold.release",
        "hedonic.authority_hold.safety",
        "hedonic.authority_hold.stability",
        "hedonic.authority_hold.strict_similarity",
    }
    assert all(
        claim.claim_value.startswith("NOT TESTED / HOLD:")
        for claim in assessment.claims
        if claim.claim_key.startswith("hedonic.authority_hold.")
    )


def test_packet_and_assessment_round_trip_hash_and_input_order_invariance() -> None:
    first = _observation(
        "observation:first",
        participant_id="participant-01",
        outcome=PreferenceOutcome.PREFER_A,
    )
    second = _observation(
        "observation:second",
        participant_id="participant-02",
        outcome=PreferenceOutcome.NO_PREFERENCE,
    )
    population = PopulationPreferenceView(
        view_id="population:cluster-1",
        condition=_condition(),
        cluster_id="cluster-1",
        participant_ids=("participant-02", "participant-01"),
        stability=ClusterStability.PROVISIONAL,
        outcome=PreferenceOutcome.NO_PREFERENCE,
        support=UnitInterval(0.4, 0.7),
        provenance_refs=(_provenance("prov:population"),),
    )
    left_packet = HedonicEvidencePlatform(
        temporal_observations=(first, second),
        population_views=(population,),
    )
    right_packet = HedonicEvidencePlatform(
        temporal_observations=(second, first),
        population_views=(population,),
    )
    restored_packet = HedonicEvidencePlatform.from_dict(
        json.loads(json.dumps(left_packet.as_dict()))
    )
    left = assess_hedonic_platform(left_packet, scope=_scope())
    right = assess_hedonic_platform(right_packet, scope=_scope())
    restored = PlaneAssessment.from_dict(json.loads(json.dumps(left.as_dict())))

    assert left_packet == right_packet == restored_packet
    assert left_packet.content_sha256 == right_packet.content_sha256
    assert left == right == restored
    assert left.as_dict() == right.as_dict() == restored.as_dict()
    assert left.content_sha256 == right.content_sha256 == restored.content_sha256


def test_read_only_adapter_conforms_and_hot_path_imports_are_bounded() -> None:
    packet = HedonicEvidencePlatform(
        temporal_observations=(
            _observation(
                "observation:adapter",
                participant_id="participant-01",
                outcome=PreferenceOutcome.PREFER_A,
            ),
        )
    )
    adapter = HedonicPlatformPlaneAdapter(platform=packet, scope=_scope())

    assert isinstance(adapter, PlaneAssessmentAdapter)
    assert adapter.to_plane_assessment() == assess_hedonic_platform(packet, scope=_scope())

    module_path = Path("engine/formulation_intelligence/hedonic_platform.py")
    source = module_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")

    assert imported <= {
        "__future__",
        "collections.abc",
        "dataclasses",
        "enum",
        "hashlib",
        "math",
        "types",
        "typing",
        "contracts",
    }
    assert "hedonic_score" not in source
    assert "overall_score" not in source
    assert "aggregate_score" not in source
