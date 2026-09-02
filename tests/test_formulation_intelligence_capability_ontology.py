from __future__ import annotations

from dataclasses import FrozenInstanceError, replace

import pytest

from engine.formulation_intelligence.capability_ontology import (
    CapabilityApplicability,
    CapabilityDefinition,
    CapabilityGapKind,
    CapabilityOntology,
    CapabilityState,
    CapabilitySupport,
    EvidenceNeed,
    ScopeMode,
    analyze_capability_coverage,
    default_capability_ontology,
    query_capability_gaps,
)
from engine.formulation_intelligence.contracts import (
    AuthorityCeiling,
    EvidenceClass,
    PlaneId,
    ProvenanceRef,
)

_A = "a" * 64
_B = "b" * 64
_C = "c" * 64


def _provenance(
    provenance_id: str,
    *,
    source_sha256: str = _A,
    evidence_class: EvidenceClass = EvidenceClass.HEURISTIC,
) -> ProvenanceRef:
    return ProvenanceRef(
        provenance_id=provenance_id,
        source_ref=f"test:{provenance_id}",
        evidence_class=evidence_class,
        independence_key=provenance_id,
        source_sha256=source_sha256,
    )


def _support(
    definition: CapabilityDefinition,
    *,
    module_id: str,
    state: CapabilityState = CapabilityState.IMPLEMENTED,
    source_sha256: str = _B,
) -> CapabilitySupport:
    return CapabilitySupport(
        support_id=f"support:{module_id}:{definition.capability_id}",
        capability_id=definition.capability_id,
        module_id=module_id,
        module_path=f"engine/formulation_intelligence/{module_id}.py",
        state=state,
        interface_ids=(f"{module_id}:public-contract-v1",),
        required_evidence_need_ids=tuple(
            item.evidence_need_id for item in definition.evidence_needs
        ),
        covered_evidence_need_ids=tuple(
            item.evidence_need_id for item in definition.evidence_needs
        ),
        limitations=("No downstream empirical authority.",),
        module_source_sha256=source_sha256,
        authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
        provenance_refs=(
            _provenance(
                f"module:{module_id}:{definition.capability_id}",
                source_sha256=source_sha256,
            ),
        ),
    )


def test_default_ontology_covers_every_plane_and_open_family_namespaces() -> None:
    ontology = default_capability_ontology()

    assert {item.plane_id for item in ontology.capabilities} == set(PlaneId)
    assert len(ontology.capabilities) == len(PlaneId)
    assert ontology.authority_ceiling is AuthorityCeiling.STRUCTURAL_ONLY
    assert ontology.content_sha256 == default_capability_ontology().content_sha256

    for definition in ontology.capabilities:
        assert definition.authority_ceiling.is_no_stronger_than(AuthorityCeiling.STRUCTURAL_ONLY)
        assert definition.applicability.family_mode is ScopeMode.ALL
        assert definition.applicability.floral_mode is ScopeMode.ALL
        assert definition.applicability.accepts_new_family_ids is True
        assert definition.applicability.accepts_new_floral_subtype_ids is True
        assert definition.applicability.applies_to(
            family_id="future-marine-chypre",
            floral_subtype_id="future-orchid-metallic",
        )
        assert definition.provenance_refs
        assert all(
            item.evidence_class is EvidenceClass.HEURISTIC and item.source_sha256 is not None
            for item in definition.provenance_refs
        )


def test_records_are_strict_versioned_round_trippable_and_immutable() -> None:
    ontology = default_capability_ontology()
    restored = CapabilityOntology.from_dict(ontology.as_dict())

    assert restored == ontology
    assert restored.content_sha256 == ontology.content_sha256

    payload = ontology.as_dict()
    payload["unexpected"] = True
    with pytest.raises(ValueError, match="closed schema"):
        CapabilityOntology.from_dict(payload)

    payload = ontology.as_dict()
    payload["schema_version"] = "capability_ontology_v0"
    with pytest.raises(ValueError, match="schema_version"):
        CapabilityOntology.from_dict(payload)

    with pytest.raises(FrozenInstanceError):
        ontology.ontology_id = "mutated"  # type: ignore[misc]


def test_unregistered_capabilities_are_missing_without_scalarization() -> None:
    ontology = default_capability_ontology()
    report = analyze_capability_coverage(ontology)

    assert len(report.coverage) == len(PlaneId)
    assert {item.state for item in report.coverage} == {CapabilityState.MISSING}
    assert {gap.kind for gap in report.gaps} == {CapabilityGapKind.MISSING_SUPPORT}
    assert "overall_score" not in report.as_dict()
    assert "coverage_percent" not in report.as_dict()
    assert report.sensory_authority is False
    assert report.liking_authority is False
    assert report.performance_authority is False
    assert report.safety_authority is False
    assert report.stability_authority is False
    assert report.physical_execution_authority is False
    assert report.release_authority is False


def test_prerequisite_gap_demotes_declared_implementation_to_partial() -> None:
    base = default_capability_ontology()
    identity = base.capability("identity.exact_subject_binding")
    ontology = replace(base, module_support=(_support(identity, module_id="identity"),))

    report = analyze_capability_coverage(
        ontology,
        required_capability_ids=(identity.capability_id,),
    )

    assert report.coverage[0].state is CapabilityState.PARTIAL
    assert report.coverage[0].implemented_module_ids == ("identity",)
    assert any(
        gap.kind is CapabilityGapKind.UNSATISFIED_PREREQUISITE
        and gap.related_capability_ids == ("evidence.authority_firewall",)
        for gap in report.gaps
    )


def test_satisfied_prerequisite_allows_implemented_coverage() -> None:
    base = default_capability_ontology()
    evidence = base.capability("evidence.authority_firewall")
    identity = base.capability("identity.exact_subject_binding")
    ontology = replace(
        base,
        module_support=(
            _support(evidence, module_id="contracts"),
            _support(identity, module_id="identity"),
        ),
    )

    report = analyze_capability_coverage(
        ontology,
        required_capability_ids=(identity.capability_id,),
    )

    assert report.coverage[0].state is CapabilityState.IMPLEMENTED
    assert report.gaps == ()


def test_partial_support_and_missing_evidence_are_reported_separately() -> None:
    base = default_capability_ontology()
    evidence = base.capability("evidence.authority_firewall")
    partial = _support(
        evidence,
        module_id="contracts",
        state=CapabilityState.PARTIAL,
    )
    partial = replace(partial, covered_evidence_need_ids=())
    ontology = replace(base, module_support=(partial,))

    report = analyze_capability_coverage(
        ontology,
        required_capability_ids=(evidence.capability_id,),
    )

    assert report.coverage[0].state is CapabilityState.PARTIAL
    assert {gap.kind for gap in report.gaps} == {
        CapabilityGapKind.PARTIAL_SUPPORT,
        CapabilityGapKind.UNMET_EVIDENCE_NEED,
    }


def test_module_support_is_exact_source_hash_and_provenance_bound() -> None:
    definition = default_capability_ontology().capabilities[0]

    with pytest.raises(ValueError, match="exact module source SHA-256"):
        replace(
            _support(definition, module_id="bad-binding"),
            provenance_refs=(_provenance("module:bad-binding", source_sha256=_C),),
        )

    with pytest.raises(ValueError, match="implemented support must satisfy"):
        replace(
            _support(definition, module_id="missing-evidence"),
            covered_evidence_need_ids=(),
        )


def test_custom_incompatibility_is_deterministic_and_never_silently_resolved() -> None:
    applicability = CapabilityApplicability.all_extensible()
    provenance = (_provenance("ontology:incompatibility"),)
    evidence_need = EvidenceNeed(
        evidence_need_id="need:declaration",
        description="A hash-bound declaration.",
        acceptable_evidence_classes=(EvidenceClass.HEURISTIC,),
    )
    first = CapabilityDefinition(
        capability_id="custom.first",
        title="First",
        plane_id=PlaneId.FUNCTION,
        structural_role="First mutually exclusive structural policy.",
        applicability=applicability,
        prerequisite_capability_ids=(),
        evidence_needs=(evidence_need,),
        incompatible_capability_ids=("custom.second",),
        authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
        provenance_refs=provenance,
    )
    second = CapabilityDefinition(
        capability_id="custom.second",
        title="Second",
        plane_id=PlaneId.RELATION,
        structural_role="Second mutually exclusive structural policy.",
        applicability=applicability,
        prerequisite_capability_ids=(),
        evidence_needs=(replace(evidence_need, evidence_need_id="need:second-declaration"),),
        incompatible_capability_ids=("custom.first",),
        authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
        provenance_refs=provenance,
    )
    ontology = CapabilityOntology(
        ontology_id="custom:incompatibility:v1",
        semantic_version="1.0.0",
        capabilities=(second, first),
        module_support=(
            _support(first, module_id="first"),
            _support(second, module_id="second"),
        ),
        authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
        provenance_refs=provenance,
    )

    gaps = query_capability_gaps(ontology)

    assert tuple(gap.kind for gap in gaps) == (
        CapabilityGapKind.INCOMPATIBLE_ACTIVE_CAPABILITIES,
        CapabilityGapKind.INCOMPATIBLE_ACTIVE_CAPABILITIES,
    )
    assert tuple(gap.capability_id for gap in gaps) == ("custom.first", "custom.second")


def test_unknown_links_and_prerequisite_cycles_fail_closed() -> None:
    base = default_capability_ontology()
    first = base.capabilities[0]

    with pytest.raises(ValueError, match="unknown prerequisite"):
        replace(
            base,
            capabilities=(
                replace(
                    first,
                    prerequisite_capability_ids=("unknown.capability",),
                ),
                *base.capabilities[1:],
            ),
        )

    custom = tuple(base.capabilities[:2])
    cyclic = (
        replace(
            custom[0],
            prerequisite_capability_ids=(custom[1].capability_id,),
        ),
        replace(
            custom[1],
            prerequisite_capability_ids=(custom[0].capability_id,),
        ),
    )
    with pytest.raises(ValueError, match="prerequisite cycle"):
        CapabilityOntology(
            ontology_id="custom:cycle:v1",
            semantic_version="1.0.0",
            capabilities=cyclic,
            module_support=(),
            authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
            provenance_refs=base.provenance_refs,
        )


def test_explicit_scope_can_be_closed_or_forward_extensible() -> None:
    closed = CapabilityApplicability(
        family_mode=ScopeMode.EXPLICIT,
        family_ids=("floral",),
        accepts_new_family_ids=False,
        floral_mode=ScopeMode.EXPLICIT,
        floral_subtype_ids=("rose",),
        accepts_new_floral_subtype_ids=False,
    )
    extensible = replace(
        closed,
        accepts_new_family_ids=True,
        accepts_new_floral_subtype_ids=True,
    )

    assert closed.applies_to(family_id="floral", floral_subtype_id="rose")
    assert not closed.applies_to(family_id="woody", floral_subtype_id="orchid")
    assert extensible.applies_to(family_id="woody", floral_subtype_id="orchid")
