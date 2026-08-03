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
from engine.scientific_validation.first_claim import (
    FIRST_CLAIM_ID,
    build_prada_orris_first_claim,
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


def test_first_claim_defines_the_complete_d0_exit_gate() -> None:
    control = formula_binding("prada-control", "1" * 64)
    intervention = formula_binding("prada-luxury-orris", "2" * 64)
    software = software_binding("3" * 64)

    claim = build_prada_orris_first_claim(
        control_binding=control,
        intervention_binding=intervention,
        software_binding=software,
    )

    assert claim.claim_id == FIRST_CLAIM_ID
    assert claim.claim_id == "D0-PRADA-ORRIS-INTERVENTION-001"
    assert claim.version == 1
    assert claim.family is ClaimFamily.INTERVENTION_EFFECTIVENESS
    assert claim.claimant_versions == (intervention, software)
    assert claim.comparator.binding == control
    assert claim.assessor_type is AssessorType.TRAINED_DESCRIPTIVE_PANEL
    assert claim.primary_endpoint.attribute == "iris/orris intensity"
    assert claim.primary_endpoint.timepoint == "30 minutes post-application"
    assert claim.primary_endpoint.criterion.lower_margin == Decimal("0.50")
    assert claim.primary_endpoint.criterion.upper_margin is None
    assert len(claim.secondary_endpoints) == 3
    assert tuple(endpoint.attribute for endpoint in claim.secondary_endpoints) == (
        "clean pressed-shirt/soapy character",
        "wood-amber structure",
        "dryness/balance",
    )
    assert {
        endpoint.criterion.lower_margin for endpoint in claim.secondary_endpoints
    } == {Decimal("-0.75")}
    assert {
        endpoint.criterion.upper_margin for endpoint in claim.secondary_endpoints
    } == {Decimal("0.75")}
    assert all(
        endpoint.criterion.margin_authority
        is MarginAuthority.PROVISIONAL_PREPILOT
        for endpoint in (claim.primary_endpoint, *claim.secondary_endpoints)
    )
    assert tuple(item.evidence_id for item in claim.required_evidence) == (
        "regenerated-formulas",
        "stock-identity",
        "study-safety",
        "sample-conditions",
        "panel-authority",
        "separate-pilot",
        "margin-power-lock",
        "immutable-study-lock",
        "confirmatory-observations",
        "locked-analysis",
        "claim-specific-analytical-safety",
        "human-release-review",
    )
    assert len(claim.expiration_triggers) == 8
    assert claim.scope.population.state is BindingState.BOUND
    assert claim.scope.substrate.value == "standardized fragrance blotter"
    assert claim.scope.formula.state is BindingState.REQUIRED_UNBOUND
    assert claim.scope.lot.state is BindingState.REQUIRED_UNBOUND
    assert claim.scope.matrix.state is BindingState.REQUIRED_UNBOUND
    assert claim.scope.condition.state is BindingState.REQUIRED_UNBOUND
    assert claim.authority_state is ClaimAuthorityState.PLANNING_ONLY
    assert claim.study_authorized is False
    assert claim.release_authority is False
    assert claim.observed_outcome == "unmeasured"
    validate_claim_method_alignment(claim)


def test_first_claim_is_deterministic_and_immutable() -> None:
    arguments = {
        "control_binding": formula_binding("control", "1" * 64),
        "intervention_binding": formula_binding("intervention", "2" * 64),
        "software_binding": software_binding("3" * 64),
    }
    first = build_prada_orris_first_claim(**arguments)
    second = build_prada_orris_first_claim(**arguments)
    assert first == second
    assert first.content_sha256 == second.content_sha256
    with pytest.raises(FrozenInstanceError):
        first.title = "changed"  # type: ignore[misc]


def test_first_claim_rejects_nonquarantined_formula_bindings() -> None:
    control = replace(
        formula_binding("control"),
        authority_state=BindingAuthorityState.VALIDATED_EXACT_SCOPE,
    )
    with pytest.raises(ValueError, match="quarantined planning bindings"):
        build_prada_orris_first_claim(
            control_binding=control,
            intervention_binding=formula_binding("intervention", "2" * 64),
            software_binding=software_binding(),
        )


@pytest.mark.parametrize(
    "overrides",
    [
        {"intervention_binding": formula_binding("control", "2" * 64)},
        {"intervention_binding": formula_binding("intervention", "1" * 64)},
        {"software_binding": formula_binding("not-software", "3" * 64)},
    ],
)
def test_first_claim_rejects_ambiguous_or_wrong_kind_bindings(
    overrides: dict[str, VersionBinding],
) -> None:
    arguments = {
        "control_binding": formula_binding("control", "1" * 64),
        "intervention_binding": formula_binding("intervention", "2" * 64),
        "software_binding": software_binding("3" * 64),
    }
    arguments.update(overrides)
    with pytest.raises(ValueError):
        build_prada_orris_first_claim(**arguments)
