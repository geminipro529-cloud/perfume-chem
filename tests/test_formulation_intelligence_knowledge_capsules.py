from __future__ import annotations

from dataclasses import FrozenInstanceError, replace

import pytest

from engine.formulation_intelligence.accord_graph import (
    MANDATORY_GRAPH_EXCLUSIONS,
    AccordRelationGraph,
    EdgeOrientation,
    EpistemicState,
    GraphEdge,
    GraphNode,
    GraphScope,
    NodeKind,
    RelationKind,
    accord_graph_to_plane_assessment,
)
from engine.formulation_intelligence.admission import SourceIdentity
from engine.formulation_intelligence.contracts import (
    AssessmentScope,
    AuthorityCeiling,
    ClaimKind,
    EvidenceClass,
    PlaneAssessment,
    PlaneId,
    ProvenanceRef,
    ScopedClaim,
)
from engine.formulation_intelligence.knowledge_capsules import (
    MANDATORY_CAPSULE_EXCLUSIONS,
    CapsuleArtifact,
    CapsuleArtifactDisposition,
    CapsuleArtifactRole,
    CapsuleManifestVerificationReceipt,
    CapsuleVerificationStatus,
    KnowledgeCapsule,
    KnowledgeCapsuleProjection,
    KnowledgeCapsuleState,
    capsule_artifact_manifest_sha256,
    project_knowledge_capsule,
)

_A = "a" * 64
_B = "b" * 64
_C = "c" * 64


def _source() -> SourceIdentity:
    return SourceIdentity(
        repository_id="perfume-chem",
        source_task_id="peer-studio",
        worktree_path=r"C:\Users\ASUS\.codex\worktrees\6992\perfume-chem",
        branch_ref="detached",
        head_commit="398800c5da43038f3159956362681a2ed92091f0",
        workspace_state_sha256=_C,
    )


def _artifacts() -> tuple[CapsuleArtifact, ...]:
    return (
        CapsuleArtifact(
            artifact_id="source",
            role=CapsuleArtifactRole.SOURCE,
            source_relative_path="engine/studio.py",
            byte_size=101,
            sha256=_A,
            disposition=CapsuleArtifactDisposition.COPIED_BYTE_VERIFIED,
            destination_relative_path="engine/studio.py",
        ),
        CapsuleArtifact(
            artifact_id="test",
            role=CapsuleArtifactRole.TEST,
            source_relative_path="tests/test_studio.py",
            byte_size=43,
            sha256=_B,
            disposition=CapsuleArtifactDisposition.REFERENCE_ONLY,
            exclusion_reason="retained in the peer worktree",
        ),
    )


def _assessment(
    *,
    source_sha256: str | None = _A,
    provenance_id: str = "peer-source",
    source_ref: str = "engine/studio.py",
    assessment_id: str = "peer-layer-order",
    module_id: str = "peer-studio",
) -> PlaneAssessment:
    provenance = ProvenanceRef(
        provenance_id=provenance_id,
        source_ref=source_ref,
        evidence_class=EvidenceClass.HEURISTIC,
        independence_key="peer-studio",
        source_sha256=source_sha256,
    )
    claim = ScopedClaim(
        claim_id="layer-order",
        claim_key="architecture.layer-order",
        claim_value="opening before heart before drydown",
        claim_kind=ClaimKind.REQUIREMENT,
        authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
        provenance_refs=(provenance,),
    )
    return PlaneAssessment(
        assessment_id=assessment_id,
        module_id=module_id,
        plane_id=PlaneId.TEMPORAL,
        scope=AssessmentScope(
            target_scope="peer reference",
            temporal_scope="opening-to-drydown",
            matrix_scope="design-only",
        ),
        claims=(claim,),
        support_intervals=(),
        conflicts=(),
        unknowns=(),
        failure_modes=("No observed smell evidence",),
        proposed_experiments=("Run a blinded temporal evaluation",),
        provenance_refs=(provenance,),
        authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
        freshness_hashes=(_A,),
        native_criteria=(),
    )


def _receipt(
    *,
    source: SourceIdentity | None = None,
    artifacts: tuple[CapsuleArtifact, ...] | None = None,
    manifest_sha256: str | None = None,
) -> CapsuleManifestVerificationReceipt:
    source = source or _source()
    artifacts = artifacts or _artifacts()
    return CapsuleManifestVerificationReceipt(
        receipt_id="peer-studio-manifest",
        verifier_id="codex-local-byte-manifest-verifier",
        verifier_version="1",
        source_identity_sha256=source.content_sha256,
        artifact_manifest_sha256=(
            manifest_sha256
            if manifest_sha256 is not None
            else capsule_artifact_manifest_sha256(source, artifacts)
        ),
        output_sha256=_C,
        verification_status=CapsuleVerificationStatus.PASS,
        blockers=(),
    )


def _graph(*, graph_id: str = "peer-relation-graph", empty: bool = False) -> AccordRelationGraph:
    provenance = ProvenanceRef(
        provenance_id="peer-source",
        source_ref="engine/studio.py",
        evidence_class=EvidenceClass.HEURISTIC,
        independence_key="peer-studio",
        source_sha256=_A,
    )
    scope = GraphScope(
        target_scope="peer reference",
        condition_scope="design condition only",
        temporal_scope="opening-to-drydown",
        matrix_scope="design-only",
    )
    nodes: tuple[GraphNode, ...] = ()
    edges: tuple[GraphEdge, ...] = ()
    if not empty:
        target = GraphNode(
            node_id="target",
            node_kind=NodeKind.TARGET,
            label="peer reference",
            scope=scope,
            plane_ids=(PlaneId.IDENTITY,),
            epistemic_state=EpistemicState.DECLARED,
            authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
            provenance_refs=(provenance,),
        )
        layer = GraphNode(
            node_id="layer",
            node_kind=NodeKind.ACCORD,
            label="temporal layer",
            scope=scope,
            plane_ids=(PlaneId.RELATION, PlaneId.TEMPORAL),
            epistemic_state=EpistemicState.HYPOTHESIS,
            authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
            provenance_refs=(provenance,),
        )
        nodes = (target, layer)
        edges = (
            GraphEdge(
                edge_id="layer-supports-target",
                source_node_id=layer.node_id,
                target_node_id=target.node_id,
                relation_kind=RelationKind.SUPPORTS,
                orientation=EdgeOrientation.DIRECTED,
                scope=scope,
                plane_ids=(PlaneId.IDENTITY, PlaneId.RELATION, PlaneId.TEMPORAL),
                epistemic_state=EpistemicState.HYPOTHESIS,
                authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
                provenance_refs=(provenance,),
                rationale="Preserved peer relation hypothesis",
            ),
        )
    return AccordRelationGraph(
        graph_id=graph_id,
        scope=scope,
        nodes=nodes,
        edges=edges,
        alternative_sets=(),
        unknowns=(),
        provenance_refs=(provenance,),
        authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
        authority_exclusions=MANDATORY_GRAPH_EXCLUSIONS,
    )


def _capsule(**changes: object) -> KnowledgeCapsule:
    values: dict[str, object] = {
        "capsule_id": "derive",
        "version": 1,
        "predecessor_sha256": None,
        "source_identity": _source(),
        "source_module_id": "peer-studio",
        "source_module_version": "2026-09-01",
        "source_root_artifact_id": "source",
        "artifacts": _artifacts(),
        "manifest_verification_receipt": _receipt(),
        "state": KnowledgeCapsuleState.CAPTURED_READ_ONLY,
        "assessments": (_assessment(),),
        "relation_graphs": (),
        "authority_ceiling": AuthorityCeiling.STRUCTURAL_ONLY,
        "authority_exclusions": MANDATORY_CAPSULE_EXCLUSIONS,
    }
    values.update(changes)
    return KnowledgeCapsule(**values)  # type: ignore[arg-type]


def test_capsule_round_trip_is_canonical_and_immutable() -> None:
    capsule = _capsule(artifacts=tuple(reversed(_artifacts())))

    restored = KnowledgeCapsule.from_dict(capsule.as_dict())

    assert restored == capsule
    assert restored.content_sha256 == capsule.content_sha256
    assert restored.capsule_id.startswith("knowledge-capsule/v1/")
    assert tuple(item.artifact_id for item in restored.artifacts) == ("source", "test")
    with pytest.raises(FrozenInstanceError):
        restored.state = KnowledgeCapsuleState.HOLD  # type: ignore[misc]


def test_capsule_identity_binds_complete_content() -> None:
    original = _capsule()
    payload = original.as_dict()
    payload["source_module_version"] = "forged"

    with pytest.raises(ValueError, match="capsule_id does not match"):
        KnowledgeCapsule.from_dict(payload)


@pytest.mark.parametrize(
    "changes,match",
    (
        ({"assessments": ()}, "at least one typed"),
        (
            {
                "state": KnowledgeCapsuleState.CAPTURED_READ_ONLY,
                "manifest_verification_receipt": None,
                "authority_ceiling": AuthorityCeiling.WITHHELD,
            },
            "require a PASS manifest receipt",
        ),
        (
            {
                "state": KnowledgeCapsuleState.HOLD,
                "authority_ceiling": AuthorityCeiling.STRUCTURAL_ONLY,
            },
            "require WITHHELD authority",
        ),
        (
            {
                "authority_exclusions": tuple(
                    item
                    for item in MANDATORY_CAPSULE_EXCLUSIONS
                    if item != "release authority"
                )
            },
            "omit mandatory boundaries",
        ),
        ({"release_authority": True}, "cannot be granted"),
    ),
)
def test_capsule_fails_closed_on_authority_and_completeness(
    changes: dict[str, object], match: str
) -> None:
    with pytest.raises(ValueError, match=match):
        _capsule(**changes)


def test_capsule_rejects_unmanifested_or_unbound_provenance() -> None:
    with pytest.raises(ValueError, match="absent from the artifact manifest"):
        _capsule(assessments=(_assessment(source_sha256="d" * 64),))

    with pytest.raises(ValueError, match="must bind an artifact"):
        _capsule(assessments=(_assessment(source_sha256=None),))


def test_capsule_rejects_conflicting_semantic_and_provenance_ids() -> None:
    first = _assessment()
    same_assessment_id = _assessment(
        assessment_id=first.assessment_id,
        module_id="different-peer-module",
    )
    with pytest.raises(ValueError, match="assessment_id values must identify exact records"):
        _capsule(assessments=(first, same_assessment_id))

    conflicting_provenance = _assessment(
        source_sha256=_B,
        provenance_id="peer-source",
        source_ref="tests/test_studio.py",
        assessment_id="peer-layer-order-two",
        module_id="peer-studio-two",
    )
    with pytest.raises(ValueError, match="provenance_id values must identify exact records"):
        _capsule(assessments=(first, conflicting_provenance))


def test_empty_or_provenance_free_assessment_cannot_earn_authority() -> None:
    empty = replace(
        _assessment(),
        claims=(),
        failure_modes=(),
        proposed_experiments=(),
        provenance_refs=(),
        freshness_hashes=(),
    )
    with pytest.raises(ValueError, match="reject empty assessments"):
        _capsule(assessments=(empty,))

    provenance_free = replace(
        empty,
        failure_modes=("Unbound design claim",),
    )
    with pytest.raises(ValueError, match="require bound provenance"):
        _capsule(assessments=(provenance_free,))


def test_manifest_receipt_binds_source_artifacts_and_authority_state() -> None:
    with pytest.raises(ValueError, match="exact artifact manifest"):
        _capsule(manifest_verification_receipt=_receipt(manifest_sha256="d" * 64))

    other_source = replace(_source(), workspace_state_sha256="d" * 64)
    with pytest.raises(ValueError, match="exact source identity"):
        _capsule(manifest_verification_receipt=_receipt(source=other_source))

    with pytest.raises(ValueError, match="quarantined capsules require WITHHELD"):
        _capsule(
            state=KnowledgeCapsuleState.QUARANTINED,
            authority_ceiling=AuthorityCeiling.HYPOTHESIS_ONLY,
        )


def test_capsule_rejects_path_aliases_and_duplicate_destinations() -> None:
    with pytest.raises(ValueError, match="repository-relative"):
        replace(_artifacts()[0], source_relative_path="../engine/studio.py")

    duplicate_destination = replace(
        _artifacts()[1],
        disposition=CapsuleArtifactDisposition.COPIED_BYTE_VERIFIED,
        destination_relative_path="engine/studio.py",
        exclusion_reason=None,
    )
    with pytest.raises(ValueError, match="unique destination paths"):
        _capsule(artifacts=(_artifacts()[0], duplicate_destination))

    source_alias = replace(
        _artifacts()[1],
        source_relative_path="Engine/Studio.py",
    )
    with pytest.raises(ValueError, match="unique source paths"):
        _capsule(artifacts=(_artifacts()[0], source_alias))


def test_capsule_rejects_empty_graph_and_projection_id_collision() -> None:
    with pytest.raises(ValueError, match="reject empty relation graphs"):
        _capsule(assessments=(), relation_graphs=(_graph(empty=True),))

    graph = _graph()
    derived = accord_graph_to_plane_assessment(graph)
    conflicting = _assessment(
        assessment_id=derived.assessment_id,
        module_id="conflicting-explicit-assessment",
    )
    with pytest.raises(ValueError, match="assessment_id values must identify exact records"):
        _capsule(assessments=(conflicting,), relation_graphs=(graph,))


def test_projection_is_derived_and_cannot_promote_authority() -> None:
    capsule = _capsule()
    projection = project_knowledge_capsule(capsule)

    assert projection.assessments == capsule.assessments
    assert projection.effective_authority_ceiling is AuthorityCeiling.STRUCTURAL_ONLY
    assert not projection.condition_aware_synthesis_authorized
    assert KnowledgeCapsuleProjection.from_dict(projection.as_dict()) == projection

    with pytest.raises(ValueError, match="explicit source meet"):
        KnowledgeCapsuleProjection(
            capsule=capsule,
            assessments=capsule.assessments,
            effective_authority_ceiling=AuthorityCeiling.DESIGN_ONLY,
        )
    with pytest.raises(ValueError, match="complete capsule"):
        KnowledgeCapsuleProjection(
            capsule=capsule,
            assessments=(replace(_assessment(), assessment_id="forged"),),
            effective_authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
        )
    with pytest.raises(ValueError, match="condition-aware synthesis remains disabled"):
        replace(projection, condition_aware_synthesis_authorized=True)


def test_closed_schema_rejects_extra_fields() -> None:
    payload = _capsule().as_dict()
    payload["summary"] = "lossy replacement"

    with pytest.raises(ValueError, match="closed schema"):
        KnowledgeCapsule.from_dict(payload)
