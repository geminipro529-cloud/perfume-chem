from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from decimal import Decimal

import pytest

from engine.scientific_validation.claim_registry import (
    CLAIM_FAMILY_POLICIES,
    is_authoritative_method,
    validate_claim_method_alignment,
)
from engine.scientific_validation.contracts import (
    AssessorType,
    BindingAuthorityState,
    BindingState,
    ClaimAuthorityState,
    ClaimDefinition,
    ClaimFamily,
    ClaimScope,
    ComparatorDefinition,
    CriterionKind,
    DecisionCriterion,
    EndpointDefinition,
    EndpointRole,
    EvidenceRequirement,
    MarginAuthority,
    ScopeValue,
    ValidationMethodFamily,
    VersionBinding,
)

EXPECTED_CLAIM_FAMILIES = (
    "exact_bottle_arithmetic",
    "event_replay",
    "analytical_identity",
    "analytical_quantity",
    "equilibrium_headspace_prediction",
    "physical_release_trajectory",
    "above_threshold_screening",
    "perceptible_difference",
    "sensory_similarity_equivalence",
    "descriptive_profile_accuracy",
    "temporal_profile_accuracy",
    "reconstruction_similarity",
    "intervention_effectiveness",
    "protected_attribute_preservation",
    "preference_liking_prediction",
    "longevity_projection_proxy",
    "regulatory_screening",
)

EXPECTED_AUTHORITY_METHODS = {
    ClaimFamily.EXACT_BOTTLE_ARITHMETIC: (
        ValidationMethodFamily.DETERMINISTIC_ARITHMETIC,
    ),
    ClaimFamily.EVENT_REPLAY: (ValidationMethodFamily.EVENT_STREAM_REPLAY,),
    ClaimFamily.ANALYTICAL_IDENTITY: (
        ValidationMethodFamily.ANALYTICAL_IDENTITY,
    ),
    ClaimFamily.ANALYTICAL_QUANTITY: (
        ValidationMethodFamily.ANALYTICAL_QUANTITATION,
    ),
    ClaimFamily.EQUILIBRIUM_HEADSPACE_PREDICTION: (
        ValidationMethodFamily.HELD_OUT_HEADSPACE_BENCHMARK,
        ValidationMethodFamily.ANALYTICAL_QUANTITATION,
    ),
    ClaimFamily.PHYSICAL_RELEASE_TRAJECTORY: (
        ValidationMethodFamily.HELD_OUT_PHYSICAL_RELEASE_BENCHMARK,
        ValidationMethodFamily.ANALYTICAL_QUANTITATION,
    ),
    ClaimFamily.ABOVE_THRESHOLD_SCREENING: (
        ValidationMethodFamily.CONTEXTUAL_THRESHOLD_SCREENING,
    ),
    ClaimFamily.PERCEPTIBLE_DIFFERENCE: (
        ValidationMethodFamily.SENSORY_DISCRIMINATION,
        ValidationMethodFamily.DIRECTIONAL_PAIRED_COMPARISON,
    ),
    ClaimFamily.SENSORY_SIMILARITY_EQUIVALENCE: (
        ValidationMethodFamily.TRAINED_QUANTITATIVE_DESCRIPTIVE_PROFILE,
    ),
    ClaimFamily.DESCRIPTIVE_PROFILE_ACCURACY: (
        ValidationMethodFamily.TRAINED_QUANTITATIVE_DESCRIPTIVE_PROFILE,
    ),
    ClaimFamily.TEMPORAL_PROFILE_ACCURACY: (
        ValidationMethodFamily.REPEATED_TEMPORAL_INTENSITY_PROFILE,
    ),
    ClaimFamily.RECONSTRUCTION_SIMILARITY: (
        ValidationMethodFamily.TRAINED_QUANTITATIVE_DESCRIPTIVE_PROFILE,
        ValidationMethodFamily.SENSOMICS_RECOMBINATION,
    ),
    ClaimFamily.INTERVENTION_EFFECTIVENESS: (
        ValidationMethodFamily.TRAINED_QUANTITATIVE_DESCRIPTIVE_PROFILE,
    ),
    ClaimFamily.PROTECTED_ATTRIBUTE_PRESERVATION: (
        ValidationMethodFamily.TRAINED_QUANTITATIVE_DESCRIPTIVE_PROFILE,
    ),
    ClaimFamily.PREFERENCE_LIKING_PREDICTION: (
        ValidationMethodFamily.CONTROLLED_CONSUMER_HEDONIC,
    ),
    ClaimFamily.LONGEVITY_PROJECTION_PROXY: (
        ValidationMethodFamily.REPEATED_TEMPORAL_INTENSITY_PROFILE,
        ValidationMethodFamily.HELD_OUT_PHYSICAL_RELEASE_BENCHMARK,
    ),
    ClaimFamily.REGULATORY_SCREENING: (
        ValidationMethodFamily.REGULATORY_EVIDENCE_REVIEW,
    ),
}


def formula_binding(identifier: str, digest: str = "a" * 64) -> VersionBinding:
    return VersionBinding(
        kind="formula",
        identifier=identifier,
        version="overlay-sha256",
        sha256=digest,
        authority_state=BindingAuthorityState.QUARANTINED,
    )


def software_binding(digest: str = "b" * 64) -> VersionBinding:
    return VersionBinding(
        kind="software",
        identifier="perfume-chem",
        version="859cf79666318fd09499d170ead63e4e916d4621",
        sha256=digest,
        authority_state=BindingAuthorityState.REFERENCE_ONLY,
    )


def minimum_effect() -> DecisionCriterion:
    return DecisionCriterion(
        criterion_id="minimum-effect",
        kind=CriterionKind.MINIMUM_EFFECT,
        lower_margin=Decimal("0.50"),
        upper_margin=None,
        unit="scale points",
        margin_authority=MarginAuthority.PROVISIONAL_PREPILOT,
        success_rule="lower confidence bound meets the margin",
        failure_rule="upper confidence bound is nonpositive",
        inconclusive_rule="all other interval positions are inconclusive",
    )


def primary_endpoint() -> EndpointDefinition:
    return EndpointDefinition(
        endpoint_id="primary-iris",
        claim_family=ClaimFamily.INTERVENTION_EFFECTIVENESS,
        role=EndpointRole.PRIMARY,
        attribute="iris/orris intensity",
        method_family=(
            ValidationMethodFamily.TRAINED_QUANTITATIVE_DESCRIPTIVE_PROFILE
        ),
        timepoint="30 minutes",
        scale="anchored 0-to-10",
        estimand="paired mean difference",
        criterion=minimum_effect(),
    )


def valid_claim() -> ClaimDefinition:
    control = formula_binding("control", "1" * 64)
    intervention = formula_binding("intervention", "2" * 64)
    return ClaimDefinition(
        claim_id="D0-TEST-001",
        version=1,
        title="test planning claim",
        family=ClaimFamily.INTERVENTION_EFFECTIVENESS,
        claimant_versions=(intervention, software_binding()),
        assessor_type=AssessorType.TRAINED_DESCRIPTIVE_PANEL,
        scope=ClaimScope(
            population=ScopeValue.bound("trained panel"),
            product=ScopeValue.bound("research product"),
            formula=ScopeValue.required_unbound("formula must be locked"),
            lot=ScopeValue.required_unbound("lot must be created"),
            matrix=ScopeValue.required_unbound("matrix must be locked"),
            substrate=ScopeValue.bound("blotter"),
            condition=ScopeValue.required_unbound("condition must be locked"),
        ),
        primary_endpoint=primary_endpoint(),
        secondary_endpoints=(),
        comparator=ComparatorDefinition(
            comparator_id="control",
            description="locked control",
            binding=control,
        ),
        required_evidence=(EvidenceRequirement("evidence", "real evidence"),),
        authority_state=ClaimAuthorityState.PLANNING_ONLY,
        expiration_triggers=("formula hash changes",),
    )


def test_scope_value_requires_exactly_one_bound_value_or_unbound_reason() -> None:
    assert ScopeValue.bound("standardized blotter").state is BindingState.BOUND
    assert ScopeValue.required_unbound("lot not created").value is None
    with pytest.raises(ValueError, match="bound scope value"):
        ScopeValue(state=BindingState.BOUND, value=None, reason=None)
    with pytest.raises(ValueError, match="unbound scope value"):
        ScopeValue(
            state=BindingState.REQUIRED_UNBOUND,
            value="fabricated",
            reason="not allowed",
        )


def test_version_binding_rejects_malformed_hash_and_empty_identity() -> None:
    with pytest.raises(ValueError, match="identifier"):
        formula_binding("")
    with pytest.raises(ValueError, match="sha256"):
        formula_binding("control", "not-a-hash")


def test_contracts_are_frozen() -> None:
    binding = formula_binding("control")
    with pytest.raises(FrozenInstanceError):
        binding.identifier = "changed"  # type: ignore[misc]


def test_decision_criterion_rejects_invalid_margin_geometry() -> None:
    with pytest.raises(ValueError, match="minimum-effect"):
        replace(minimum_effect(), upper_margin=Decimal("0.75"))
    with pytest.raises(ValueError, match="equivalence"):
        DecisionCriterion(
            criterion_id="bad-equivalence",
            kind=CriterionKind.EQUIVALENCE,
            lower_margin=Decimal("0"),
            upper_margin=Decimal("0.75"),
            unit="scale points",
            margin_authority=MarginAuthority.PROVISIONAL_PREPILOT,
            success_rule="inside",
            failure_rule="outside",
            inconclusive_rule="overlap",
        )


def test_claim_rejects_invalid_version_duplicate_evidence_and_primary_shape() -> None:
    claim = valid_claim()
    with pytest.raises(ValueError, match="version"):
        replace(claim, version=0)
    with pytest.raises(ValueError, match="evidence"):
        replace(claim, required_evidence=claim.required_evidence * 2)
    with pytest.raises(ValueError, match="primary endpoint"):
        replace(
            claim,
            primary_endpoint=replace(
                claim.primary_endpoint,
                role=EndpointRole.SECONDARY_SUPPORTIVE,
            ),
        )


def test_claim_hash_is_stable_and_fixed_authority_fields_are_false() -> None:
    first = valid_claim()
    second = valid_claim()
    assert first.content_sha256 == second.content_sha256
    assert len(first.content_sha256) == 64
    assert first.study_authorized is False
    assert first.release_authority is False
    assert first.observed_outcome == "unmeasured"


def test_registry_contains_exactly_17_unique_master_claim_families() -> None:
    assert tuple(family.value for family in ClaimFamily) == EXPECTED_CLAIM_FAMILIES
    assert tuple(policy.family for policy in CLAIM_FAMILY_POLICIES) == tuple(
        ClaimFamily
    )
    assert len({policy.family for policy in CLAIM_FAMILY_POLICIES}) == 17
    assert all(policy.authoritative_methods for policy in CLAIM_FAMILY_POLICIES)
    assert {
        policy.family: policy.authoritative_methods
        for policy in CLAIM_FAMILY_POLICIES
    } == EXPECTED_AUTHORITY_METHODS


@pytest.mark.parametrize(
    ("family", "method"),
    [
        (
            ClaimFamily.EXACT_BOTTLE_ARITHMETIC,
            ValidationMethodFamily.SENSORY_DISCRIMINATION,
        ),
        (
            ClaimFamily.PREFERENCE_LIKING_PREDICTION,
            ValidationMethodFamily.ANALYTICAL_QUANTITATION,
        ),
        (
            ClaimFamily.SENSORY_SIMILARITY_EQUIVALENCE,
            ValidationMethodFamily.SENSORY_DISCRIMINATION,
        ),
    ],
)
def test_master_category_errors_fail_closed(
    family: ClaimFamily,
    method: ValidationMethodFamily,
) -> None:
    assert is_authoritative_method(family, method) is False


def test_claim_method_alignment_checks_primary_and_secondary_endpoints() -> None:
    claim = valid_claim()
    validate_claim_method_alignment(claim)

    misaligned = replace(
        claim,
        primary_endpoint=replace(
            claim.primary_endpoint,
            method_family=ValidationMethodFamily.SENSORY_DISCRIMINATION,
        ),
    )
    with pytest.raises(ValueError, match="cannot authorize"):
        validate_claim_method_alignment(misaligned)
