from __future__ import annotations

import ast
import json
from dataclasses import replace
from pathlib import Path

import pytest

from engine.formulation_intelligence.contracts import (
    AssessmentScope,
    AuthorityCeiling,
    EvidenceClass,
    PlaneId,
    ProvenanceRef,
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
from engine.formulation_intelligence.floral_integration import (
    FloralFamilyIntegrationAdapter,
    build_floral_family_synthesis,
)
from engine.formulation_intelligence.floral_lattice import (
    FacetRole,
    FacetSelection,
    FloralAbstraction,
    FloralFacet,
    FloralMorphologyIntent,
    FloralSubject,
    FloralSubtype,
)
from engine.formulation_intelligence.plane_synthesis import PlaneSynthesisResult

ROOT = Path(__file__).resolve().parents[1]


def _provenance() -> ProvenanceRef:
    return ProvenanceRef(
        provenance_id="floral-integration-test-source",
        source_ref="test://floral-integration/source",
        evidence_class=EvidenceClass.USER_REPORT,
        independence_key="floral-integration-test-source",
        source_sha256="a" * 64,
    )


def _scope() -> AssessmentScope:
    return AssessmentScope(
        target_scope="target:rose-wood-chiaroscuro:v1",
        temporal_scope="opening through drydown",
        matrix_scope="ideal target; inventory build remains separate",
    )


def _definition(*, hybrid: bool = False) -> FamilyDefinition:
    reference = FamilyDefinitionRef(
        "hybrid:floral-woody" if hybrid else "family:floral",
        "2026.1",
    )
    return FamilyDefinition(
        definition_ref=reference,
        label="Rose wood chiaroscuro" if hybrid else "Target-specific floral",
        definition_kind=(
            FamilyDefinitionKind.HYBRID if hybrid else FamilyDefinitionKind.REFERENCE
        ),
        component_definitions=(
            (
                FamilyDefinitionRef("family:floral", "2026.1"),
                FamilyDefinitionRef("family:woody", "2026.1"),
            )
            if hybrid
            else ()
        ),
        architecture_planes=(
            FamilyPlane(
                plane_id="heart",
                order_index=0,
                label="Named floral heart",
                structural_function="Keep the exact floral subject legible.",
                temporal_window="opening through heart",
            ),
            FamilyPlane(
                plane_id="drydown",
                order_index=1,
                label="Target-linked residue",
                structural_function="Resolve without generic floral or wood drift.",
                temporal_window="heart through drydown",
            ),
        ),
        protected_recognizers=(
            FamilyRecognizer(
                recognizer_id="exact-floral-subject",
                label="Exact floral subject",
                protected_function="Protect the requested subtype and style.",
                plane_ids=("heart", "drydown"),
                absence_failure="The design collapses into generic floralness.",
            ),
        ),
        forbidden_drift=(
            ForbiddenFamilyDrift(
                drift_id="generic-floral-heart",
                description="Generic floral-heart substitution.",
                conflict_with_target="The exact named subject and style disappear.",
            ),
        ),
        temporal_relations=(
            FamilyTemporalRelation(
                relation_id="heart-to-drydown",
                order_index=0,
                source_plane_id="heart",
                destination_plane_id="drydown",
                relation_kind="transformation",
                continuity_requirement="The named recognizer remains traceable.",
                failure_mode="A disconnected generic residue replaces the subject.",
            ),
        ),
        source_version="test-family-2026.1",
        definition_evidence_class=EvidenceClass.USER_REPORT,
        provenance_refs=(_provenance(),),
    )


def _resolution(*, resolved: bool = True, hybrid: bool = False) -> FamilyResolution:
    definition = _definition(hybrid=hybrid)
    scope = _scope()
    request = FamilyArchitectureRequest(
        request_id="floral-family-request",
        target_scope=scope.target_scope,
        named_target="rose wood chiaroscuro",
        requested_definition=definition.definition_ref,
        family_neighborhood=(),
        temporal_scope=scope.temporal_scope,
        matrix_scope=scope.matrix_scope,
        provenance_refs=(_provenance(),),
    )
    return FamilyResolution(
        resolution_id=(
            "floral-family-resolution" if resolved else "floral-family-unresolved"
        ),
        request=request,
        status=(
            FamilyResolutionStatus.RESOLVED
            if resolved
            else FamilyResolutionStatus.UNKNOWN_FAMILY
        ),
        definition=definition if resolved else None,
        named_target=request.named_target,
        family_neighborhood=(),
        reason=None if resolved else "The exact family definition is unavailable.",
        provenance_refs=(_provenance(),),
    )


def _rose_intent(
    *,
    expressions: tuple[str, ...] = ("dewy", "peppery", "tea"),
    recognizers: tuple[str, ...] = ("living petal identity", "tea rose contour"),
    drifts: tuple[str, ...] = ("generic floral heart", "jammy confection"),
) -> FloralMorphologyIntent:
    return FloralMorphologyIntent(
        flower_subject=FloralSubject.ROSE,
        exact_subtype=FloralSubtype.ROSE,
        abstraction_level=FloralAbstraction.STYLIZED,
        requested_expression=expressions,
        protected_recognizers=recognizers,
        forbidden_drift=drifts,
        intended_temporal_transformations=(),
        selected_facets=(
            FacetSelection(
                subject=FloralSubject.ROSE,
                facet=FloralFacet.AQUEOUS_DEW,
                role=FacetRole.CORE_RECOGNIZER,
                rationale="Keep a living dewy petal contour.",
            ),
        ),
        deliberate_omissions=(),
        bouquet_hierarchy=(),
    )


def _assessment_by_plane(
    result: PlaneSynthesisResult,
) -> dict[PlaneId, object]:
    return {item.plane_id: item for item in result.assessments}


def test_exact_scope_family_and_floral_planes_integrate_without_flattening() -> None:
    resolution = _resolution()
    intent = _rose_intent()
    result = build_floral_family_synthesis(
        resolution,
        intent,
        scope=_scope(),
    )
    assessments = _assessment_by_plane(result)

    assert set(assessments) == {PlaneId.IDENTITY, PlaneId.MORPHOLOGY}
    assert all(item.scope == _scope() for item in result.assessments)
    identity = assessments[PlaneId.IDENTITY]
    morphology = assessments[PlaneId.MORPHOLOGY]
    identity_values = {item.claim_value for item in identity.claims}
    morphology_keys = {item.claim_key for item in morphology.claims}
    assert resolution.request.named_target in identity_values
    assert resolution.request.requested_definition.qualified_name in identity_values
    assert "morphology.subject" in morphology_keys
    assert "morphology.exact_subtype.rose" in morphology_keys
    assert "morphology.facet.rose.aqueous_dew" in morphology_keys
    assert result.authority_ceiling is AuthorityCeiling.STRUCTURAL_ONLY
    assert len(result.assessments) == 2


def test_hybrid_component_refs_exact_subtype_and_style_survive_synthesis_round_trip() -> None:
    resolution = _resolution(hybrid=True)
    intent = _rose_intent()
    result = FloralFamilyIntegrationAdapter(
        resolution=resolution,
        intent=intent,
        scope=_scope(),
    ).to_synthesis()
    restored = PlaneSynthesisResult.from_dict(
        json.loads(json.dumps(result.as_dict()))
    )
    identity = _assessment_by_plane(restored)[PlaneId.IDENTITY]
    morphology = _assessment_by_plane(restored)[PlaneId.MORPHOLOGY]

    component_values = {
        claim.claim_value
        for claim in identity.claims
        if claim.claim_key == "family.component_definition"
    }
    assert component_values == {
        "family:floral@2026.1",
        "family:woody@2026.1",
    }
    assert any(
        claim.claim_key == "morphology.exact_subtype.rose"
        for claim in morphology.claims
    )
    for style in intent.requested_expression:
        assert any(style in claim.claim_value for claim in morphology.claims)
    assert restored == result
    assert restored.content_sha256 == result.content_sha256


def test_unresolved_family_keeps_morphology_but_withholds_integration() -> None:
    result = build_floral_family_synthesis(
        _resolution(resolved=False),
        _rose_intent(),
        scope=_scope(),
    )
    assessments = _assessment_by_plane(result)

    assert set(assessments) == {PlaneId.IDENTITY, PlaneId.MORPHOLOGY}
    assert any(
        item.field_key == "family_definition"
        for item in assessments[PlaneId.IDENTITY].unknowns
    )
    assert any(
        claim.claim_key == "morphology.exact_subtype.rose"
        for claim in assessments[PlaneId.MORPHOLOGY].claims
    )
    assert result.authority_ceiling is AuthorityCeiling.WITHHELD
    assert result.formula_generation_authorized is False
    assert result.hedonic_score_authorized is False
    assert result.sensory_authority is False
    assert result.safety_authority is False
    assert result.release_authority is False


@pytest.mark.parametrize(
    ("field_name", "replacement"),
    (
        ("target_scope", "target:other:v1"),
        ("temporal_scope", "opening only"),
        ("matrix_scope", "different matrix"),
    ),
)
def test_target_temporal_or_matrix_scope_mismatch_fails_closed(
    field_name: str,
    replacement: str,
) -> None:
    with pytest.raises(ValueError, match=field_name):
        FloralFamilyIntegrationAdapter(
            resolution=_resolution(),
            intent=_rose_intent(),
            scope=replace(_scope(), **{field_name: replacement}),
        )


def test_grouped_missing_subtype_remains_unknown_not_generic() -> None:
    grouped = FloralMorphologyIntent(
        flower_subject=FloralSubject.MAGNOLIA_CHAMPACA,
        exact_subtype=None,
        abstraction_level=FloralAbstraction.STYLIZED,
        requested_expression=("tea", "waxy"),
        protected_recognizers=("magnolia champaca contour",),
        forbidden_drift=("generic floral heart",),
        intended_temporal_transformations=(),
        selected_facets=(),
        deliberate_omissions=(),
        bouquet_hierarchy=(),
    )
    result = build_floral_family_synthesis(
        _resolution(),
        grouped,
        scope=_scope(),
    )
    morphology = _assessment_by_plane(result)[PlaneId.MORPHOLOGY]

    assert any(
        claim.claim_key == "morphology.subject"
        and "magnolia_champaca" in claim.claim_value
        for claim in morphology.claims
    )
    assert any(
        item.field_key == "morphology.exact_subtype.magnolia_champaca"
        for item in morphology.unknowns
    )
    assert not any(
        claim.claim_key in {
            "morphology.exact_subtype.magnolia",
            "morphology.exact_subtype.champaca",
        }
        for claim in morphology.claims
    )
    assert result.authority_ceiling is AuthorityCeiling.STRUCTURAL_ONLY


def test_adapter_is_stock_free_and_imports_only_contract_family_floral_synthesis() -> None:
    path = ROOT / "engine" / "formulation_intelligence" / "floral_integration.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    project_imports = {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and (node.module or "").startswith("engine")
    }

    assert project_imports == {
        "engine.formulation_intelligence.contracts",
        "engine.formulation_intelligence.family_architecture",
        "engine.formulation_intelligence.floral_lattice",
        "engine.formulation_intelligence.plane_synthesis",
    }
    source = path.read_text(encoding="utf-8")
    for prohibited in (
        "inventory_parser",
        "inventory_projection",
        "candidate_selector",
        "candidate_assembler",
        "engine.pipeline",
        "soliflore_structures",
        "accord_library",
        "whole_perfume_assembler",
    ):
        assert prohibited not in source


def test_permuted_floral_inputs_are_hash_deterministic() -> None:
    first = _rose_intent()
    second = _rose_intent(
        expressions=tuple(reversed(first.requested_expression)),
        recognizers=tuple(reversed(first.protected_recognizers)),
        drifts=tuple(reversed(first.forbidden_drift)),
    )
    left = build_floral_family_synthesis(_resolution(), first, scope=_scope())
    right = build_floral_family_synthesis(_resolution(), second, scope=_scope())

    assert first == second
    assert left == right
    assert left.as_dict() == right.as_dict()
    assert left.content_sha256 == right.content_sha256
