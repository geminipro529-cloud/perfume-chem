from __future__ import annotations

from copy import deepcopy
from dataclasses import FrozenInstanceError, replace

import pytest

from engine.formulation_intelligence.contracts import (
    AssessmentScope,
    AuthorityCeiling,
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
from engine.formulation_intelligence.family_architecture import (
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
)
from engine.formulation_intelligence.inventory_projection import (
    AliquotState,
    ExactStockRef,
    IdealMaterialSelection,
    IdealProposal,
    InventoryProjection,
    ProjectionDisposition,
    StockAvailability,
    current_inventory_stock_corrections,
    project_ideal_to_current_build,
)
from engine.formulation_intelligence.plane_synthesis import (
    synthesize_plane_assessments,
)
from engine.formulation_intelligence.target_compiler import (
    AbstractionLevel,
    BuildProjectionId,
    TargetAcceptance,
    TargetAcceptanceState,
    TargetBranch,
    TargetBrief,
    TargetIntent,
    TargetMode,
    TargetRequestSource,
    TargetResolution,
    TargetSourceSpan,
    TemporalTransformation,
    compile_target_intent,
)
from engine.formulation_intelligence.whole_perfume_assembler import (
    PlaneBlueprint,
    WholePerfumeBlueprint,
    assemble_whole_perfume_blueprint,
)
from engine.formulation_intelligence.wood_integration import (
    assemble_wood_whole_perfume_blueprint,
)
from engine.formulation_intelligence.wood_registry import (
    WoodFunctionalRole,
    WoodTargetRequest,
    default_wood_capability_registry,
)


def _provenance() -> ProvenanceRef:
    return ProvenanceRef(
        provenance_id="inventory-whole-test-source",
        source_ref="exact test target declaration",
        evidence_class=EvidenceClass.USER_REPORT,
        independence_key="inventory-whole-test-source",
        source_sha256="1" * 64,
    )


def _target_brief() -> TargetBrief:
    raw = "Build a transparent magnolia architecture with a mineral drydown."
    branch = TargetBranch(
        branch_id="transparent-magnolia-branch",
        interpretation="transparent magnolia with a mineral drydown",
        claim_keys=("target_identity", "expression"),
        evidence_ids=(),
    )
    return TargetBrief(
        request_id="magnolia glass architecture",
        mode=TargetMode.CONCEPT_ONLY,
        subject="Magnolia de Verre",
        named_references=(),
        family_neighborhoods=("transparent floral",),
        abstraction_level=AbstractionLevel.RECOGNIZABLE_ABSTRACTION,
        expression_terms=("mineral drydown", "transparent magnolia"),
        exclusions=("generic floral cloud",),
        protected_recognizers=("magnolia petal subject",),
        forbidden_drift=("anonymous woody amber",),
        transformations=(
            TemporalTransformation(
                transformation_id="petal-to-mineral",
                source_state="magnolia petal",
                destination_state="mineral drydown",
                temporal_window="heart-to-drydown",
                continuity_requirement="magnolia remains traceable",
            ),
        ),
        temporal_requests=("opening", "heart", "drydown"),
        matrix_context="ethanol fragrance matrix; concentration unresolved",
        criterion_vocabulary=("recognizer integrity", "transition continuity"),
        reference_evidence=(),
        provenance_refs=(_provenance(),),
        request_source=TargetRequestSource(
            raw_request=raw,
            source_ref="codex://inventory-whole-test/target",
            source_sha256="2" * 64,
            span=TargetSourceSpan(start_char=11, end_char=11 + len(raw)),
            origin="direct test request",
        ),
        branches=(branch,),
        conflicts=(),
        unknowns=(),
        acceptance=TargetAcceptance(
            acceptance_id="accepted-transparent-magnolia",
            state=TargetAcceptanceState.ACCEPTED,
            accepted_branch_ids=(branch.branch_id,),
            decision_basis="the exact target branch is accepted for structural design",
            provenance_refs=(_provenance(),),
        ),
    )


def _target(*, resolved: bool = True) -> TargetIntent:
    brief = _target_brief()
    if not resolved:
        brief = replace(brief, request_source=None)
    return compile_target_intent(brief)


def _ideal(*material_names: str, resolved: bool = True) -> IdealProposal:
    return IdealProposal(
        proposal_id="ideal:magnolia-glass:v2",
        target_intent=_target(resolved=resolved),
        selections=tuple(
            IdealMaterialSelection(
                selection_id=f"selection:{index}",
                material_name=material_name,
                target_function=f"target-linked function {index}",
            )
            for index, material_name in enumerate(material_names, start=1)
        ),
        design_notes=("inventory must not rewrite this ideal",),
    )


def _stock(
    material_name: str = "Clearwood",
    *,
    authority_notes: tuple[str, ...] = ("exact stock authority",),
) -> ExactStockRef:
    return ExactStockRef(
        exact_stock_ref=f"inventory:test:{material_name.casefold().replace(' ', '-')}",
        material_name=material_name,
        availability=StockAvailability.OWNED,
        fraction=1.0,
        fraction_basis="neat_as_supplied",
        carrier="none",
        aliquot_state=AliquotState.READY,
        authority_source="exact test stock declaration",
        exact_identity=True,
        quantitative_authority=True,
        composition_complete=True,
        authority_notes=authority_notes,
    )


def _project(
    ideal: IdealProposal,
    stocks: tuple[ExactStockRef, ...],
    *,
    inventory_hash: str = "a" * 64,
    overlay_hash: str = "b" * 64,
) -> InventoryProjection:
    return project_ideal_to_current_build(
        ideal,
        stocks,
        inventory_content_sha256=inventory_hash,
        stock_authority_overlay_sha256=overlay_hash,
        stock_authority_snapshot_id="inventory-v7-20260830",
    )


def _wood_family_resolution(
    ideal: IdealProposal,
    *,
    family_id: str = "family:woody-floral",
    resolved: bool = True,
) -> FamilyResolution:
    provenance = _provenance()
    definition_ref = FamilyDefinitionRef(family_id, "2026.1")
    request = FamilyArchitectureRequest(
        request_id="family-request-wood-whole",
        target_scope=ideal.ideal_target_id,
        named_target=ideal.ideal_target_id,
        requested_definition=definition_ref,
        family_neighborhood=(),
        temporal_scope="opening through drydown",
        matrix_scope="ethanol fragrance matrix; exact formula unresolved",
        provenance_refs=(provenance,),
    )
    if not resolved:
        return FamilyResolution(
            resolution_id="family-resolution-wood-whole-unresolved",
            request=request,
            status=FamilyResolutionStatus.UNKNOWN_FAMILY,
            definition=None,
            named_target=request.named_target,
            family_neighborhood=(),
            reason="Exact family definition unavailable.",
            provenance_refs=(provenance,),
        )
    definition = FamilyDefinition(
        definition_ref=definition_ref,
        label="Woody floral integration test definition",
        definition_kind=FamilyDefinitionKind.REFERENCE,
        component_definitions=(),
        architecture_planes=(
            FamilyPlane(
                plane_id="heart",
                order_index=0,
                label="Floral wood heart",
                structural_function="Bind the floral subject to a differentiated wood role.",
                temporal_window="heart",
            ),
            FamilyPlane(
                plane_id="drydown",
                order_index=1,
                label="Wood residue",
                structural_function="Keep the named subject traceable through residue.",
                temporal_window="drydown",
            ),
        ),
        protected_recognizers=(
            FamilyRecognizer(
                recognizer_id="floral-wood-continuity",
                label="Floral wood continuity",
                protected_function="Preserve subject identity through the wood handoff.",
                plane_ids=("heart", "drydown"),
                absence_failure="The wood base becomes disconnected from the floral heart.",
            ),
        ),
        forbidden_drift=(
            ForbiddenFamilyDrift(
                drift_id="generic-wood-pile",
                description="Generic material-count-driven woody base.",
                conflict_with_target="It erases the target-linked floral subject.",
            ),
        ),
        temporal_relations=(
            FamilyTemporalRelation(
                relation_id="heart-drydown-handoff",
                order_index=0,
                source_plane_id="heart",
                destination_plane_id="drydown",
                relation_kind="handoff",
                continuity_requirement="The named subject remains traceable.",
                failure_mode="The base appears as a disconnected slab.",
            ),
        ),
        source_version="test-source-2026.1",
        definition_evidence_class=EvidenceClass.USER_REPORT,
        provenance_refs=(provenance,),
    )
    return FamilyResolution(
        resolution_id="family-resolution-wood-whole",
        request=request,
        status=FamilyResolutionStatus.RESOLVED,
        definition=definition,
        named_target=request.named_target,
        family_neighborhood=(),
        reason=None,
        provenance_refs=(provenance,),
    )


def _temporal_assessment(target: TargetIntent) -> PlaneAssessment:
    provenance = _provenance()
    claim = ScopedClaim(
        claim_id="temporal-continuity-claim",
        claim_key="temporal_continuity",
        claim_value="magnolia petal remains traceable into the mineral drydown",
        claim_kind=ClaimKind.HYPOTHESIS,
        authority_ceiling=AuthorityCeiling.HYPOTHESIS_ONLY,
        provenance_refs=(provenance,),
    )
    return PlaneAssessment(
        assessment_id="temporal-magnolia-assessment",
        module_id="temporal-test-module",
        plane_id=PlaneId.TEMPORAL,
        scope=AssessmentScope(
            target_scope=target.ideal_target_id.value,
            temporal_scope="heart-to-drydown",
            matrix_scope="ethanol-fragrance-matrix",
        ),
        claims=(claim,),
        support_intervals=(),
        conflicts=(
            PlaneConflict(
                conflict_id="temporal-reveal-alternatives",
                claim_key="temporal_continuity",
                alternatives=("continuous petal trace", "delayed mineral reveal"),
                reason="both reveal paths remain structural alternatives",
                claim_ids=(claim.claim_id,),
                provenance_refs=(provenance,),
            ),
        ),
        unknowns=(
            UnknownFact(
                unknown_id="temporal-observation-missing",
                field_key="observed_temporal_transition",
                reason="no exact sensory observation exists",
                needed_evidence="time-resolved blinded observation",
                provenance_refs=(provenance,),
            ),
        ),
        failure_modes=("heart and drydown become disconnected",),
        proposed_experiments=("constant-total time-resolved comparison",),
        provenance_refs=(provenance,),
        authority_ceiling=AuthorityCeiling.HYPOTHESIS_ONLY,
        freshness_hashes=("3" * 64,),
        native_criteria=(
            ParetoCriterion(
                criterion_id="transition_continuity",
                direction=CriterionDirection.PRESERVE,
                value=CriterionValue.unknown("no candidate observation exists"),
                unit="criterion-specific observation",
                authority_ceiling=AuthorityCeiling.HYPOTHESIS_ONLY,
                provenance_refs=(provenance,),
            ),
        ),
    )


def test_projection_binds_typed_target_build_and_preserves_immutable_ideal() -> None:
    ideal = _ideal("Clearwood")
    before = ideal.content_sha256
    projection = _project(ideal, (_stock(),))

    assert isinstance(ideal.target_intent, TargetIntent)
    assert isinstance(projection.build_projection_id, BuildProjectionId)
    assert projection.build_projection_id.ideal_target_id == ideal.target_intent.ideal_target_id
    assert projection.build_projection_id.inventory_content_sha256 == "a" * 64
    assert projection.ideal_proposal == ideal
    assert projection.ideal_proposal_sha256 == before
    assert projection.target_intent_sha256 == ideal.target_intent.content_sha256
    assert projection.authority_ceiling is AuthorityCeiling.STRUCTURAL_ONLY
    assert ideal.content_sha256 == before
    with pytest.raises(FrozenInstanceError):
        projection.ideal_proposal = _ideal("Alpha Irone")  # type: ignore[misc]


def test_stock_authority_notes_and_separate_overlay_hash_change_projection_identity() -> None:
    ideal = _ideal("Clearwood")
    first = _project(ideal, (_stock(authority_notes=("first note",)),))
    changed_note = _project(ideal, (_stock(authority_notes=("second note",)),))
    changed_overlay = _project(
        ideal,
        (_stock(authority_notes=("first note",)),),
        overlay_hash="c" * 64,
    )

    assert first.lines == changed_note.lines
    assert first.stock_authority_records_sha256 != changed_note.stock_authority_records_sha256
    assert first.projection_id != changed_note.projection_id
    assert first.content_sha256 != changed_note.content_sha256
    assert first.inventory_content_sha256 == changed_overlay.inventory_content_sha256
    assert first.stock_authority_overlay_sha256 != changed_overlay.stock_authority_overlay_sha256
    assert first.projection_id != changed_overlay.projection_id


def test_closed_schemas_require_version_all_fields_no_extras_and_real_booleans() -> None:
    stock = _stock()
    for mutation in ("missing_schema", "missing_field", "extra_field", "string_bool"):
        payload = stock.as_dict()
        if mutation == "missing_schema":
            payload.pop("schema_version")
        elif mutation == "missing_field":
            payload.pop("composition_complete")
        elif mutation == "extra_field":
            payload["unreviewed"] = True
        else:
            payload["exact_identity"] = "false"
        with pytest.raises((TypeError, ValueError)):
            ExactStockRef.from_dict(payload)

    assert ExactStockRef.from_dict(stock.as_dict()) == stock
    projection = _project(_ideal("Clearwood"), (stock,))
    payload = projection.as_dict()
    payload["physical_execution_authorized"] = 0
    with pytest.raises(TypeError, match="bool"):
        InventoryProjection.from_dict(payload)


def test_ambiguous_stock_holds_without_quantitative_math_and_adapter_is_lossless() -> None:
    ideal = _ideal("Test Material")
    first = replace(
        _stock("Test Material"),
        exact_stock_ref="inventory:test:a",
        fraction=0.10,
        fraction_basis="w/w",
        carrier="dep",
    )
    second = replace(first, exact_stock_ref="inventory:test:b", carrier="dpg")
    projection = _project(ideal, (first, second))
    line = projection.lines[0]

    assert line.disposition is ProjectionDisposition.HOLD
    assert projection.authority_ceiling is AuthorityCeiling.WITHHELD
    assert line.exact_stock_ref is None
    assert line.candidate_stock_refs == ("inventory:test:a", "inventory:test:b")
    assert "AMBIGUOUS_EXACT_STOCK_REF" in line.hold_reasons
    assert {
        line.active_amount_ul,
        line.concentration_ppm,
        line.oav,
        line.carrier_displacement_ul,
    } == {None}

    assessment = projection.to_plane_assessment()
    restored = PlaneAssessment.from_dict(assessment.as_dict())
    assert restored == assessment
    assert assessment.plane_id is PlaneId.INVENTORY_BUILD
    assert assessment.scope == ideal.target_intent.to_plane_assessment().scope
    assert assessment.authority_ceiling is AuthorityCeiling.WITHHELD
    assert assessment.support_intervals == ()
    assert {item.content_sha256 for item in assessment.provenance_refs}.issuperset(
        {item.content_sha256 for item in ideal.target_intent.provenance_refs}
    )
    assert assessment.conflicts[0].alternatives == line.candidate_stock_refs
    assert any("AMBIGUOUS_EXACT_STOCK_REF" in item.reason for item in assessment.unknowns)
    assert projection.stock_authority_records_sha256 in assessment.freshness_hashes
    assert projection.stock_authority_overlay_sha256 in assessment.freshness_hashes


def test_unresolved_target_remains_typed_and_withheld_through_projection_and_blueprint() -> None:
    ideal = _ideal("Clearwood", resolved=False)
    projection = _project(ideal, (_stock(),))
    blueprint = assemble_whole_perfume_blueprint(ideal, projection, (), version=1)

    assert ideal.target_intent.resolution is TargetResolution.UNRESOLVED_HOLD
    assert "request_source" in ideal.target_intent.unresolved_fields
    assert projection.target_intent == ideal.target_intent
    assert projection.authority_ceiling is AuthorityCeiling.WITHHELD
    assert blueprint.ideal_proposal.target_intent == ideal.target_intent
    assert blueprint.authority_ceiling is AuthorityCeiling.WITHHELD
    assert blueprint.physical_execution_authorized is False
    assert blueprint.observed_smell is False
    assert blueprint.release_authorized is False


def test_whole_blueprint_preserves_complete_assessment_and_synthesis_sources() -> None:
    ideal = _ideal("Clearwood")
    projection = _project(ideal, (_stock(),))
    assessment = _temporal_assessment(ideal.target_intent)
    synthesis = synthesize_plane_assessments((assessment,))
    blueprint = assemble_whole_perfume_blueprint(
        ideal,
        projection,
        (assessment,),
        syntheses=(synthesis,),
        version=1,
    )
    restored = WholePerfumeBlueprint.from_dict(blueprint.as_dict())
    temporal = next(item for item in blueprint.planes if item.plane_id is PlaneId.TEMPORAL)

    assert restored == blueprint
    assert restored.content_sha256 == blueprint.content_sha256
    assert temporal.assessments == (assessment,)
    assert temporal.syntheses == (synthesis,)
    assert set(temporal.source_hashes) == {
        assessment.content_sha256,
        synthesis.content_sha256,
    }
    assert assessment.conflicts[0] in temporal.conflicts
    assert assessment.unknowns[0] in temporal.unknowns
    assert assessment.native_criteria[0] in temporal.native_criteria
    assert assessment.proposed_experiments[0] in temporal.proposed_experiments
    assert assessment.provenance_refs[0] in temporal.provenance_refs
    assert blueprint.authority_ceiling is AuthorityCeiling.STRUCTURAL_ONLY
    assert blueprint.authority_ceiling is not AuthorityCeiling.DESIGN_ONLY
    assert blueprint.proposed_experiments
    assert blueprint.alternatives


def test_missing_or_fabricated_plane_sources_fail_closed() -> None:
    ideal = _ideal("Clearwood")
    projection = _project(ideal, (_stock(),))
    assessment = _temporal_assessment(ideal.target_intent)
    synthesis = synthesize_plane_assessments((assessment,))
    blueprint = assemble_whole_perfume_blueprint(
        ideal,
        projection,
        (assessment,),
        syntheses=(synthesis,),
        version=1,
    )
    payload = blueprint.as_dict()
    temporal = next(
        item for item in payload["planes"] if item["plane_id"] == PlaneId.TEMPORAL.value
    )
    temporal["assessments"] = []
    temporal["source_hashes"] = [synthesis.content_sha256]
    with pytest.raises(ValueError, match="omitted"):
        WholePerfumeBlueprint.from_dict(payload)

    plane_payload = blueprint.planes[0].as_dict()
    plane_payload["source_hashes"] = ["f" * 64]
    with pytest.raises(ValueError, match="derived"):
        PlaneBlueprint.from_dict(plane_payload)

    extra = deepcopy(blueprint.as_dict())
    extra["unreviewed_summary"] = "pass"
    with pytest.raises(ValueError, match="closed"):
        WholePerfumeBlueprint.from_dict(extra)


def test_successor_binds_predecessor_and_rejects_projection_for_another_ideal() -> None:
    ideal = _ideal("Clearwood")
    projection = _project(ideal, (_stock(),))
    first = assemble_whole_perfume_blueprint(ideal, projection, (), version=1)
    second = assemble_whole_perfume_blueprint(
        ideal,
        projection,
        (),
        version=2,
        predecessor_sha256=first.content_sha256,
    )
    assert second.predecessor_sha256 == first.content_sha256
    assert second.blueprint_id != first.blueprint_id
    with pytest.raises(ValueError, match="predecessor"):
        assemble_whole_perfume_blueprint(ideal, projection, (), version=2)

    other = _ideal("Clearwood", resolved=False)
    other_projection = _project(other, (_stock(),))
    with pytest.raises(ValueError, match="supplied ideal"):
        assemble_whole_perfume_blueprint(ideal, other_projection, (), version=1)


def test_current_inventory_corrections_remain_exact_and_fail_closed() -> None:
    stocks = {item.exact_stock_ref: item for item in current_inventory_stock_corrections()}
    alpha = stocks["inventory:v7:alpha-irone:10pct-ww-dep"]
    agarwood = stocks["inventory:v7:black-agarwood-artificial:10pct-ww-dpg"]
    benzyl = stocks["inventory:v8:benzyl-salicylate:neat"]

    assert (alpha.fraction, alpha.fraction_basis, alpha.carrier) == (0.10, "w/w", "dep")
    assert (agarwood.fraction, agarwood.fraction_basis, agarwood.carrier) == (
        0.10,
        "w/w",
        "dpg",
    )
    assert (
        benzyl.material_name,
        benzyl.availability,
        benzyl.fraction,
        benzyl.fraction_basis,
        benzyl.carrier,
        benzyl.aliquot_state,
        benzyl.exact_identity,
        benzyl.quantitative_authority,
        benzyl.composition_complete,
    ) == (
        "benzyl salicylate",
        StockAvailability.OWNED,
        1.0,
        "neat_as_supplied",
        "none",
        AliquotState.READY,
        True,
        True,
        True,
    )
    assert all(
        not (
            item.material_name == "black agarwood artificial"
            and item.availability is StockAvailability.OWNED
            and item.fraction == 1.0
        )
        for item in stocks.values()
    )
    ambrofix = stocks["inventory:historical:ambrofix-liquid:7.27pct-ww-heterogeneous"]
    assert ambrofix.availability is StockAvailability.HISTORICAL_ONLY
    assert ambrofix.aliquot_state is AliquotState.HETEROGENEOUS
    bacdanol = stocks["inventory:v8:bacdanol:neat"]
    guaiacwood = stocks["inventory:v8:guaiacwood-eo:one-third-ww"]
    assert (
        bacdanol.fraction,
        bacdanol.fraction_basis,
        bacdanol.carrier,
        bacdanol.aliquot_state,
        bacdanol.quantitative_authority,
        bacdanol.composition_complete,
    ) == (
        1.0,
        "neat_as_supplied",
        "none",
        AliquotState.READY,
        True,
        True,
    )
    assert guaiacwood.fraction == pytest.approx(1.0 / 3.0)
    assert (
        guaiacwood.fraction_basis,
        guaiacwood.carrier,
        guaiacwood.aliquot_state,
        guaiacwood.quantitative_authority,
        guaiacwood.composition_complete,
    ) == (
        "mass_fraction",
        "ethanol + dep",
        AliquotState.READY,
        True,
        True,
    )

    projection = _project(
        _ideal(
            "Castoreum Synthetic",
            "Bacdanol",
            "Guaiacwood EO",
            "Benzyl Salicylate",
        ),
        tuple(stocks.values()),
    )
    by_material = {line.ideal_material_name: line for line in projection.lines}
    assert by_material["castoreum synthetic"].disposition is ProjectionDisposition.HOLD
    assert "FRACTION_BASIS_UNRESOLVED" in (
        by_material["castoreum synthetic"].hold_reasons
    )
    assert (
        by_material["bacdanol"].disposition
        is ProjectionDisposition.BUILD_IDENTIFIED
    )
    assert by_material["bacdanol"].hold_reasons == ()
    assert (
        by_material["guaiacwood eo"].disposition
        is ProjectionDisposition.BUILD_IDENTIFIED
    )
    assert by_material["guaiacwood eo"].hold_reasons == ()
    assert (
        by_material["benzyl salicylate"].disposition
        is ProjectionDisposition.BUILD_IDENTIFIED
    )
    assert (
        by_material["benzyl salicylate"].exact_stock_ref
        == "inventory:v8:benzyl-salicylate:neat"
    )
    assert by_material["benzyl salicylate"].hold_reasons == ()
    assert projection.physical_execution_authorized is False
    assert projection.release_authorized is False


def test_wood_planes_survive_whole_perfume_assembly_without_authority_gain() -> None:
    ideal = _ideal("Bacdanol")
    projection = _project(ideal, current_inventory_stock_corrections())
    registry = default_wood_capability_registry()
    request = WoodTargetRequest(
        target_id=ideal.ideal_target_id,
        family_id="family:woody-floral",
        required_functional_roles=(WoodFunctionalRole.CREAMY_BODY,),
    )

    blueprint = assemble_wood_whole_perfume_blueprint(
        ideal,
        projection,
        request,
        registry=registry,
        family_resolution=_wood_family_resolution(ideal),
        temporal_scope="opening through drydown",
        matrix_scope="ethanol fragrance matrix; exact formula unresolved",
        condition_scope="structural design hypothesis only",
        version=1,
    )
    by_plane = {plane.plane_id: plane for plane in blueprint.planes}

    assert {
        PlaneId.IDENTITY,
        PlaneId.FUNCTION,
        PlaneId.HEDONIC,
        PlaneId.RELATION,
    }.issubset(by_plane)
    assert any(
        registry.content_sha256 in assessment.freshness_hashes
        for assessment in by_plane[PlaneId.FUNCTION].assessments
    )
    assert any(
        registry.content_sha256 in assessment.freshness_hashes
        for assessment in by_plane[PlaneId.HEDONIC].assessments
    )
    assert blueprint.authority_ceiling is AuthorityCeiling.WITHHELD
    assert blueprint.physical_execution_authorized is False
    assert blueprint.observed_smell is False
    assert blueprint.release_authorized is False


def test_wood_whole_assembly_rejects_an_unrelated_family_resolution() -> None:
    ideal = _ideal("Bacdanol")
    projection = _project(ideal, current_inventory_stock_corrections())
    registry = default_wood_capability_registry()
    request = WoodTargetRequest(
        target_id=ideal.ideal_target_id,
        family_id="family:woody-floral",
        required_functional_roles=(WoodFunctionalRole.CREAMY_BODY,),
    )

    with pytest.raises(ValueError, match="exact wood family"):
        assemble_wood_whole_perfume_blueprint(
            ideal,
            projection,
            request,
            registry=registry,
            family_resolution=_wood_family_resolution(
                ideal,
                family_id="family:unrelated",
            ),
            temporal_scope="opening through drydown",
            matrix_scope="ethanol fragrance matrix; exact formula unresolved",
            condition_scope="structural design hypothesis only",
            version=1,
        )


def test_unresolved_family_withholds_wood_frontier_in_whole_assembly() -> None:
    ideal = _ideal("Bacdanol")
    projection = _project(ideal, current_inventory_stock_corrections())
    registry = default_wood_capability_registry()
    request = WoodTargetRequest(
        target_id=ideal.ideal_target_id,
        family_id="family:woody-floral",
        required_functional_roles=(WoodFunctionalRole.CREAMY_BODY,),
    )
    blueprint = assemble_wood_whole_perfume_blueprint(
        ideal,
        projection,
        request,
        registry=registry,
        family_resolution=_wood_family_resolution(ideal, resolved=False),
        temporal_scope="opening through drydown",
        matrix_scope="ethanol fragrance matrix; exact formula unresolved",
        condition_scope="structural design hypothesis only",
        version=1,
    )
    by_plane = {plane.plane_id: plane for plane in blueprint.planes}
    function_assessment = by_plane[PlaneId.FUNCTION].assessments[0]
    relation_assessment = by_plane[PlaneId.RELATION].assessments[0]

    assert not any(
        claim.claim_key == "wood.target_linked_candidate"
        for claim in function_assessment.claims
    )
    assert any(
        item.field_key == "wood.candidate_frontier"
        for item in function_assessment.unknowns
    )
    assert any(
        item.field_key == "wood.relation.candidate_frontier"
        for item in relation_assessment.unknowns
    )
    assert blueprint.authority_ceiling is AuthorityCeiling.WITHHELD
