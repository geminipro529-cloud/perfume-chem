"""Adapters from the central wood registry into formulation planes.

These adapters expose one registry to family, function, relation/accord, and
hedonic consumers.  They never create a formula or numeric liking value.  The
outputs are ordinary :class:`PlaneAssessment` records, so whole-perfume
synthesis can preserve the wood layer without flattening it into one score.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Iterable

from .accord_graph import (
    MANDATORY_GRAPH_EXCLUSIONS,
    AccordRelationGraph,
    EdgeOrientation,
    EpistemicState,
    GraphEdge,
    GraphNode,
    GraphScope,
    GraphUnknown,
    NodeKind,
    RelationKind,
    accord_graph_to_plane_assessment,
)
from .candidate_selector import (
    CandidateRequirement,
    CandidateSelectionReport,
    InventoryState,
    MaterialCapabilityDeclaration,
    select_candidates,
)
from .contracts import (
    AssessmentScope,
    AuthorityCeiling,
    ClaimCardinality,
    ClaimKind,
    CriterionDirection,
    CriterionValue,
    ParetoCriterion,
    PlaneAssessment,
    PlaneId,
    ProvenanceRef,
    ScopedClaim,
    UnknownFact,
)
from .family_architecture import (
    FamilyArchitectureAdapter,
    FamilyResolution,
    FamilyResolutionStatus,
)
from .inventory_projection import (
    AliquotState,
    ExactStockRef,
    IdealProposal,
    InventoryProjection,
    StockAvailability,
)
from .whole_perfume_assembler import (
    WholePerfumeBlueprint,
    assemble_whole_perfume_blueprint,
)
from .wood_registry import (
    QuantitativeOAVState,
    WoodCandidateDisposition,
    WoodCandidateMatch,
    WoodCapabilityRegistry,
    WoodFacet,
    WoodFunctionalRole,
    WoodGroup,
    WoodMaterialCapability,
    WoodTargetRequest,
)


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def _canonical_json(value: object) -> str:
    if hasattr(value, "as_dict"):
        value = value.as_dict()  # type: ignore[union-attr]
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _plane_union(*values: PlaneId) -> tuple[PlaneId, ...]:
    return tuple(sorted(set(values), key=lambda item: item.value))


def _merged_provenance(
    values: Iterable[ProvenanceRef],
) -> tuple[ProvenanceRef, ...]:
    by_id: dict[str, ProvenanceRef] = {}
    for value in values:
        if not isinstance(value, ProvenanceRef):
            raise TypeError("provenance must contain ProvenanceRef values")
        existing = by_id.get(value.provenance_id)
        if existing is not None and existing != value:
            raise ValueError(
                f"provenance_id {value.provenance_id!r} has conflicting definitions"
            )
        by_id[value.provenance_id] = value
    return tuple(by_id[key] for key in sorted(by_id))


def wood_candidate_requirement(request: WoodTargetRequest) -> CandidateRequirement:
    """Translate one exact wood request into the shared selector vocabulary."""

    if not isinstance(request, WoodTargetRequest):
        raise TypeError("request must be a WoodTargetRequest")
    return CandidateRequirement(
        target_id=request.target_id,
        target_name=request.target_id,
        required_recognizers=(
            *(f"wood-group:{value.value}" for value in request.required_groups),
            *(f"wood-facet:{value.value}" for value in request.required_facets),
        ),
        exclusions=tuple(
            f"wood-facet:{value.value}" for value in request.forbidden_facets
        ),
        required_temporal_roles=(),
        required_spatial_roles=(),
        required_functional_roles=tuple(
            value.value for value in request.required_functional_roles
        ),
        minimum_authority=AuthorityCeiling.STRUCTURAL_ONLY,
    )


def _stock_records_by_ref(
    stock_refs: Iterable[ExactStockRef],
) -> dict[str, ExactStockRef]:
    records: dict[str, ExactStockRef] = {}
    for stock in stock_refs:
        if not isinstance(stock, ExactStockRef):
            raise TypeError("stock_refs must contain ExactStockRef values")
        if stock.exact_stock_ref in records:
            raise ValueError(
                f"stock_refs contains duplicate exact stock {stock.exact_stock_ref!r}"
            )
        records[stock.exact_stock_ref] = stock
    return records


def _bound_stock_state(
    item: WoodMaterialCapability,
    records: dict[str, ExactStockRef] | None,
) -> tuple[InventoryState, str | None, bool | None]:
    if records is None:
        return InventoryState.UNKNOWN, None, None
    stock = records.get(item.exact_stock_ref)
    if stock is None:
        return InventoryState.UNKNOWN, None, None
    if stock.availability is not StockAvailability.OWNED:
        return InventoryState.NOT_OWNED, None, False
    bound_hashes = {
        ref.source_sha256
        for ref in item.provenance_refs
        if ref.provenance_id.startswith("wood-stock:")
        and ref.source_ref == item.exact_stock_ref
        and ref.source_sha256 is not None
    }
    exact_bound_record = (
        bound_hashes == {stock.content_sha256}
        and stock.material_name.casefold() == item.canonical_material_name.casefold()
        and stock.exact_identity
        and stock.composition_complete
        and stock.quantitative_authority
        and stock.aliquot_state is AliquotState.READY
    )
    if not exact_bound_record:
        return InventoryState.UNKNOWN, None, None
    return InventoryState.OWNED, stock.exact_stock_ref, True


@dataclass(frozen=True, slots=True)
class WoodCandidateBundle:
    """One exact shared selector result consumed by every wood plane."""

    request_sha256: str
    registry_sha256: str
    requirement: CandidateRequirement
    declarations: tuple[MaterialCapabilityDeclaration, ...]
    report: CandidateSelectionReport
    frontier: tuple[tuple[WoodCandidateMatch, WoodMaterialCapability], ...]

    def __post_init__(self) -> None:
        if self.requirement.content_sha256 != self.report.requirement_sha256:
            raise ValueError("candidate report is not bound to its requirement")
        declaration_hashes = tuple(
            f"{item.candidate_id}={item.content_sha256}"
            for item in sorted(self.declarations, key=lambda value: value.candidate_id)
        )
        if declaration_hashes != self.report.declaration_sha256s:
            raise ValueError("candidate report is not bound to its declarations")
        frontier_ids = tuple(item.capability_id for item, _ in self.frontier)
        if frontier_ids != self.report.ideal_frontier_ids:
            raise ValueError("candidate frontier must come from the shared report")
        if any(item.registry_sha256 != self.registry_sha256 for item, _ in self.frontier):
            raise ValueError("candidate frontier is bound to another registry")


def _match_from_shared_assessment(
    assessment: object,
    *,
    registry_sha256: str,
) -> WoodCandidateMatch:
    recognizers = tuple(getattr(assessment, "matched_recognizers"))
    group_by_value = {value.value.casefold(): value for value in WoodGroup}
    facet_by_value = {value.value.casefold(): value for value in WoodFacet}
    role_by_value = {value.value.casefold(): value for value in WoodFunctionalRole}
    groups = tuple(
        group_by_value[value.removeprefix("wood-group:").casefold()]
        for value in recognizers
        if value.startswith("wood-group:")
    )
    facets = tuple(
        facet_by_value[value.removeprefix("wood-facet:").casefold()]
        for value in recognizers
        if value.startswith("wood-facet:")
    )
    roles = tuple(
        role_by_value[value.casefold()]
        for value in getattr(assessment, "matched_functional_roles")
    )
    return WoodCandidateMatch(
        capability_id=getattr(assessment, "candidate_id"),
        disposition=WoodCandidateDisposition.FRONTIER,
        matched_groups=groups,
        matched_functional_roles=roles,
        matched_facets=facets,
        reason_codes=("shared_pareto_frontier",),
        registry_sha256=registry_sha256,
    )


def _candidate_bundle_from_declarations(
    request: WoodTargetRequest,
    registry: WoodCapabilityRegistry,
    declarations: tuple[MaterialCapabilityDeclaration, ...],
) -> WoodCandidateBundle:
    requirement = wood_candidate_requirement(request)
    report = select_candidates(requirement, declarations)
    material_by_id = {item.capability_id: item for item in registry.materials}
    ideal_by_id = {item.candidate_id: item for item in report.ideal_assessments}
    frontier = tuple(
        (
            _match_from_shared_assessment(
                ideal_by_id[candidate_id],
                registry_sha256=registry.content_sha256,
            ),
            material_by_id[candidate_id],
        )
        for candidate_id in report.ideal_frontier_ids
    )
    return WoodCandidateBundle(
        request_sha256=request.content_sha256,
        registry_sha256=registry.content_sha256,
        requirement=requirement,
        declarations=declarations,
        report=report,
        frontier=frontier,
    )


def build_wood_candidate_bundle(
    request: WoodTargetRequest,
    *,
    registry: WoodCapabilityRegistry,
    stock_refs: Iterable[ExactStockRef] | None = None,
) -> WoodCandidateBundle:
    return _candidate_bundle_from_declarations(
        request,
        registry,
        wood_candidate_declarations(registry, stock_refs=stock_refs),
    )


def _require_candidate_bundle(
    request: WoodTargetRequest,
    registry: WoodCapabilityRegistry,
    candidate_bundle: WoodCandidateBundle | None,
    stock_refs: Iterable[ExactStockRef] | None,
) -> WoodCandidateBundle:
    if candidate_bundle is None:
        return build_wood_candidate_bundle(
            request,
            registry=registry,
            stock_refs=stock_refs,
        )
    if stock_refs is not None:
        raise ValueError("stock_refs cannot be supplied with a candidate_bundle")
    if candidate_bundle.request_sha256 != request.content_sha256:
        raise ValueError("candidate bundle is bound to another wood request")
    if candidate_bundle.registry_sha256 != registry.content_sha256:
        raise ValueError("candidate bundle is bound to another wood registry")
    return candidate_bundle


def _require_assessment_scope(
    request: WoodTargetRequest,
    scope: AssessmentScope,
) -> None:
    if not isinstance(scope, AssessmentScope):
        raise TypeError("scope must be an AssessmentScope")
    if scope.target_scope != request.target_id:
        raise ValueError("wood assessment scope must match the exact target request")


def _require_graph_scope(request: WoodTargetRequest, scope: GraphScope) -> None:
    if not isinstance(scope, GraphScope):
        raise TypeError("scope must be a GraphScope")
    if scope.target_scope != request.target_id:
        raise ValueError("wood graph scope must match the exact target request")


def wood_capabilities_for_family(
    resolution: FamilyResolution,
    *,
    registry: WoodCapabilityRegistry,
    required_groups: Iterable[WoodGroup] = (),
    required_functional_roles: Iterable[WoodFunctionalRole] = (),
    required_facets: Iterable[WoodFacet] = (),
    forbidden_facets: Iterable[WoodFacet] = (),
) -> tuple[WoodCandidateMatch, ...]:
    """Resolve wood candidates only beneath an exact family resolution.

    A resolved family name alone is insufficient.  At least one target-linked
    group, role, or facet must also be declared, so ownership cannot become a
    generic family-fit assertion.
    """

    if not isinstance(resolution, FamilyResolution):
        raise TypeError("resolution must be a FamilyResolution")
    groups = tuple(required_groups)
    roles = tuple(required_functional_roles)
    facets = tuple(required_facets)
    forbidden = tuple(forbidden_facets)
    if resolution.status is not FamilyResolutionStatus.RESOLVED:
        return ()
    if not (groups or roles or facets):
        return ()
    if resolution.definition is None:  # defensive; FamilyResolution also enforces this
        return ()
    request = WoodTargetRequest(
        target_id=resolution.named_target,
        family_id=resolution.definition.definition_ref.family_id,
        required_groups=groups,
        required_functional_roles=roles,
        required_facets=facets,
        forbidden_facets=forbidden,
    )
    bundle = build_wood_candidate_bundle(request, registry=registry)
    return tuple(match for match, _ in bundle.frontier)


def wood_candidate_declarations(
    registry: WoodCapabilityRegistry,
    *,
    stock_refs: Iterable[ExactStockRef] | None = None,
) -> tuple[MaterialCapabilityDeclaration, ...]:
    """Translate the registry once into the generic candidate-selector contract."""

    if not isinstance(registry, WoodCapabilityRegistry):
        raise TypeError("registry must be a WoodCapabilityRegistry")
    records = None if stock_refs is None else _stock_records_by_ref(stock_refs)
    declarations = []
    for item in registry.materials:
        inventory_state, exact_stock_ref, execution_ready = _bound_stock_state(
            item,
            records,
        )
        declarations.append(
            MaterialCapabilityDeclaration(
                candidate_id=item.capability_id,
                material_name=item.canonical_material_name,
                exact_identity_ref=(
                    f"wood-identity:{item.capability_id}:{registry.semantic_version}"
                ),
                target_recognizers=(
                    *(f"wood-group:{value.value}" for value in item.groups),
                    *(f"wood-facet:{value.value}" for value in item.facets),
                ),
                exclusion_tags=tuple(
                    f"wood-facet:{value.value}" for value in item.facets
                ),
                temporal_roles=tuple(
                    value.value for value in item.temporal_windows
                ),
                spatial_roles=(),
                functional_roles=tuple(
                    value.value for value in item.functional_roles
                ),
                authority_ceiling=item.authority_ceiling,
                provenance_refs=tuple(
                    f"{ref.provenance_id}:{ref.source_sha256 or 'unbound'}"
                    for ref in item.provenance_refs
                ),
                declaration_complete=True,
                missing_data=(),
                inventory_state=inventory_state,
                exact_stock_ref=exact_stock_ref,
                execution_ready=execution_ready,
            )
        )
    return tuple(sorted(declarations, key=lambda item: item.candidate_id))


def wood_candidate_selection_report(
    request: WoodTargetRequest,
    *,
    registry: WoodCapabilityRegistry,
    stock_refs: Iterable[ExactStockRef] | None = None,
) -> CandidateSelectionReport:
    """Run the shared non-scalar Pareto selector on registry declarations."""

    return build_wood_candidate_bundle(
        request,
        registry=registry,
        stock_refs=stock_refs,
    ).report


def _oav_unknown(
    item: WoodMaterialCapability,
) -> tuple[str, str]:
    if item.quantitative_oav_state is (
        QuantitativeOAVState.NATURAL_COMPOSITE_REQUIRED_UNBOUND
    ):
        return (
            "Natural-mixture OAV is unavailable; no exact-lot composite "
            "decomposition and constituent threshold lineage is bound",
            "exact-identity natural decomposition, constituent fractions, "
            "constituent ODT lineage, stock density when dosing by volume, and "
            "condition-bound composite OAV",
        )
    if item.quantitative_oav_state is (
        QuantitativeOAVState.OPAQUE_BULK_REFERENCE_REQUIRED_UNBOUND
    ):
        return (
            "Opaque product OAV is unavailable; no exact-product bulk threshold "
            "or composition-bound quantitative model is authorized",
            "exact-product bulk threshold or disclosed composition with matching "
            "physical data and condition-bound validation",
        )
    return (
        "The structural registry does not authorize a quantitative OAV",
        "condition-bound ppm, ODT, activity coefficient, vapor pressure, matrix, "
        "temperature, and model provenance",
    )


def wood_function_plane_assessment(
    request: WoodTargetRequest,
    *,
    registry: WoodCapabilityRegistry,
    scope: AssessmentScope,
    stock_refs: Iterable[ExactStockRef] | None = None,
    candidate_bundle: WoodCandidateBundle | None = None,
) -> PlaneAssessment:
    """Emit target-linked wood roles as non-formula structural hypotheses."""

    _require_assessment_scope(request, scope)
    candidates = _require_candidate_bundle(
        request,
        registry,
        candidate_bundle,
        stock_refs,
    )
    frontier = candidates.frontier
    provenance = _merged_provenance(
        ref for _, item in frontier for ref in item.provenance_refs
    )
    if not provenance:
        provenance = _merged_provenance(
            ref for item in registry.materials for ref in item.provenance_refs
        )
    claims: list[ScopedClaim] = [
        ScopedClaim(
            claim_id=f"wood-candidate-report-{candidates.report.report_id}",
            claim_key="wood.candidate_selection_report",
            claim_value=_canonical_json(candidates.report),
            claim_kind=ClaimKind.DIAGNOSTIC,
            authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
            provenance_refs=provenance,
        )
    ]
    for match, item in frontier:
        claims.append(
            ScopedClaim(
                claim_id=f"wood-candidate-{_slug(item.capability_id)}",
                claim_key="wood.target_linked_candidate",
                claim_value=_canonical_json(
                    {
                        "capability": item.as_dict(),
                        "match": match.as_dict(),
                        "target_request_sha256": request.content_sha256,
                    }
                ),
                claim_kind=ClaimKind.HYPOTHESIS,
                authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
                provenance_refs=item.provenance_refs,
                cardinality=ClaimCardinality.SET_MEMBER,
                member_id=item.capability_id,
            )
        )
    for exclusion in sorted(
        {value for item in registry.materials for value in item.authority_exclusions}
    ):
        claims.append(
            ScopedClaim(
                claim_id=f"wood-exclusion-{_slug(exclusion)}",
                claim_key="wood.authority_exclusion",
                claim_value=exclusion,
                claim_kind=ClaimKind.PROHIBITION,
                authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
                provenance_refs=provenance,
                cardinality=ClaimCardinality.SET_MEMBER,
                member_id=f"wood-exclusion:{_slug(exclusion)}",
            )
        )

    unknowns = [
        UnknownFact(
            unknown_id=f"wood-oav-{_slug(item.capability_id)}",
            field_key=f"wood.quantitative_oav.{item.capability_id}",
            reason=_oav_unknown(item)[0],
            needed_evidence=_oav_unknown(item)[1],
            provenance_refs=item.provenance_refs,
        )
        for _, item in frontier
    ]
    unknowns.append(
        UnknownFact(
            unknown_id="wood-observed-target-fit",
            field_key="wood.observed_target_fit",
            reason=(
                "Structural role matching does not observe smell, depth, richness, "
                "transition quality, or target identity"
            ),
            needed_evidence=(
                "carrier-matched controlled smelling at declared time windows with "
                "exact formula and assessor records"
            ),
            provenance_refs=provenance,
        )
    )
    if not frontier:
        unknowns.append(
            UnknownFact(
                unknown_id="wood-no-target-linked-candidate",
                field_key="wood.candidate_frontier",
                reason="No registry record matched the declared wood requirements",
                needed_evidence=(
                    "revised target requirements or a source-bound new capability "
                    "record; ownership alone is insufficient"
                ),
                provenance_refs=provenance,
            )
        )
    freshness = {
        registry.content_sha256,
        registry.stock_authority_sha256,
        request.content_sha256,
        candidates.requirement.content_sha256,
        candidates.report.content_sha256,
        *(item.content_sha256 for item in candidates.declarations),
        *(item.content_sha256 for _, item in frontier),
        *(
            ref.source_sha256
            for ref in provenance
            if ref.source_sha256 is not None
        ),
    }
    return PlaneAssessment(
        assessment_id=(
            f"wood-function-{request.content_sha256}-{registry.content_sha256}"
        ),
        module_id="wood-capability-registry-v1",
        plane_id=PlaneId.FUNCTION,
        scope=scope,
        claims=tuple(claims),
        support_intervals=(),
        conflicts=(),
        unknowns=tuple(unknowns),
        failure_modes=(
            "HOLD: structural candidates are not formula or sensory authority",
            "HOLD: quantitative OAV requires exact physicochemical evidence",
        ),
        proposed_experiments=(
            "constant-total target-linked omission or alternative comparison",
            "time-windowed carrier-matched evaluation of the selected wood role",
        ),
        provenance_refs=provenance,
        authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
        freshness_hashes=tuple(sorted(freshness)),
        native_criteria=(),
    )


_HEDONIC_ENDPOINTS: tuple[str, ...] = (
    "comfort",
    "depth",
    "identity_clarity",
    "liking",
    "novelty",
    "richness",
    "target_fit",
)


def wood_hedonic_plane_assessment(
    request: WoodTargetRequest,
    *,
    registry: WoodCapabilityRegistry,
    scope: AssessmentScope,
    stock_refs: Iterable[ExactStockRef] | None = None,
    candidate_bundle: WoodCandidateBundle | None = None,
) -> PlaneAssessment:
    """Represent every unobserved wood hedonic endpoint as explicit UNKNOWN."""

    _require_assessment_scope(request, scope)
    candidates = _require_candidate_bundle(
        request,
        registry,
        candidate_bundle,
        stock_refs,
    )
    frontier = candidates.frontier
    provenance = _merged_provenance(
        ref for _, item in frontier for ref in item.provenance_refs
    )
    if not provenance:
        provenance = _merged_provenance(
            ref for item in registry.materials for ref in item.provenance_refs
        )
    unknowns: list[UnknownFact] = []
    criteria: list[ParetoCriterion] = []
    for _, item in frontier:
        for endpoint in _HEDONIC_ENDPOINTS:
            reason = (
                f"No exact-formula, condition-matched participant {endpoint} "
                f"observation is bound for {item.canonical_material_name}"
            )
            unknowns.append(
                UnknownFact(
                    unknown_id=(
                        f"wood-hedonic-{_slug(item.capability_id)}-{endpoint}"
                    ),
                    field_key=f"wood.hedonic.{item.capability_id}.{endpoint}",
                    reason=reason,
                    needed_evidence=(
                        "blinded participant observations with exact formula, "
                        "matrix, concentration, time, order, repeats, population, "
                        "criterion, and uncertainty"
                    ),
                    provenance_refs=item.provenance_refs,
                )
            )
            criteria.append(
                ParetoCriterion(
                    criterion_id=(
                        f"wood_{_slug(item.capability_id).replace('-', '_')}_{endpoint}"
                    ),
                    direction=(
                        CriterionDirection.PRESERVE
                        if endpoint in {"identity_clarity", "target_fit"}
                        else CriterionDirection.MAXIMIZE
                    ),
                    value=CriterionValue.unknown(reason),
                    unit="participant criterion; not tested",
                    authority_ceiling=AuthorityCeiling.WITHHELD,
                    provenance_refs=item.provenance_refs,
                )
            )
    if not frontier:
        unknowns.append(
            UnknownFact(
                unknown_id="wood-hedonic-no-candidate",
                field_key="wood.hedonic.candidate_frontier",
                reason="No target-linked wood candidate exists for hedonic evaluation",
                needed_evidence="a target-linked structural candidate frontier",
                provenance_refs=provenance,
            )
        )
    freshness = {
        registry.content_sha256,
        registry.stock_authority_sha256,
        request.content_sha256,
        candidates.requirement.content_sha256,
        candidates.report.content_sha256,
        *(item.content_sha256 for item in candidates.declarations),
        *(item.content_sha256 for _, item in frontier),
    }
    return PlaneAssessment(
        assessment_id=(
            f"wood-hedonic-{request.content_sha256}-{registry.content_sha256}"
        ),
        module_id="wood-hedonic-firewall-v1",
        plane_id=PlaneId.HEDONIC,
        scope=scope,
        claims=(),
        support_intervals=(),
        conflicts=(),
        unknowns=tuple(unknowns),
        failure_modes=(
            "NOT TESTED: no scalar or aggregate liking authority",
            "HOLD: supplier prose, stock ownership, OAV, and material priors are non-hedonic",
        ),
        proposed_experiments=(
            "blinded exact-formula participant evaluation by native criterion",
        ),
        provenance_refs=provenance,
        authority_ceiling=AuthorityCeiling.WITHHELD,
        freshness_hashes=tuple(sorted(freshness)),
        native_criteria=tuple(criteria),
    )


def wood_accord_relation_graph(
    request: WoodTargetRequest,
    *,
    registry: WoodCapabilityRegistry,
    scope: GraphScope,
    stock_refs: Iterable[ExactStockRef] | None = None,
    candidate_bundle: WoodCandidateBundle | None = None,
) -> AccordRelationGraph:
    """Expose material-to-role-to-target relations without invented synergy."""

    _require_graph_scope(request, scope)
    candidates = _require_candidate_bundle(
        request,
        registry,
        candidate_bundle,
        stock_refs,
    )
    frontier = candidates.frontier
    provenance = _merged_provenance(
        ref for _, item in frontier for ref in item.provenance_refs
    )
    if not provenance:
        provenance = _merged_provenance(
            ref for item in registry.materials for ref in item.provenance_refs
        )
    target_node_id = f"wood-target:{request.target_id}"
    nodes: list[GraphNode] = [
        GraphNode(
            node_id=target_node_id,
            node_kind=NodeKind.TARGET,
            label=request.target_id,
            scope=scope,
            plane_ids=(PlaneId.MORPHOLOGY,),
            epistemic_state=EpistemicState.DECLARED,
            authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
            provenance_refs=provenance,
        )
    ]
    feature_sources: dict[tuple[str, str], list[ProvenanceRef]] = {}
    feature_metadata: dict[
        tuple[str, str], tuple[str, NodeKind, tuple[PlaneId, ...]]
    ] = {}
    features_by_material: dict[str, tuple[tuple[str, str], ...]] = {}
    for match, item in frontier:
        nodes.append(
            GraphNode(
                node_id=f"wood-material:{item.capability_id}",
                node_kind=NodeKind.MATERIAL_CANDIDATE,
                label=item.canonical_material_name,
                scope=scope,
                plane_ids=(PlaneId.FUNCTION, PlaneId.IDENTITY),
                epistemic_state=EpistemicState.HYPOTHESIS,
                authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
                provenance_refs=item.provenance_refs,
            )
        )
        features: list[tuple[str, str]] = []
        for role in match.matched_functional_roles:
            key = ("role", role.value)
            features.append(key)
            feature_metadata[key] = (
                role.value.replace("_", " "),
                NodeKind.FUNCTIONAL_ROLE,
                (PlaneId.FUNCTION,),
            )
        for group in match.matched_groups:
            key = ("group", group.value)
            features.append(key)
            feature_metadata[key] = (
                group.value,
                NodeKind.ACCORD,
                (PlaneId.MORPHOLOGY,),
            )
        for facet in match.matched_facets:
            key = ("facet", facet.value)
            features.append(key)
            feature_metadata[key] = (
                facet.value.replace("_", " "),
                NodeKind.FACET,
                (PlaneId.MORPHOLOGY,),
            )
        features_by_material[item.capability_id] = tuple(sorted(features))
        for feature in features:
            feature_sources.setdefault(feature, []).extend(item.provenance_refs)
    for feature, refs in sorted(feature_sources.items()):
        label, node_kind, plane_ids = feature_metadata[feature]
        feature_type, feature_value = feature
        nodes.append(
            GraphNode(
                node_id=f"wood-{feature_type}:{feature_value}",
                node_kind=node_kind,
                label=label,
                scope=scope,
                plane_ids=plane_ids,
                epistemic_state=EpistemicState.HYPOTHESIS,
                authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
                provenance_refs=_merged_provenance(refs),
            )
        )

    edges: list[GraphEdge] = []
    for _, item in frontier:
        for feature in features_by_material[item.capability_id]:
            feature_type, feature_value = feature
            feature_planes = feature_metadata[feature][2]
            edges.append(
                GraphEdge(
                    edge_id=(
                        f"wood-support:{item.capability_id}:"
                        f"{feature_type}:{feature_value}"
                    ),
                    source_node_id=f"wood-material:{item.capability_id}",
                    target_node_id=f"wood-{feature_type}:{feature_value}",
                    relation_kind=RelationKind.SUPPORTS,
                    orientation=EdgeOrientation.DIRECTED,
                    scope=scope,
                    plane_ids=_plane_union(
                        PlaneId.FUNCTION,
                        PlaneId.IDENTITY,
                        PlaneId.RELATION,
                        *feature_planes,
                    ),
                    epistemic_state=EpistemicState.HYPOTHESIS,
                    authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
                    provenance_refs=item.provenance_refs,
                    rationale=(
                        "Registry-declared target-role candidacy; no mixture synergy, "
                        "observed smell, or formula ratio is inferred"
                    ),
                )
            )
    for feature, refs in sorted(feature_sources.items()):
        feature_type, feature_value = feature
        feature_planes = feature_metadata[feature][2]
        edges.append(
            GraphEdge(
                edge_id=(
                    f"wood-target-support:{feature_type}:{feature_value}"
                ),
                source_node_id=f"wood-{feature_type}:{feature_value}",
                target_node_id=target_node_id,
                relation_kind=RelationKind.SUPPORTS,
                orientation=EdgeOrientation.DIRECTED,
                scope=scope,
                plane_ids=_plane_union(
                    PlaneId.MORPHOLOGY,
                    PlaneId.RELATION,
                    *feature_planes,
                ),
                epistemic_state=EpistemicState.HYPOTHESIS,
                authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
                provenance_refs=_merged_provenance(refs),
                rationale=(
                    "The target request declared this role; physical realization "
                    "and perceptual success remain untested"
                ),
            )
        )
    graph_unknowns: tuple[GraphUnknown, ...] = ()
    if not frontier:
        graph_unknowns = (
            GraphUnknown(
                unknown_id="wood-relation-no-candidate-frontier",
                field_key="wood.relation.candidate_frontier",
                scope=scope,
                reason=(
                    "No candidate is present on the exact shared Pareto frontier; "
                    "a target-only graph is not a complete wood relation model"
                ),
                needed_evidence=(
                    "an exact family-bound target request and a source-bound shared "
                    "candidate report with at least one ideal frontier member"
                ),
                provenance_refs=provenance,
            ),
        )
    return AccordRelationGraph(
        graph_id=(
            f"wood-accord:{request.content_sha256}:{registry.content_sha256}:"
            f"{candidates.report.content_sha256}"
        ),
        scope=scope,
        nodes=tuple(nodes),
        edges=tuple(edges),
        alternative_sets=(),
        unknowns=graph_unknowns,
        provenance_refs=provenance,
        authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
        authority_exclusions=MANDATORY_GRAPH_EXCLUSIONS,
    )


@dataclass(frozen=True, slots=True)
class WoodPlaneBundle:
    """Small convenience bundle for non-flattening whole-perfume synthesis."""

    candidates: WoodCandidateBundle
    function: PlaneAssessment
    hedonic: PlaneAssessment

    def __post_init__(self) -> None:
        if not isinstance(self.candidates, WoodCandidateBundle):
            raise TypeError("candidates must be a WoodCandidateBundle")
        if self.function.plane_id is not PlaneId.FUNCTION:
            raise ValueError("function assessment must use the function plane")
        if self.hedonic.plane_id is not PlaneId.HEDONIC:
            raise ValueError("hedonic assessment must use the hedonic plane")
        if self.function.scope != self.hedonic.scope:
            raise ValueError("wood plane bundle assessments must share exact scope")

    @property
    def assessments(self) -> tuple[PlaneAssessment, PlaneAssessment]:
        return (self.function, self.hedonic)


def build_wood_plane_bundle(
    request: WoodTargetRequest,
    *,
    registry: WoodCapabilityRegistry,
    scope: AssessmentScope,
    stock_refs: Iterable[ExactStockRef] | None = None,
    candidate_bundle: WoodCandidateBundle | None = None,
) -> WoodPlaneBundle:
    candidates = _require_candidate_bundle(
        request,
        registry,
        candidate_bundle,
        stock_refs,
    )
    return WoodPlaneBundle(
        candidates=candidates,
        function=wood_function_plane_assessment(
            request,
            registry=registry,
            scope=scope,
            candidate_bundle=candidates,
        ),
        hedonic=wood_hedonic_plane_assessment(
            request,
            registry=registry,
            scope=scope,
            candidate_bundle=candidates,
        ),
    )


def assemble_wood_whole_perfume_blueprint(
    ideal: IdealProposal,
    projection: InventoryProjection,
    request: WoodTargetRequest,
    *,
    registry: WoodCapabilityRegistry,
    family_resolution: FamilyResolution,
    temporal_scope: str,
    matrix_scope: str,
    condition_scope: str,
    version: int,
    predecessor_sha256: str | None = None,
) -> WholePerfumeBlueprint:
    """Carry the wood function, relation, and hedonic planes into a whole receipt."""

    if not isinstance(ideal, IdealProposal):
        raise TypeError("ideal must be an IdealProposal")
    if not isinstance(projection, InventoryProjection):
        raise TypeError("projection must be an InventoryProjection")
    if not isinstance(family_resolution, FamilyResolution):
        raise TypeError("family_resolution must be a FamilyResolution")
    if request.target_id != ideal.ideal_target_id:
        raise ValueError("wood target request must match the exact ideal target")
    if not (
        family_resolution.named_target
        == family_resolution.request.target_scope
        == request.target_id
    ):
        raise ValueError("family resolution must match the exact wood target")
    if family_resolution.request.requested_definition.family_id != request.family_id:
        raise ValueError("family resolution must match the exact wood family")
    if family_resolution.status is FamilyResolutionStatus.RESOLVED:
        if (
            family_resolution.definition is None
            or family_resolution.definition.definition_ref.family_id
            != request.family_id
        ):
            raise ValueError("resolved family definition must match the exact wood family")
        candidates = build_wood_candidate_bundle(
            request,
            registry=registry,
            stock_refs=projection.stock_authority_records,
        )
    else:
        candidates = _candidate_bundle_from_declarations(request, registry, ())
    scope = AssessmentScope(
        target_scope=ideal.ideal_target_id,
        temporal_scope=temporal_scope,
        matrix_scope=matrix_scope,
    )
    bundle = build_wood_plane_bundle(
        request,
        registry=registry,
        scope=scope,
        candidate_bundle=candidates,
    )
    graph = wood_accord_relation_graph(
        request,
        registry=registry,
        scope=GraphScope(
            target_scope=ideal.ideal_target_id,
            condition_scope=condition_scope,
            temporal_scope=temporal_scope,
            matrix_scope=matrix_scope,
        ),
        candidate_bundle=candidates,
    )
    family_assessment = FamilyArchitectureAdapter(
        family_resolution
    ).to_plane_assessment()
    return assemble_whole_perfume_blueprint(
        ideal,
        projection,
        (
            family_assessment,
            *bundle.assessments,
            accord_graph_to_plane_assessment(graph),
        ),
        version=version,
        predecessor_sha256=predecessor_sha256,
    )


__all__ = [
    "WoodPlaneBundle",
    "assemble_wood_whole_perfume_blueprint",
    "build_wood_plane_bundle",
    "wood_accord_relation_graph",
    "wood_candidate_declarations",
    "wood_candidate_selection_report",
    "wood_capabilities_for_family",
    "wood_function_plane_assessment",
    "wood_hedonic_plane_assessment",
]
