from __future__ import annotations

import json
from itertools import permutations

import pytest

from engine.formulation_intelligence import (
    AssessmentScope,
    AuthorityCeiling,
    ClaimCardinality,
    ClaimKind,
    CriterionDirection,
    CriterionValue,
    EvidenceClass,
    ParetoCriterion,
    PlaneAssessment,
    PlaneConflict,
    PlaneId,
    PlaneSynthesisResult,
    ProvenanceRef,
    ScopedClaim,
    SupportInterval,
    SupportMeasure,
    UnknownFact,
    synthesize_plane_assessments,
)


def _scope(
    *,
    target: str = "Target:CYP-02",
    temporal: str = "30 min",
    matrix: str = "20% EdP in ethanol",
) -> AssessmentScope:
    return AssessmentScope(
        target_scope=target,
        temporal_scope=temporal,
        matrix_scope=matrix,
    )


def _provenance(
    provenance_id: str,
    *,
    evidence_class: EvidenceClass = EvidenceClass.HEURISTIC,
    independence_key: str = "method:generic-design-review-v1",
) -> ProvenanceRef:
    return ProvenanceRef(
        provenance_id=provenance_id,
        source_ref=f"module://{provenance_id}",
        evidence_class=evidence_class,
        independence_key=independence_key,
    )


def _assessment(
    assessment_id: str,
    *,
    module_id: str,
    plane_id: PlaneId,
    claim_value: str = "magnolia-orris dual register",
    scope: AssessmentScope | None = None,
    lower: float = 0.35,
    upper: float = 0.65,
    authority: AuthorityCeiling = AuthorityCeiling.DESIGN_ONLY,
    provenance: ProvenanceRef | None = None,
    criterion: ParetoCriterion | None = None,
    unknowns: tuple[UnknownFact, ...] = (),
    conflicts: tuple[PlaneConflict, ...] = (),
) -> PlaneAssessment:
    source = provenance or _provenance(f"prov:{assessment_id}")
    claim = ScopedClaim(
        claim_id=f"claim:{assessment_id}",
        claim_key="heart.identity",
        claim_value=claim_value,
        claim_kind=ClaimKind.HYPOTHESIS,
        authority_ceiling=authority,
        provenance_refs=(source,),
    )
    support = SupportInterval(
        interval_id=f"support:{assessment_id}",
        claim_id=claim.claim_id,
        lower=lower,
        upper=upper,
        provenance_refs=(source,),
    )
    return PlaneAssessment(
        assessment_id=assessment_id,
        module_id=module_id,
        plane_id=plane_id,
        scope=scope or _scope(),
        claims=(claim,),
        support_intervals=(support,),
        conflicts=conflicts,
        unknowns=unknowns,
        failure_modes=("generic floral-heart substitution",),
        proposed_experiments=("constant-total carrier-matched omission",),
        provenance_refs=(source,),
        authority_ceiling=authority,
        freshness_hashes=("a" * 64,),
        native_criteria=(criterion,) if criterion is not None else (),
    )


def test_scope_normalization_and_nonblank_validation() -> None:
    scope = _scope(
        target="  TARGET:CYP-02  ",
        temporal="  30   MIN ",
        matrix="  20% EdP   IN Ethanol ",
    )

    assert scope.as_dict() == {
        "schema_version": "assessment_scope_v1",
        "target_scope": "target:cyp-02",
        "temporal_scope": "30 min",
        "matrix_scope": "20% edp in ethanol",
    }
    assert len(PlaneId) == 13
    assert PlaneId.RELATION.value == "relation"
    assert PlaneId.BIOLOGICAL_SENSITIVITY.value == "biological_sensitivity"
    with pytest.raises(ValueError, match="target_scope"):
        AssessmentScope(" ", "30 min", "ethanol")


def test_support_bounds_and_unknown_are_not_zero() -> None:
    source = _provenance("prov:bounds")
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        SupportInterval("bad", "claim", -0.01, 0.5, (source,))
    with pytest.raises(ValueError, match="must not exceed"):
        SupportInterval("bad", "claim", 0.7, 0.6, (source,))

    zero = CriterionValue.known(0.0)
    unknown = CriterionValue.unknown("no scoped observation")

    assert zero.as_dict()["state"] == "known"
    assert zero.as_dict()["value"] == 0.0
    assert unknown.as_dict()["state"] == "unknown"
    assert unknown.as_dict()["value"] is None
    assert unknown != zero


def test_deterministic_dict_hash_and_round_trip_like_reconstruction() -> None:
    criterion = ParetoCriterion(
        criterion_id="transition_continuity",
        direction=CriterionDirection.MAXIMIZE,
        value=CriterionValue.known(0.0),
        unit="declared native scale",
        authority_ceiling=AuthorityCeiling.DESIGN_ONLY,
        provenance_refs=(_provenance("prov:criterion"),),
    )
    assessments = (
        _assessment(
            "morphology",
            module_id="floral-lattice",
            plane_id=PlaneId.MORPHOLOGY,
            criterion=criterion,
        ),
        _assessment(
            "temporal",
            module_id="temporal-architecture",
            plane_id=PlaneId.TEMPORAL,
            provenance=_provenance("prov:temporal"),
        ),
    )

    result = synthesize_plane_assessments(assessments)
    encoded = json.dumps(result.as_dict(), sort_keys=True)
    restored = PlaneSynthesisResult.from_dict(json.loads(encoded))

    assert restored == result
    assert restored.as_dict() == result.as_dict()
    assert restored.content_sha256 == result.content_sha256
    assert len(result.content_sha256) == 64
    assert result.native_criteria[0].criterion.value.value == 0.0
    assert {item.provenance_id for item in result.provenance_refs} >= {
        "prov:criterion",
        "prov:morphology",
        "prov:temporal",
    }


def test_scope_mismatch_never_merges() -> None:
    ethanol = _assessment(
        "ethanol",
        module_id="mixture-plane",
        plane_id=PlaneId.MIXTURE,
        scope=_scope(matrix="20% EdP in ethanol"),
    )
    oil = _assessment(
        "oil",
        module_id="mixture-plane",
        plane_id=PlaneId.MIXTURE,
        scope=_scope(matrix="oil concentrate"),
    )

    result = synthesize_plane_assessments((ethanol, oil))

    assert len(result.harmonized_claims) == 2
    assert {item.scope.matrix_scope for item in result.harmonized_claims} == {
        "20% edp in ethanol",
        "oil concentrate",
    }


def test_duplicate_module_and_heuristic_repetition_do_not_amplify_support() -> None:
    direct = _assessment(
        "direct",
        module_id="direct-review",
        plane_id=PlaneId.EVIDENCE_AUTHORITY,
        lower=0.4,
        upper=0.7,
        provenance=_provenance(
            "prov:direct",
            evidence_class=EvidenceClass.DIRECT_OBSERVATION,
            independence_key="study:exact-scope-a",
        ),
        authority=AuthorityCeiling.EVIDENCE_LIMITED,
    )
    baseline = synthesize_plane_assessments((direct,))
    repeated = tuple(
        _assessment(
            f"heuristic-{index}",
            module_id="same-heuristic-module",
            plane_id=PlaneId.MORPHOLOGY,
            lower=0.9,
            upper=0.99,
            provenance=_provenance(
                f"prov:heuristic-{index}",
                evidence_class=EvidenceClass.HEURISTIC,
                independence_key="method:repeated-heuristic-v1",
            ),
        )
        for index in range(3)
    )

    result = synthesize_plane_assessments((direct, *repeated, repeated[0]))

    assert baseline.harmonized_claims[0].conservative_support is None
    assert result.harmonized_claims[0].conservative_support is None
    expected_support = {
        interval.content_sha256
        for assessment in (direct, *repeated)
        for interval in assessment.support_intervals
    }
    assert {
        interval.content_sha256
        for interval in result.harmonized_claims[0].support_intervals
    } == expected_support
    assert result.harmonized_claims[0].module_ids == (
        "direct-review",
        "same-heuristic-module",
    )
    assert len(result.assessments) == 4  # exact duplicate input is canonicalized once


def test_exact_scope_conflicts_are_preserved_not_voted_away() -> None:
    dual = _assessment(
        "dual-register",
        module_id="floral-lattice",
        plane_id=PlaneId.MORPHOLOGY,
        claim_value="magnolia-orris dual register",
    )
    generic = _assessment(
        "generic-heart",
        module_id="independent-critic",
        plane_id=PlaneId.IDENTITY,
        claim_value="generic floral heart",
        provenance=_provenance(
            "prov:critic",
            evidence_class=EvidenceClass.DIRECT_OBSERVATION,
            independence_key="study:critic-a",
        ),
    )

    result = synthesize_plane_assessments((dual, dual, dual, generic))
    restored = PlaneSynthesisResult.from_dict(result.as_dict())

    assert not result.harmonized_claims
    assert len(result.conflicts) == 1
    assert result.conflicts[0].alternatives == (
        "generic floral heart",
        "magnolia-orris dual register",
    )
    assert result.conflicts[0].claim_key == "heart.identity"
    assert restored.conflicts == result.conflicts


def test_explicit_unknowns_and_conflicts_survive_synthesis() -> None:
    source = _provenance("prov:unknown")
    unknown = UnknownFact(
        unknown_id="unknown:continuity",
        field_key="temporal.subject_continuity",
        reason="no participant-linked temporal observation",
        needed_evidence="blinded time-resolved observation",
        provenance_refs=(source,),
    )
    explicit_conflict = PlaneConflict(
        conflict_id="conflict:matrix",
        claim_key="mixture.baseline",
        alternatives=("dominance", "weighted-component"),
        reason="both baselines remain plausible",
        claim_ids=(),
        provenance_refs=(source,),
    )
    criterion = ParetoCriterion(
        criterion_id="target_fidelity",
        direction=CriterionDirection.MAXIMIZE,
        value=CriterionValue.unknown("not observed"),
        unit="participant-linked rating",
        authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
        provenance_refs=(source,),
    )
    assessment = _assessment(
        "unknowns",
        module_id="temporal-plane",
        plane_id=PlaneId.TEMPORAL,
        authority=AuthorityCeiling.STRUCTURAL_ONLY,
        provenance=source,
        criterion=criterion,
        unknowns=(unknown,),
        conflicts=(explicit_conflict,),
    )

    result = synthesize_plane_assessments((assessment,))

    assert result.unknowns[0].unknown.reason == unknown.reason
    assert result.native_criteria[0].criterion.value.state.value == "unknown"
    assert result.native_criteria[0].criterion.value.value is None
    assert result.conflicts[0].explicit_conflict_ids == ("conflict:matrix",)


def test_authority_is_monotone_and_claim_cannot_exceed_its_plane() -> None:
    design = _assessment(
        "design",
        module_id="design-plane",
        plane_id=PlaneId.FUNCTION,
        authority=AuthorityCeiling.DESIGN_ONLY,
    )
    structural = _assessment(
        "structural",
        module_id="structure-plane",
        plane_id=PlaneId.EVIDENCE_AUTHORITY,
        authority=AuthorityCeiling.STRUCTURAL_ONLY,
    )

    result = synthesize_plane_assessments(
        (design, structural),
        authority_ceiling=AuthorityCeiling.EVIDENCE_LIMITED,
    )

    assert result.authority_ceiling is AuthorityCeiling.STRUCTURAL_ONLY
    assert result.harmonized_claims[0].authority_ceiling is AuthorityCeiling.STRUCTURAL_ONLY
    assert result.formula_generation_authorized is False
    assert result.formula_mutation_authorized is False
    assert result.physical_execution_authorized is False
    assert result.pass_fail_authority is False
    assert result.sensory_authority is False
    assert result.beauty_authority is False
    assert result.hedonic_score_authorized is False
    assert result.safety_authority is False
    assert result.release_authority is False

    source = _provenance(
        "prov:invalid-authority",
        evidence_class=EvidenceClass.DIRECT_OBSERVATION,
    )
    overclaim = ScopedClaim(
        claim_id="claim:overclaim",
        claim_key="target.identity",
        claim_value="observed",
        claim_kind=ClaimKind.OBSERVATION,
        authority_ceiling=AuthorityCeiling.EVIDENCE_LIMITED,
        provenance_refs=(source,),
    )
    with pytest.raises(ValueError, match="exceeds assessment authority"):
        PlaneAssessment(
            assessment_id="overclaim",
            module_id="bad-module",
            plane_id=PlaneId.IDENTITY,
            scope=_scope(),
            claims=(overclaim,),
            support_intervals=(),
            conflicts=(),
            unknowns=(),
            failure_modes=(),
            proposed_experiments=(),
            provenance_refs=(source,),
            authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
            freshness_hashes=(),
            native_criteria=(),
        )


def test_from_dict_schemas_are_closed_and_require_every_declared_field() -> None:
    assessment = _assessment(
        "closed-schema",
        module_id="module:closed-schema",
        plane_id=PlaneId.IDENTITY,
    )

    with_extra = assessment.as_dict()
    with_extra["unexpected"] = "must fail closed"
    with pytest.raises(ValueError, match="closed schema"):
        PlaneAssessment.from_dict(with_extra)

    with_missing = assessment.as_dict()
    del with_missing["failure_modes"]
    with pytest.raises(ValueError, match="closed schema"):
        PlaneAssessment.from_dict(with_missing)


def test_harmonized_members_preserve_claim_cardinality_and_uncombined_support() -> None:
    first = _assessment(
        "member-a",
        module_id="module:member-a",
        plane_id=PlaneId.IDENTITY,
    )
    second = _assessment(
        "member-b",
        module_id="module:member-b",
        plane_id=PlaneId.IDENTITY,
    )

    result = synthesize_plane_assessments((first, second))
    harmonized = result.harmonized_claims[0]

    assert tuple(
        (
            member.assessment_id,
            member.claim_id,
            tuple(interval.interval_id for interval in member.support_intervals),
        )
        for member in harmonized.members
    ) == (
        ("member-a", "claim:member-a", ("support:member-a",)),
        ("member-b", "claim:member-b", ("support:member-b",)),
    )
    assert harmonized.conservative_support is None


def test_collection_members_do_not_self_conflict_and_order_is_preserved() -> None:
    source = _provenance("prov:collection")
    claims = (
        ScopedClaim(
            claim_id="claim:family:floral",
            claim_key="family_neighborhood",
            claim_value="floral",
            claim_kind=ClaimKind.REQUIREMENT,
            authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
            provenance_refs=(source,),
            cardinality=ClaimCardinality.SET_MEMBER,
            member_id="family:floral",
        ),
        ScopedClaim(
            claim_id="claim:family:chypre",
            claim_key="family_neighborhood",
            claim_value="chypre",
            claim_kind=ClaimKind.REQUIREMENT,
            authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
            provenance_refs=(source,),
            cardinality=ClaimCardinality.SET_MEMBER,
            member_id="family:chypre",
        ),
        ScopedClaim(
            claim_id="claim:reference:primary",
            claim_key="named_reference",
            claim_value="primary reference",
            claim_kind=ClaimKind.REQUIREMENT,
            authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
            provenance_refs=(source,),
            cardinality=ClaimCardinality.ORDERED_MEMBER,
            member_id="reference:primary",
            order_index=0,
        ),
        ScopedClaim(
            claim_id="claim:reference:secondary",
            claim_key="named_reference",
            claim_value="secondary reference",
            claim_kind=ClaimKind.REQUIREMENT,
            authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
            provenance_refs=(source,),
            cardinality=ClaimCardinality.ORDERED_MEMBER,
            member_id="reference:secondary",
            order_index=1,
        ),
    )
    assessment = PlaneAssessment(
        assessment_id="assessment:collection",
        module_id="target-compiler",
        plane_id=PlaneId.IDENTITY,
        scope=_scope(),
        claims=claims,
        support_intervals=(),
        conflicts=(),
        unknowns=(),
        failure_modes=(),
        proposed_experiments=(),
        provenance_refs=(source,),
        authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
        freshness_hashes=(),
        native_criteria=(),
    )

    result = synthesize_plane_assessments((assessment,))

    assert result.conflicts == ()
    assert len(result.harmonized_claims) == 4
    ordered = sorted(
        (
            claim.members[0].claim.order_index,
            claim.claim_value,
        )
        for claim in result.harmonized_claims
        if claim.members[0].claim.cardinality is ClaimCardinality.ORDERED_MEMBER
    )
    assert ordered == [(0, "primary reference"), (1, "secondary reference")]


def test_support_measures_round_trip_without_cross_measure_combination() -> None:
    source = _provenance("prov:support-measure")
    interval = SupportInterval(
        interval_id="support:declaration",
        claim_id="claim:declaration",
        lower=1.0,
        upper=1.0,
        provenance_refs=(source,),
        support_measure=SupportMeasure.DECLARATION_PRESENCE,
    )

    rebuilt = SupportInterval.from_dict(interval.as_dict())

    assert rebuilt.support_measure is SupportMeasure.DECLARATION_PRESENCE
    assert rebuilt == interval


def test_generic_contract_rejects_fake_observation_and_certain_evidence() -> None:
    heuristic = _provenance("prov:fake-observation")
    fake_observation = ScopedClaim(
        claim_id="claim:fake-observation",
        claim_key="sensory.observation",
        claim_value="smells proven",
        claim_kind=ClaimKind.OBSERVATION,
        authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
        provenance_refs=(heuristic,),
    )
    with pytest.raises(ValueError, match="observation-eligible provenance"):
        PlaneAssessment(
            assessment_id="assessment:fake-observation",
            module_id="module:fake-observation",
            plane_id=PlaneId.HEDONIC,
            scope=_scope(),
            claims=(fake_observation,),
            support_intervals=(),
            conflicts=(),
            unknowns=(),
            failure_modes=(),
            proposed_experiments=(),
            provenance_refs=(heuristic,),
            authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
            freshness_hashes=(),
            native_criteria=(),
        )

    with pytest.raises(ValueError, match="cannot declare unqualified"):
        SupportInterval(
            interval_id="support:fake-certainty",
            claim_id="claim:fake-observation",
            lower=1.0,
            upper=1.0,
            provenance_refs=(heuristic,),
            support_measure=SupportMeasure.EVIDENCE_SUPPORT,
        )


def test_evidence_limited_assessment_requires_qualifying_provenance() -> None:
    with pytest.raises(ValueError, match="requires qualifying evidence"):
        _assessment(
            "unsupported-evidence-ceiling",
            module_id="module:unsupported-evidence-ceiling",
            plane_id=PlaneId.EVIDENCE_AUTHORITY,
            authority=AuthorityCeiling.EVIDENCE_LIMITED,
            provenance=_provenance("prov:heuristic-only"),
        )


def test_ordered_collection_reordering_is_one_explicit_conflict() -> None:
    source = _provenance("prov:ordered-conflict")

    def assessment(
        assessment_id: str,
        ordered_values: tuple[tuple[str, str], ...],
    ) -> PlaneAssessment:
        return PlaneAssessment(
            assessment_id=assessment_id,
            module_id=f"module:{assessment_id}",
            plane_id=PlaneId.IDENTITY,
            scope=_scope(),
            claims=tuple(
                ScopedClaim(
                    claim_id=f"claim:{assessment_id}:{member_id}",
                    claim_key="named_reference",
                    claim_value=value,
                    claim_kind=ClaimKind.REQUIREMENT,
                    authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
                    provenance_refs=(source,),
                    cardinality=ClaimCardinality.ORDERED_MEMBER,
                    member_id=member_id,
                    order_index=index,
                )
                for index, (member_id, value) in enumerate(ordered_values)
            ),
            support_intervals=(),
            conflicts=(),
            unknowns=(),
            failure_modes=(),
            proposed_experiments=(),
            provenance_refs=(source,),
            authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
            freshness_hashes=(),
            native_criteria=(),
        )

    first = assessment(
        "ordered-first",
        (("reference-primary", "primary"), ("reference-secondary", "secondary")),
    )
    reversed_order = assessment(
        "ordered-reversed",
        (("reference-secondary", "secondary"), ("reference-primary", "primary")),
    )

    forward = synthesize_plane_assessments((first, reversed_order))
    reverse = synthesize_plane_assessments((reversed_order, first))

    assert len(forward.conflicts) == 1
    assert forward.conflicts[0].claim_key == "named_reference"
    assert "ordered collection" in forward.conflicts[0].reason
    assert not any(
        claim.members[0].claim.cardinality is ClaimCardinality.ORDERED_MEMBER
        for claim in forward.harmonized_claims
    )
    assert forward.as_dict() == reverse.as_dict()
    assert PlaneSynthesisResult.from_dict(forward.as_dict()) == forward


def test_breaking_nested_contracts_have_new_outer_receipt_versions() -> None:
    assessment = _assessment(
        "schema-successor",
        module_id="module:schema-successor",
        plane_id=PlaneId.IDENTITY,
    )
    result = synthesize_plane_assessments((assessment,))

    assert assessment.SCHEMA_VERSION == "plane_assessment_v2"
    assert result.SCHEMA_VERSION == "plane_synthesis_result_v2"
    assert result.harmonized_claims[0].SCHEMA_VERSION == "harmonized_plane_claim_v2"

    historical_assessment = assessment.as_dict()
    historical_assessment["schema_version"] = "plane_assessment_v1"
    with pytest.raises(ValueError, match="schema_version must be"):
        PlaneAssessment.from_dict(historical_assessment)

    historical_result = result.as_dict()
    historical_result["schema_version"] = "plane_synthesis_result_v1"
    with pytest.raises(ValueError, match="schema_version must be"):
        PlaneSynthesisResult.from_dict(historical_result)


@pytest.mark.parametrize("left", tuple(AuthorityCeiling))
@pytest.mark.parametrize("right", tuple(AuthorityCeiling))
def test_authority_meet_is_explicit_commutative_and_non_promoting(
    left: AuthorityCeiling,
    right: AuthorityCeiling,
) -> None:
    forward = AuthorityCeiling.minimum((left, right))
    reverse = AuthorityCeiling.minimum((right, left))

    assert forward is reverse
    assert forward.rank <= left.rank
    assert forward.rank <= right.rank


def test_derived_receipt_rejects_forged_nested_members_ids_and_authority() -> None:
    result = synthesize_plane_assessments(
        (
            _assessment(
                "receipt",
                module_id="module:receipt",
                plane_id=PlaneId.IDENTITY,
            ),
        )
    )

    forged_member = result.as_dict()
    forged_member["harmonized_claims"][0]["source_claim_ids"] = ["claim:forged"]
    with pytest.raises(ValueError, match="canonical"):
        type(result).from_dict(forged_member)

    forged_id = result.as_dict()
    forged_id["harmonized_claims"][0]["harmonized_id"] = "harmonized:forged"
    with pytest.raises(ValueError, match="canonical"):
        type(result).from_dict(forged_id)

    raised_authority = result.as_dict()
    raised_authority["harmonized_claims"][0]["authority_ceiling"] = (
        AuthorityCeiling.EVIDENCE_LIMITED.value
    )
    with pytest.raises(ValueError, match="canonical|authority"):
        type(result).from_dict(raised_authority)


def test_assessment_input_order_is_fully_invariant() -> None:
    assessments = (
        _assessment(
            "identity",
            module_id="identity-plane",
            plane_id=PlaneId.IDENTITY,
        ),
        _assessment(
            "spatial",
            module_id="spatial-plane",
            plane_id=PlaneId.SPATIAL_COMPOSITION,
        ),
        _assessment(
            "experiment",
            module_id="experiment-plane",
            plane_id=PlaneId.EXPERIMENT,
        ),
    )
    reference = synthesize_plane_assessments(assessments)

    for permuted in permutations(assessments):
        candidate = synthesize_plane_assessments(permuted)
        assert candidate.as_dict() == reference.as_dict()
        assert candidate.content_sha256 == reference.content_sha256
