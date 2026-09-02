from __future__ import annotations

from dataclasses import replace
from typing import TypedDict

import pytest

from engine.formulation_intelligence.candidate_assembler import (
    ArchitectureAlternative,
    AssemblyLayer,
    CandidateAssemblyBlueprint,
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
    ClaimCardinality,
    ClaimKind,
    CriterionDirection,
    CriterionValue,
    EvidenceClass,
    ParetoCriterion,
    PlaneAssessment,
    PlaneConflict,
    PlaneId,
    ProvenanceRef,
    ScopedClaim,
    UnknownFact,
)

TARGET_ID = "target/ideal/white-floral-study-v1"
BUILD_ID = "current-inventory-build/white-floral-study-v1"


def _provenance(suffix: str) -> ProvenanceRef:
    return ProvenanceRef(
        provenance_id=f"source-{suffix}",
        source_ref=f"fixture://{suffix}",
        evidence_class=EvidenceClass.HEURISTIC,
        independence_key=f"fixture-{suffix}",
        source_sha256=suffix[0] * 64,
    )


def _scope(window: str) -> AssessmentScope:
    return AssessmentScope(
        target_scope=TARGET_ID,
        temporal_scope=window,
        matrix_scope="structural-design/no-physical-matrix",
    )


def _assessment(
    *,
    plane_id: PlaneId,
    window: str,
    suffix: str,
    with_unknown: bool = False,
    with_conflict: bool = False,
) -> PlaneAssessment:
    provenance = _provenance(suffix)
    claim = ScopedClaim(
        claim_id=f"{suffix}-member-a",
        claim_key="architectural_members",
        claim_value=f"member-{suffix}",
        claim_kind=ClaimKind.HYPOTHESIS,
        authority_ceiling=AuthorityCeiling.HYPOTHESIS_ONLY,
        provenance_refs=(provenance,),
        cardinality=ClaimCardinality.SET_MEMBER,
        member_id=f"member-{suffix}",
    )
    criterion = ParetoCriterion(
        criterion_id=f"{suffix}-target-continuity",
        direction=CriterionDirection.PRESERVE,
        value=CriterionValue.unknown("requires a controlled comparison"),
        unit="structural hypothesis",
        authority_ceiling=AuthorityCeiling.HYPOTHESIS_ONLY,
        provenance_refs=(provenance,),
    )
    return PlaneAssessment(
        assessment_id=f"assessment-{suffix}",
        module_id=f"fixture-{suffix}",
        plane_id=plane_id,
        scope=_scope(window),
        claims=(claim,),
        support_intervals=(),
        conflicts=(
            PlaneConflict(
                conflict_id=f"conflict-{suffix}",
                claim_key="bridge_shape",
                alternatives=("continuous", "punctuated"),
                reason="the source evidence does not adjudicate the alternatives",
                claim_ids=(claim.claim_id,),
                provenance_refs=(provenance,),
            ),
        )
        if with_conflict
        else (),
        unknowns=(
            UnknownFact(
                unknown_id=f"unknown-{suffix}",
                field_key="observed_transition",
                reason="no controlled observation is attached",
                needed_evidence="time-resolved blinded observation",
                provenance_refs=(provenance,),
            ),
        )
        if with_unknown
        else (),
        failure_modes=("structural discontinuity remains possible",),
        proposed_experiments=("compare the alternatives under a coded protocol",),
        provenance_refs=(provenance,),
        authority_ceiling=AuthorityCeiling.HYPOTHESIS_ONLY,
        freshness_hashes=(suffix[0] * 64,),
        native_criteria=(criterion,),
    )


def _withheld_assessment(plane_id: PlaneId, index: int) -> PlaneAssessment:
    suffix = f"withheld-{plane_id.value}"
    digest_character = "0123456789abcdef"[index]
    return PlaneAssessment(
        assessment_id=f"assessment-{suffix}",
        module_id="candidate-assembly-missing-plane-declaration",
        plane_id=plane_id,
        scope=_scope("whole-wear"),
        claims=(),
        support_intervals=(),
        conflicts=(),
        unknowns=(
            UnknownFact(
                unknown_id=f"unknown-{suffix}",
                field_key="plane_evidence",
                reason=f"no admissible {plane_id.value} evidence is attached",
                needed_evidence=(
                    f"an exact-scope {plane_id.value} assessment with source provenance"
                ),
            ),
        ),
        failure_modes=(f"{plane_id.value} architecture remains unadjudicated",),
        proposed_experiments=(f"collect exact-scope {plane_id.value} evidence",),
        provenance_refs=(),
        authority_ceiling=AuthorityCeiling.WITHHELD,
        freshness_hashes=(digest_character * 64,),
        native_criteria=(),
    )


def _decision(
    *,
    decision_id: str,
    alternative_id: str,
    candidate_id: str,
    disposition: CandidateDisposition,
    layer: AssemblyLayer,
    plane_id: PlaneId,
    window: str,
    suffix: str,
) -> CandidateDecisionPacket:
    return CandidateDecisionPacket(
        decision_id=decision_id,
        alternative_id=alternative_id,
        target_ideal_id=TARGET_ID,
        current_inventory_build_id=(
            BUILD_ID if layer is AssemblyLayer.CURRENT_INVENTORY_BUILD else None
        ),
        layer=layer,
        plane_id=plane_id,
        scope=_scope(window),
        candidate_id=candidate_id,
        disposition=disposition,
        target_linked_function="preserve the named target transition",
        omission_loss="the target transition may lose continuity",
        failure_mode="the structural candidate may dominate its neighboring layer",
        provenance_refs=(_provenance(suffix),),
        freshness_hashes=(suffix[0] * 64,),
        authority_ceiling=AuthorityCeiling.DESIGN_ONLY,
    )


def _relation(
    *,
    packet_id: str,
    alternative_id: str,
    disposition: RelationDisposition,
    suffix: str,
) -> RelationPacket:
    return RelationPacket(
        packet_id=packet_id,
        alternative_id=alternative_id,
        target_ideal_id=TARGET_ID,
        current_inventory_build_id=None,
        layer=AssemblyLayer.TARGET_IDEAL,
        plane_id=PlaneId.RELATION,
        scope=_scope("whole-wear"),
        relation_kind="bridge",
        subject_candidate_ids=(f"candidate-{alternative_id}",),
        object_candidate_ids=("target-recognizer",),
        disposition=disposition,
        rationale="a typed bridge is proposed without claiming observed smell",
        provenance_refs=(_provenance(suffix),),
        freshness_hashes=(suffix[0] * 64,),
        authority_ceiling=AuthorityCeiling.HYPOTHESIS_ONLY,
    )


SourceRecord = PlaneAssessment | CandidateDecisionPacket | RelationPacket


def _receipt(record: SourceRecord, kind: SourceRecordKind, suffix: str) -> SourceReceipt:
    if isinstance(record, PlaneAssessment):
        record_id = record.assessment_id
    elif isinstance(record, CandidateDecisionPacket):
        record_id = record.decision_id
    else:
        record_id = record.packet_id
    return SourceReceipt(
        receipt_id=f"receipt-{suffix}",
        record_kind=kind,
        record_id=record_id,
        record_sha256=record.content_sha256,
        plane_id=record.plane_id,
        scope=record.scope,
        authority_ceiling=record.authority_ceiling,
        provenance_refs=(_provenance(suffix),),
    )


class _Inputs(TypedDict):
    assessments: tuple[PlaneAssessment, ...]
    decisions: tuple[CandidateDecisionPacket, ...]
    relations: tuple[RelationPacket, ...]
    alternatives: tuple[ArchitectureAlternative, ...]
    fronts: tuple[ParetoFront, ...]
    receipts: tuple[SourceReceipt, ...]
    requirements: tuple[PlaneRequirement, ...]


def _inputs() -> _Inputs:
    identity = _assessment(
        plane_id=PlaneId.IDENTITY,
        window="whole-wear",
        suffix="a",
        with_unknown=True,
    )
    relation = _assessment(
        plane_id=PlaneId.RELATION,
        window="whole-wear",
        suffix="b",
        with_conflict=True,
    )
    decisions = (
        _decision(
            decision_id="decision-alt-a-select",
            alternative_id="alternative-a",
            candidate_id="candidate-alternative-a",
            disposition=CandidateDisposition.SELECT,
            layer=AssemblyLayer.TARGET_IDEAL,
            plane_id=PlaneId.IDENTITY,
            window="whole-wear",
            suffix="c",
        ),
        _decision(
            decision_id="decision-alt-a-reject",
            alternative_id="alternative-a",
            candidate_id="candidate-excluded",
            disposition=CandidateDisposition.REJECT,
            layer=AssemblyLayer.CURRENT_INVENTORY_BUILD,
            plane_id=PlaneId.IDENTITY,
            window="whole-wear",
            suffix="d",
        ),
        _decision(
            decision_id="decision-alt-b-hold",
            alternative_id="alternative-b",
            candidate_id="candidate-alternative-b",
            disposition=CandidateDisposition.HOLD,
            layer=AssemblyLayer.TARGET_IDEAL,
            plane_id=PlaneId.IDENTITY,
            window="whole-wear",
            suffix="e",
        ),
    )
    relations = (
        _relation(
            packet_id="relation-alt-a",
            alternative_id="alternative-a",
            disposition=RelationDisposition.PROPOSED,
            suffix="f",
        ),
        _relation(
            packet_id="relation-alt-b",
            alternative_id="alternative-b",
            disposition=RelationDisposition.HOLD,
            suffix="1",
        ),
    )
    alternatives = (
        ArchitectureAlternative(
            alternative_id="alternative-a",
            label="continuous bridge",
            candidate_decision_ids=(
                "decision-alt-a-select",
                "decision-alt-a-reject",
            ),
            relation_packet_ids=("relation-alt-a",),
        ),
        ArchitectureAlternative(
            alternative_id="alternative-b",
            label="punctuated bridge",
            candidate_decision_ids=("decision-alt-b-hold",),
            relation_packet_ids=("relation-alt-b",),
        ),
    )
    fronts = (
        ParetoFront(
            front_id="front-unranked",
            alternative_ids=("alternative-a", "alternative-b"),
            native_criterion_ids=(
                "a-target-continuity",
                "b-target-continuity",
            ),
        ),
    )
    represented_planes = {PlaneId.IDENTITY, PlaneId.RELATION}
    withheld = tuple(
        _withheld_assessment(plane_id, index)
        for index, plane_id in enumerate(
            (item for item in PlaneId if item not in represented_planes)
        )
    )
    assessments = (identity, relation, *withheld)
    receipts = tuple(
        [
            _receipt(item, SourceRecordKind.PLANE_ASSESSMENT, f"a-assessment-{index}")
            for index, item in enumerate(assessments)
        ]
        + [
            _receipt(item, SourceRecordKind.CANDIDATE_DECISION, f"d-decision-{index}")
            for index, item in enumerate(decisions)
        ]
        + [
            _receipt(item, SourceRecordKind.RELATION_PACKET, f"e-relation-{index}")
            for index, item in enumerate(relations)
        ]
    )
    return {
        "assessments": assessments,
        "decisions": decisions,
        "relations": relations,
        "alternatives": alternatives,
        "fronts": fronts,
        "receipts": receipts,
        "requirements": tuple(
            PlaneRequirement(plane_id, _scope("whole-wear")) for plane_id in PlaneId
        ),
    }


def _assemble(
    *,
    assessments: tuple[PlaneAssessment, ...] | None = None,
    decisions: tuple[CandidateDecisionPacket, ...] | None = None,
    relations: tuple[RelationPacket, ...] | None = None,
    alternatives: tuple[ArchitectureAlternative, ...] | None = None,
    fronts: tuple[ParetoFront, ...] | None = None,
    receipts: tuple[SourceReceipt, ...] | None = None,
    requirements: tuple[PlaneRequirement, ...] | None = None,
) -> CandidateAssemblyBlueprint:
    values = _inputs()
    return assemble_candidate_blueprint(
        target_ideal_id=TARGET_ID,
        current_inventory_build_id=BUILD_ID,
        required_plane_scopes=requirements or values["requirements"],
        plane_assessments=assessments or values["assessments"],
        candidate_decisions=decisions or values["decisions"],
        relation_packets=relations or values["relations"],
        alternatives=alternatives or values["alternatives"],
        pareto_fronts=fronts or values["fronts"],
        source_receipts=receipts or values["receipts"],
        version=1,
        caller_blockers=("inventory adjudication is not attached",),
        caller_exclusions=("no physical instructions",),
    )


def test_assembly_is_deterministic_closed_and_preserves_unresolved_state() -> None:
    blueprint = _assemble()
    reversed_inputs = _inputs()
    reordered = assemble_candidate_blueprint(
        target_ideal_id=TARGET_ID,
        current_inventory_build_id=BUILD_ID,
        required_plane_scopes=tuple(reversed(reversed_inputs["requirements"])),
        plane_assessments=tuple(reversed(reversed_inputs["assessments"])),
        candidate_decisions=tuple(reversed(reversed_inputs["decisions"])),
        relation_packets=tuple(reversed(reversed_inputs["relations"])),
        alternatives=tuple(reversed(reversed_inputs["alternatives"])),
        pareto_fronts=reversed_inputs["fronts"],
        source_receipts=tuple(reversed(reversed_inputs["receipts"])),
        version=1,
        caller_blockers=("inventory adjudication is not attached",),
        caller_exclusions=("no physical instructions",),
    )

    assert blueprint == reordered
    assert blueprint.content_sha256 == reordered.content_sha256
    assert blueprint.target_ideal_id != blueprint.current_inventory_build_id
    assert {item.plane_id for item in blueprint.required_plane_scopes} == set(PlaneId)
    identity_assessment = next(
        item for item in blueprint.plane_assessments if item.plane_id is PlaneId.IDENTITY
    )
    assert identity_assessment.claims[0].cardinality is ClaimCardinality.SET_MEMBER
    assert blueprint.unresolved_conflict_ids == ("assessment-b:conflict-b",)
    assert "assessment-a:unknown-a" in blueprint.unresolved_unknown_ids
    assert len(blueprint.unresolved_unknown_ids) == 12
    assert "hold:decision-alt-b-hold" in blueprint.blockers
    assert "hold:relation-alt-b" in blueprint.blockers
    assert "reject:decision-alt-a-reject" in blueprint.exclusions
    assert len(blueprint.alternatives) == 2
    assert blueprint.pareto_fronts[0].alternative_ids == (
        "alternative-a",
        "alternative-b",
    )
    assert blueprint.authority_ceiling is AuthorityCeiling.WITHHELD
    assert blueprint.source_hashes

    for flag in (
        "formula_generation_authorized",
        "formula_mutation_authorized",
        "inventory_mutation_authorized",
        "physical_execution_authorized",
        "compounding_authorized",
        "sensory_authority",
        "liking_authority",
        "similarity_authority",
        "performance_authority",
        "safety_authority",
        "stability_authority",
        "release_authority",
    ):
        assert getattr(blueprint, flag) is False


def test_strict_round_trip_and_tamper_rejection() -> None:
    blueprint = _assemble()
    assert CandidateAssemblyBlueprint.from_dict(blueprint.as_dict()) == blueprint

    extra = blueprint.as_dict()
    extra["unexpected"] = True
    with pytest.raises(ValueError, match="closed schema"):
        CandidateAssemblyBlueprint.from_dict(extra)

    promoted = blueprint.as_dict()
    promoted["sensory_authority"] = True
    with pytest.raises(ValueError, match="must all remain false"):
        CandidateAssemblyBlueprint.from_dict(promoted)

    tampered = blueprint.as_dict()
    tampered["assembly_id"] = "candidate-assembly/v1/" + "0" * 64
    with pytest.raises(ValueError, match="assembly_id"):
        CandidateAssemblyBlueprint.from_dict(tampered)


def test_missing_required_plane_or_source_receipt_fails_closed() -> None:
    values = _inputs()
    identity_only = (values["assessments"][0],)
    with pytest.raises(ValueError, match="required plane/scope coverage"):
        _assemble(assessments=identity_only)

    with pytest.raises(ValueError, match="source receipt coverage"):
        _assemble(receipts=values["receipts"][:-1])


def test_omitting_a_plane_even_with_internally_matched_sources_fails_closed() -> None:
    values = _inputs()
    omitted = PlaneId.PHYSICOCHEMICAL
    assessments = tuple(
        item for item in values["assessments"] if item.plane_id is not omitted
    )
    requirements = tuple(
        item for item in values["requirements"] if item.plane_id is not omitted
    )
    assessment_ids = {item.assessment_id for item in assessments}
    receipts = tuple(
        item
        for item in values["receipts"]
        if item.record_kind is not SourceRecordKind.PLANE_ASSESSMENT
        or item.record_id in assessment_ids
    )

    with pytest.raises(ValueError, match="all 13 architectural planes"):
        _assemble(
            assessments=assessments,
            requirements=requirements,
            receipts=receipts,
        )


@pytest.mark.parametrize("authority", [AuthorityCeiling.WITHHELD, AuthorityCeiling.DESIGN_ONLY])
def test_no_evidence_plane_requires_withheld_authority_and_explicit_unknown(
    authority: AuthorityCeiling,
) -> None:
    values = _inputs()
    original = next(
        item
        for item in values["assessments"]
        if item.plane_id is PlaneId.PHYSICOCHEMICAL
    )
    invalid = replace(original, unknowns=(), authority_ceiling=authority)
    assessments = tuple(
        invalid if item.assessment_id == original.assessment_id else item
        for item in values["assessments"]
    )
    receipts = tuple(
        replace(
            item,
            record_sha256=invalid.content_sha256,
            authority_ceiling=invalid.authority_ceiling,
        )
        if item.record_kind is SourceRecordKind.PLANE_ASSESSMENT
        and item.record_id == original.assessment_id
        else item
        for item in values["receipts"]
    )

    with pytest.raises(ValueError, match="no-evidence plane assessments"):
        _assemble(assessments=assessments, receipts=receipts)


def test_mismatched_receipt_hash_scope_or_authority_fails_closed() -> None:
    values = _inputs()
    receipt = values["receipts"][0]

    with pytest.raises(ValueError, match="receipt hash"):
        _assemble(
            receipts=(replace(receipt, record_sha256="0" * 64), *values["receipts"][1:])
        )
    with pytest.raises(ValueError, match="receipt scope"):
        _assemble(
            receipts=(
                replace(receipt, scope=_scope("opening")),
                *values["receipts"][1:],
            )
        )
    with pytest.raises(ValueError, match="receipt authority"):
        _assemble(
            receipts=(
                replace(receipt, authority_ceiling=AuthorityCeiling.WITHHELD),
                *values["receipts"][1:],
            )
        )


def test_target_build_and_exact_scope_incompatibilities_fail_closed() -> None:
    values = _inputs()
    build_decision = values["decisions"][1]
    with pytest.raises(ValueError, match="current-inventory build"):
        _assemble(
            decisions=(
                values["decisions"][0],
                replace(build_decision, current_inventory_build_id="other-build"),
                values["decisions"][2],
            )
        )

    bad_scope = replace(values["decisions"][0], scope=_scope("opening"))
    with pytest.raises(ValueError, match="required plane/scope"):
        _assemble(decisions=(bad_scope, *values["decisions"][1:]))

    with pytest.raises(ValueError, match="must remain distinct"):
        assemble_candidate_blueprint(
            target_ideal_id=TARGET_ID,
            current_inventory_build_id=TARGET_ID,
            required_plane_scopes=values["requirements"],
            plane_assessments=values["assessments"],
            candidate_decisions=values["decisions"],
            relation_packets=values["relations"],
            alternatives=values["alternatives"],
            pareto_fronts=values["fronts"],
            source_receipts=values["receipts"],
            version=1,
        )


def test_orphans_and_scalarized_pareto_fronts_are_rejected() -> None:
    values = _inputs()
    orphan = ArchitectureAlternative(
        alternative_id="alternative-orphan",
        label="orphan",
        candidate_decision_ids=("decision-missing",),
        relation_packet_ids=(),
    )
    with pytest.raises(ValueError, match="unknown candidate decision"):
        _assemble(alternatives=(*values["alternatives"], orphan))

    bad_front = ParetoFront(
        front_id="front-invalid",
        alternative_ids=("alternative-a", "alternative-b"),
        native_criterion_ids=("overall_score",),
    )
    with pytest.raises(ValueError, match="unknown native criterion"):
        _assemble(fronts=(bad_front,))


def test_version_successors_require_and_bind_predecessor_hash() -> None:
    values = _inputs()
    first = _assemble()
    second = assemble_candidate_blueprint(
        target_ideal_id=TARGET_ID,
        current_inventory_build_id=BUILD_ID,
        required_plane_scopes=values["requirements"],
        plane_assessments=values["assessments"],
        candidate_decisions=values["decisions"],
        relation_packets=values["relations"],
        alternatives=values["alternatives"],
        pareto_fronts=values["fronts"],
        source_receipts=values["receipts"],
        version=2,
        predecessor_sha256=first.content_sha256,
    )
    assert second.version == 2
    assert second.predecessor_sha256 == first.content_sha256
    assert second.assembly_id != first.assembly_id

    with pytest.raises(ValueError, match="successors require predecessor_sha256"):
        assemble_candidate_blueprint(
            target_ideal_id=TARGET_ID,
            current_inventory_build_id=BUILD_ID,
            required_plane_scopes=values["requirements"],
            plane_assessments=values["assessments"],
            candidate_decisions=values["decisions"],
            relation_packets=values["relations"],
            alternatives=values["alternatives"],
            pareto_fronts=values["fronts"],
            source_receipts=values["receipts"],
            version=2,
        )
