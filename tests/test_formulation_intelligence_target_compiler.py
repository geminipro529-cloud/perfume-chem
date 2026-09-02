from __future__ import annotations

from dataclasses import replace

import pytest

from engine.formulation_intelligence.contracts import (
    AuthorityCeiling,
    ClaimCardinality,
    EvidenceClass,
    PlaneId,
    ProvenanceRef,
)
from engine.formulation_intelligence.plane_synthesis import synthesize_plane_assessments
from engine.formulation_intelligence.target_compiler import (
    AbstractionLevel,
    ReferenceEvidenceTier,
    TargetAcceptance,
    TargetAcceptanceState,
    TargetAuthorityFlags,
    TargetBranch,
    TargetBrief,
    TargetConflict,
    TargetEvidenceRef,
    TargetIntent,
    TargetMode,
    TargetRequestSource,
    TargetResolution,
    TargetSourceSpan,
    TargetUnknown,
    TemporalTransformation,
    compile_target_intent,
    create_build_projection_id,
)


def _brief_provenance() -> ProvenanceRef:
    return ProvenanceRef(
        provenance_id="user-brief-20260831",
        source_ref="current user target brief",
        evidence_class=EvidenceClass.USER_REPORT,
        independence_key="user-brief-20260831",
    )


def _reference_provenance() -> ProvenanceRef:
    return ProvenanceRef(
        provenance_id="reference-description-20260831",
        source_ref="https://example.invalid/reference-description",
        evidence_class=EvidenceClass.PRIMARY_SOURCE,
        independence_key="reference-description-20260831",
        source_sha256="d" * 64,
    )


def _reference_evidence() -> TargetEvidenceRef:
    return TargetEvidenceRef(
        evidence_id="reference-public-description",
        source_ref="https://example.invalid/reference-description",
        tier=ReferenceEvidenceTier.STRUCTURAL_DESCRIPTION,
        claim_scope="public descriptive reference only; no formula or headspace",
        source_sha256="d" * 64,
        claim_keys=("named_reference", "protected_recognizer"),
        provenance_refs=(_reference_provenance(),),
    )


def _request_source(raw_request: str = "Build a recognizable dry Aventus architecture.") -> TargetRequestSource:
    return TargetRequestSource(
        raw_request=raw_request,
        source_ref="codex://current-user-turn/20260831",
        source_sha256="c" * 64,
        span=TargetSourceSpan(start_char=120, end_char=120 + len(raw_request)),
        origin="direct user request",
    )


def _accepted_branch() -> TargetBranch:
    return TargetBranch(
        branch_id="dry-reference-architecture",
        interpretation="recognizable dry reference architecture, not a literal clone",
        claim_keys=("target_identity", "named_reference", "protected_recognizer"),
        evidence_ids=(),
    )


def _acceptance(*branch_ids: str) -> TargetAcceptance:
    return TargetAcceptance(
        acceptance_id="user-acceptance-20260831",
        state=TargetAcceptanceState.ACCEPTED,
        accepted_branch_ids=branch_ids,
        decision_basis="the user explicitly accepted this interpretation branch",
        provenance_refs=(_brief_provenance(),),
    )


def _complete_named_brief() -> TargetBrief:
    return TargetBrief(
        request_id="Aventus Architecture 01",
        mode=TargetMode.NAMED_REFERENCE,
        subject="Creed Aventus Reference Architecture",
        named_references=("Creed Aventus",),
        family_neighborhoods=("Fruity Chypre", "Woody Chypre"),
        abstraction_level=AbstractionLevel.RECOGNIZABLE_ABSTRACTION,
        expression_terms=("dry mineral woods", "fruit-to-smoke transition"),
        exclusions=("wet pineapple foreground", "anonymous amber drydown"),
        protected_recognizers=(
            "fruit-to-dry-wood continuity",
            "smoke/leather transition",
        ),
        forbidden_drift=("generic woody amber", "citrus cleaner"),
        transformations=(
            TemporalTransformation(
                transformation_id="fruit-to-smoke",
                source_state="dry fruit lift",
                destination_state="smoke leather bridge",
                temporal_window="opening-to-heart",
                continuity_requirement="fruit subject remains traceable",
            ),
        ),
        temporal_requests=("opening", "heart", "drydown"),
        matrix_context="ethanol fragrance matrix; exact concentration unresolved",
        criterion_vocabulary=(
            "target fidelity",
            "transition continuity",
            "recognizer integrity",
        ),
        reference_evidence=(_reference_evidence(),),
        provenance_refs=(_brief_provenance(),),
        request_source=_request_source(),
        branches=(_accepted_branch(),),
        conflicts=(),
        unknowns=(),
        acceptance=_acceptance("dry-reference-architecture"),
    )


def test_named_reference_compiles_deterministically_without_generic_flattening() -> None:
    first = compile_target_intent(_complete_named_brief())
    reordered = compile_target_intent(
        replace(
            _complete_named_brief(),
            request_id="  aventus   architecture 01 ",
            subject="CREED AVENTUS REFERENCE ARCHITECTURE",
            named_references=("creed aventus",),
            family_neighborhoods=("woody chypre", "FRUITY CHYPRE"),
            expression_terms=("FRUIT-TO-SMOKE TRANSITION", "dry mineral woods"),
            exclusions=("anonymous amber drydown", "WET PINEAPPLE FOREGROUND"),
            protected_recognizers=(
                "SMOKE/LEATHER TRANSITION",
                "fruit-to-dry-wood continuity",
            ),
            forbidden_drift=("CITRUS CLEANER", "generic woody amber"),
            temporal_requests=("drydown", "HEART", "opening"),
            criterion_vocabulary=(
                "recognizer integrity",
                "TARGET FIDELITY",
                "transition continuity",
            ),
        )
    )

    assert first == reordered
    assert first.content_sha256 == reordered.content_sha256
    assert first.resolution is TargetResolution.RESOLVED_FOR_DESIGN
    assert first.mode is TargetMode.NAMED_REFERENCE
    assert first.named_references == ("creed aventus",)
    assert first.family_neighborhoods == ("fruity chypre", "woody chypre")
    assert "generic" not in first.as_dict().values()
    assert not first.unresolved_fields


@pytest.mark.parametrize(
    ("mode", "subject", "references", "expressions", "expected_missing"),
    [
        (
            TargetMode.NAMED_REFERENCE,
            "explicit reference request",
            (),
            (),
            ("named_references",),
        ),
        (TargetMode.CONCEPT_ONLY, None, (), (), ("target_identity",)),
        (
            TargetMode.HYBRID,
            "hybrid request",
            ("named reference",),
            (),
            ("expression_terms",),
        ),
        (
            TargetMode.FAMILY_ARCHITECTURE,
            "family request",
            (),
            ("transparent",),
            ("family_neighborhoods",),
        ),
    ],
)
def test_explicit_or_sparse_briefs_fail_closed(
    mode: TargetMode,
    subject: str | None,
    references: tuple[str, ...],
    expressions: tuple[str, ...],
    expected_missing: tuple[str, ...],
) -> None:
    brief = TargetBrief(
        request_id="incomplete explicit brief",
        mode=mode,
        subject=subject,
        named_references=references,
        family_neighborhoods=(),
        abstraction_level=AbstractionLevel.UNSPECIFIED,
        expression_terms=expressions,
        exclusions=(),
        protected_recognizers=(),
        forbidden_drift=(),
        transformations=(),
        temporal_requests=(),
        matrix_context=None,
        criterion_vocabulary=(),
        reference_evidence=(),
        provenance_refs=(_brief_provenance(),),
    )

    intent = compile_target_intent(brief)

    assert intent.resolution is not TargetResolution.RESOLVED_FOR_DESIGN
    assert set(expected_missing).issubset(intent.unresolved_fields)
    assert "generic" not in intent.family_neighborhoods
    assert "not requested" not in intent.as_dict().values()
    assert intent.authority_flags == TargetAuthorityFlags()


def test_concept_and_hybrid_modes_remain_distinct() -> None:
    concept = compile_target_intent(
        replace(
            _complete_named_brief(),
            request_id="glass magnolia",
            mode=TargetMode.CONCEPT_ONLY,
            subject="Magnolia de Verre",
            named_references=(),
            reference_evidence=(),
            expression_terms=("transparent magnolia", "cool mineral air"),
        )
    )
    hybrid = compile_target_intent(
        replace(
            _complete_named_brief(),
            request_id="aventus adjacent",
            mode=TargetMode.HYBRID,
            subject="Thai Aventus-adjacent study",
            expression_terms=("humid fruit", "dry smoke transition"),
        )
    )

    assert concept.mode is TargetMode.CONCEPT_ONLY
    assert concept.named_references == ()
    assert hybrid.mode is TargetMode.HYBRID
    assert hybrid.named_references == ("creed aventus",)
    assert concept.ideal_target_id != hybrid.ideal_target_id


def test_inventory_projection_cannot_mutate_ideal_target_identity() -> None:
    intent = compile_target_intent(_complete_named_brief())
    inventory_a = create_build_projection_id(
        intent,
        inventory_content_sha256="a" * 64,
        stock_authority_snapshot_id="inventory-authority-20260831-a",
        projection_variant="current inventory build",
    )
    inventory_b = create_build_projection_id(
        intent,
        inventory_content_sha256="b" * 64,
        stock_authority_snapshot_id="inventory-authority-20260831-b",
        projection_variant="current inventory build",
    )

    assert inventory_a.ideal_target_id == intent.ideal_target_id
    assert inventory_b.ideal_target_id == intent.ideal_target_id
    assert inventory_a != inventory_b
    assert inventory_a.projection_id != inventory_b.projection_id
    assert inventory_a.authority_flags == TargetAuthorityFlags()
    assert inventory_b.authority_flags == TargetAuthorityFlags()


def test_roundtrip_hash_and_plane_assessment_preserve_fail_closed_authority() -> None:
    intent = compile_target_intent(_complete_named_brief())
    restored = TargetIntent.from_dict(intent.as_dict())
    assessment = restored.to_plane_assessment()

    assert restored == intent
    assert restored.content_sha256 == intent.content_sha256
    assert assessment.plane_id is PlaneId.IDENTITY
    assert assessment.authority_ceiling is AuthorityCeiling.STRUCTURAL_ONLY
    assert assessment.target_scope == intent.ideal_target_id.value
    assert assessment.temporal_scope == "multi-window-request"
    assert assessment.matrix_scope == "ethanol-fragrance-matrix-exact-concentration-unresolved"
    assert not assessment.support_intervals
    assert all(
        criterion.value.value is None for criterion in assessment.native_criteria
    )
    assert all(
        criterion.value.reason is not None for criterion in assessment.native_criteria
    )


def test_target_output_contains_no_formula_material_or_dose_surface() -> None:
    payload = compile_target_intent(_complete_named_brief()).as_dict()
    serialized_keys = " ".join(_walk_keys(payload))

    for prohibited in (
        "formula",
        "ingredient",
        "material_selection",
        "dose",
        "ratio",
        "oav",
        "ppm",
        "compounding",
        "release_authorized",
    ):
        assert prohibited not in serialized_keys


def _walk_keys(value: object) -> tuple[str, ...]:
    if isinstance(value, dict):
        return tuple(
            key
            for item_key, item_value in value.items()
            for key in (str(item_key), *_walk_keys(item_value))
        )
    if isinstance(value, (list, tuple)):
        return tuple(key for item in value for key in _walk_keys(item))
    return ()


def test_authority_flags_cannot_be_promoted_by_caller() -> None:
    with pytest.raises(ValueError, match="cannot be promoted"):
        TargetAuthorityFlags(strict_similarity=True)


def test_exact_request_receipt_is_distinct_from_semantic_target_identity() -> None:
    first = compile_target_intent(_complete_named_brief())
    raw_variant = "  Build a recognizable dry Aventus architecture.  \n"
    second = compile_target_intent(
        replace(
            _complete_named_brief(),
            request_source=_request_source(raw_variant),
        )
    )

    assert first.request_source is not None
    assert second.request_source is not None
    assert first.request_source.raw_request == (
        "Build a recognizable dry Aventus architecture."
    )
    assert second.request_source.raw_request == raw_variant
    assert first.ideal_target_id == second.ideal_target_id
    assert first.semantic_target_sha256 == second.semantic_target_sha256
    assert first.receipt_sha256 != second.receipt_sha256


def test_unaccepted_conflicted_or_unknown_target_stays_on_hold() -> None:
    alternate = TargetBranch(
        branch_id="literal-clone",
        interpretation="literal reference clone",
        claim_keys=("target_identity", "named_reference"),
        evidence_ids=("reference-public-description",),
    )
    conflict = TargetConflict(
        conflict_id="abstraction-conflict",
        claim_key="abstraction_level",
        branch_ids=("dry-reference-architecture", "literal-clone"),
        reason="the source request does not adjudicate literal versus recognizable",
        evidence_ids=("reference-public-description",),
    )
    unknown = TargetUnknown(
        unknown_id="matrix-concentration",
        field_key="matrix_concentration",
        reason="the exact ethanol concentration was not supplied",
        needed_evidence="an exact concentration and concentration basis",
        critical=True,
        evidence_ids=(),
    )
    unaccepted = TargetAcceptance(
        acceptance_id="pending-user-acceptance",
        state=TargetAcceptanceState.UNACCEPTED,
        accepted_branch_ids=(),
        decision_basis="the interpretation is awaiting user acceptance",
        provenance_refs=(_brief_provenance(),),
    )

    intent = compile_target_intent(
        replace(
            _complete_named_brief(),
            branches=(_accepted_branch(), alternate),
            conflicts=(conflict,),
            unknowns=(unknown,),
            acceptance=unaccepted,
        )
    )
    assessment = intent.to_plane_assessment()

    assert intent.resolution is TargetResolution.UNRESOLVED_HOLD
    assert "target_acceptance" in intent.unresolved_fields
    assert "conflict:abstraction-conflict" in intent.unresolved_fields
    assert "unknown:matrix_concentration" in intent.unresolved_fields
    assert tuple(item.conflict_id for item in assessment.conflicts) == (
        "abstraction-conflict",
    )
    assert any(
        item.unknown_id == "matrix-concentration" for item in assessment.unknowns
    )


def test_accepted_branch_adjudicates_preserved_conflict_without_erasing_it() -> None:
    alternate = TargetBranch(
        branch_id="literal-clone",
        interpretation="literal reference clone",
        claim_keys=("target_identity", "named_reference"),
        evidence_ids=("reference-public-description",),
    )
    conflict = TargetConflict(
        conflict_id="abstraction-conflict",
        claim_key="abstraction_level",
        branch_ids=("dry-reference-architecture", "literal-clone"),
        reason="two source-grounded interpretations require adjudication",
        evidence_ids=("reference-public-description",),
    )
    intent = compile_target_intent(
        replace(
            _complete_named_brief(),
            branches=(_accepted_branch(), alternate),
            conflicts=(conflict,),
            acceptance=_acceptance("dry-reference-architecture"),
        )
    )

    assert intent.resolution is TargetResolution.RESOLVED_FOR_DESIGN
    assert intent.conflicts == (conflict,)
    assert intent.acceptance is not None
    assert intent.acceptance.accepted_branch_ids == (
        "dry-reference-architecture",
    )
    assert intent.to_plane_assessment().conflicts


def test_evidence_is_attached_only_to_its_declared_claim_keys() -> None:
    assessment = compile_target_intent(_complete_named_brief()).to_plane_assessment()

    evidence_provenance_id = _reference_provenance().provenance_id
    named_ids = {
        item.provenance_id
        for claim in assessment.claims
        if claim.claim_key == "named_reference"
        for item in claim.provenance_refs
    }
    exclusion_ids = {
        item.provenance_id
        for claim in assessment.claims
        if claim.claim_key == "exclusion"
        for item in claim.provenance_refs
    }

    assert evidence_provenance_id in named_ids
    assert evidence_provenance_id not in exclusion_ids


def test_collection_claims_keep_members_distinct_without_self_conflict() -> None:
    intent = compile_target_intent(
        replace(
            _complete_named_brief(),
            named_references=("Creed Aventus", "Montblanc Explorer"),
        )
    )
    assessment = intent.to_plane_assessment()
    named = tuple(
        claim for claim in assessment.claims if claim.claim_key == "named_reference"
    )

    assert [claim.cardinality for claim in named] == [
        ClaimCardinality.ORDERED_MEMBER,
        ClaimCardinality.ORDERED_MEMBER,
    ]
    assert [claim.order_index for claim in named] == [0, 1]
    assert len({claim.member_id for claim in named}) == 2
    assert not synthesize_plane_assessments((assessment,)).conflicts


def test_strict_schema_and_receipt_hash_reject_unknown_fields_and_tampering() -> None:
    intent = compile_target_intent(_complete_named_brief())

    unexpected = intent.as_dict()
    unexpected["unexpected"] = "not in target_intent_v2"
    with pytest.raises(ValueError, match="unexpected fields"):
        TargetIntent.from_dict(unexpected)

    missing_schema = intent.as_dict()
    del missing_schema["schema_version"]
    with pytest.raises(ValueError, match="schema_version"):
        TargetIntent.from_dict(missing_schema)

    tampered = intent.as_dict()
    source = tampered["request_source"]
    source["raw_request"] += "!"
    source["span"]["end_char"] += 1
    with pytest.raises(ValueError, match="receipt_sha256"):
        TargetIntent.from_dict(tampered)


def test_build_projection_roundtrip_is_strict_and_cannot_rebind_ideal() -> None:
    intent = compile_target_intent(_complete_named_brief())
    projection = create_build_projection_id(
        intent,
        inventory_content_sha256="a" * 64,
        stock_authority_snapshot_id="inventory-authority-20260831-a",
        projection_variant="current inventory build",
    )
    payload = projection.as_dict()
    payload["ideal_target_id"]["digest"] = "b" * 64

    with pytest.raises(ValueError, match="projection_id"):
        type(projection).from_dict(payload)
