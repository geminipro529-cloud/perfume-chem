from __future__ import annotations

from dataclasses import replace
from itertools import permutations
from typing import Any, Callable, Mapping

import pytest

from engine.formulation_intelligence.contracts import (
    AuthorityCeiling,
    EvidenceClass,
    PlaneAssessment,
    ProvenanceRef,
    UnitInterval,
    ValueState,
)
from engine.formulation_intelligence.mixture_hypotheses import (
    MixtureHypothesis,
    MixtureHypothesisKind,
    MixtureHypothesisScope,
    build_mixture_plane_assessment,
)
from engine.formulation_intelligence.plane_synthesis import (
    synthesize_plane_assessments,
)
from engine.formulation_intelligence.target_compiler import (
    AbstractionLevel,
    TargetBrief,
    TargetMode,
    compile_target_intent,
)
from engine.formulation_intelligence.temporal_architecture import (
    CANONICAL_TEMPORAL_SEQUENCE,
    ParticipantLinkedObservation,
    PredictedPhysicalEvolution,
    TemporalArchitecture,
    TemporalHypothesisScope,
    TemporalTransitionHypothesis,
    TemporalTransitionKind,
    TemporalTransitionSpec,
    TemporalWindow,
    TemporalWindowHypothesis,
    WithinSniffObservation,
    WithinSniffPhase,
    build_temporal_plane_assessment,
)


def _provenance(
    provenance_id: str,
    *,
    evidence_class: EvidenceClass = EvidenceClass.HEURISTIC,
    independence_key: str | None = None,
) -> ProvenanceRef:
    return ProvenanceRef(
        provenance_id=provenance_id,
        source_ref=f"test://{provenance_id}",
        evidence_class=evidence_class,
        independence_key=independence_key or f"method:{provenance_id}",
    )


def _mixture_scope(
    *,
    subject: str = "sample:magnolia-orris-v1",
    concentration: str = "20% w/w",
    temporal: str = "30 min",
    matrix: str = "ethanol-water 95:5 w/w",
    condition: str = "blotter:22c:50rh",
) -> MixtureHypothesisScope:
    return MixtureHypothesisScope(
        target_scope="target:magnolia-orris-study",
        subject_scope=subject,
        concentration_scope=concentration,
        temporal_scope=temporal,
        matrix_scope=matrix,
        condition_scope=condition,
    )


def _mixture_hypothesis(
    kind: MixtureHypothesisKind,
    *,
    suffix: str | None = None,
    scope: MixtureHypothesisScope | None = None,
    lower: float = 0.25,
    upper: float = 0.65,
    independence_key: str | None = None,
) -> MixtureHypothesis:
    token = suffix or kind.value
    component = _provenance(
        f"component:{token}",
        independence_key=independence_key or f"component-study:{token}",
    )
    mixture = _provenance(
        f"mixture:{token}",
        independence_key=independence_key or f"mixture-study:{token}",
    )
    return MixtureHypothesis(
        hypothesis_id=f"mixture:{token}",
        kind=kind,
        scope=scope or _mixture_scope(),
        statement=f"{kind.value} remains an exact-scope explanatory alternative",
        component_provenance=(component,),
        mixture_provenance=(mixture,),
        support=UnitInterval(lower, upper),
        uncertainty=f"{kind.value} has not been discriminated from alternatives",
        counterfactual=f"constant-total evidence may reject {kind.value}",
        failure_mode=f"misclassifying the mixture as {kind.value}",
        minimum_resolving_experiment=(
            "carrier-matched constant-total component-versus-mixture comparison"
        ),
    )


def _temporal_scope(
    window: TemporalWindow,
    *,
    subject: str = "sample:magnolia-orris-v1",
    condition: str = "blotter:22c:50rh",
) -> TemporalHypothesisScope:
    return TemporalHypothesisScope(
        target_scope="target:magnolia-orris-study",
        subject_scope=subject,
        concentration_scope="20% w/w",
        temporal_window=window,
        matrix_scope="ethanol-water 95:5 w/w",
        condition_scope=condition,
    )


def _prediction(window: TemporalWindow) -> PredictedPhysicalEvolution:
    source = _provenance(
        f"physical:{window.value}",
        evidence_class=EvidenceClass.COMPUTATIONAL_MODEL,
        independence_key=f"physical-model:{window.value}",
    )
    return PredictedPhysicalEvolution(
        prediction_id=f"prediction:{window.value}",
        scope=_temporal_scope(window),
        description=f"modeled physical state at {window.value}",
        support=UnitInterval(0.2, 0.55),
        provenance_refs=(source,),
    )


def _observation(window: TemporalWindow) -> ParticipantLinkedObservation:
    source = _provenance(
        f"observation:{window.value}",
        evidence_class=EvidenceClass.DIRECT_OBSERVATION,
        independence_key=f"participant:p01:repeat:r01:{window.value}",
    )
    return ParticipantLinkedObservation(
        observation_id=f"observation:{window.value}",
        scope=_temporal_scope(window),
        participant_id="participant:p01",
        repeat_id="repeat:r01",
        endpoint_id="subject-description",
        description=f"participant-linked description at {window.value}",
        provenance_refs=(source,),
    )


def _window_hypothesis(
    window: TemporalWindow,
    *,
    observed: bool = True,
) -> TemporalWindowHypothesis:
    source = _provenance(f"temporal-hypothesis:{window.value}")
    return TemporalWindowHypothesis(
        hypothesis_id=f"window:{window.value}",
        scope=_temporal_scope(window),
        subject_hypothesis=(
            "magnolia petal" if window in CANONICAL_TEMPORAL_SEQUENCE[:3] else "orris root"
        ),
        predicted_physical=_prediction(window),
        observed_perceptions=(_observation(window),) if observed else (),
        support=UnitInterval(0.3, 0.6),
        provenance_refs=(source,),
        uncertainty=f"subject state at {window.value} remains provisional",
        counterfactual=f"a blinded observation may reject the {window.value} subject",
        failure_mode=f"subject loss at {window.value}",
        minimum_resolving_experiment=(f"participant-linked blinded observation at {window.value}"),
    )


def _transition_spec(
    index: int,
    kind: TemporalTransitionKind,
) -> TemporalTransitionSpec:
    source = _provenance(f"transition:{index}:{kind.value}")
    return TemporalTransitionSpec(
        transition_spec_id=f"transition-spec:{index}:{kind.value}",
        kind=kind,
        bridge_or_handoff=("petal-to-root bridge" if kind.is_handoff else None),
        support=UnitInterval(0.2, 0.5),
        provenance_refs=(source,),
        uncertainty=f"{kind.value} transition is unobserved",
        counterfactual=f"reversed order may reject {kind.value}",
        failure_mode=f"{kind.value} transition failure",
        minimum_resolving_experiment="blinded adjacent-window handoff observation",
    )


def _architecture(
    *,
    missing_observation: TemporalWindow | None = None,
    windows_order: tuple[TemporalWindow, ...] | None = None,
    sequence: tuple[TemporalWindow, ...] = CANONICAL_TEMPORAL_SEQUENCE,
    transition_kinds: tuple[TemporalTransitionKind, ...] | None = None,
    within_sniff: tuple[WithinSniffObservation, ...] = (),
    within_sniff_requested: bool = False,
) -> TemporalArchitecture:
    raw_order = windows_order or CANONICAL_TEMPORAL_SEQUENCE
    windows = tuple(
        _window_hypothesis(
            window,
            observed=window is not missing_observation,
        )
        for window in raw_order
    )
    kinds = transition_kinds or (
        TemporalTransitionKind.CONTINUITY,
        TemporalTransitionKind.TRANSFORMATION,
        TemporalTransitionKind.BRIDGE_HANDOFF,
        TemporalTransitionKind.DELAYED_REVEAL,
        TemporalTransitionKind.TAKEOVER,
        TemporalTransitionKind.GENERIC_RESIDUE_FAILURE,
    )
    return TemporalArchitecture(
        architecture_id="temporal:magnolia-orris",
        windows=windows,
        declared_sequence=sequence,
        transition_specs=tuple(_transition_spec(index, kind) for index, kind in enumerate(kinds)),
        within_sniff_requested=within_sniff_requested,
        within_sniff_scope=(
            _temporal_scope(TemporalWindow.OPENING) if within_sniff_requested else None
        ),
        within_sniff_observations=within_sniff,
    )


def _sniff(phase: WithinSniffPhase) -> WithinSniffObservation:
    source = _provenance(
        f"sniff:{phase.value}",
        evidence_class=EvidenceClass.DIRECT_OBSERVATION,
        independence_key=f"participant:p01:sniff:{phase.value}",
    )
    return WithinSniffObservation(
        observation_id=f"sniff:{phase.value}",
        scope=_temporal_scope(TemporalWindow.OPENING),
        phase=phase,
        participant_id="participant:p01",
        repeat_id="repeat:r01",
        endpoint_id="within-sniff-subject",
        description=f"observed {phase.value}",
        provenance_refs=(source,),
    )


def test_all_mixture_alternatives_are_separate_immutable_hypotheses() -> None:
    hypotheses = tuple(_mixture_hypothesis(kind) for kind in MixtureHypothesisKind)
    assessment = build_mixture_plane_assessment(hypotheses)

    assert {kind.value for kind in MixtureHypothesisKind} == {
        "weighted_component",
        "strongest_component",
        "dominance",
        "masking",
        "suppression",
        "unmasking",
        "configural_residual",
    }
    assert len(assessment.claims) == len(MixtureHypothesisKind)
    assert {claim.claim_value.split(":", 1)[0] for claim in assessment.claims} == {
        kind.value for kind in MixtureHypothesisKind
    }
    assert all(hypothesis.component_provenance for hypothesis in hypotheses)
    assert all(hypothesis.mixture_provenance for hypothesis in hypotheses)
    with pytest.raises(Exception):
        hypotheses[0].statement = "mutated"  # type: ignore[misc]


def test_dominance_and_weighted_baseline_remain_an_explicit_conflict() -> None:
    assessment = build_mixture_plane_assessment(
        (
            _mixture_hypothesis(MixtureHypothesisKind.DOMINANCE),
            _mixture_hypothesis(MixtureHypothesisKind.WEIGHTED_COMPONENT),
        )
    )
    result = synthesize_plane_assessments((assessment,))

    assert assessment.conflicts
    alternatives = " ".join(assessment.conflicts[0].alternatives)
    assert "dominance" in alternatives
    assert "weighted_component" in alternatives
    assert any("repetition is not a vote" in item.reason for item in result.conflicts)


def test_repeated_heuristic_hypotheses_do_not_amplify_support() -> None:
    alternatives = (
        _mixture_hypothesis(MixtureHypothesisKind.WEIGHTED_COMPONENT),
        _mixture_hypothesis(MixtureHypothesisKind.MASKING),
    )
    baseline = build_mixture_plane_assessment(alternatives)
    duplicated = build_mixture_plane_assessment((*alternatives, *alternatives))

    assert duplicated.as_dict() == baseline.as_dict()
    assert duplicated.content_sha256 == baseline.content_sha256
    assert len(duplicated.support_intervals) == 2


def test_mixture_scope_mismatch_never_merges_competing_alternatives() -> None:
    scopes = (
        _mixture_scope(),
        _mixture_scope(subject="sample:magnolia-orris-v2"),
        _mixture_scope(temporal="2 hour"),
        _mixture_scope(concentration="10% w/w"),
        _mixture_scope(matrix="jojoba oil"),
        _mixture_scope(condition="skin:35c:70rh"),
    )
    assessments = tuple(
        build_mixture_plane_assessment(
            (
                _mixture_hypothesis(
                    MixtureHypothesisKind.WEIGHTED_COMPONENT,
                    suffix=f"scope-{index}-weighted",
                    scope=scope,
                ),
                _mixture_hypothesis(
                    MixtureHypothesisKind.MASKING,
                    suffix=f"scope-{index}-masking",
                    scope=scope,
                ),
            )
        )
        for index, scope in enumerate(scopes)
    )

    result = synthesize_plane_assessments(assessments)

    assert not result.harmonized_claims
    assert len({item.scope.key for item in result.conflicts}) == 6


def test_configural_residual_never_promotes_linear_misfit_to_emergence() -> None:
    hypothesis = _mixture_hypothesis(MixtureHypothesisKind.CONFIGURAL_RESIDUAL)
    payload = hypothesis.as_dict()

    assert hypothesis.causal_emergence_inferred is False
    assert hypothesis.oav_as_observed_perception is False
    assert hypothesis.pleasantness_inferred is False
    assert hypothesis.percent_perceived_contribution_inferred is False
    assert hypothesis.mixture_beauty_inferred is False
    payload["causal_emergence_inferred"] = True
    with pytest.raises(ValueError, match="authority flags"):
        MixtureHypothesis.from_dict(payload)


def test_predicted_physical_and_observed_perception_are_firewalled() -> None:
    architecture = _architecture()
    assessment = build_temporal_plane_assessment(architecture)
    claims_by_key = {claim.claim_key: claim for claim in assessment.claims}

    assert any("predicted_physical" in key for key in claims_by_key)
    assert any("observed_perception" in key for key in claims_by_key)
    assert not any(
        "predicted_physical" in key and "observed_perception" in key for key in claims_by_key
    )
    for window in architecture.windows:
        assert window.predicted_physical is not None
        assert window.predicted_physical.observed_perception is False
        assert window.predicted_physical.sensory_authority is False

    with pytest.raises(TypeError, match="ParticipantLinkedObservation"):
        TemporalWindowHypothesis(
            hypothesis_id="bad-firewall",
            scope=_temporal_scope(TemporalWindow.OPENING),
            subject_hypothesis="magnolia petal",
            predicted_physical=None,
            observed_perceptions=(_prediction(TemporalWindow.OPENING),),  # type: ignore[arg-type]
            support=UnitInterval(0.2, 0.4),
            provenance_refs=(_provenance("bad-firewall"),),
            uncertainty="unknown",
            counterfactual="observe it",
            failure_mode="type confusion",
            minimum_resolving_experiment="participant-linked observation",
        )


def test_temporal_architecture_requires_and_represents_every_window() -> None:
    architecture = _architecture()
    assessment = build_temporal_plane_assessment(architecture)

    assert {item.scope.temporal_window for item in architecture.windows} == set(
        CANONICAL_TEMPORAL_SEQUENCE
    )
    assert len(architecture.windows) == 7
    assert len(architecture.transitions) == 6
    subject_keys = {
        claim.claim_key for claim in assessment.claims if claim.claim_key.endswith(".subject")
    }
    assert len(subject_keys) == 7

    with pytest.raises(ValueError, match="all seven temporal windows"):
        TemporalArchitecture(
            architecture_id="incomplete",
            windows=architecture.windows[:-1],
            declared_sequence=CANONICAL_TEMPORAL_SEQUENCE,
            transition_specs=architecture.transition_specs,
            within_sniff_requested=False,
            within_sniff_scope=None,
            within_sniff_observations=(),
        )


def test_transition_vocabulary_subject_handoff_and_generic_residue_failure() -> None:
    assert {item.value for item in TemporalTransitionKind} == {
        "continuity",
        "transformation",
        "bridge_handoff",
        "delayed_reveal",
        "discontinuity",
        "takeover",
        "generic_residue_failure",
    }
    architecture = _architecture()
    assessment = build_temporal_plane_assessment(architecture)
    handoff = next(
        item
        for item in architecture.transitions
        if item.kind is TemporalTransitionKind.BRIDGE_HANDOFF
    )

    assert handoff.from_subject == "magnolia petal"
    assert handoff.to_subject == "orris root"
    assert handoff.bridge_or_handoff == "petal-to-root bridge"
    assert any("generic residue" in failure.casefold() for failure in assessment.failure_modes)


def test_reversing_declared_sequence_changes_transitions_deterministically() -> None:
    forward = _architecture()
    reversed_once = forward.reversed()
    reversed_twice = reversed_once.reversed()
    forward_assessment = build_temporal_plane_assessment(forward)
    reverse_assessment = build_temporal_plane_assessment(reversed_once)

    assert reversed_once.declared_sequence == tuple(reversed(CANONICAL_TEMPORAL_SEQUENCE))
    assert reversed_twice == forward
    assert reversed_once.transitions[0].from_window is TemporalWindow.HOUR_24
    assert reversed_once.transitions[0].to_window is TemporalWindow.HOUR_8
    assert reverse_assessment.content_sha256 != forward_assessment.content_sha256
    forward_transition_values = {
        claim.claim_value
        for claim in forward_assessment.claims
        if claim.claim_key.startswith("temporal.transition.")
    }
    reverse_transition_values = {
        claim.claim_value
        for claim in reverse_assessment.claims
        if claim.claim_key.startswith("temporal.transition.")
    }
    assert forward_transition_values != reverse_transition_values
    assert build_temporal_plane_assessment(reversed_once) == reverse_assessment


def test_missing_observations_and_within_sniff_phases_remain_unknown() -> None:
    architecture = _architecture(
        missing_observation=TemporalWindow.HOUR_8,
        within_sniff=(_sniff(WithinSniffPhase.ONSET),),
        within_sniff_requested=True,
    )
    assessment = build_temporal_plane_assessment(architecture)
    restored = PlaneAssessment.from_dict(assessment.as_dict())

    field_keys = {unknown.field_key for unknown in assessment.unknowns}
    assert "temporal.window.8_hour.observed_perception" in field_keys
    assert "temporal.within_sniff.opening.peak.observation" in field_keys
    assert "temporal.within_sniff.opening.offset.observation" in field_keys
    assert all(
        criterion.value.state is ValueState.UNKNOWN for criterion in assessment.native_criteria
    )
    assert all(criterion.value.value is None for criterion in assessment.native_criteria)
    assert restored.unknowns == assessment.unknowns


def test_authority_is_monotone_for_both_plane_packets_and_synthesis() -> None:
    mixture = build_mixture_plane_assessment(
        (
            _mixture_hypothesis(MixtureHypothesisKind.WEIGHTED_COMPONENT),
            _mixture_hypothesis(MixtureHypothesisKind.MASKING),
        ),
        authority_ceiling=AuthorityCeiling.EVIDENCE_LIMITED,
    )
    temporal = build_temporal_plane_assessment(
        _architecture(),
        authority_ceiling=AuthorityCeiling.EVIDENCE_LIMITED,
    )
    result = synthesize_plane_assessments(
        (mixture, temporal),
        authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
    )

    assert mixture.authority_ceiling is AuthorityCeiling.HYPOTHESIS_ONLY
    assert temporal.authority_ceiling is AuthorityCeiling.DESIGN_ONLY
    assert result.authority_ceiling is AuthorityCeiling.STRUCTURAL_ONLY
    assert all(
        claim.authority_ceiling.rank <= mixture.authority_ceiling.rank for claim in mixture.claims
    )
    assert all(
        claim.authority_ceiling.rank <= temporal.authority_ceiling.rank for claim in temporal.claims
    )
    assert result.formula_generation_authorized is False
    assert result.sensory_authority is False
    assert result.beauty_authority is False
    assert result.performance_authority is False
    assert result.safety_authority is False
    assert result.release_authority is False


def test_deterministic_dict_hash_reconstruction_and_input_order_invariance() -> None:
    hypotheses = tuple(
        _mixture_hypothesis(kind)
        for kind in (
            MixtureHypothesisKind.MASKING,
            MixtureHypothesisKind.SUPPRESSION,
            MixtureHypothesisKind.UNMASKING,
        )
    )
    reference_mixture = build_mixture_plane_assessment(hypotheses)
    for permuted in permutations(hypotheses):
        candidate = build_mixture_plane_assessment(permuted)
        assert candidate.as_dict() == reference_mixture.as_dict()
        assert candidate.content_sha256 == reference_mixture.content_sha256

    sniff = tuple(_sniff(phase) for phase in WithinSniffPhase)
    reference_architecture = _architecture(
        within_sniff=sniff,
        within_sniff_requested=True,
    )
    reordered_architecture = _architecture(
        windows_order=tuple(reversed(CANONICAL_TEMPORAL_SEQUENCE)),
        within_sniff=tuple(reversed(sniff)),
        within_sniff_requested=True,
    )
    reference_temporal = build_temporal_plane_assessment(reference_architecture)
    reordered_temporal = build_temporal_plane_assessment(reordered_architecture)

    assert reordered_architecture.as_dict() == reference_architecture.as_dict()
    assert reordered_temporal.as_dict() == reference_temporal.as_dict()
    assert reordered_temporal.content_sha256 == reference_temporal.content_sha256
    assert PlaneAssessment.from_dict(reference_mixture.as_dict()) == reference_mixture
    assert PlaneAssessment.from_dict(reference_temporal.as_dict()) == reference_temporal
    assert MixtureHypothesis.from_dict(hypotheses[0].as_dict()) == hypotheses[0]
    first_transition = reference_architecture.transitions[0]
    assert TemporalTransitionHypothesis.from_dict(first_transition.as_dict()) == first_transition
    assert (
        TemporalArchitecture.from_dict(reference_architecture.as_dict()) == reference_architecture
    )


def test_mixture_requires_distinct_explicit_competing_alternatives() -> None:
    hypothesis = _mixture_hypothesis(MixtureHypothesisKind.MASKING)

    with pytest.raises(ValueError, match="distinct competing alternatives"):
        build_mixture_plane_assessment((hypothesis,))
    with pytest.raises(ValueError, match="distinct competing alternatives"):
        build_mixture_plane_assessment((hypothesis, hypothesis))


def test_model_predictions_reject_observation_provenance_and_certainty() -> None:
    observed_ref = _provenance(
        "prediction-observation-confusion",
        evidence_class=EvidenceClass.DIRECT_OBSERVATION,
    )
    with pytest.raises(ValueError, match="prediction provenance"):
        PredictedPhysicalEvolution(
            prediction_id="prediction:confused",
            scope=_temporal_scope(TemporalWindow.OPENING),
            description="an observation mislabeled as a prediction",
            support=UnitInterval(0.2, 0.6),
            provenance_refs=(observed_ref,),
        )

    with pytest.raises(ValueError, match="empirical certainty"):
        _mixture_hypothesis(
            MixtureHypothesisKind.MASKING,
            lower=1.0,
            upper=1.0,
        )


def test_scope_records_bind_exact_subject_and_evaluation_condition() -> None:
    mixture_scope = _mixture_scope()
    temporal_scope = _temporal_scope(TemporalWindow.OPENING)

    assert mixture_scope.subject_scope == "sample:magnolia-orris-v1"
    assert mixture_scope.condition_scope == "blotter:22c:50rh"
    assert temporal_scope.subject_scope == "sample:magnolia-orris-v1"
    assert temporal_scope.condition_scope == "blotter:22c:50rh"


def test_continuity_and_generic_residue_are_both_explicit_unknown_criteria() -> None:
    assessment = build_temporal_plane_assessment(_architecture())
    criteria = {item.criterion_id: item for item in assessment.native_criteria}

    assert set(criteria) == {
        "temporal_generic_residue",
        "temporal_subject_continuity",
    }
    assert all(item.value.state is ValueState.UNKNOWN for item in criteria.values())
    assert all(item.value.value is None for item in criteria.values())


def test_nested_temporal_evidence_must_match_exact_window_scope() -> None:
    opening = _window_hypothesis(TemporalWindow.OPENING)
    wrong_prediction = _prediction(TemporalWindow.MINUTE_5)
    wrong_observation = _observation(TemporalWindow.MINUTE_5)

    with pytest.raises(ValueError, match="predicted_physical.*exact window scope"):
        replace(opening, predicted_physical=wrong_prediction)
    with pytest.raises(ValueError, match="observed_perceptions.*exact window scope"):
        replace(opening, observed_perceptions=(wrong_observation,))


def test_temporal_architecture_rejects_subject_or_condition_scope_drift() -> None:
    architecture = _architecture(within_sniff_requested=True)
    original = architecture.window_map[TemporalWindow.HOUR_24]
    assert original.predicted_physical is not None
    drifted_scope = _temporal_scope(
        TemporalWindow.HOUR_24,
        subject="sample:magnolia-orris-v2",
        condition="skin:35c:70rh",
    )
    drifted = replace(
        original,
        scope=drifted_scope,
        predicted_physical=replace(
            original.predicted_physical,
            scope=drifted_scope,
        ),
        observed_perceptions=tuple(
            replace(item, scope=drifted_scope) for item in original.observed_perceptions
        ),
    )
    windows = tuple(
        drifted if item.scope.temporal_window is TemporalWindow.HOUR_24 else item
        for item in architecture.windows
    )

    with pytest.raises(ValueError, match="subject.*condition.*scope mismatch"):
        replace(architecture, windows=windows)

    drifted_sniff = replace(
        _sniff(WithinSniffPhase.ONSET),
        scope=_temporal_scope(
            TemporalWindow.OPENING,
            condition="skin:35c:70rh",
        ),
    )
    with pytest.raises(ValueError, match="exact within_sniff_scope"):
        replace(architecture, within_sniff_observations=(drifted_sniff,))

    with pytest.raises(ValueError, match="requires an exact within_sniff_scope"):
        replace(architecture, within_sniff_scope=None)


def _assert_closed_schema(
    record: object,
    loader: Callable[[Mapping[str, Any]], object],
) -> None:
    payload = record.as_dict()  # type: ignore[attr-defined]
    extra = {**payload, "unexpected": "field"}
    with pytest.raises(ValueError, match="closed schema"):
        loader(extra)

    missing = dict(payload)
    missing_key = next(key for key in missing if key != "schema_version")
    missing.pop(missing_key)
    with pytest.raises(ValueError, match="closed schema"):
        loader(missing)

    wrong_version = {**payload, "schema_version": "obsolete_or_future_schema"}
    with pytest.raises(ValueError, match="schema_version"):
        loader(wrong_version)


def test_all_leased_records_reject_open_or_wrong_version_payloads() -> None:
    mixture = _mixture_hypothesis(MixtureHypothesisKind.MASKING)
    architecture = _architecture(
        within_sniff=(_sniff(WithinSniffPhase.ONSET),),
        within_sniff_requested=True,
    )
    window = architecture.windows[0]
    prediction = window.predicted_physical
    assert prediction is not None
    observation = window.observed_perceptions[0]
    sniff = architecture.within_sniff_observations[0]
    transition_spec = architecture.transition_specs[0]
    transition = architecture.transitions[0]
    records_and_loaders: tuple[tuple[object, Callable[[Mapping[str, Any]], object]], ...] = (
        (mixture.scope, MixtureHypothesisScope.from_dict),
        (mixture, MixtureHypothesis.from_dict),
        (prediction.scope, TemporalHypothesisScope.from_dict),
        (prediction, PredictedPhysicalEvolution.from_dict),
        (observation, ParticipantLinkedObservation.from_dict),
        (sniff, WithinSniffObservation.from_dict),
        (window, TemporalWindowHypothesis.from_dict),
        (transition_spec, TemporalTransitionSpec.from_dict),
        (transition, TemporalTransitionHypothesis.from_dict),
        (architecture, TemporalArchitecture.from_dict),
    )

    for record, loader in records_and_loaders:
        _assert_closed_schema(record, loader)


def test_semantic_target_id_is_identical_across_target_mixture_and_temporal_packets() -> None:
    target_intent = compile_target_intent(
        TargetBrief(
            request_id="cross-plane magnolia orris",
            mode=TargetMode.CONCEPT_ONLY,
            subject="Magnolia Orris Study",
            named_references=(),
            family_neighborhoods=("floral",),
            abstraction_level=AbstractionLevel.RECOGNIZABLE_ABSTRACTION,
            expression_terms=("magnolia petal into cool orris root",),
            exclusions=("generic floral residue",),
            protected_recognizers=("magnolia-to-orris continuity",),
            forbidden_drift=("anonymous woody musk",),
            transformations=(),
            temporal_requests=("opening", "drydown"),
            matrix_context="20% w/w in ethanol-water 95:5 w/w",
            criterion_vocabulary=("target fidelity", "temporal continuity"),
            reference_evidence=(),
            provenance_refs=(_provenance("cross-plane-target"),),
        )
    )
    target_packet = target_intent.to_plane_assessment()
    semantic_target_id = target_packet.scope.target_scope

    mixture_scope = MixtureHypothesisScope(
        target_scope=semantic_target_id,
        subject_scope="sample:magnolia-orris-v1",
        concentration_scope="20% w/w",
        temporal_scope="30 min",
        matrix_scope="ethanol-water 95:5 w/w",
        condition_scope="blotter:22c:50rh",
    )
    mixture_packet = build_mixture_plane_assessment(
        (
            _mixture_hypothesis(
                MixtureHypothesisKind.WEIGHTED_COMPONENT,
                suffix="cross-plane-weighted",
                scope=mixture_scope,
            ),
            _mixture_hypothesis(
                MixtureHypothesisKind.MASKING,
                suffix="cross-plane-masking",
                scope=mixture_scope,
            ),
        )
    )

    architecture = _architecture()
    retargeted_windows = tuple(
        replace(
            item,
            scope=replace(item.scope, target_scope=semantic_target_id),
            predicted_physical=(
                replace(
                    item.predicted_physical,
                    scope=replace(item.scope, target_scope=semantic_target_id),
                )
                if item.predicted_physical is not None
                else None
            ),
            observed_perceptions=tuple(
                replace(
                    observation,
                    scope=replace(observation.scope, target_scope=semantic_target_id),
                )
                for observation in item.observed_perceptions
            ),
        )
        for item in architecture.windows
    )
    temporal_packet = build_temporal_plane_assessment(
        replace(architecture, windows=retargeted_windows)
    )

    assert target_packet.scope.target_scope == semantic_target_id
    assert mixture_packet.scope.target_scope == semantic_target_id
    assert temporal_packet.scope.target_scope == semantic_target_id

    second_scope = replace(
        mixture_scope,
        subject_scope="sample:magnolia-orris-v2",
        condition_scope="skin:35c:70rh",
    )
    second_packet = build_mixture_plane_assessment(
        (
            _mixture_hypothesis(
                MixtureHypothesisKind.WEIGHTED_COMPONENT,
                suffix="cross-plane-second-weighted",
                scope=second_scope,
            ),
            _mixture_hypothesis(
                MixtureHypothesisKind.MASKING,
                suffix="cross-plane-second-masking",
                scope=second_scope,
            ),
        )
    )
    synthesis = synthesize_plane_assessments((mixture_packet, second_packet))

    assert mixture_packet.scope.target_scope == second_packet.scope.target_scope
    assert mixture_packet.scope.key != second_packet.scope.key
    assert len({item.scope.key for item in synthesis.conflicts}) == 2
