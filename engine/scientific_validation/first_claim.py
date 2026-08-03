"""Pure factory for the first Build D confirmatory-claim plan."""

from __future__ import annotations

from decimal import Decimal

from engine.scientific_validation.claim_registry import (
    validate_claim_method_alignment,
)
from engine.scientific_validation.contracts import (
    AssessorType,
    BindingAuthorityState,
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

FIRST_CLAIM_ID = "D0-PRADA-ORRIS-INTERVENTION-001"

REQUIRED_EVIDENCE = (
    EvidenceRequirement(
        "regenerated-formulas",
        "regenerated and revalidated formula artifacts bound to exact hashes",
    ),
    EvidenceRequirement(
        "stock-identity",
        (
            "exact ingredient and stock-lot identity, basis, carrier, density, "
            "and concentration records"
        ),
    ),
    EvidenceRequirement(
        "study-safety",
        "actual-dose safety and regulatory screening appropriate to the study",
    ),
    EvidenceRequirement(
        "sample-conditions",
        (
            "locked common matrix, concentration, substrate, dose, maturation, "
            "storage, and environment"
        ),
    ),
    EvidenceRequirement(
        "panel-authority",
        (
            "consent, ethics, privacy, qualification, and trained-panel "
            "performance receipt"
        ),
    ),
    EvidenceRequirement(
        "separate-pilot",
        "pilot observations kept separate from confirmatory observations",
    ),
    EvidenceRequirement(
        "margin-power-lock",
        "prespecified margin and power rationale ratified before outcome access",
    ),
    EvidenceRequirement(
        "immutable-study-lock",
        (
            "immutable protocol, sample, prediction, randomization, and "
            "analysis locks"
        ),
    ),
    EvidenceRequirement(
        "confirmatory-observations",
        "blinded randomized replicated append-only confirmatory observations",
    ),
    EvidenceRequirement(
        "locked-analysis",
        (
            "locked analysis with effect sizes, intervals, deviations, and "
            "pass/fail/inconclusive output"
        ),
    ),
    EvidenceRequirement(
        "claim-specific-analytical-safety",
        "analytical or safety evidence required by final scoped wording",
    ),
    EvidenceRequirement(
        "human-release-review",
        "authorized human review and scoped release decision",
    ),
)

EXPIRATION_TRIGGERS = (
    (
        "claimant formula, software, model, or canonical serialization hash "
        "changes"
    ),
    (
        "target, comparator, build, ingredient lot, bottle, matrix, substrate, "
        "dose, maturation, storage, or condition changes"
    ),
    (
        "assessor population, screening, training, lexicon, performance "
        "standard, or panel composition changes"
    ),
    (
        "endpoint, attribute, scale, timepoint, margin, decision rule, "
        "sample-size rationale, exclusion rule, or analysis changes"
    ),
    "randomization, blinding, carryover, or data-lock procedure changes",
    "analytical, safety, regulatory, or adverse-event evidence changes",
    "a major or critical protocol deviation occurs",
    "a contradictory study or evidence-expiration event is recorded",
)


def _protected_endpoint(endpoint_id: str, attribute: str) -> EndpointDefinition:
    return EndpointDefinition(
        endpoint_id=endpoint_id,
        claim_family=ClaimFamily.PROTECTED_ATTRIBUTE_PRESERVATION,
        role=EndpointRole.SECONDARY_PROTECTED,
        attribute=attribute,
        method_family=(
            ValidationMethodFamily.TRAINED_QUANTITATIVE_DESCRIPTIVE_PROFILE
        ),
        timepoint="30 minutes post-application",
        scale="locked anchored 0-to-10 intensity scale",
        estimand="model-adjusted paired mean difference Luxury Orris - Control",
        criterion=DecisionCriterion(
            criterion_id=f"{endpoint_id}-equivalence",
            kind=CriterionKind.EQUIVALENCE,
            lower_margin=Decimal("-0.75"),
            upper_margin=Decimal("0.75"),
            unit="scale points",
            margin_authority=MarginAuthority.PROVISIONAL_PREPILOT,
            success_rule=(
                "multiplicity-controlled two-one-sided equivalence interval "
                "lies wholly within [-0.75,+0.75]"
            ),
            failure_rule=(
                "interval lies wholly below -0.75 or wholly above +0.75"
            ),
            inconclusive_rule="all other interval positions are inconclusive",
        ),
    )


def build_prada_orris_first_claim(
    *,
    control_binding: VersionBinding,
    intervention_binding: VersionBinding,
    software_binding: VersionBinding,
) -> ClaimDefinition:
    """Create the immutable, unmeasured D0 planning claim."""

    formula_bindings = (control_binding, intervention_binding)
    if any(binding.kind != "formula" for binding in formula_bindings):
        raise ValueError("first claim requires formula bindings")
    if any(
        binding.authority_state is not BindingAuthorityState.QUARANTINED
        for binding in formula_bindings
    ):
        raise ValueError("first claim requires quarantined planning bindings")
    if control_binding.identifier == intervention_binding.identifier:
        raise ValueError("control and intervention must be distinct")
    if control_binding.sha256 == intervention_binding.sha256:
        raise ValueError("control and intervention hashes must be distinct")
    if software_binding.kind != "software":
        raise ValueError("first claim requires a software binding")

    primary = EndpointDefinition(
        endpoint_id="iris-orris-intensity-30m",
        claim_family=ClaimFamily.INTERVENTION_EFFECTIVENESS,
        role=EndpointRole.PRIMARY,
        attribute="iris/orris intensity",
        method_family=(
            ValidationMethodFamily.TRAINED_QUANTITATIVE_DESCRIPTIVE_PROFILE
        ),
        timepoint="30 minutes post-application",
        scale="locked anchored 0-to-10 intensity scale",
        estimand="model-adjusted paired mean difference Luxury Orris - Control",
        criterion=DecisionCriterion(
            criterion_id="iris-orris-minimum-effect",
            kind=CriterionKind.MINIMUM_EFFECT,
            lower_margin=Decimal("0.50"),
            upper_margin=None,
            unit="scale points",
            margin_authority=MarginAuthority.PROVISIONAL_PREPILOT,
            success_rule="two-sided 95% CI lower bound is at least +0.50",
            failure_rule="two-sided 95% CI upper bound is at most 0.00",
            inconclusive_rule="all other interval positions are inconclusive",
        ),
    )
    claim = ClaimDefinition(
        claim_id=FIRST_CLAIM_ID,
        version=1,
        title="Prada Luxury Orris intervention with protected attributes",
        family=ClaimFamily.INTERVENTION_EFFECTIVENESS,
        claimant_versions=(intervention_binding, software_binding),
        assessor_type=AssessorType.TRAINED_DESCRIPTIVE_PANEL,
        scope=ClaimScope(
            population=ScopeValue.bound(
                "trained quantitative descriptive panel meeting D3 qualification"
            ),
            product=ScopeValue.bound(
                "Prada L'Homme architecture research study"
            ),
            formula=ScopeValue.required_unbound(
                "regenerated exact control and intervention builds must be locked"
            ),
            lot=ScopeValue.required_unbound(
                (
                    "exact control, intervention, ingredient, and stock lots "
                    "do not yet exist"
                )
            ),
            matrix=ScopeValue.required_unbound(
                (
                    "one common final concentration and hydroalcoholic matrix "
                    "must be locked"
                )
            ),
            substrate=ScopeValue.bound("standardized fragrance blotter"),
            condition=ScopeValue.required_unbound(
                (
                    "D1 must lock dose, environment, session, and 30-minute "
                    "presentation condition"
                )
            ),
        ),
        primary_endpoint=primary,
        secondary_endpoints=(
            _protected_endpoint(
                "clean-pressed-shirt-soapy",
                "clean pressed-shirt/soapy character",
            ),
            _protected_endpoint(
                "wood-amber-structure",
                "wood-amber structure",
            ),
            _protected_endpoint("dryness-balance", "dryness/balance"),
        ),
        comparator=ComparatorDefinition(
            comparator_id="prada-architecture-control",
            description="Prada L'Homme Architecture Control planning binding",
            binding=control_binding,
        ),
        required_evidence=REQUIRED_EVIDENCE,
        authority_state=ClaimAuthorityState.PLANNING_ONLY,
        expiration_triggers=EXPIRATION_TRIGGERS,
    )
    validate_claim_method_alignment(claim)
    return claim


__all__ = [
    "EXPIRATION_TRIGGERS",
    "FIRST_CLAIM_ID",
    "REQUIRED_EVIDENCE",
    "build_prada_orris_first_claim",
]
