from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, replace
from typing import Any

import pytest

from engine.formulation_intelligence.contracts import (
    AuthorityCeiling,
    ClaimCardinality,
    EvidenceClass,
    PlaneAssessment,
    PlaneId,
    ProvenanceRef,
    ScopedClaim,
)
from engine.formulation_intelligence.family_architecture import (
    FamilyArchitectureAdapter,
    FamilyArchitectureCatalog,
    FamilyArchitectureRequest,
    FamilyDefinition,
    FamilyDefinitionKind,
    FamilyDefinitionRef,
    FamilyPlane,
    FamilyRecognizer,
    FamilyResolution,
    FamilyResolutionStatus,
    FamilyTemporalRelation,
    ForbiddenFamilyDrift,
    UnsupportedFamilyDefinition,
)
from engine.formulation_intelligence.plane_synthesis import (
    synthesize_plane_assessments,
)


def _provenance(
    source: str = "family-source-a",
    *,
    evidence_class: EvidenceClass = EvidenceClass.PRIMARY_SOURCE,
) -> ProvenanceRef:
    return ProvenanceRef(
        provenance_id=source,
        source_ref=f"docs://{source}",
        evidence_class=evidence_class,
        independence_key=source,
        source_sha256="a" * 64,
    )


def _reference(
    family_id: str = "family:floral",
    version: str = "2026.1",
) -> FamilyDefinitionRef:
    return FamilyDefinitionRef(family_id=family_id, version=version)


def _definition(
    *,
    family_id: str = "family:floral",
    version: str = "2026.1",
    kind: FamilyDefinitionKind = FamilyDefinitionKind.REFERENCE,
    components: tuple[FamilyDefinitionRef, ...] = (),
    source: str = "family-source-a",
) -> FamilyDefinition:
    planes = (
        FamilyPlane(
            plane_id="opening",
            order_index=0,
            label="Opening identity",
            structural_function="Establish the target-specific opening identity.",
            temporal_window="opening through five minutes",
        ),
        FamilyPlane(
            plane_id="heart",
            order_index=1,
            label="Heart identity",
            structural_function="Carry the protected recognizers through the heart.",
            temporal_window="five minutes through two hours",
        ),
        FamilyPlane(
            plane_id="drydown",
            order_index=2,
            label="Drydown identity",
            structural_function="Resolve the target without generic base drift.",
            temporal_window="two hours onward",
        ),
    )
    recognizers = (
        FamilyRecognizer(
            recognizer_id="recognizer-floral-subject",
            label="Named floral subject remains legible",
            protected_function="Protect the requested subject rather than generic floralness.",
            plane_ids=("opening", "heart", "drydown"),
            absence_failure="The result becomes an unnamed floral neighborhood.",
        ),
        FamilyRecognizer(
            recognizer_id="recognizer-heart-continuity",
            label="Heart continuity",
            protected_function="Maintain a target-linked bridge into the heart.",
            plane_ids=("heart",),
            absence_failure="Opening and drydown read as disconnected fragments.",
        ),
    )
    drifts = (
        ForbiddenFamilyDrift(
            drift_id="drift-generic-clean-floral",
            description="Generic clean-floral substitution for the named subject.",
            conflict_with_target="It erases the subject-specific recognizer architecture.",
        ),
    )
    relations = (
        FamilyTemporalRelation(
            relation_id="relation-opening-heart",
            order_index=0,
            source_plane_id="opening",
            destination_plane_id="heart",
            relation_kind="handoff",
            continuity_requirement="The named subject remains traceable across the handoff.",
            failure_mode="The opening detaches from the floral heart.",
        ),
        FamilyTemporalRelation(
            relation_id="relation-heart-drydown",
            order_index=1,
            source_plane_id="heart",
            destination_plane_id="drydown",
            relation_kind="transformation",
            continuity_requirement="A protected recognizer survives into residue identity.",
            failure_mode="The drydown becomes a generic woody-musky endpoint.",
        ),
    )
    return FamilyDefinition(
        definition_ref=_reference(family_id, version),
        label=f"{family_id} definition",
        definition_kind=kind,
        component_definitions=components,
        architecture_planes=planes,
        protected_recognizers=recognizers,
        forbidden_drift=drifts,
        temporal_relations=relations,
        source_version="source-edition-2026",
        definition_evidence_class=EvidenceClass.PRIMARY_SOURCE,
        provenance_refs=(_provenance(source),),
    )


def _request(
    *,
    definition_ref: FamilyDefinitionRef | None = None,
    named_target: str = "target: night-blooming white floral",
    neighborhoods: tuple[FamilyDefinitionRef, ...] = (
        FamilyDefinitionRef("family:white-floral", "2026.1"),
        FamilyDefinitionRef("family:soft-floral", "2026.1"),
    ),
) -> FamilyArchitectureRequest:
    return FamilyArchitectureRequest(
        request_id="family-request-a",
        target_scope="ideal-target: night-blooming-white-floral:v1",
        named_target=named_target,
        requested_definition=definition_ref or _reference(),
        family_neighborhood=neighborhoods,
        temporal_scope="opening through drydown",
        matrix_scope="ideal-target architecture; no inventory mapping",
        provenance_refs=(_provenance("request-source", evidence_class=EvidenceClass.USER_REPORT),),
    )


def _catalog(
    *definitions: FamilyDefinition,
    unsupported: tuple[UnsupportedFamilyDefinition, ...] = (),
) -> FamilyArchitectureCatalog:
    values = definitions or (_definition(),)
    return FamilyArchitectureCatalog(
        catalog_id="family-catalog-2026",
        definitions=tuple(values),
        unsupported_definitions=unsupported,
    )


def test_exact_named_target_and_family_neighborhood_remain_distinct() -> None:
    request = _request()
    resolution = _catalog().resolve(request)

    assert resolution.status is FamilyResolutionStatus.RESOLVED
    assert resolution.named_target == "target: night-blooming white floral"
    assert resolution.definition is not None
    assert resolution.definition.definition_ref == _reference()
    assert resolution.family_neighborhood == request.family_neighborhood
    assert resolution.family_neighborhood != (resolution.definition.definition_ref,)

    packet = FamilyArchitectureAdapter(resolution).to_plane_assessment()
    assert packet.plane_id is PlaneId.IDENTITY
    assert packet.authority_ceiling is AuthorityCeiling.STRUCTURAL_ONLY
    by_key: dict[str, list[ScopedClaim]] = {}
    for claim in packet.claims:
        by_key.setdefault(claim.claim_key, []).append(claim)

    assert by_key["family.named_target"][0].cardinality is ClaimCardinality.SINGLE
    assert {
        claim.member_id for claim in by_key["family.neighborhood"]
    } == {
        "family-neighborhood-family-soft-floral-2026-1",
        "family-neighborhood-family-white-floral-2026-1",
    }
    assert all(
        claim.cardinality is ClaimCardinality.SET_MEMBER
        for claim in by_key["family.neighborhood"]
    )
    plane_order_indices = [
        claim.order_index for claim in by_key["family.architecture_plane"]
    ]
    assert all(index is not None for index in plane_order_indices)
    assert sorted(index for index in plane_order_indices if index is not None) == [
        0,
        1,
        2,
    ]
    assert all(
        claim.cardinality is ClaimCardinality.ORDERED_MEMBER
        for claim in by_key["family.architecture_plane"]
    )

    synthesis = synthesize_plane_assessments((packet,))
    assert synthesis.conflicts == ()


def test_definition_is_versioned_provenance_bound_and_strictly_round_trips() -> None:
    definition = _definition()
    payload = definition.as_dict()
    rebuilt = FamilyDefinition.from_dict(json.loads(json.dumps(payload)))

    assert rebuilt == definition
    assert rebuilt.content_sha256 == definition.content_sha256
    assert rebuilt.source_version == "source-edition-2026"
    assert rebuilt.definition_evidence_class is EvidenceClass.PRIMARY_SOURCE
    assert rebuilt.provenance_refs[0].source_sha256 == "a" * 64
    with pytest.raises(FrozenInstanceError):
        definition.label = "mutated"  # type: ignore[misc]

    invalid: dict[str, Any] = dict(payload)
    invalid["unexpected"] = True
    with pytest.raises(ValueError, match="closed schema"):
        FamilyDefinition.from_dict(invalid)

    request = _request()
    catalog = _catalog(definition)
    resolution = catalog.resolve(request)
    assert FamilyArchitectureRequest.from_dict(request.as_dict()) == request
    assert FamilyArchitectureCatalog.from_dict(catalog.as_dict()) == catalog
    assert FamilyResolution.from_dict(resolution.as_dict()) == resolution


def test_wrong_version_unknown_family_and_explicit_unsupported_fail_closed() -> None:
    definition = _definition()
    catalog = _catalog(
        definition,
        unsupported=(
            UnsupportedFamilyDefinition(
                definition_ref=_reference("family:leather", "2026.1"),
                reason="No source-bounded architecture has been admitted.",
                provenance_refs=(_provenance("unsupported-ledger"),),
            ),
        ),
    )

    wrong_version = catalog.resolve(
        _request(definition_ref=_reference("family:floral", "2099.1"))
    )
    unknown = catalog.resolve(
        _request(definition_ref=_reference("family:unknown-future-family", "1"))
    )
    unsupported = catalog.resolve(
        _request(definition_ref=_reference("family:leather", "2026.1"))
    )

    assert wrong_version.status is FamilyResolutionStatus.UNSUPPORTED_VERSION
    assert unknown.status is FamilyResolutionStatus.UNKNOWN_FAMILY
    assert unsupported.status is FamilyResolutionStatus.UNSUPPORTED_FAMILY
    for item in (wrong_version, unknown, unsupported):
        assert item.definition is None
        packet = FamilyArchitectureAdapter(item).to_plane_assessment()
        assert packet.authority_ceiling is AuthorityCeiling.WITHHELD
        assert packet.unknowns
        assert not any(
            claim.claim_key.startswith("family.architecture")
            for claim in packet.claims
        )
        assert packet.support_intervals == ()


def test_custom_and_hybrid_definitions_preserve_identity_without_flattening() -> None:
    floral = _definition()
    woody = _definition(family_id="family:woody")
    custom = _definition(
        family_id="custom:rain-on-warm-stone",
        kind=FamilyDefinitionKind.CUSTOM,
        source="custom-source",
    )
    hybrid_ref = _reference("hybrid:floral-woody-chiaroscuro")
    hybrid = _definition(
        family_id=hybrid_ref.family_id,
        kind=FamilyDefinitionKind.HYBRID,
        components=(floral.definition_ref, woody.definition_ref),
        source="hybrid-source",
    )
    catalog = _catalog(floral, woody, custom, hybrid)

    custom_result = catalog.resolve(_request(definition_ref=custom.definition_ref))
    hybrid_result = catalog.resolve(_request(definition_ref=hybrid_ref))

    assert custom_result.status is FamilyResolutionStatus.RESOLVED
    assert custom_result.definition is not None
    assert custom_result.definition.definition_kind is FamilyDefinitionKind.CUSTOM
    assert hybrid_result.status is FamilyResolutionStatus.RESOLVED
    assert hybrid_result.definition is not None
    assert hybrid_result.definition.definition_ref == hybrid_ref
    assert hybrid_result.definition.component_definitions == (
        floral.definition_ref,
        woody.definition_ref,
    )
    packet = FamilyArchitectureAdapter(hybrid_result).to_plane_assessment()
    component_claims = [
        claim for claim in packet.claims if claim.claim_key == "family.component_definition"
    ]
    assert {claim.claim_value for claim in component_claims} == {
        "family:floral@2026.1",
        "family:woody@2026.1",
    }
    assert all(
        claim.cardinality is ClaimCardinality.SET_MEMBER for claim in component_claims
    )


def test_hybrid_catalog_rejects_missing_components_and_reference_flattening() -> None:
    floral = _definition()
    woody_ref = _reference("family:woody")
    hybrid = _definition(
        family_id="hybrid:floral-woody",
        kind=FamilyDefinitionKind.HYBRID,
        components=(floral.definition_ref, woody_ref),
    )
    with pytest.raises(ValueError, match="missing component definitions"):
        _catalog(floral, hybrid)

    with pytest.raises(ValueError, match="reference definitions cannot declare components"):
        replace(floral, component_definitions=(woody_ref,))

    with pytest.raises(ValueError, match="at least two component definitions"):
        replace(hybrid, component_definitions=(floral.definition_ref,))


def test_relations_and_recognizers_must_reference_exact_declared_planes() -> None:
    definition = _definition()
    broken_recognizer = replace(
        definition.protected_recognizers[0],
        plane_ids=("missing-plane",),
    )
    with pytest.raises(ValueError, match="unknown architecture planes"):
        replace(
            definition,
            protected_recognizers=(
                broken_recognizer,
                definition.protected_recognizers[1],
            ),
        )

    broken_relation = replace(
        definition.temporal_relations[0],
        destination_plane_id="missing-plane",
    )
    with pytest.raises(ValueError, match="unknown architecture planes"):
        replace(
            definition,
            temporal_relations=(broken_relation, definition.temporal_relations[1]),
        )

    backward_relation = replace(
        definition.temporal_relations[0],
        source_plane_id="heart",
        destination_plane_id="opening",
    )
    with pytest.raises(ValueError, match="move forward"):
        replace(
            definition,
            temporal_relations=(backward_relation, definition.temporal_relations[1]),
        )


def test_resolution_withholds_empirical_and_release_authority() -> None:
    resolution = _catalog().resolve(_request())
    assert resolution.ingredient_count_complexity_authority is False
    assert resolution.empirical_smell_authority is False
    assert resolution.liking_authority is False
    assert resolution.safety_authority is False
    assert resolution.stability_authority is False
    assert resolution.release_authority is False

    payload = resolution.as_dict()
    for field_name in (
        "ingredient_count_complexity_authority",
        "empirical_smell_authority",
        "liking_authority",
        "safety_authority",
        "stability_authority",
        "release_authority",
    ):
        payload[field_name] = True
        with pytest.raises(ValueError, match="authority flags"):
            FamilyResolution.from_dict(payload)
        payload[field_name] = False


def test_family_definition_requires_complete_relational_architecture() -> None:
    definition = _definition()
    with pytest.raises(ValueError, match="architecture_planes must not be empty"):
        replace(definition, architecture_planes=())
    with pytest.raises(ValueError, match="protected_recognizers must not be empty"):
        replace(definition, protected_recognizers=())
    with pytest.raises(ValueError, match="forbidden_drift must not be empty"):
        replace(definition, forbidden_drift=())
    with pytest.raises(ValueError, match="temporal_relations must not be empty"):
        replace(definition, temporal_relations=())


def test_catalog_and_plane_packet_are_deterministic_under_input_permutation() -> None:
    floral = _definition()
    woody = _definition(family_id="family:woody", source="woody-source")
    first = _catalog(floral, woody)
    second = _catalog(woody, floral)

    assert first == second
    assert first.content_sha256 == second.content_sha256
    first_packet = FamilyArchitectureAdapter(first.resolve(_request())).to_plane_assessment()
    second_packet = FamilyArchitectureAdapter(second.resolve(_request())).to_plane_assessment()
    assert first_packet == second_packet
    assert PlaneAssessment.from_dict(first_packet.as_dict()) == first_packet
