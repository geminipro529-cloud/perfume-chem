from __future__ import annotations

from copy import deepcopy

import pytest

from engine.formulation_intelligence.candidate_assembler import (
    ArchitectureAlternative,
    AssemblyLayer,
    CandidateDecisionPacket,
    CandidateDisposition,
    ParetoFront,
    PlaneRequirement,
    RelationDisposition,
    RelationPacket,
    SourceReceipt,
    SourceRecordKind,
    assemble_candidate_blueprint,
)
from engine.formulation_intelligence.contracts import (
    AssessmentScope,
    AuthorityCeiling,
    CriterionDirection,
    CriterionValue,
    EvidenceClass,
    ParetoCriterion,
    PlaneAssessment,
    PlaneId,
    ProvenanceRef,
    UnknownFact,
)
from engine.formulation_intelligence.inventory_projection import (
    AliquotState,
    ExactStockRef,
    IdealMaterialSelection,
    IdealProposal,
    StockAvailability,
    project_ideal_to_current_build,
)
from engine.formulation_intelligence.plane_synthesis import (
    synthesize_plane_assessments,
)
from engine.formulation_intelligence.target_compiler import (
    AbstractionLevel,
    TargetAcceptance,
    TargetAcceptanceState,
    TargetBranch,
    TargetBrief,
    TargetMode,
    TargetRequestSource,
    TargetSourceSpan,
    compile_target_intent,
)
from engine.formulation_intelligence.whole_perfume_assembler import (
    IntegratedWholePerfumeBlueprint,
    assemble_integrated_whole_perfume_blueprint,
)

SourceRecord = PlaneAssessment | CandidateDecisionPacket | RelationPacket


def _provenance(label: str) -> ProvenanceRef:
    digest_character = "0123456789abcdef"[sum(label.encode("utf-8")) % 16]
    return ProvenanceRef(
        provenance_id=f"end-to-end-{label}",
        source_ref=f"fixture://end-to-end/{label}",
        evidence_class=EvidenceClass.HEURISTIC,
        independence_key=f"end-to-end-{label}",
        source_sha256=digest_character * 64,
    )


def _ideal() -> IdealProposal:
    raw = "Design a transparent magnolia architecture with a mineral drydown."
    source = _provenance("target")
    branch = TargetBranch(
        branch_id="magnolia-mineral-branch",
        interpretation="transparent magnolia connected to a mineral drydown",
        claim_keys=("target_identity", "expression"),
        evidence_ids=(),
    )
    brief = TargetBrief(
        request_id="magnolia-mineral-end-to-end",
        mode=TargetMode.CONCEPT_ONLY,
        subject="Magnolia de Verre",
        named_references=(),
        family_neighborhoods=("transparent floral",),
        abstraction_level=AbstractionLevel.RECOGNIZABLE_ABSTRACTION,
        expression_terms=("transparent magnolia", "mineral drydown"),
        exclusions=("generic floral cloud",),
        protected_recognizers=("magnolia petal subject",),
        forbidden_drift=("anonymous woody amber",),
        transformations=(),
        temporal_requests=("opening", "heart", "drydown"),
        matrix_context="ethanol fragrance matrix; concentration unresolved",
        criterion_vocabulary=("recognizer integrity", "transition continuity"),
        reference_evidence=(),
        provenance_refs=(source,),
        request_source=TargetRequestSource(
            raw_request=raw,
            source_ref="codex://end-to-end/target",
            source_sha256="2" * 64,
            span=TargetSourceSpan(start_char=0, end_char=len(raw)),
            origin="direct structural test request",
        ),
        branches=(branch,),
        conflicts=(),
        unknowns=(),
        acceptance=TargetAcceptance(
            acceptance_id="accept-magnolia-mineral",
            state=TargetAcceptanceState.ACCEPTED,
            accepted_branch_ids=(branch.branch_id,),
            decision_basis="the branch is accepted only for structural design",
            provenance_refs=(source,),
        ),
    )
    return IdealProposal(
        proposal_id="ideal:magnolia-mineral:end-to-end:v1",
        target_intent=compile_target_intent(brief),
        selections=(
            IdealMaterialSelection(
                selection_id="selection-clearwood",
                material_name="Clearwood",
                target_function="structural mineral transition candidate",
            ),
        ),
        design_notes=("inventory must not rewrite the ideal target",),
    )


def _projection(ideal: IdealProposal):
    stock = ExactStockRef(
        exact_stock_ref="inventory:end-to-end:clearwood-neat",
        material_name="Clearwood",
        availability=StockAvailability.OWNED,
        fraction=1.0,
        fraction_basis="neat_as_supplied",
        carrier="none",
        aliquot_state=AliquotState.READY,
        authority_source="exact end-to-end stock declaration",
        exact_identity=True,
        quantitative_authority=True,
        composition_complete=True,
        authority_notes=("structural mapping only",),
    )
    return project_ideal_to_current_build(
        ideal,
        (stock,),
        inventory_content_sha256="a" * 64,
        stock_authority_overlay_sha256="b" * 64,
        stock_authority_snapshot_id="end-to-end-inventory-v1",
    )


def _scope(target_id: str) -> AssessmentScope:
    return AssessmentScope(
        target_scope=target_id,
        temporal_scope="whole-wear",
        matrix_scope="structural-design/no-physical-matrix",
    )


def _assessment(plane_id: PlaneId, target_id: str, index: int) -> PlaneAssessment:
    provenance = _provenance(plane_id.value)
    criterion = (
        ParetoCriterion(
            criterion_id="target-recognizer-preservation",
            direction=CriterionDirection.PRESERVE,
            value=CriterionValue.unknown("no controlled observation exists"),
            unit="target-linked structural criterion",
            authority_ceiling=AuthorityCeiling.HYPOTHESIS_ONLY,
            provenance_refs=(provenance,),
        ),
    ) if plane_id is PlaneId.IDENTITY else ()
    return PlaneAssessment(
        assessment_id=f"end-to-end-{plane_id.value}",
        module_id="end-to-end-plane-coverage",
        plane_id=plane_id,
        scope=_scope(target_id),
        claims=(),
        support_intervals=(),
        conflicts=(),
        unknowns=(
            UnknownFact(
                unknown_id=f"unknown-{plane_id.value}",
                field_key=f"{plane_id.value}.evidence",
                reason=f"no admissible {plane_id.value} observation is attached",
                needed_evidence=f"exact-scope {plane_id.value} evidence",
                provenance_refs=(provenance,),
            ),
        ),
        failure_modes=(f"{plane_id.value} remains unadjudicated",),
        proposed_experiments=(f"collect exact-scope {plane_id.value} evidence",),
        provenance_refs=(provenance,),
        authority_ceiling=(
            AuthorityCeiling.HYPOTHESIS_ONLY
            if criterion
            else AuthorityCeiling.WITHHELD
        ),
        freshness_hashes=("0123456789abcdef"[index] * 64,),
        native_criteria=criterion,
    )


def _candidate_assembly(ideal: IdealProposal, projection):
    target_id = ideal.target_intent.ideal_target_id.value
    build_id = projection.build_projection_id.projection_id
    scope = _scope(target_id)
    assessments = tuple(
        _assessment(plane_id, target_id, index)
        for index, plane_id in enumerate(PlaneId)
    )
    source = _provenance("candidate")
    decisions = tuple(
        CandidateDecisionPacket(
            decision_id=f"decision-{suffix}",
            alternative_id=f"alternative-{suffix}",
            target_ideal_id=target_id,
            current_inventory_build_id=None,
            layer=AssemblyLayer.TARGET_IDEAL,
            plane_id=PlaneId.FUNCTION,
            scope=scope,
            candidate_id=f"candidate-{suffix}",
            disposition=disposition,
            target_linked_function="preserve magnolia-to-mineral continuity",
            omission_loss="the named transition may disconnect",
            failure_mode="the candidate may obscure the magnolia subject",
            provenance_refs=(source,),
            freshness_hashes=(digest * 64,),
            authority_ceiling=AuthorityCeiling.DESIGN_ONLY,
        )
        for suffix, disposition, digest in (
            ("continuous", CandidateDisposition.SELECT, "c"),
            ("punctuated", CandidateDisposition.HOLD, "d"),
        )
    )
    relations = tuple(
        RelationPacket(
            packet_id=f"relation-{suffix}",
            alternative_id=f"alternative-{suffix}",
            target_ideal_id=target_id,
            current_inventory_build_id=None,
            layer=AssemblyLayer.TARGET_IDEAL,
            plane_id=PlaneId.RELATION,
            scope=scope,
            relation_kind="temporal_bridge",
            subject_candidate_ids=(f"candidate-{suffix}",),
            object_candidate_ids=("magnolia-recognizer",),
            disposition=disposition,
            rationale="a structural bridge remains a hypothesis",
            provenance_refs=(source,),
            freshness_hashes=(digest * 64,),
            authority_ceiling=AuthorityCeiling.HYPOTHESIS_ONLY,
        )
        for suffix, disposition, digest in (
            ("continuous", RelationDisposition.PROPOSED, "e"),
            ("punctuated", RelationDisposition.HOLD, "f"),
        )
    )
    alternatives = tuple(
        ArchitectureAlternative(
            alternative_id=f"alternative-{suffix}",
            label=f"{suffix} bridge",
            candidate_decision_ids=(f"decision-{suffix}",),
            relation_packet_ids=(f"relation-{suffix}",),
        )
        for suffix in ("continuous", "punctuated")
    )
    records: tuple[tuple[SourceRecordKind, str, SourceRecord], ...] = (
        *((SourceRecordKind.PLANE_ASSESSMENT, item.assessment_id, item) for item in assessments),
        *((SourceRecordKind.CANDIDATE_DECISION, item.decision_id, item) for item in decisions),
        *((SourceRecordKind.RELATION_PACKET, item.packet_id, item) for item in relations),
    )
    receipts = tuple(
        SourceReceipt(
            receipt_id=f"receipt-{kind.value}-{index}",
            record_kind=kind,
            record_id=record_id,
            record_sha256=record.content_sha256,
            plane_id=record.plane_id,
            scope=record.scope,
            authority_ceiling=record.authority_ceiling,
            provenance_refs=(source,),
        )
        for index, (kind, record_id, record) in enumerate(records)
    )
    return assemble_candidate_blueprint(
        target_ideal_id=target_id,
        current_inventory_build_id=build_id,
        required_plane_scopes=tuple(
            PlaneRequirement(plane_id, scope) for plane_id in PlaneId
        ),
        plane_assessments=assessments,
        candidate_decisions=decisions,
        relation_packets=relations,
        alternatives=alternatives,
        pareto_fronts=(
            ParetoFront(
                front_id="front-unranked",
                alternative_ids=("alternative-continuous", "alternative-punctuated"),
                native_criterion_ids=("target-recognizer-preservation",),
            ),
        ),
        source_receipts=receipts,
        version=1,
        caller_blockers=("empirical comparison is not attached",),
        caller_exclusions=("no physical instructions",),
    )


def test_integrated_blueprint_binds_all_planes_target_build_and_authority() -> None:
    ideal = _ideal()
    projection = _projection(ideal)
    candidate = _candidate_assembly(ideal, projection)
    synthesis = synthesize_plane_assessments(candidate.plane_assessments)

    integrated = assemble_integrated_whole_perfume_blueprint(
        ideal,
        projection,
        candidate,
        syntheses=(synthesis,),
        version=1,
    )
    restored = IntegratedWholePerfumeBlueprint.from_dict(integrated.as_dict())

    assert restored == integrated
    assert integrated.candidate_assembly == candidate
    assert integrated.whole_blueprint.ideal_target_id == candidate.target_ideal_id
    assert (
        integrated.whole_blueprint.inventory_projection.build_projection_id.projection_id
        == candidate.current_inventory_build_id
    )
    assert {item.plane_id for item in integrated.whole_blueprint.planes} == set(PlaneId)
    assert set(candidate.unresolved_unknown_ids).issubset(
        {
            f"{assessment.assessment_id}:{unknown.unknown_id}"
            for plane in integrated.whole_blueprint.planes
            for assessment in plane.assessments
            for unknown in assessment.unknowns
        }
    )
    assert integrated.authority_ceiling is AuthorityCeiling.WITHHELD
    assert integrated.formula_generation_authorized is False
    assert integrated.physical_execution_authorized is False
    assert integrated.observed_smell is False
    assert integrated.release_authorized is False


def test_integrated_blueprint_rejects_tampering_and_cross_build_laundering() -> None:
    ideal = _ideal()
    projection = _projection(ideal)
    candidate = _candidate_assembly(ideal, projection)
    integrated = assemble_integrated_whole_perfume_blueprint(
        ideal,
        projection,
        candidate,
        version=1,
    )

    payload = deepcopy(integrated.as_dict())
    payload["candidate_assembly"]["current_inventory_build_id"] = "other-build"
    with pytest.raises(ValueError):
        IntegratedWholePerfumeBlueprint.from_dict(payload)

    promoted = deepcopy(integrated.as_dict())
    promoted["release_authorized"] = True
    with pytest.raises(ValueError, match="cannot be promoted"):
        IntegratedWholePerfumeBlueprint.from_dict(promoted)
