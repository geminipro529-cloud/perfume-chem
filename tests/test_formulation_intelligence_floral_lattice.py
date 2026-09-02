from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from engine.formulation_intelligence.contracts import (
    AssessmentScope,
    AuthorityCeiling,
    EvidenceClass,
    PlaneAssessment,
    PlaneId,
    ProvenanceRef,
    SupportMeasure,
    ValueState,
)
from engine.formulation_intelligence.floral_lattice import (
    BouquetMember,
    BouquetRelation,
    BouquetRelationKind,
    BouquetRole,
    CustomFloralExpression,
    CustomFloralFacet,
    FacetOmission,
    FacetRole,
    FacetSelection,
    FloralAbstraction,
    FloralCandidateSignals,
    FloralCaricature,
    FloralFacet,
    FloralFailureMode,
    FloralMorphologyIntent,
    FloralMorphologyPlaneAdapter,
    FloralSubject,
    FloralSubtype,
    MorphologyEvidence,
    NaturalMixtureRepresentation,
    NaturalMixtureTreatment,
    PersistenceEvidence,
    TemporalTransformation,
    TemporalWindow,
    TransformationKind,
    assess_floral_morphology,
    detect_floral_failure_modes,
    expression_space_for,
    subtype_space_for,
)
from engine.formulation_intelligence.plane_synthesis import PlaneAssessmentAdapter


def _scope() -> AssessmentScope:
    return AssessmentScope(
        target_scope="target:floral-study-v1",
        temporal_scope="opening through 8 h",
        matrix_scope="ideal target; matrix not yet bound",
    )


def _source(provenance_id: str = "prov:local-review") -> ProvenanceRef:
    return ProvenanceRef(
        provenance_id=provenance_id,
        source_ref=f"study://{provenance_id}",
        evidence_class=EvidenceClass.DIRECT_OBSERVATION,
        independence_key=f"study:{provenance_id}",
    )


def _rose_intent(
    *,
    selected_facets: tuple[FacetSelection, ...] = (),
    temporal_transformations: tuple[TemporalTransformation, ...] = (),
    exact_subtype: FloralSubtype | None = None,
    custom_expressions: tuple[CustomFloralExpression, ...] = (),
) -> FloralMorphologyIntent:
    return FloralMorphologyIntent(
        flower_subject=FloralSubject.ROSE,
        abstraction_level=FloralAbstraction.STYLIZED,
        requested_expression=("dewy", "peppery", "tea"),
        protected_recognizers=("living petal identity", "tea-rose contour"),
        forbidden_drift=("jammy confection", "generic floral heart"),
        intended_temporal_transformations=temporal_transformations,
        selected_facets=selected_facets,
        deliberate_omissions=(
            FacetOmission(
                subject=FloralSubject.ROSE,
                facet=FloralFacet.SENESCENT_DRIED,
                rationale="Keep the requested living dewy expression out of potpourri drift.",
            ),
        ),
        bouquet_hierarchy=(),
        exact_subtype=exact_subtype,
        custom_expressions=custom_expressions,
    )


def _claim_keys(assessment: PlaneAssessment) -> set[str]:
    return {claim.claim_key for claim in assessment.claims}


def test_subject_catalog_covers_every_design_spec_family_and_expression_space() -> None:
    expected = {
        FloralSubject.ROSE: {"tea", "fresh garden", "dewy", "peppery", "fruity/damask"},
        FloralSubject.JASMINE: {"luminous", "tea-like", "green", "narcotic", "nocturnal"},
        FloralSubject.TUBEROSE: {
            "green/camphoraceous",
            "creamy/lactonic",
            "mentholic",
            "rubbery",
        },
        FloralSubject.MUGUET_LILY: {"watery", "green", "airy", "soapy", "waxy", "pollen"},
        FloralSubject.ORANGE_BLOSSOM_NEROLI: {
            "citrus-flower",
            "leafy",
            "honeyed",
            "indolic",
            "solar",
        },
        FloralSubject.IRIS_ORRIS_VIOLET: {
            "petal",
            "root/rhizome",
            "carrot",
            "suede",
            "concrete-like",
        },
        FloralSubject.MAGNOLIA_CHAMPACA: {
            "lemony",
            "watery",
            "waxy",
            "tea",
            "humid",
            "shadowed",
        },
        FloralSubject.YLANG_GARDENIA_FRANGIPANI: {
            "banana-fruity",
            "lactonic",
            "mushroomy",
            "tropical",
        },
        FloralSubject.OSMANTHUS: {"apricot", "tea", "leather/suede", "honey", "hay"},
        FloralSubject.MIMOSA_CASSIE_ACACIA: {
            "pollen",
            "powder",
            "honey",
            "almond",
            "suede",
        },
        FloralSubject.NARCISSUS_HYACINTH_LILAC_CARNATION_PEONY_LINDEN: {
            "flower-specific green",
            "spicy",
            "watery",
            "phenolic",
            "textural",
        },
        FloralSubject.BOUQUET_HYBRID: {
            "hierarchical",
            "overlapping",
            "bridged",
            "contrasted",
            "anti-takeover",
        },
    }

    assert set(FloralSubject) == set(expected)
    for subject, required in expected.items():
        assert required <= set(expression_space_for(subject))

    assert subtype_space_for(FloralSubject.IRIS_ORRIS_VIOLET) == (
        FloralSubtype.IRIS,
        FloralSubtype.ORRIS,
        FloralSubtype.VIOLET,
    )


def test_custom_terms_and_exact_subtypes_are_explicit_not_silent_enum_coercions() -> None:
    custom_expression = CustomFloralExpression(
        expression_id="rain-mineral-petal",
        label="rain on mineral petal",
        rationale="The named target asks for a wet mineral contrast absent from the base list.",
    )
    custom_facet = CustomFloralFacet(
        facet_id="ozonic-static",
        label="ozonic static",
    )
    intent = _rose_intent(
        exact_subtype=FloralSubtype.ROSE,
        custom_expressions=(custom_expression,),
        selected_facets=(
            FacetSelection(
                subject=FloralSubject.ROSE,
                facet=custom_facet,
                role=FacetRole.CONTRAST,
                rationale="Keep the custom facet subordinate to the living rose recognizer.",
            ),
        ),
    )

    assessment = assess_floral_morphology(intent, scope=_scope())

    assert "morphology.exact_subtype.rose" in _claim_keys(assessment)
    assert "morphology.expression.custom.rain-mineral-petal" in _claim_keys(assessment)
    assert "morphology.facet.rose.custom.ozonic-static" in _claim_keys(assessment)
    assert not any(item.field_key == "morphology.exact_subtype.rose" for item in assessment.unknowns)

    with pytest.raises(ValueError, match="does not belong to"):
        _rose_intent(exact_subtype=FloralSubtype.MAGNOLIA)

    with pytest.raises((TypeError, ValueError), match="CustomFloralFacet"):
        FacetSelection(
            subject=FloralSubject.ROSE,
            facet="ozonic-static",  # type: ignore[arg-type]
            role=FacetRole.CONTRAST,
            rationale="A raw string must not become a custom ontology term implicitly.",
        )


def test_grouped_subject_without_exact_subtype_stays_explicitly_unknown() -> None:
    intent = FloralMorphologyIntent(
        flower_subject=FloralSubject.IRIS_ORRIS_VIOLET,
        abstraction_level=FloralAbstraction.STYLIZED,
        requested_expression=("root/rhizome", "cool"),
        protected_recognizers=("cool rhizome identity",),
        forbidden_drift=("generic powder",),
        intended_temporal_transformations=(),
        selected_facets=(),
        deliberate_omissions=(),
        bouquet_hierarchy=(),
    )

    assessment = assess_floral_morphology(intent, scope=_scope())

    assert any(
        item.field_key == "morphology.exact_subtype.iris_orris_violet"
        for item in assessment.unknowns
    )


def test_ontology_provenance_is_heuristic_and_bound_to_its_exact_hash() -> None:
    assessment = assess_floral_morphology(_rose_intent(), scope=_scope())
    ontology = next(
        item
        for item in assessment.provenance_refs
        if item.provenance_id.startswith("floral-lattice:ontology")
    )

    assert ontology.evidence_class is EvidenceClass.HEURISTIC
    assert ontology.source_sha256 is not None
    assert len(ontology.source_sha256) == 64
    assert ontology.source_sha256 in assessment.freshness_hashes
    assert ontology.source_sha256 in ontology.source_ref


def test_rose_assessment_is_exact_scope_target_linked_and_provenance_bearing() -> None:
    facet = FacetSelection(
        subject=FloralSubject.ROSE,
        facet=FloralFacet.AQUEOUS_DEW,
        role=FacetRole.CORE_RECOGNIZER,
        rationale="Protect the requested dew-lit living petal rather than generic freshness.",
    )
    temporal = TemporalTransformation(
        transformation_id="rose-dew-to-tea",
        subject=FloralSubject.ROSE,
        from_window=TemporalWindow.OPENING,
        to_window=TemporalWindow.THIRTY_MIN,
        kind=TransformationKind.REVEAL,
        intended_change="Dew recedes while the tea-rose contour remains identifiable.",
        protected_recognizers=("tea-rose contour",),
    )
    intent = _rose_intent(selected_facets=(facet,), temporal_transformations=(temporal,))
    evidence = MorphologyEvidence(
        evidence_id="evidence:dew-facet",
        claim_key="morphology.facet.rose.aqueous_dew",
        scope=_scope(),
        lower=0.35,
        upper=0.62,
        provenance_refs=(_source(),),
    )

    assessment = assess_floral_morphology(intent, scope=_scope(), evidence=(evidence,))

    assert assessment.plane_id is PlaneId.MORPHOLOGY
    assert assessment.scope == _scope()
    assert assessment.authority_ceiling is AuthorityCeiling.STRUCTURAL_ONLY
    assert "morphology.subject" in _claim_keys(assessment)
    assert "morphology.facet.rose.aqueous_dew" in _claim_keys(assessment)
    assert "morphology.temporal.rose-dew-to-tea" in _claim_keys(assessment)
    assert any(item.lower == 0.35 and item.upper == 0.62 for item in assessment.support_intervals)
    assert "prov:local-review" in {item.provenance_id for item in assessment.provenance_refs}
    assert all("rose" in experiment.casefold() for experiment in assessment.proposed_experiments)


def test_evidence_is_exact_scope_and_declarations_are_not_empirical_support() -> None:
    facet = FacetSelection(
        subject=FloralSubject.ROSE,
        facet=FloralFacet.AQUEOUS_DEW,
        role=FacetRole.CORE_RECOGNIZER,
        rationale="Protect the requested dew-lit petal.",
    )
    intent = _rose_intent(selected_facets=(facet,))
    evidence = MorphologyEvidence(
        evidence_id="evidence:exact-scope-dew",
        claim_key="morphology.facet.rose.aqueous_dew",
        scope=_scope(),
        lower=0.2,
        upper=0.7,
        provenance_refs=(_source("prov:exact-scope-dew"),),
    )

    assessment = assess_floral_morphology(intent, scope=_scope(), evidence=(evidence,))
    claim = next(
        item
        for item in assessment.claims
        if item.claim_key == "morphology.facet.rose.aqueous_dew"
    )
    intervals = tuple(
        item for item in assessment.support_intervals if item.claim_id == claim.claim_id
    )

    assert {item.support_measure for item in intervals} == {
        SupportMeasure.DECLARATION_PRESENCE,
        SupportMeasure.EVIDENCE_SUPPORT,
    }
    declaration = next(
        item
        for item in intervals
        if item.support_measure is SupportMeasure.DECLARATION_PRESENCE
    )
    empirical = next(
        item for item in intervals if item.support_measure is SupportMeasure.EVIDENCE_SUPPORT
    )
    assert (declaration.lower, declaration.upper) == (1.0, 1.0)
    assert (empirical.lower, empirical.upper) == (0.2, 0.7)
    assert all(
        ref.evidence_class in {EvidenceClass.USER_REPORT, EvidenceClass.HEURISTIC}
        for ref in declaration.provenance_refs
    )
    assert empirical.provenance_refs == (_source("prov:exact-scope-dew"),)

    wrong_scope = AssessmentScope(
        target_scope=_scope().target_scope,
        temporal_scope="opening through 4 h",
        matrix_scope=_scope().matrix_scope,
    )
    mismatched = MorphologyEvidence(
        evidence_id="evidence:wrong-scope-dew",
        claim_key="morphology.facet.rose.aqueous_dew",
        scope=wrong_scope,
        lower=0.2,
        upper=0.7,
        provenance_refs=(_source("prov:wrong-scope-dew"),),
    )
    with pytest.raises(ValueError, match="exact assessment scope"):
        assess_floral_morphology(intent, scope=_scope(), evidence=(mismatched,))


@pytest.mark.parametrize(
    ("subject", "expressions", "facets"),
    (
        (
            FloralSubject.TUBEROSE,
            ("green/camphoraceous", "creamy/lactonic"),
            (FloralFacet.GREEN_STEM_LEAF, FloralFacet.LACTONE_CREAM),
        ),
        (
            FloralSubject.IRIS_ORRIS_VIOLET,
            ("root/rhizome", "mineral", "suede"),
            (FloralFacet.EARTH_ROOT_RHIZOME, FloralFacet.MINERAL_CONCRETE),
        ),
        (
            FloralSubject.MAGNOLIA_CHAMPACA,
            ("watery", "tea", "shadowed"),
            (FloralFacet.AQUEOUS_DEW, FloralFacet.TEA, FloralFacet.DARK_SHADOW),
        ),
    ),
)
def test_target_appropriate_subject_morphologies(
    subject: FloralSubject,
    expressions: tuple[str, ...],
    facets: tuple[FloralFacet, ...],
) -> None:
    intent = FloralMorphologyIntent(
        flower_subject=subject,
        abstraction_level=FloralAbstraction.NATURALISTIC,
        requested_expression=expressions,
        protected_recognizers=(f"{subject.value} identity",),
        forbidden_drift=("generic floral heart",),
        intended_temporal_transformations=(),
        selected_facets=tuple(
            FacetSelection(
                subject=subject,
                facet=facet,
                role=FacetRole.SUPPORT,
                rationale=f"Keep {facet.value} tied to the requested {subject.value} expression.",
            )
            for facet in facets
        ),
        deliberate_omissions=(),
        bouquet_hierarchy=(),
    )

    assessment = assess_floral_morphology(intent, scope=_scope())

    assert all(
        f"morphology.facet.{subject.value}.{facet.value}" in _claim_keys(assessment)
        for facet in facets
    )
    assert any(unknown.field_key == "morphology.sensory_target_fidelity" for unknown in assessment.unknowns)


def test_facets_are_optional_and_inappropriate_facets_fail_closed() -> None:
    sparse = assess_floral_morphology(_rose_intent(), scope=_scope())

    assert not any(key.startswith("morphology.facet.") for key in _claim_keys(sparse))
    assert FloralFailureMode.MATERIAL_COUNT_INFLATION.value not in sparse.failure_modes

    with pytest.raises(ValueError, match="not target-appropriate"):
        _rose_intent(
            selected_facets=(
                FacetSelection(
                    subject=FloralSubject.ROSE,
                    facet=FloralFacet.RUBBER,
                    role=FacetRole.CONTRAST,
                    rationale="Invalid on purpose.",
                ),
            )
        )


def test_protected_recognizers_and_deliberate_omissions_remain_distinct() -> None:
    assessment = assess_floral_morphology(_rose_intent(), scope=_scope())
    keys = _claim_keys(assessment)

    assert "morphology.protected_recognizer.living-petal-identity" in keys
    assert "morphology.protected_recognizer.tea-rose-contour" in keys
    assert "morphology.omission.rose.senescent_dried" in keys
    assert any(claim.claim_kind.value == "prohibition" for claim in assessment.claims)


def test_hierarchical_bouquet_preserves_relations_and_detects_takeover() -> None:
    hierarchy = (
        BouquetMember(
            subject=FloralSubject.ROSE,
            exact_subtype=FloralSubtype.ROSE,
            role=BouquetRole.PRIMARY,
            rank=0,
            requested_expressions=("tea", "dewy"),
            takeover_prohibited=False,
        ),
        BouquetMember(
            subject=FloralSubject.IRIS_ORRIS_VIOLET,
            exact_subtype=FloralSubtype.ORRIS,
            role=BouquetRole.SHADOW,
            rank=2,
            requested_expressions=("root/rhizome", "cool"),
            takeover_prohibited=True,
        ),
        BouquetMember(
            subject=FloralSubject.MAGNOLIA_CHAMPACA,
            exact_subtype=FloralSubtype.MAGNOLIA,
            role=BouquetRole.BRIDGE,
            rank=1,
            requested_expressions=("tea", "waxy"),
            takeover_prohibited=True,
        ),
        BouquetMember(
            subject=FloralSubject.TUBEROSE,
            exact_subtype=FloralSubtype.TUBEROSE,
            role=BouquetRole.CONTRAST,
            rank=3,
            requested_expressions=("green/camphoraceous",),
            takeover_prohibited=True,
        ),
    )
    relations = (
        BouquetRelation(
            relation_id="rose-orris-overlap",
            source_subtype=FloralSubtype.ROSE,
            target_subtype=FloralSubtype.ORRIS,
            kind=BouquetRelationKind.OVERLAP,
            rationale="Keep the orris shadow inside the rose-led petal contour.",
        ),
        BouquetRelation(
            relation_id="magnolia-rose-bridge",
            source_subtype=FloralSubtype.MAGNOLIA,
            target_subtype=FloralSubtype.ROSE,
            kind=BouquetRelationKind.BRIDGE,
            rationale="Use the magnolia tea-wax contour as a bridge into rose.",
        ),
        BouquetRelation(
            relation_id="magnolia-orris-bridge",
            source_subtype=FloralSubtype.MAGNOLIA,
            target_subtype=FloralSubtype.ORRIS,
            kind=BouquetRelationKind.BRIDGE,
            rationale="Join magnolia wax to the cool orris shadow.",
        ),
    )
    intent = FloralMorphologyIntent(
        flower_subject=FloralSubject.BOUQUET_HYBRID,
        abstraction_level=FloralAbstraction.HYBRID,
        requested_expression=("hierarchical", "bridged", "anti-takeover"),
        protected_recognizers=("rose-led hierarchy", "orris shadow"),
        forbidden_drift=("white floral foreground", "homogeneous floral heart"),
        intended_temporal_transformations=(),
        selected_facets=(),
        deliberate_omissions=(),
        bouquet_hierarchy=hierarchy,
        bouquet_relations=relations,
    )
    signals = FloralCandidateSignals(
        declared_foreground_subjects=(FloralSubject.TUBEROSE,),
    )

    assessment = assess_floral_morphology(
        intent,
        scope=_scope(),
        candidate_signals=signals,
    )

    assert "morphology.bouquet.rose" in _claim_keys(assessment)
    assert "morphology.bouquet.magnolia_champaca" in _claim_keys(assessment)
    assert "morphology.bouquet_relation.magnolia-rose-bridge" in _claim_keys(assessment)
    assert FloralFailureMode.WHITE_FLORAL_TAKEOVER.value in assessment.failure_modes
    assert any("takeover" in item.casefold() for item in assessment.proposed_experiments)


def test_generic_heart_and_every_required_failure_detector() -> None:
    intent = _rose_intent()
    signals = FloralCandidateSignals(
        generic_floral_heart_substitution=True,
        canned_ratio_reuse_without_target_evidence=True,
        white_floral_takeover=True,
        disconnected_fruit_citrus_foreground=True,
        comfort_substituted_for_development=True,
        anonymous_wood_musk_amber_drydown=True,
        petal_to_base_discontinuity=True,
        caricatures=tuple(FloralCaricature),
        declared_material_count=40,
        material_count_used_as_quality_evidence=True,
        natural_mixtures=(
            NaturalMixtureRepresentation(
                mixture_id="natural-mixture-a",
                declared_treatment=NaturalMixtureTreatment.MONOMOLECULAR,
            ),
        ),
        prestige_used_as_target_fit_evidence=True,
        persistence_evidence=PersistenceEvidence.MODELED_ONLY,
        persistence_claimed_as_observed_continuity=True,
    )

    detected = detect_floral_failure_modes(intent, signals)
    assessment = assess_floral_morphology(
        intent,
        scope=_scope(),
        candidate_signals=signals,
    )

    assert detected == tuple(sorted(FloralFailureMode, key=lambda item: item.value))
    assert set(assessment.failure_modes) == {item.value for item in FloralFailureMode}
    assert all(key.startswith("morphology.failure.") for key in _claim_keys(assessment) if ".failure." in key)


def test_material_count_is_not_an_endpoint_and_does_not_change_assessment() -> None:
    intent = _rose_intent()
    sparse = assess_floral_morphology(
        intent,
        scope=_scope(),
        candidate_signals=FloralCandidateSignals(declared_material_count=3),
    )
    dense = assess_floral_morphology(
        intent,
        scope=_scope(),
        candidate_signals=FloralCandidateSignals(declared_material_count=300),
    )

    assert sparse.as_dict() == dense.as_dict()
    assert sparse.content_sha256 == dense.content_sha256
    assert all("count" not in criterion.criterion_id for criterion in sparse.native_criteria)


def test_natural_mixture_firewall_and_unknown_preservation() -> None:
    intent = _rose_intent()
    composite = assess_floral_morphology(
        intent,
        scope=_scope(),
        candidate_signals=FloralCandidateSignals(
            natural_mixtures=(
                NaturalMixtureRepresentation(
                    mixture_id="natural-mixture-a",
                    declared_treatment=NaturalMixtureTreatment.COMPOSITE,
                ),
            )
        ),
    )
    monomolecular = assess_floral_morphology(
        intent,
        scope=_scope(),
        candidate_signals=FloralCandidateSignals(
            natural_mixtures=(
                NaturalMixtureRepresentation(
                    mixture_id="natural-mixture-a",
                    declared_treatment=NaturalMixtureTreatment.MONOMOLECULAR,
                ),
            )
        ),
    )
    unknown = assess_floral_morphology(
        intent,
        scope=_scope(),
        candidate_signals=FloralCandidateSignals(
            natural_mixtures=(
                NaturalMixtureRepresentation(
                    mixture_id="natural-mixture-a",
                    declared_treatment=NaturalMixtureTreatment.UNKNOWN,
                ),
            )
        ),
    )

    assert FloralFailureMode.NATURAL_MIXTURE_MONOMOLECULAR.value not in composite.failure_modes
    assert FloralFailureMode.NATURAL_MIXTURE_MONOMOLECULAR.value in monomolecular.failure_modes
    assert any(item.field_key == "morphology.natural_mixture.natural-mixture-a" for item in unknown.unknowns)
    assert all(criterion.value.state is ValueState.UNKNOWN for criterion in unknown.native_criteria)
    assert all(criterion.value.value is None for criterion in unknown.native_criteria)


def test_declared_composite_is_not_verified_composite_without_exact_scope_evidence() -> None:
    declared = assess_floral_morphology(
        _rose_intent(),
        scope=_scope(),
        candidate_signals=FloralCandidateSignals(
            natural_mixtures=(
                NaturalMixtureRepresentation(
                    mixture_id="rose-natural",
                    declared_treatment=NaturalMixtureTreatment.COMPOSITE,
                ),
            )
        ),
    )
    verified_record = NaturalMixtureRepresentation(
        mixture_id="rose-natural",
        declared_treatment=NaturalMixtureTreatment.COMPOSITE,
        verified_treatment=NaturalMixtureTreatment.COMPOSITE,
        verification_scope=_scope(),
        verification_provenance_refs=(_source("prov:composite-gco"),),
    )
    verified = assess_floral_morphology(
        _rose_intent(),
        scope=_scope(),
        candidate_signals=FloralCandidateSignals(natural_mixtures=(verified_record,)),
    )

    assert any(
        item.field_key == "morphology.natural_mixture.rose-natural.composite_verification"
        for item in declared.unknowns
    )
    assert not any(
        item.field_key == "morphology.natural_mixture.rose-natural.composite_verification"
        for item in verified.unknowns
    )
    assert "morphology.natural_mixture.rose-natural.declaration" in _claim_keys(declared)
    verification_key = "morphology.natural_mixture.rose-natural.verification"
    assert verification_key not in _claim_keys(declared)
    assert verification_key in _claim_keys(verified)
    verification_claim = next(
        item for item in verified.claims if item.claim_key == verification_key
    )
    assert any(
        interval.claim_id == verification_claim.claim_id
        and interval.support_measure is SupportMeasure.DECLARATION_PRESENCE
        for interval in verified.support_intervals
    )

    mismatched_record = NaturalMixtureRepresentation(
        mixture_id="rose-natural",
        declared_treatment=NaturalMixtureTreatment.COMPOSITE,
        verified_treatment=NaturalMixtureTreatment.COMPOSITE,
        verification_scope=AssessmentScope(
            target_scope=_scope().target_scope,
            temporal_scope="opening through 4 h",
            matrix_scope=_scope().matrix_scope,
        ),
        verification_provenance_refs=(_source("prov:wrong-composite-scope"),),
    )
    with pytest.raises(ValueError, match="exact assessment scope"):
        assess_floral_morphology(
            _rose_intent(),
            scope=_scope(),
            candidate_signals=FloralCandidateSignals(
                natural_mixtures=(mismatched_record,)
            ),
        )


def test_authority_ceiling_never_grants_forbidden_outcomes() -> None:
    assessment = assess_floral_morphology(_rose_intent(), scope=_scope())
    forbidden_words = {
        "beauty",
        "liking",
        "sensory pass",
        "safe",
        "release",
        "purchase",
        "compound",
        "stable",
        "performance proven",
    }

    assert assessment.authority_ceiling is AuthorityCeiling.STRUCTURAL_ONLY
    assert all(
        claim.authority_ceiling.rank <= AuthorityCeiling.STRUCTURAL_ONLY.rank
        for claim in assessment.claims
    )
    assert all(
        criterion.authority_ceiling.rank <= AuthorityCeiling.STRUCTURAL_ONLY.rank
        for criterion in assessment.native_criteria
    )
    claim_text = " ".join(claim.claim_value.casefold() for claim in assessment.claims)
    assert not any(word in claim_text for word in forbidden_words)


def test_deterministic_round_trip_hash_and_input_order_invariance() -> None:
    facets = (
        FacetSelection(
            subject=FloralSubject.ROSE,
            facet=FloralFacet.TEA,
            role=FacetRole.SUPPORT,
            rationale="Tie the dry tea register to rose identity.",
        ),
        FacetSelection(
            subject=FloralSubject.ROSE,
            facet=FloralFacet.AQUEOUS_DEW,
            role=FacetRole.CORE_RECOGNIZER,
            rationale="Protect a living dew-lit petal.",
        ),
    )
    transformations = (
        TemporalTransformation(
            transformation_id="tea-reveal",
            subject=FloralSubject.ROSE,
            from_window=TemporalWindow.FIVE_MIN,
            to_window=TemporalWindow.THIRTY_MIN,
            kind=TransformationKind.REVEAL,
            intended_change="Tea contour emerges without loss of petal identity.",
            protected_recognizers=("living petal identity",),
        ),
        TemporalTransformation(
            transformation_id="dew-recede",
            subject=FloralSubject.ROSE,
            from_window=TemporalWindow.OPENING,
            to_window=TemporalWindow.FIVE_MIN,
            kind=TransformationKind.HANDOFF,
            intended_change="Dew recedes into the tea contour.",
            protected_recognizers=("tea-rose contour",),
        ),
    )
    first = _rose_intent(
        selected_facets=facets,
        temporal_transformations=transformations,
    )
    second = FloralMorphologyIntent(
        flower_subject=FloralSubject.ROSE,
        abstraction_level=FloralAbstraction.STYLIZED,
        requested_expression=("tea", "peppery", "dewy"),
        protected_recognizers=("tea-rose contour", "living petal identity"),
        forbidden_drift=("generic floral heart", "jammy confection"),
        intended_temporal_transformations=tuple(reversed(transformations)),
        selected_facets=tuple(reversed(facets)),
        deliberate_omissions=first.deliberate_omissions,
        bouquet_hierarchy=(),
    )

    left = assess_floral_morphology(first, scope=_scope())
    right = assess_floral_morphology(second, scope=_scope())
    restored = PlaneAssessment.from_dict(json.loads(json.dumps(left.as_dict())))

    assert left == right == restored
    assert left.as_dict() == right.as_dict() == restored.as_dict()
    assert left.content_sha256 == right.content_sha256 == restored.content_sha256
    assert len(left.content_sha256) == 64


def test_read_only_adapter_matches_plane_synthesis_protocol() -> None:
    intent = _rose_intent()
    direct = assess_floral_morphology(intent, scope=_scope())
    adapter = FloralMorphologyPlaneAdapter(intent=intent, scope=_scope())

    assert isinstance(adapter, PlaneAssessmentAdapter)
    assert adapter.to_plane_assessment() == direct


def test_module_import_boundary_is_contracts_plus_standard_library_only() -> None:
    module_path = Path("engine/formulation_intelligence/floral_lattice.py")
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")

    assert not any(
        name.startswith(
            (
                "engine.pipeline",
                "engine.inventory",
                "engine.formulas",
                "engine.knowledge.accord_library",
                "engine.knowledge.soliflore_structures",
            )
        )
        for name in imported
    )
    assert imported <= {
        "__future__",
        "collections.abc",
        "dataclasses",
        "enum",
        "hashlib",
        "types",
        "typing",
        "contracts",
    }
