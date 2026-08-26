"""Canonical Build D claim-family and method-authority registry."""

from __future__ import annotations

from dataclasses import dataclass

from engine.scientific_validation.contracts import (
    ClaimDefinition,
    ClaimFamily,
    ValidationMethodFamily,
)


@dataclass(frozen=True, slots=True)
class ClaimFamilyPolicy:
    family: ClaimFamily
    authoritative_methods: tuple[ValidationMethodFamily, ...]
    insufficient_shortcuts: tuple[str, ...]


CLAIM_FAMILY_POLICIES: tuple[ClaimFamilyPolicy, ...] = (
    ClaimFamilyPolicy(
        ClaimFamily.EXACT_BOTTLE_ARITHMETIC,
        (ValidationMethodFamily.DETERMINISTIC_ARITHMETIC,),
        ("sensory testing cannot revalidate exact arithmetic",),
    ),
    ClaimFamilyPolicy(
        ClaimFamily.EVENT_REPLAY,
        (ValidationMethodFamily.EVENT_STREAM_REPLAY,),
        ("assessor recollection is not event-stream authority",),
    ),
    ClaimFamilyPolicy(
        ClaimFamily.ANALYTICAL_IDENTITY,
        (ValidationMethodFamily.ANALYTICAL_IDENTITY,),
        ("odour description alone does not establish identity",),
    ),
    ClaimFamilyPolicy(
        ClaimFamily.ANALYTICAL_QUANTITY,
        (ValidationMethodFamily.ANALYTICAL_QUANTITATION,),
        ("liking or intensity ratings do not establish quantity",),
    ),
    ClaimFamilyPolicy(
        ClaimFamily.EQUILIBRIUM_HEADSPACE_PREDICTION,
        (
            ValidationMethodFamily.HELD_OUT_HEADSPACE_BENCHMARK,
            ValidationMethodFamily.ANALYTICAL_QUANTITATION,
        ),
        ("in-sample model fit is not held-out prediction authority",),
    ),
    ClaimFamilyPolicy(
        ClaimFamily.PHYSICAL_RELEASE_TRAJECTORY,
        (
            ValidationMethodFamily.HELD_OUT_PHYSICAL_RELEASE_BENCHMARK,
            ValidationMethodFamily.ANALYTICAL_QUANTITATION,
        ),
        ("equilibrium-only output does not establish release trajectory",),
    ),
    ClaimFamilyPolicy(
        ClaimFamily.ABOVE_THRESHOLD_SCREENING,
        (ValidationMethodFamily.CONTEXTUAL_THRESHOLD_SCREENING,),
        ("raw concentration alone is not contextual threshold authority",),
    ),
    ClaimFamilyPolicy(
        ClaimFamily.PERCEPTIBLE_DIFFERENCE,
        (
            ValidationMethodFamily.SENSORY_DISCRIMINATION,
            ValidationMethodFamily.DIRECTIONAL_PAIRED_COMPARISON,
        ),
        ("a model score alone does not establish perceptibility",),
    ),
    ClaimFamilyPolicy(
        ClaimFamily.SENSORY_SIMILARITY_EQUIVALENCE,
        (
            ValidationMethodFamily.TRAINED_QUANTITATIVE_DESCRIPTIVE_PROFILE,
        ),
        ("discrimination non-significance does not establish equivalence",),
    ),
    ClaimFamilyPolicy(
        ClaimFamily.DESCRIPTIVE_PROFILE_ACCURACY,
        (
            ValidationMethodFamily.TRAINED_QUANTITATIVE_DESCRIPTIVE_PROFILE,
        ),
        ("consumer liking is not descriptive-profile authority",),
    ),
    ClaimFamilyPolicy(
        ClaimFamily.TEMPORAL_PROFILE_ACCURACY,
        (ValidationMethodFamily.REPEATED_TEMPORAL_INTENSITY_PROFILE,),
        ("one static endpoint does not establish a temporal profile",),
    ),
    ClaimFamilyPolicy(
        ClaimFamily.RECONSTRUCTION_SIMILARITY,
        (
            ValidationMethodFamily.TRAINED_QUANTITATIVE_DESCRIPTIVE_PROFILE,
            ValidationMethodFamily.SENSOMICS_RECOMBINATION,
        ),
        ("formula arithmetic does not establish sensory reconstruction",),
    ),
    ClaimFamilyPolicy(
        ClaimFamily.INTERVENTION_EFFECTIVENESS,
        (
            ValidationMethodFamily.TRAINED_QUANTITATIVE_DESCRIPTIVE_PROFILE,
        ),
        ("an unblinded anecdote does not establish intervention effect",),
    ),
    ClaimFamilyPolicy(
        ClaimFamily.PROTECTED_ATTRIBUTE_PRESERVATION,
        (
            ValidationMethodFamily.TRAINED_QUANTITATIVE_DESCRIPTIVE_PROFILE,
        ),
        ("no significant difference does not establish equivalence",),
    ),
    ClaimFamilyPolicy(
        ClaimFamily.PREFERENCE_LIKING_PREDICTION,
        (ValidationMethodFamily.CONTROLLED_CONSUMER_HEDONIC,),
        ("analytical quantity or trained-panel intensity cannot prove liking",),
    ),
    ClaimFamilyPolicy(
        ClaimFamily.LONGEVITY_PROJECTION_PROXY,
        (
            ValidationMethodFamily.REPEATED_TEMPORAL_INTENSITY_PROFILE,
            ValidationMethodFamily.HELD_OUT_PHYSICAL_RELEASE_BENCHMARK,
        ),
        ("equilibrium headspace alone is not longevity/projection authority",),
    ),
    ClaimFamilyPolicy(
        ClaimFamily.REGULATORY_SCREENING,
        (ValidationMethodFamily.REGULATORY_EVIDENCE_REVIEW,),
        ("sensory or model prediction is not regulatory authority",),
    ),
)


def get_claim_family_policy(family: ClaimFamily) -> ClaimFamilyPolicy:
    """Return the one registered policy for a claim family."""

    for policy in CLAIM_FAMILY_POLICIES:
        if policy.family is family:
            return policy
    raise ValueError(f"unregistered claim family: {family.value}")


def is_authoritative_method(
    family: ClaimFamily,
    method: ValidationMethodFamily,
) -> bool:
    """Return whether a method can provide primary authority for a family."""

    return method in get_claim_family_policy(family).authoritative_methods


def validate_claim_method_alignment(claim: ClaimDefinition) -> None:
    """Fail closed when any endpoint uses an incompatible authority method."""

    endpoints = (claim.primary_endpoint, *claim.secondary_endpoints)
    for endpoint in endpoints:
        if not is_authoritative_method(endpoint.claim_family, endpoint.method_family):
            raise ValueError(
                f"method {endpoint.method_family.value} cannot authorize "
                f"claim family {endpoint.claim_family.value}"
            )


__all__ = [
    "CLAIM_FAMILY_POLICIES",
    "ClaimFamilyPolicy",
    "get_claim_family_policy",
    "is_authoritative_method",
    "validate_claim_method_alignment",
]
