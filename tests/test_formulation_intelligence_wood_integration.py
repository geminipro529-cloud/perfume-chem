from __future__ import annotations

import ast
import json
from dataclasses import replace
from fractions import Fraction
from pathlib import Path

import pytest

from engine.formulation_intelligence.accord_graph import (
    GraphScope,
    accord_graph_to_plane_assessment,
)
from engine.formulation_intelligence.candidate_selector import (
    CandidateDisposition as GenericCandidateDisposition,
)
from engine.formulation_intelligence.contracts import (
    AssessmentScope,
    AuthorityCeiling,
    EvidenceClass,
    PlaneAssessment,
    PlaneId,
    ProvenanceRef,
    ValueState,
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
    StockAvailability,
    current_inventory_stock_corrections,
)
from engine.formulation_intelligence.physicochemical_plane import MaterialKind
from engine.formulation_intelligence.plane_synthesis import (
    synthesize_plane_assessments,
)
from engine.formulation_intelligence.wood_integration import (
    build_wood_candidate_bundle,
    build_wood_plane_bundle,
    wood_accord_relation_graph,
    wood_candidate_declarations,
    wood_candidate_selection_report,
    wood_capabilities_for_family,
)
from engine.formulation_intelligence.wood_registry import (
    QuantitativeOAVState,
    RationalFraction,
    WoodCandidateDisposition,
    WoodCapabilityRegistry,
    WoodFacet,
    WoodFunctionalRole,
    WoodGroup,
    WoodTargetRequest,
    default_wood_capability_registry,
    select_wood_capabilities,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def registry() -> WoodCapabilityRegistry:
    return default_wood_capability_registry()


def _scope() -> AssessmentScope:
    return AssessmentScope(
        target_scope="target:woody-floral-shadow:v1",
        temporal_scope="opening through drydown",
        matrix_scope="ideal architecture; current stock mapping separate",
    )


def _request(
    *,
    groups: tuple[WoodGroup, ...] = (),
    roles: tuple[WoodFunctionalRole, ...] = (),
    facets: tuple[WoodFacet, ...] = (),
    forbidden: tuple[WoodFacet, ...] = (),
) -> WoodTargetRequest:
    return WoodTargetRequest(
        target_id="target:woody-floral-shadow:v1",
        family_id="family:woody-floral",
        required_groups=groups,
        required_functional_roles=roles,
        required_facets=facets,
        forbidden_facets=forbidden,
    )


def _family_provenance() -> ProvenanceRef:
    return ProvenanceRef(
        provenance_id="test-family-source",
        source_ref="test://family-source",
        evidence_class=EvidenceClass.USER_REPORT,
        independence_key="test-family-source",
        source_sha256="a" * 64,
    )


def _family_resolution(*, resolved: bool = True) -> FamilyResolution:
    provenance = _family_provenance()
    definition_ref = FamilyDefinitionRef("family:woody-floral", "2026.1")
    request = FamilyArchitectureRequest(
        request_id="family-request-wood",
        target_scope="target:woody-floral-shadow:v1",
        named_target="target:woody-floral-shadow:v1",
        requested_definition=definition_ref,
        family_neighborhood=(),
        temporal_scope="opening through drydown",
        matrix_scope="ideal architecture; current stock mapping separate",
        provenance_refs=(provenance,),
    )
    if not resolved:
        return FamilyResolution(
            resolution_id="family-resolution-wood-unresolved",
            request=request,
            status=FamilyResolutionStatus.UNKNOWN_FAMILY,
            definition=None,
            named_target=request.named_target,
            family_neighborhood=(),
            reason="Exact family definition unavailable",
            provenance_refs=(provenance,),
        )
    definition = FamilyDefinition(
        definition_ref=definition_ref,
        label="Woody floral test definition",
        definition_kind=FamilyDefinitionKind.REFERENCE,
        component_definitions=(),
        architecture_planes=(
            FamilyPlane(
                plane_id="heart",
                order_index=0,
                label="Wood-floral heart",
                structural_function="Bind the named floral to a differentiated wood role.",
                temporal_window="heart",
            ),
            FamilyPlane(
                plane_id="drydown",
                order_index=1,
                label="Wood drydown",
                structural_function="Preserve target identity through residue.",
                temporal_window="drydown",
            ),
        ),
        protected_recognizers=(
            FamilyRecognizer(
                recognizer_id="woody-floral-bridge",
                label="Woody floral bridge",
                protected_function="Keep floral and wood layers connected.",
                plane_ids=("heart", "drydown"),
                absence_failure="The drydown disconnects from the floral heart.",
            ),
        ),
        forbidden_drift=(
            ForbiddenFamilyDrift(
                drift_id="generic-wood-pile",
                description="Generic material-count-driven woody base.",
                conflict_with_target="It erases target-linked differentiated roles.",
            ),
        ),
        temporal_relations=(
            FamilyTemporalRelation(
                relation_id="heart-to-drydown",
                order_index=0,
                source_plane_id="heart",
                destination_plane_id="drydown",
                relation_kind="handoff",
                continuity_requirement="The floral-wood bridge remains traceable.",
                failure_mode="The base appears as a disconnected dry slab.",
            ),
        ),
        source_version="test-source-2026.1",
        definition_evidence_class=EvidenceClass.USER_REPORT,
        provenance_refs=(provenance,),
    )
    return FamilyResolution(
        resolution_id="family-resolution-wood",
        request=request,
        status=FamilyResolutionStatus.RESOLVED,
        definition=definition,
        named_target=request.named_target,
        family_neighborhood=(),
        reason=None,
        provenance_refs=(provenance,),
    )


def test_current_stock_snapshot_includes_all_six_corrected_wood_stocks() -> None:
    by_name = {
        item.material_name: item
        for item in current_inventory_stock_corrections()
        if item.exact_stock_ref
        in {
            "inventory:v8:bacdanol:neat",
            "inventory:v7:clearwood:neat",
            "inventory:v8:guaiacwood-eo:one-third-ww",
            "inventory:v7:black-agarwood-artificial:10pct-ww-dpg",
            "inventory:v8:cypress-eo:neat-as-supplied",
            "inventory:v8:cabreuva-eo:50pct-ww-dpg",
        }
    }

    assert set(by_name) == {
        "bacdanol",
        "black agarwood artificial",
        "cabreuva eo",
        "clearwood",
        "cypress eo",
        "guaiacwood eo",
    }
    assert by_name["bacdanol"].fraction == 1.0
    assert by_name["cypress eo"].fraction == 1.0
    assert by_name["cabreuva eo"].fraction == 0.5
    assert by_name["cabreuva eo"].fraction_basis == "w/w"
    assert by_name["black agarwood artificial"].fraction == 0.1
    assert by_name["black agarwood artificial"].carrier == "dpg"


def test_registry_is_closed_deterministic_and_round_trips(
    registry: WoodCapabilityRegistry,
) -> None:
    restored = WoodCapabilityRegistry.from_dict(registry.as_dict())

    assert restored == registry
    assert restored.content_sha256 == registry.content_sha256
    assert json.dumps(registry.as_dict(), allow_nan=False, sort_keys=True)
    invalid = registry.as_dict()
    invalid["unexpected"] = True
    with pytest.raises(ValueError, match="closed schema"):
        WoodCapabilityRegistry.from_dict(invalid)


def test_registry_hash_is_order_independent_and_uses_proper_canonical_names(
    registry: WoodCapabilityRegistry,
) -> None:
    reversed_registry = default_wood_capability_registry(
        tuple(reversed(current_inventory_stock_corrections()))
    )

    assert reversed_registry == registry
    assert reversed_registry.content_sha256 == registry.content_sha256
    assert tuple(item.canonical_material_name for item in registry.materials) == (
        "Bacdanol",
        "Black Agarwood Artificial",
        "Cabreuva EO",
        "Clearwood",
        "Cypress EO",
        "Guaiacwood EO",
    )


@pytest.mark.parametrize(
    "replacement",
    (
        {"fraction_basis": "volume_fraction"},
        {"carrier": "DEP"},
        {"aliquot_state": AliquotState.NOT_PREPARED},
        {"quantitative_authority": False},
    ),
)
def test_registry_rejects_stock_basis_carrier_readiness_or_authority_drift(
    replacement: dict[str, object],
) -> None:
    stocks = current_inventory_stock_corrections()
    changed = tuple(
        replace(item, **replacement)
        if item.exact_stock_ref == "inventory:v8:cabreuva-eo:50pct-ww-dpg"
        else item
        for item in stocks
    )

    with pytest.raises(ValueError):
        default_wood_capability_registry(changed)


def test_exact_one_third_guaiacwood_stock_survives_registry_round_trip(
    registry: WoodCapabilityRegistry,
) -> None:
    guaiac = registry.resolve("Guaiacwood EO")
    assert guaiac is not None

    fractions = tuple(item.fraction.value for item in guaiac.stock_components)
    assert fractions == (Fraction(1, 3), Fraction(1, 3), Fraction(1, 3))
    assert sum(fractions, Fraction()) == Fraction(1, 1)
    assert guaiac.active_fraction == Fraction(1, 3)
    restored = WoodCapabilityRegistry.from_dict(registry.as_dict())
    assert restored.resolve("Guaiac Wood EO") == guaiac


@pytest.mark.parametrize(
    ("numerator", "denominator"),
    ((2, 6), (0, 3), (4, 3), (1, 0), (1, -3)),
)
def test_invalid_or_noncanonical_exact_fractions_fail_closed(
    numerator: int,
    denominator: int,
) -> None:
    with pytest.raises((TypeError, ValueError)):
        RationalFraction(numerator, denominator)


def test_aliases_resolve_once_without_identity_collapse(
    registry: WoodCapabilityRegistry,
) -> None:
    assert registry.resolve("Bacnadol") == registry.resolve("Bacdanol")
    assert registry.resolve("Cypress Essential Oil") == registry.resolve("Cypress EO")
    assert registry.resolve("Guaiacol") is None
    assert registry.resolve("Sandalore") is None


def test_corrected_woods_have_distinct_target_linked_structural_roles(
    registry: WoodCapabilityRegistry,
) -> None:
    bacdanol = registry.resolve("Bacdanol")
    clearwood = registry.resolve("Clearwood")
    guaiac = registry.resolve("Guaiacwood EO")
    cypress = registry.resolve("Cypress EO")
    cabreuva = registry.resolve("Cabreuva EO")
    agarwood = registry.resolve("Black Agarwood Artificial")

    assert bacdanol is not None and bacdanol.groups == (
        WoodGroup.G17_CREAMY_WOODS,
    )
    assert clearwood is not None and WoodFunctionalRole.TRANSPARENT_PATCHOULI in (
        clearwood.functional_roles
    )
    assert guaiac is not None and WoodGroup.RESIN_SMOKE_SHADOW in guaiac.groups
    assert cypress is not None and WoodFacet.CONIFEROUS in cypress.facets
    assert cabreuva is not None and WoodFunctionalRole.FLORAL_WOOD_BRIDGE in (
        cabreuva.functional_roles
    )
    assert agarwood is not None and agarwood.material_kind is MaterialKind.OPAQUE_MIXTURE


def test_target_role_query_selects_bacdanol_not_every_owned_wood(
    registry: WoodCapabilityRegistry,
) -> None:
    matches = select_wood_capabilities(
        _request(roles=(WoodFunctionalRole.CREAMY_BODY,)),
        registry,
    )

    assert tuple(item.capability_id for item in matches) == ("wood.bacdanol",)
    assert matches[0].disposition is WoodCandidateDisposition.FRONTIER


def test_registry_declarations_run_through_shared_candidate_selector(
    registry: WoodCapabilityRegistry,
) -> None:
    report = wood_candidate_selection_report(
        _request(roles=(WoodFunctionalRole.CREAMY_BODY,)),
        registry=registry,
    )

    assert report.ideal_frontier_ids == ("wood.bacdanol",)
    assert report.current_inventory_frontier_ids == ()
    current = {
        item.candidate_id: item for item in report.current_inventory_assessments
    }
    assert current["wood.bacdanol"].disposition is GenericCandidateDisposition.HOLD
    assert current["wood.bacdanol"].hold_reasons == ("INVENTORY_STATE_UNKNOWN",)
    assert current["wood.bacdanol"].exact_stock_ref is None
    assert current["wood.bacdanol"].execution_ready is None
    assert report.scalar_utility_used is False
    assert report.execution_authorized is False
    assert report.sensory_claims_authorized is False
    assert report.liking_claims_authorized is False
    assert report.release_authorized is False


def test_every_wood_consumer_uses_the_exact_shared_pareto_frontier(
    registry: WoodCapabilityRegistry,
) -> None:
    request = _request(
        roles=(
            WoodFunctionalRole.FLORAL_WOOD_BRIDGE,
            WoodFunctionalRole.ROOT_GRAIN_BRIDGE,
        )
    )
    local_ids = tuple(
        item.capability_id for item in select_wood_capabilities(request, registry)
    )
    candidates = build_wood_candidate_bundle(request, registry=registry)
    plane_bundle = build_wood_plane_bundle(
        request,
        registry=registry,
        scope=_scope(),
        candidate_bundle=candidates,
    )
    graph = wood_accord_relation_graph(
        request,
        registry=registry,
        scope=GraphScope(
            target_scope=request.target_id,
            condition_scope="design hypothesis only",
            temporal_scope="opening through drydown",
            matrix_scope="ideal architecture; current stock mapping separate",
        ),
        candidate_bundle=candidates,
    )

    assert local_ids == (
        "wood.bacdanol",
        "wood.cabreuva-eo",
        "wood.clearwood",
        "wood.cypress-eo",
        "wood.guaiacwood-eo",
    )
    assert candidates.report.ideal_frontier_ids == (
        "wood.cabreuva-eo",
        "wood.guaiacwood-eo",
    )
    assert tuple(item.capability_id for item, _ in candidates.frontier) == (
        "wood.cabreuva-eo",
        "wood.guaiacwood-eo",
    )
    function_candidates = {
        item.member_id
        for item in plane_bundle.function.claims
        if item.claim_key == "wood.target_linked_candidate"
    }
    assert function_candidates == set(candidates.report.ideal_frontier_ids)
    graph_candidates = {
        node.node_id.removeprefix("wood-material:")
        for node in graph.nodes
        if node.node_id.startswith("wood-material:")
    }
    assert graph_candidates == set(candidates.report.ideal_frontier_ids)
    assert candidates.requirement.content_sha256 in plane_bundle.function.freshness_hashes
    assert candidates.report.content_sha256 in plane_bundle.function.freshness_hashes


def test_explicit_exact_stock_records_bind_only_the_current_inventory_view(
    registry: WoodCapabilityRegistry,
) -> None:
    stocks = current_inventory_stock_corrections()
    report = wood_candidate_selection_report(
        _request(roles=(WoodFunctionalRole.CREAMY_BODY,)),
        registry=registry,
        stock_refs=stocks,
    )
    declarations = {
        item.candidate_id: item
        for item in wood_candidate_declarations(registry, stock_refs=stocks)
    }

    assert report.ideal_frontier_ids == ("wood.bacdanol",)
    assert report.current_inventory_frontier_ids == ("wood.bacdanol",)
    assert declarations["wood.bacdanol"].inventory_state.value == "owned"
    assert declarations["wood.bacdanol"].exact_stock_ref == (
        "inventory:v8:bacdanol:neat"
    )
    assert declarations["wood.bacdanol"].execution_ready is True

    changed_stocks = tuple(
        replace(item, authority_notes=(*item.authority_notes, "unbound drift"))
        if item.exact_stock_ref == "inventory:v8:bacdanol:neat"
        else item
        for item in stocks
    )
    changed = {
        item.candidate_id: item
        for item in wood_candidate_declarations(
            registry,
            stock_refs=changed_stocks,
        )
    }
    assert changed["wood.bacdanol"].inventory_state.value == "unknown"
    assert changed["wood.bacdanol"].exact_stock_ref is None
    assert changed["wood.bacdanol"].execution_ready is None


def test_forbidden_facet_blocks_candidate_even_when_another_requirement_matches(
    registry: WoodCapabilityRegistry,
) -> None:
    matches = select_wood_capabilities(
        _request(
            groups=(WoodGroup.RESIN_SMOKE_SHADOW,),
            forbidden=(WoodFacet.OUD,),
        ),
        registry,
        include_rejected=True,
    )
    by_id = {item.capability_id: item for item in matches}

    assert by_id["wood.black-agarwood-artificial"].disposition is (
        WoodCandidateDisposition.FORBIDDEN_FACET
    )
    assert by_id["wood.guaiacwood-eo"].disposition is (
        WoodCandidateDisposition.FRONTIER
    )


def test_family_bridge_requires_exact_resolution_and_substantive_target_role(
    registry: WoodCapabilityRegistry,
) -> None:
    resolved = _family_resolution()
    matches = wood_capabilities_for_family(
        resolved,
        registry=registry,
        required_facets=(WoodFacet.CONIFEROUS,),
    )

    assert tuple(item.capability_id for item in matches) == ("wood.cypress-eo",)
    assert wood_capabilities_for_family(resolved, registry=registry) == ()
    assert wood_capabilities_for_family(
        _family_resolution(resolved=False),
        registry=registry,
        required_facets=(WoodFacet.CONIFEROUS,),
    ) == ()


def test_natural_and_opaque_mixture_quantitative_firewalls_remain_active(
    registry: WoodCapabilityRegistry,
) -> None:
    for name in ("Guaiacwood EO", "Cypress EO", "Cabreuva EO"):
        item = registry.resolve(name)
        assert item is not None
        assert item.material_kind is MaterialKind.NATURAL_MIXTURE
        assert item.quantitative_oav_state is (
            QuantitativeOAVState.NATURAL_COMPOSITE_REQUIRED_UNBOUND
        )
        assert item.formula_constituent_expansion is False
    black = registry.resolve("Black Agarwood Artificial")
    assert black is not None
    assert black.quantitative_oav_state is (
        QuantitativeOAVState.OPAQUE_BULK_REFERENCE_REQUIRED_UNBOUND
    )


def test_every_registry_hedonic_value_is_unknown_not_numeric(
    registry: WoodCapabilityRegistry,
) -> None:
    for item in registry.materials:
        assert item.liking.state is ValueState.UNKNOWN
        assert item.liking.value is None
        assert item.authority_ceiling.is_no_stronger_than(
            AuthorityCeiling.STRUCTURAL_ONLY
        )


def test_plane_bundle_preserves_function_and_non_scalar_hedonic_unknowns(
    registry: WoodCapabilityRegistry,
) -> None:
    request = _request(
        roles=(
            WoodFunctionalRole.CREAMY_BODY,
            WoodFunctionalRole.FLORAL_WOOD_BRIDGE,
        )
    )
    bundle = build_wood_plane_bundle(request, registry=registry, scope=_scope())
    synthesis = synthesize_plane_assessments(bundle.assessments)

    assert bundle.function.plane_id is PlaneId.FUNCTION
    assert bundle.hedonic.plane_id is PlaneId.HEDONIC
    assert bundle.function.authority_ceiling is AuthorityCeiling.STRUCTURAL_ONLY
    assert bundle.hedonic.authority_ceiling is AuthorityCeiling.WITHHELD
    assert all(item.value.state is ValueState.UNKNOWN for item in bundle.hedonic.native_criteria)
    assert all(item.value.value is None for item in bundle.hedonic.native_criteria)
    assert not any(
        item.criterion_id in {"hedonic_score", "beauty", "overall_score"}
        for item in bundle.hedonic.native_criteria
    )
    assert synthesis.authority_ceiling is AuthorityCeiling.WITHHELD
    assert registry.content_sha256 in bundle.function.freshness_hashes
    assert registry.content_sha256 in bundle.hedonic.freshness_hashes
    assert PlaneAssessment.from_dict(bundle.function.as_dict()) == bundle.function
    assert PlaneAssessment.from_dict(bundle.hedonic.as_dict()) == bundle.hedonic


def test_scope_mismatch_cannot_launder_a_wood_request_into_another_target(
    registry: WoodCapabilityRegistry,
) -> None:
    request = _request(roles=(WoodFunctionalRole.CREAMY_BODY,))
    with pytest.raises(ValueError, match="exact target"):
        build_wood_plane_bundle(
            request,
            registry=registry,
            scope=AssessmentScope(
                target_scope="target:other-perfume:v1",
                temporal_scope="opening through drydown",
                matrix_scope="ideal architecture",
            ),
        )
    with pytest.raises(ValueError, match="exact target"):
        wood_accord_relation_graph(
            request,
            registry=registry,
            scope=GraphScope(
                target_scope="target:other-perfume:v1",
                condition_scope="design hypothesis only",
                temporal_scope="opening through drydown",
                matrix_scope="ideal architecture",
            ),
        )


def test_accord_graph_exposes_material_role_target_relations_without_synergy(
    registry: WoodCapabilityRegistry,
) -> None:
    request = _request(roles=(WoodFunctionalRole.CONIFER_TRANSITION,))
    graph = wood_accord_relation_graph(
        request,
        registry=registry,
        scope=GraphScope(
            target_scope="target:woody-floral-shadow:v1",
            condition_scope="design hypothesis only",
            temporal_scope="opening through drydown",
            matrix_scope="ideal architecture; current stock mapping separate",
        ),
    )
    assessment = accord_graph_to_plane_assessment(graph)

    assert {node.node_id for node in graph.nodes} >= {
        "wood-material:wood.cypress-eo",
        "wood-role:conifer_transition",
        "wood-target:target:woody-floral-shadow:v1",
    }
    assert {edge.relation_kind.value for edge in graph.edges} == {"supports"}
    assert assessment.plane_id is PlaneId.RELATION
    assert assessment.authority_ceiling is AuthorityCeiling.STRUCTURAL_ONLY
    assert registry.content_sha256 in graph.graph_id


def test_accord_graph_exposes_only_matched_features_not_every_material_role(
    registry: WoodCapabilityRegistry,
) -> None:
    graph = wood_accord_relation_graph(
        _request(roles=(WoodFunctionalRole.CREAMY_BODY,)),
        registry=registry,
        scope=GraphScope(
            target_scope="target:woody-floral-shadow:v1",
            condition_scope="design hypothesis only",
            temporal_scope="opening through drydown",
            matrix_scope="ideal architecture; current stock mapping separate",
        ),
    )
    node_ids = {node.node_id for node in graph.nodes}

    assert "wood-role:creamy_body" in node_ids
    assert "wood-role:floral_wood_bridge" not in node_ids
    assert "wood-role:drydown_continuity" not in node_ids
    assert not any(
        edge.relation_kind.value == "hypothesis_synergy" for edge in graph.edges
    )


def test_no_shared_frontier_is_an_explicit_relation_unknown(
    registry: WoodCapabilityRegistry,
) -> None:
    request = _request(groups=(WoodGroup.G19_AMBERWOODS,))
    graph = wood_accord_relation_graph(
        request,
        registry=registry,
        scope=GraphScope(
            target_scope=request.target_id,
            condition_scope="design hypothesis only",
            temporal_scope="opening through drydown",
            matrix_scope="ideal architecture; current stock mapping separate",
        ),
    )
    assessment = accord_graph_to_plane_assessment(graph)

    assert not graph.edges
    assert len(graph.nodes) == 1
    assert tuple(item.field_key for item in graph.unknowns) == (
        "wood.relation.candidate_frontier",
    )
    assert any(
        item.field_key == "wood.relation.candidate_frontier"
        for item in assessment.unknowns
    )


def test_group_and_facet_requests_create_explicit_relation_nodes(
    registry: WoodCapabilityRegistry,
) -> None:
    graph = wood_accord_relation_graph(
        _request(
            groups=(WoodGroup.G16_GRAIN_ROOT,),
            facets=(WoodFacet.CONIFEROUS,),
        ),
        registry=registry,
        scope=GraphScope(
            target_scope="target:woody-floral-shadow:v1",
            condition_scope="design hypothesis only",
            temporal_scope="opening through drydown",
            matrix_scope="ideal architecture; current stock mapping separate",
        ),
    )
    node_ids = {node.node_id for node in graph.nodes}

    assert "wood-facet:coniferous" in node_ids
    assert any(value.startswith("wood-group:g16") for value in node_ids)


def test_registry_is_the_only_material_allowlist_and_does_not_import_consumers() -> None:
    registry_path = ROOT / "engine" / "formulation_intelligence" / "wood_registry.py"
    tree = ast.parse(registry_path.read_text(encoding="utf-8"))
    imports = {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }

    assert "accord_graph" not in imports
    assert "family_architecture" not in imports
    assert "wood_integration" not in imports
    consumer_paths = (
        ROOT / "engine" / "formulation_intelligence" / "candidate_selector.py",
        ROOT / "engine" / "formulation_intelligence" / "accord_graph.py",
        ROOT / "engine" / "formulation_intelligence" / "family_architecture.py",
        ROOT / "engine" / "formulation_intelligence" / "hedonic_platform.py",
        ROOT / "engine" / "formulation_intelligence" / "whole_perfume_assembler.py",
    )
    names = tuple(item.canonical_material_name for item in default_wood_capability_registry().materials)
    for path in consumer_paths:
        source = path.read_text(encoding="utf-8")
        for name in names:
            assert name not in source, (path, name)


def test_registry_hash_changes_when_a_structural_record_changes(
    registry: WoodCapabilityRegistry,
) -> None:
    bacdanol = registry.resolve("Bacdanol")
    assert bacdanol is not None
    changed = replace(
        registry,
        materials=tuple(
            replace(item, facets=(*item.facets, WoodFacet.DRY))
            if item.capability_id == bacdanol.capability_id
            else item
            for item in registry.materials
        ),
    )

    assert changed.content_sha256 != registry.content_sha256


def test_registry_stock_digest_is_derived_and_binds_neat_tombstone(
    registry: WoodCapabilityRegistry,
) -> None:
    payload = registry.as_dict()
    payload["stock_authority_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="bound stock provenance"):
        WoodCapabilityRegistry.from_dict(payload)

    stocks = current_inventory_stock_corrections()
    without_tombstone = tuple(
        item
        for item in stocks
        if item.exact_stock_ref
        != "inventory:tombstone:black-agarwood-artificial:neat"
    )
    with pytest.raises(ValueError, match="neat tombstone is required"):
        default_wood_capability_registry(without_tombstone)


def test_registry_rejects_competing_owned_neat_black_agarwood() -> None:
    stocks = current_inventory_stock_corrections()
    tombstone = next(
        item
        for item in stocks
        if item.exact_stock_ref
        == "inventory:tombstone:black-agarwood-artificial:neat"
    )
    competing = replace(
        tombstone,
        exact_stock_ref="inventory:conflict:black-agarwood-artificial:neat",
        availability=StockAvailability.OWNED,
        aliquot_state=AliquotState.READY,
        carrier=None,
        quantitative_authority=True,
    )
    with pytest.raises(ValueError, match="conflicts with the current tombstone"):
        default_wood_capability_registry((*stocks, competing))
