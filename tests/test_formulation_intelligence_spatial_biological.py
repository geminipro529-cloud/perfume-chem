from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from typing import Any

import pytest

from engine.formulation_intelligence.biological_sensitivity import (
    BiologicalIdentity,
    BiologicalIdentityKind,
    BiologicalMechanismHypothesis,
    BiologicalObservationEndpoint,
    BiologicalSensitivityArchitecture,
    BiologicalSensitivityPlaneAdapter,
    BiologicalStudyScope,
    ParticipantSensitivityObservation,
)
from engine.formulation_intelligence.contracts import (
    AuthorityCeiling,
    CriterionValue,
    EvidenceClass,
    PlaneAssessment,
    PlaneConflict,
    PlaneId,
    ProvenanceRef,
    SupportInterval,
)
from engine.formulation_intelligence.plane_synthesis import (
    PlaneAssessmentAdapter,
    synthesize_plane_assessments,
)
from engine.formulation_intelligence.spatial_architecture import (
    ParticipantSpatialObservation,
    PredictedSpatialTransport,
    SpatialArchitecture,
    SpatialDimension,
    SpatialDimensionHypothesis,
    SpatialPlaneAdapter,
    SpatialRelationHypothesis,
    SpatialRelationKind,
    SpatialScope,
)
from engine.formulation_intelligence.target_compiler import (
    AbstractionLevel,
    TargetBrief,
    TargetMode,
    compile_target_intent,
)


def _provenance(
    source: str,
    *,
    evidence_class: EvidenceClass = EvidenceClass.COMPUTATIONAL_MODEL,
    condition: str = "condition-a",
) -> ProvenanceRef:
    return ProvenanceRef(
        provenance_id=source,
        source_ref=f"test://{source}",
        evidence_class=evidence_class,
        independence_key=condition,
    )


def _support(source: str, condition: str = "condition-a") -> SupportInterval:
    return SupportInterval(
        interval_id=f"interval-{source}",
        claim_id=f"claim-{source}",
        lower=0.35,
        upper=0.65,
        provenance_refs=(_provenance(f"{source}-{condition}", condition=condition),),
    )


def _spatial_scope(
    *,
    target: str = "target: chiaroscuro spatial brief",
    subject: str = "sample: spatial-candidate-v1",
    material: str = "formula-version: spatial-candidate-v1",
    condition: str = "condition-a",
    temporal: str = "30-minute",
    matrix: str = "ethanol blotter",
    context: str = "controlled booth",
    protocol: str = "protocol-v1",
) -> SpatialScope:
    return SpatialScope(
        target_scope=target,
        subject_id=subject,
        material_identity_id=material,
        condition_id=condition,
        temporal_scope=temporal,
        matrix_scope=matrix,
        context_scope=context,
        protocol_scope=protocol,
    )


def _dimension(
    dimension: SpatialDimension,
    *,
    suffix: str | None = None,
    scope: SpatialScope | None = None,
) -> SpatialDimensionHypothesis:
    token = suffix or dimension.value
    resolved_scope = scope or _spatial_scope()
    return SpatialDimensionHypothesis(
        hypothesis_id=f"dimension-{token}",
        dimension=dimension,
        scope=resolved_scope,
        condition_id=resolved_scope.condition_id,
        target_state=f"target state for {dimension.value}",
        support=_support(f"spatial-{token}", condition=resolved_scope.condition_id),
        uncertainty="No participant-linked observation establishes this target state.",
        counterfactual="A protocol-matched observation may contradict the proposed state.",
        failure_mode="The dimension collapses into an adjacent but distinct dimension.",
        minimum_resolving_experiment="Run a blinded, dimension-specific comparison.",
    )


def _all_dimensions(
    scope: SpatialScope | None = None,
) -> tuple[SpatialDimensionHypothesis, ...]:
    return tuple(_dimension(dimension, scope=scope) for dimension in SpatialDimension)


def _spatial_architecture(
    *,
    architecture_id: str = "spatial-architecture-a",
    scope: SpatialScope | None = None,
    dimensions: tuple[SpatialDimensionHypothesis, ...] | None = None,
    predicted: tuple[PredictedSpatialTransport, ...] = (),
    observations: tuple[ParticipantSpatialObservation, ...] = (),
    relations: tuple[SpatialRelationHypothesis, ...] = (),
) -> SpatialArchitecture:
    resolved_scope = scope or _spatial_scope()
    return SpatialArchitecture(
        architecture_id=architecture_id,
        scope=resolved_scope,
        dimension_hypotheses=dimensions or _all_dimensions(resolved_scope),
        predicted_transport=predicted,
        participant_observations=observations,
        relations=relations,
    )


def _exact_identity(
    *,
    stereochemistry: str = "(R)",
    identity_id: str = "mol-r",
    source: str | None = "supplier-a",
    lot: str | None = "lot-7",
) -> BiologicalIdentity:
    return BiologicalIdentity(
        identity_id=identity_id,
        kind=BiologicalIdentityKind.EXACT_MOLECULE,
        identity_label="reference odorant",
        exact_molecule_id="CAS:123-45-6",
        stereochemistry=stereochemistry,
        grade_product_basis="isolated analytical reference, >=99%",
        source_name=source,
        lot_id=lot,
    )


def _biological_scope(
    *,
    target: str = "target: sensitivity architecture",
    subject: str = "study-subject: exact-odorant sensitivity cohort a",
    material_identity_key: str | None = None,
    condition: str = "bio-condition-a",
    assay: str = "OR-X concentration-response assay",
    population: str = "adult participants, cohort A",
    matrix: str = "ethanol presentation",
    concentration: str = "10 ppm w/w",
    temporal: str = "5-minute endpoint",
    protocol: str = "bio-protocol-v1",
) -> BiologicalStudyScope:
    return BiologicalStudyScope(
        target_scope=target,
        subject_scope=subject,
        material_identity_key=(material_identity_key or _exact_identity().scope_identity_key),
        condition_id=condition,
        assay_task=assay,
        population_scope=population,
        matrix_scope=matrix,
        concentration_scope=concentration,
        temporal_scope=temporal,
        protocol_scope=protocol,
    )


def _mechanism(
    hypothesis_id: str = "mechanism-a",
    *,
    identity: BiologicalIdentity | None = None,
    tested_identity: BiologicalIdentity | None = None,
    scope: BiologicalStudyScope | None = None,
    claim: str = "OR-X response may be associated with task sensitivity.",
    receptor: str | None = "OR-X",
    genotype: str | None = "rs-test:A/G",
    risk: CriterionValue | None = None,
) -> BiologicalMechanismHypothesis:
    claimed = identity or _exact_identity()
    resolved_scope = scope or _biological_scope(material_identity_key=claimed.scope_identity_key)
    evidence = _provenance(
        f"bio-{hypothesis_id}-{resolved_scope.condition_id}",
        evidence_class=EvidenceClass.PRIMARY_SOURCE,
        condition=resolved_scope.condition_id,
    )
    return BiologicalMechanismHypothesis(
        hypothesis_id=hypothesis_id,
        claimed_identity=claimed,
        tested_identity=tested_identity or claimed,
        scope=resolved_scope,
        receptor_id=receptor,
        genotype_id=genotype,
        sensitivity_claim=claim,
        evidence_class=EvidenceClass.PRIMARY_SOURCE,
        support=SupportInterval(
            interval_id=f"bio-interval-{hypothesis_id}",
            claim_id=f"biological-mechanism-{hypothesis_id}",
            lower=0.25,
            upper=0.55,
            provenance_refs=(evidence,),
        ),
        uncertainty="Population transfer and participant perception remain unresolved.",
        specific_anosmia_risk=risk or CriterionValue.unknown("No prevalence estimate."),
        counterfactual="A protocol-matched null response would weaken the hypothesis.",
        failure_mode="The assay association does not transfer to participant sensitivity.",
        minimum_resolving_experiment="Run preregistered genotype-stratified psychophysics.",
    )


def _biological_architecture(
    *,
    assessment_id: str = "biological-architecture-a",
    scope: BiologicalStudyScope | None = None,
    mechanisms: tuple[BiologicalMechanismHypothesis, ...] | None = None,
    observations: tuple[ParticipantSensitivityObservation, ...] = (),
) -> BiologicalSensitivityArchitecture:
    resolved_scope = scope or _biological_scope()
    return BiologicalSensitivityArchitecture(
        assessment_id=assessment_id,
        scope=resolved_scope,
        mechanism_hypotheses=mechanisms or (_mechanism(scope=resolved_scope),),
        participant_observations=observations,
    )


def _compiled_target_packet() -> PlaneAssessment:
    brief = TargetBrief(
        request_id="cross-plane-target",
        mode=TargetMode.CONCEPT_ONLY,
        subject="Chiaroscuro Magnolia Study",
        named_references=(),
        family_neighborhoods=("floral",),
        abstraction_level=AbstractionLevel.EVOCATIVE,
        expression_terms=("luminous petal field", "mineral shadow"),
        exclusions=("generic floral blur",),
        protected_recognizers=("magnolia petal identity",),
        forbidden_drift=("anonymous woody amber",),
        transformations=(),
        temporal_requests=("opening", "heart", "drydown"),
        matrix_context="ethanol fragrance matrix",
        criterion_vocabulary=("target fidelity", "transition continuity"),
        reference_evidence=(),
        provenance_refs=(
            _provenance(
                "cross-plane-target-brief",
                evidence_class=EvidenceClass.USER_REPORT,
                condition="cross-plane-target-brief",
            ),
        ),
    )
    return compile_target_intent(brief).to_plane_assessment()


def test_semantic_target_scope_is_identical_across_target_spatial_and_biological() -> None:
    target_packet = _compiled_target_packet()
    semantic_target_id = target_packet.scope.target_scope
    spatial_packet = SpatialPlaneAdapter(
        _spatial_architecture(
            scope=_spatial_scope(
                target=semantic_target_id,
                subject="sample: spatial-candidate-v7",
                material="formula-version: spatial-candidate-v7",
                condition="condition-spatial-v7",
            )
        )
    ).to_plane_assessment()
    identity = _exact_identity()
    biological_scope = _biological_scope(
        target=semantic_target_id,
        subject="study-subject: participant cohort v7",
        material_identity_key=identity.scope_identity_key,
        condition="condition-biological-v7",
    )
    biological_packet = BiologicalSensitivityPlaneAdapter(
        _biological_architecture(
            scope=biological_scope,
            mechanisms=(_mechanism(identity=identity, scope=biological_scope),),
        )
    ).to_plane_assessment()

    assert target_packet.scope.target_scope == semantic_target_id
    assert spatial_packet.scope.target_scope == semantic_target_id
    assert biological_packet.scope.target_scope == semantic_target_id

    other_spatial = SpatialPlaneAdapter(
        _spatial_architecture(
            architecture_id="spatial-other-subject",
            scope=_spatial_scope(
                target=semantic_target_id,
                subject="sample: spatial-candidate-v8",
                material="formula-version: spatial-candidate-v8",
                condition="condition-spatial-v8",
            ),
        )
    ).to_plane_assessment()
    assert spatial_packet.scope.key != other_spatial.scope.key


def test_spatial_dimensions_are_complete_and_density_is_independent_from_air() -> None:
    architecture = _spatial_architecture()
    packet = SpatialPlaneAdapter(architecture).to_plane_assessment()

    assert packet.plane_id is PlaneId.SPATIAL_COMPOSITION
    assert {item.dimension for item in architecture.dimension_hypotheses} == set(SpatialDimension)
    assert len(architecture.dimension_hypotheses) == 12
    claim_keys = {claim.claim_key for claim in packet.claims}
    assert "spatial.dimension.density" in claim_keys
    assert "spatial.dimension.negative_space_air" in claim_keys
    criteria = {criterion.criterion_id: criterion for criterion in packet.native_criteria}
    assert criteria["spatial_density"].value.value is None
    assert criteria["spatial_negative_space_air"].value.value is None
    assert criteria["spatial_density"] != criteria["spatial_negative_space_air"]

    missing = [
        hypothesis
        for hypothesis in _all_dimensions()
        if hypothesis.dimension is not SpatialDimension.SHADOW
    ]
    with pytest.raises(ValueError, match="exactly one hypothesis"):
        _spatial_architecture(dimensions=tuple(missing))


def test_spatial_predicted_transport_cannot_become_observed_perception() -> None:
    predicted = PredictedSpatialTransport(
        prediction_id="transport-a",
        dimension=SpatialDimension.PROJECTION_FIELD,
        scope=_spatial_scope(),
        condition_id="condition-a",
        prediction="A transport model predicts a wider concentration field.",
        support=_support("transport-a"),
        uncertainty="No participant-linked spatial judgment is present.",
        failure_mode="Transport assumptions do not hold in the test matrix.",
        minimum_resolving_experiment="Pair physical sampling with blinded participants.",
    )
    architecture = _spatial_architecture(predicted=(predicted,))
    packet = SpatialPlaneAdapter(architecture).to_plane_assessment()

    assert predicted.observed_space_authority is False
    assert predicted.sillage_authority is False
    assert predicted.projection_authority is False
    assert predicted.longevity_authority is False
    assert predicted.performance_authority is False
    assert predicted.sensory_authority is False
    assert not any(
        claim.claim_key.startswith("spatial.observed_participant") for claim in packet.claims
    )
    assert any(
        unknown.field_key == "spatial.projection_field.observed_perception"
        for unknown in packet.unknowns
    )

    tampered = predicted.as_dict()
    tampered["projection_authority"] = True
    with pytest.raises(ValueError, match="remain false"):
        PredictedSpatialTransport.from_dict(tampered)


def test_spatial_observations_preserve_participant_heterogeneity_and_exact_conflicts() -> None:
    positive = ParticipantSpatialObservation(
        observation_id="spatial-observation-positive",
        participant_id="participant-01",
        repeat_id="repeat-01",
        endpoint_id="width-task",
        dimension=SpatialDimension.WIDTH,
        scope=_spatial_scope(),
        condition_id="condition-a",
        observed_state="participant reported a broad field",
        provenance_refs=(
            _provenance(
                "participant-width-positive",
                evidence_class=EvidenceClass.DIRECT_OBSERVATION,
            ),
        ),
    )
    negative = ParticipantSpatialObservation(
        observation_id="spatial-observation-negative",
        participant_id="participant-02",
        repeat_id="repeat-01",
        endpoint_id="width-task",
        dimension=SpatialDimension.WIDTH,
        scope=_spatial_scope(),
        condition_id="condition-a",
        observed_state="participant reported a narrow field",
        provenance_refs=(
            _provenance(
                "participant-width-negative",
                evidence_class=EvidenceClass.USER_REPORT,
            ),
        ),
    )
    heterogeneous_packet = SpatialPlaneAdapter(
        _spatial_architecture(observations=(negative, positive))
    ).to_plane_assessment()

    observation_claims = [
        claim
        for claim in heterogeneous_packet.claims
        if claim.claim_key.startswith("spatial.observed_participant.width")
    ]
    assert len(observation_claims) == 2
    assert len({claim.claim_key for claim in observation_claims}) == 2
    assert {claim.claim_value for claim in observation_claims} == {
        positive.observed_state,
        negative.observed_state,
    }
    assert not any(
        conflict.claim_key.startswith("spatial.observed_participant.width")
        for conflict in heterogeneous_packet.conflicts
    )
    assert positive.interpolated is False

    contradiction = ParticipantSpatialObservation(
        observation_id="spatial-observation-contradiction",
        participant_id=positive.participant_id,
        repeat_id=positive.repeat_id,
        endpoint_id=positive.endpoint_id,
        dimension=positive.dimension,
        scope=positive.scope,
        condition_id=positive.condition_id,
        observed_state="the same participant record says the field was narrow",
        provenance_refs=(
            _provenance(
                "participant-width-contradiction",
                evidence_class=EvidenceClass.DIRECT_OBSERVATION,
            ),
        ),
    )
    conflict_packet = SpatialPlaneAdapter(
        _spatial_architecture(observations=(positive, contradiction))
    ).to_plane_assessment()
    assert any(
        conflict.claim_key.startswith("spatial.observed_participant.width")
        and len(conflict.alternatives) == 2
        for conflict in conflict_packet.conflicts
    )


def test_spatial_condition_mismatch_fails_closed() -> None:
    with pytest.raises(ValueError, match="condition"):
        SpatialRelationHypothesis(
            relation_id="wrong-condition-relation",
            source_dimension=SpatialDimension.APERTURE,
            target_dimension=SpatialDimension.SHADOW,
            scope=_spatial_scope(),
            relation_kind=SpatialRelationKind.TRANSITION,
            condition_id="condition-b",
            hypothesis="A condition-mismatched relation must not enter this packet.",
            support=_support("wrong-condition", condition="condition-b"),
            uncertainty="Condition transfer is unsupported.",
            counterfactual="The relation may disappear under the packet condition.",
            failure_mode="Evidence from condition B is attributed to condition A.",
            minimum_resolving_experiment="Repeat under the packet condition.",
        )


def test_spatial_relations_are_structural_and_never_scalar_beauty() -> None:
    relation = SpatialRelationHypothesis(
        relation_id="aperture-to-shadow",
        source_dimension=SpatialDimension.APERTURE,
        target_dimension=SpatialDimension.SHADOW,
        scope=_spatial_scope(),
        relation_kind=SpatialRelationKind.TRANSITION,
        condition_id="condition-a",
        hypothesis="A narrower aperture may hand off into stronger shadow.",
        support=_support("aperture-shadow"),
        uncertainty="The transition is not participant-confirmed.",
        counterfactual="Matched observations could show no handoff.",
        failure_mode="A generic residue obscures the proposed transition.",
        minimum_resolving_experiment="Run a time-linked aperture/shadow task.",
    )
    packet = SpatialPlaneAdapter(_spatial_architecture(relations=(relation,))).to_plane_assessment()

    assert any(
        claim.claim_key == "spatial.relation.aperture.shadow.aperture-to-shadow"
        for claim in packet.claims
    )
    serialized = json.dumps(packet.as_dict(), sort_keys=True).lower()
    assert "beauty_score" not in serialized
    assert "formula_selection" not in serialized
    assert "material_selection" not in serialized


@pytest.mark.parametrize(
    ("changed", "value"),
    [
        ("subject", "sample: other-subject"),
        ("material", "formula-version: other-material"),
        ("condition", "condition-b"),
        ("temporal", "2-hour"),
        ("matrix", "oil substrate"),
        ("context", "outdoor context"),
        ("protocol", "protocol-v2"),
    ],
)
def test_spatial_exact_scope_mismatches_remain_separate(
    changed: str,
    value: str,
) -> None:
    baseline = _spatial_scope()
    kwargs = {
        "subject": baseline.subject_id,
        "material": baseline.material_identity_id,
        "condition": baseline.condition_id,
        "temporal": baseline.temporal_scope,
        "matrix": baseline.matrix_scope,
        "context": baseline.context_scope,
        "protocol": baseline.protocol_scope,
    }
    kwargs[changed] = value
    different = _spatial_scope(**kwargs)

    synthesis = synthesize_plane_assessments(
        (
            SpatialPlaneAdapter(
                _spatial_architecture(
                    architecture_id="spatial-scope-baseline",
                    scope=baseline,
                )
            ).to_plane_assessment(),
            SpatialPlaneAdapter(
                _spatial_architecture(
                    architecture_id="spatial-scope-different",
                    scope=different,
                )
            ).to_plane_assessment(),
        )
    )
    assert len({item.scope.key for item in synthesis.assessments}) == 2


def test_spatial_serialization_hash_roundtrip_order_and_authority_are_stable() -> None:
    relation_a = SpatialRelationHypothesis(
        relation_id="a-relation",
        source_dimension=SpatialDimension.FOCUS,
        target_dimension=SpatialDimension.WIDTH,
        scope=_spatial_scope(),
        relation_kind=SpatialRelationKind.SPATIAL,
        condition_id="condition-a",
        hypothesis="Focus and width may remain distinct.",
        support=_support("relation-a"),
        uncertainty="Unobserved.",
        counterfactual="A matched task may couple them.",
        failure_mode="The task aliases the dimensions.",
        minimum_resolving_experiment="Run orthogonal focus and width tasks.",
    )
    relation_b = SpatialRelationHypothesis(
        relation_id="b-relation",
        source_dimension=SpatialDimension.TEXTURE,
        target_dimension=SpatialDimension.EDGE,
        scope=_spatial_scope(),
        relation_kind=SpatialRelationKind.CONTRAST,
        condition_id="condition-a",
        hypothesis="Texture may sharpen an edge contrast.",
        support=_support("relation-b"),
        uncertainty="Unobserved.",
        counterfactual="Matched observations may reverse the relation.",
        failure_mode="Texture and edge are task-confounded.",
        minimum_resolving_experiment="Run orthogonal texture and edge tasks.",
    )
    forward = _spatial_architecture(relations=(relation_a, relation_b))
    reverse = _spatial_architecture(
        dimensions=tuple(reversed(_all_dimensions())),
        relations=(relation_b, relation_a),
    )

    assert forward.as_dict() == reverse.as_dict()
    assert forward.content_sha256 == reverse.content_sha256
    restored = SpatialArchitecture.from_dict(forward.as_dict())
    assert restored == forward
    assert restored.content_sha256 == forward.content_sha256
    adapter = SpatialPlaneAdapter(forward)
    assert isinstance(adapter, PlaneAssessmentAdapter)
    assert PlaneAssessment.from_dict(adapter.to_plane_assessment().as_dict()) == (
        adapter.to_plane_assessment()
    )
    assert adapter.to_plane_assessment().authority_ceiling is AuthorityCeiling.DESIGN_ONLY
    clamped = SpatialPlaneAdapter(
        forward,
        authority_ceiling=AuthorityCeiling.EVIDENCE_LIMITED,
    )
    assert clamped.authority_ceiling is AuthorityCeiling.DESIGN_ONLY
    with pytest.raises(FrozenInstanceError):
        forward.architecture_id = "changed"  # type: ignore[misc]


def test_biological_hypothesis_binds_exact_identity_assay_population_and_scope() -> None:
    mechanism = _mechanism()
    packet = BiologicalSensitivityPlaneAdapter(
        _biological_architecture(mechanisms=(mechanism,))
    ).to_plane_assessment()

    assert packet.plane_id is PlaneId.BIOLOGICAL_SENSITIVITY
    assert mechanism.claimed_identity.exact_molecule_id == "cas:123-45-6"
    assert mechanism.claimed_identity.stereochemistry == "(R)"
    assert mechanism.scope.assay_task == "or-x concentration-response assay"
    assert mechanism.scope.population_scope == "adult participants, cohort a"
    assert mechanism.scope.concentration_scope == "10 ppm w/w"
    mechanism_claim = next(
        claim for claim in packet.claims if claim.claim_key.startswith("biological.mechanism.")
    )
    assert mechanism.scope.assay_task in mechanism_claim.claim_value
    assert mechanism.scope.population_scope in mechanism_claim.claim_value
    assert mechanism.scope.concentration_scope in mechanism_claim.claim_value
    assert mechanism_claim.authority_ceiling is AuthorityCeiling.HYPOTHESIS_ONLY


def test_biological_packet_rejects_mixed_material_identities() -> None:
    scope = _biological_scope()
    first = _mechanism("mechanism-first", scope=scope)
    assert first.claimed_identity.scope_identity_key == scope.material_identity_key
    other_identity = BiologicalIdentity(
        identity_id="mol-other",
        kind=BiologicalIdentityKind.EXACT_MOLECULE,
        identity_label="different exact odorant",
        exact_molecule_id="CAS:654-32-1",
        stereochemistry="achiral",
        grade_product_basis="isolated analytical reference, >=99%",
        source_name="supplier-b",
        lot_id="lot-9",
    )
    with pytest.raises(ValueError, match="material identity"):
        _mechanism(
            "mechanism-other",
            identity=other_identity,
            scope=scope,
            receptor="OR-Z",
        )


def test_biological_provenance_condition_mismatch_fails_closed() -> None:
    mechanism = _mechanism()
    tampered = mechanism.as_dict()
    tampered["support"]["provenance_refs"][0]["independence_key"] = "condition-b"
    with pytest.raises(ValueError, match="condition"):
        BiologicalMechanismHypothesis.from_dict(tampered)


def test_opaque_products_and_unknown_exact_bases_cannot_inherit_mechanisms() -> None:
    opaque = BiologicalIdentity(
        identity_id="opaque-product",
        kind=BiologicalIdentityKind.OPAQUE_TRADE_PRODUCT,
        identity_label="opaque trade product",
        exact_molecule_id=None,
        stereochemistry=None,
        grade_product_basis="supplier product as received",
    )
    natural = BiologicalIdentity(
        identity_id="natural-mixture",
        kind=BiologicalIdentityKind.NATURAL_MIXTURE,
        identity_label="natural extract",
        exact_molecule_id=None,
        stereochemistry=None,
        grade_product_basis="natural extract as received",
    )
    with pytest.raises(ValueError, match="isolated exact-molecule mechanism"):
        _mechanism(identity=opaque)
    with pytest.raises(ValueError, match="isolated exact-molecule mechanism"):
        _mechanism(identity=natural)
    with pytest.raises(ValueError, match="grade/product basis"):
        BiologicalIdentity(
            identity_id="unknown-basis",
            kind=BiologicalIdentityKind.EXACT_MOLECULE,
            identity_label="claimed exact molecule",
            exact_molecule_id="CAS:123-45-6",
            stereochemistry="(R)",
            grade_product_basis=None,
        )
    with pytest.raises(ValueError, match="stereochemistry"):
        BiologicalIdentity(
            identity_id="unknown-stereo",
            kind=BiologicalIdentityKind.EXACT_MOLECULE,
            identity_label="claimed exact molecule",
            exact_molecule_id="CAS:123-45-6",
            stereochemistry=None,
            grade_product_basis="isolated reference",
        )


def test_stereoisomer_or_product_basis_mismatch_fails_closed() -> None:
    claimed = _exact_identity(stereochemistry="(R)", identity_id="claimed-r")
    tested_s = _exact_identity(stereochemistry="(S)", identity_id="tested-s")
    with pytest.raises(ValueError, match="tested and claimed exact identities must match"):
        _mechanism(identity=claimed, tested_identity=tested_s)

    tested_grade = BiologicalIdentity(
        identity_id="tested-other-grade",
        kind=BiologicalIdentityKind.EXACT_MOLECULE,
        identity_label="reference odorant",
        exact_molecule_id="CAS:123-45-6",
        stereochemistry="(R)",
        grade_product_basis="technical grade, 90%",
        source_name="supplier-a",
        lot_id="lot-7",
    )
    with pytest.raises(ValueError, match="tested and claimed exact identities must match"):
        _mechanism(identity=claimed, tested_identity=tested_grade)


def test_participant_sensitivity_remains_separate_from_assay_hypotheses() -> None:
    scope = _biological_scope()
    identity = _exact_identity()
    observation = ParticipantSensitivityObservation(
        observation_id="participant-sensitivity-a",
        identity=identity,
        scope=scope,
        participant_id="participant-01",
        repeat_id="repeat-02",
        endpoint_id="three-alternative-task",
        endpoint_kind=BiologicalObservationEndpoint.DISCRIMINATION,
        observed_state="participant discriminated this condition in this repeat",
        provenance_refs=(
            _provenance(
                "participant-sensitivity",
                evidence_class=EvidenceClass.DIRECT_OBSERVATION,
                condition="bio-condition-a",
            ),
        ),
    )
    architecture = _biological_architecture(
        scope=scope,
        mechanisms=(_mechanism(identity=identity, scope=scope),),
        observations=(observation,),
    )
    packet = BiologicalSensitivityPlaneAdapter(architecture).to_plane_assessment()

    assay_claims = [
        claim for claim in packet.claims if claim.claim_key.startswith("biological.mechanism.")
    ]
    observed_claims = [
        claim
        for claim in packet.claims
        if claim.claim_key.startswith("biological.observed_participant.")
    ]
    assert len(assay_claims) == 1
    assert len(observed_claims) == 1
    assert observed_claims[0].authority_ceiling is AuthorityCeiling.EVIDENCE_LIMITED
    assert observation.interpolated is False
    assert all(
        flag is False
        for flag in (
            architecture.physical_authority,
            architecture.sensory_authority,
            architecture.hedonic_authority,
            architecture.perceptual_nonredundancy_authority,
            architecture.mixture_quality_authority,
            architecture.target_fit_authority,
            architecture.liking_authority,
            architecture.sensuality_authority,
            architecture.projection_authority,
            architecture.longevity_authority,
            architecture.safety_authority,
            architecture.release_authority,
        )
    )


def test_specific_anosmia_unknown_is_not_zero_and_promotions_are_tamper_rejected() -> None:
    mechanism = _mechanism(risk=CriterionValue.unknown("Prevalence unmeasured."))
    packet = BiologicalSensitivityPlaneAdapter(
        _biological_architecture(mechanisms=(mechanism,))
    ).to_plane_assessment()

    risk_criterion = next(
        criterion
        for criterion in packet.native_criteria
        if criterion.criterion_id == "specific_anosmia_risk_mechanism-a"
    )
    assert risk_criterion.value.value is None
    assert risk_criterion.value.state.value == "unknown"
    assert any(
        unknown.field_key == "biological.mechanism-a.specific_anosmia_risk"
        for unknown in packet.unknowns
    )

    tampered = mechanism.as_dict()
    tampered["target_fit_authority"] = True
    with pytest.raises(ValueError, match="remain false"):
        BiologicalMechanismHypothesis.from_dict(tampered)


def test_spatial_and_biological_packets_expose_downstream_holds() -> None:
    spatial_packet = SpatialPlaneAdapter(_spatial_architecture()).to_plane_assessment()
    spatial_fields = {unknown.field_key: unknown for unknown in spatial_packet.unknowns}
    assert "spatial.downstream.scalar_aesthetic_authority" in spatial_fields
    assert (
        "hold" in spatial_fields["spatial.downstream.scalar_aesthetic_authority"].reason.casefold()
    )
    assert "spatial.downstream.safety_release_authority" in spatial_fields

    biological_packet = BiologicalSensitivityPlaneAdapter(
        _biological_architecture()
    ).to_plane_assessment()
    biological_fields = {unknown.field_key: unknown for unknown in biological_packet.unknowns}
    assert "biological.downstream.universal_liking" in biological_fields
    assert "hold" in biological_fields["biological.downstream.universal_liking"].reason.casefold()
    assert "biological.downstream.safety_release" in biological_fields


@pytest.mark.parametrize(
    "record",
    [
        pytest.param(_spatial_scope(), id="spatial-scope"),
        pytest.param(_biological_scope(), id="biological-scope"),
    ],
)
def test_leaf_scope_decoders_reject_unknown_fields_and_wrong_versions(record: Any) -> None:
    record_type = type(record)
    unknown_field = record.as_dict()
    unknown_field["unexpected"] = "must fail closed"
    with pytest.raises(ValueError, match="closed schema"):
        record_type.from_dict(unknown_field)

    wrong_version = record.as_dict()
    wrong_version["schema_version"] = "future_or_stale_schema"
    with pytest.raises(ValueError, match="schema_version"):
        record_type.from_dict(wrong_version)


def test_biological_conflicting_evidence_is_retained_without_amplification() -> None:
    positive = _mechanism(
        "mechanism-positive",
        claim="OR-X response may be associated with higher task sensitivity.",
    )
    negative = _mechanism(
        "mechanism-negative",
        claim="OR-X response may be associated with lower task sensitivity.",
    )
    duplicate = BiologicalMechanismHypothesis.from_dict(positive.as_dict())
    architecture = _biological_architecture(
        mechanisms=(positive, negative, duplicate),
    )
    packet = BiologicalSensitivityPlaneAdapter(architecture).to_plane_assessment()

    mechanism_claims = [
        claim for claim in packet.claims if claim.claim_key.startswith("biological.mechanism.")
    ]
    assert len(mechanism_claims) == 2
    assert {claim.claim_value for claim in mechanism_claims} == {
        positive.sensitivity_claim_with_scope,
        negative.sensitivity_claim_with_scope,
    }
    conflict = next(
        item for item in packet.conflicts if item.claim_key.startswith("biological.mechanism.")
    )
    assert isinstance(conflict, PlaneConflict)
    assert len(conflict.alternatives) == 2


@pytest.mark.parametrize(
    ("changed", "value"),
    [
        ("subject", "study-subject: cohort b"),
        ("condition", "bio-condition-b"),
        ("assay", "genotype association task"),
        ("population", "cohort B"),
        ("matrix", "oil presentation"),
        ("concentration", "100 ppm w/w"),
        ("temporal", "30-minute endpoint"),
        ("protocol", "bio-protocol-v2"),
    ],
)
def test_biological_scope_mismatches_remain_separate(
    changed: str,
    value: str,
) -> None:
    baseline = _biological_scope()
    kwargs = {
        "subject": baseline.subject_scope,
        "material_identity_key": baseline.material_identity_key,
        "condition": baseline.condition_id,
        "assay": baseline.assay_task,
        "population": baseline.population_scope,
        "matrix": baseline.matrix_scope,
        "concentration": baseline.concentration_scope,
        "temporal": baseline.temporal_scope,
        "protocol": baseline.protocol_scope,
    }
    kwargs[changed] = value
    different = _biological_scope(**kwargs)
    baseline_architecture = _biological_architecture(
        assessment_id="biological-scope-baseline",
        scope=baseline,
    )
    different_architecture = _biological_architecture(
        assessment_id="biological-scope-different",
        scope=different,
        mechanisms=(_mechanism(scope=different),),
    )

    synthesis = synthesize_plane_assessments(
        (
            BiologicalSensitivityPlaneAdapter(baseline_architecture).to_plane_assessment(),
            BiologicalSensitivityPlaneAdapter(different_architecture).to_plane_assessment(),
        )
    )
    assert len({item.scope.key for item in synthesis.assessments}) == 2


def test_biological_serialization_hash_order_protocol_and_authority_are_stable() -> None:
    scope = _biological_scope()
    first = _mechanism("mechanism-a", scope=scope)
    second = _mechanism(
        "mechanism-b",
        scope=scope,
        receptor="OR-Y",
        genotype=None,
        claim="OR-Y response may be associated with task sensitivity.",
    )
    forward = _biological_architecture(
        scope=scope,
        mechanisms=(first, second),
    )
    reverse = _biological_architecture(
        scope=scope,
        mechanisms=(second, first),
    )

    assert forward.as_dict() == reverse.as_dict()
    assert forward.content_sha256 == reverse.content_sha256
    restored = BiologicalSensitivityArchitecture.from_dict(forward.as_dict())
    assert restored == forward
    assert restored.content_sha256 == forward.content_sha256
    adapter = BiologicalSensitivityPlaneAdapter(forward)
    assert isinstance(adapter, PlaneAssessmentAdapter)
    packet = adapter.to_plane_assessment()
    assert PlaneAssessment.from_dict(packet.as_dict()) == packet
    assert packet.authority_ceiling is AuthorityCeiling.EVIDENCE_LIMITED
    assert all(
        claim.authority_ceiling.rank <= packet.authority_ceiling.rank for claim in packet.claims
    )
    with pytest.raises(FrozenInstanceError):
        forward.assessment_id = "changed"  # type: ignore[misc]


def test_modules_do_not_import_synthesis_runtime() -> None:
    import engine.formulation_intelligence.biological_sensitivity as biological
    import engine.formulation_intelligence.spatial_architecture as spatial

    assert "plane_synthesis" not in spatial.__dict__
    assert "plane_synthesis" not in biological.__dict__
