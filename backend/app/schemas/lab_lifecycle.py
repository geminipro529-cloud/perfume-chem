"""Strict request and response contracts for versioned A2 lifecycle routes."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    StringConstraints,
)

NonBlank = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]
FiniteNonnegative = Annotated[
    float,
    Field(ge=0, allow_inf_nan=False),
]
FinitePositive = Annotated[
    float,
    Field(gt=0, allow_inf_nan=False),
]


class LifecycleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FormulaDesignChatCreate(LifecycleRequest):
    """One stateless turn in the read-only formulation conversation."""

    schema_version: Literal[
        "inventory-grounded-formula-chat-request-v1",
        "inventory-grounded-formula-chat-request-v2",
    ] = "inventory-grounded-formula-chat-request-v2"
    message: NonBlank = Field(max_length=4000)
    formula_name: NonBlank | None = Field(default=None, max_length=255)
    liquid_concentrate_ul_decimal: str = Field(
        default="6000",
        pattern=r"^[0-9]+(?:\.[0-9]+)?$",
        max_length=32,
    )
    max_materials: int = Field(default=60, ge=6, le=60)
    design_mode: Literal["FAST_SKETCH", "DEEP_COMPOSE"] = "FAST_SKETCH"
    variant_count: int | None = Field(default=None, ge=1, le=3)
    must_preserve: tuple[NonBlank, ...] = Field(default=(), max_length=24)
    must_avoid: tuple[NonBlank, ...] = Field(default=(), max_length=24)
    previous_stock_ids: tuple[NonBlank, ...] = Field(default=(), max_length=60)
    conversation_context: tuple[NonBlank, ...] = Field(default=(), max_length=8)
    execution_strategy: Literal["NEW_FORMULA", "EVOLVING_BOTTLE"] | None = None
    appeal_mode: Literal["IDENTITY_FIRST", "GLOBAL_CROWD_PLEASING"] | None = None
    comparison_evidence: Literal[
        "DOCUMENT_ONLY",
        "QUICK_BLIND",
        "CONTROLLED_PERSONAL",
        "TARGET_POPULATION",
    ] = "DOCUMENT_ONLY"
    active_bottle_id: NonBlank | None = Field(default=None, max_length=255)


class InventoryCompletionCreate(LifecycleRequest):
    """User-confirmed stock facts for personal, non-compounding formulation eligibility."""

    schema_version: Literal["personal-inventory-completion-request-v1"] = (
        "personal-inventory-completion-request-v1"
    )
    stock_id: NonBlank = Field(max_length=255)
    expected_effective_inventory_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    idempotency_key: NonBlank = Field(max_length=255)
    fraction_percent_decimal: str | None = Field(
        default=None,
        pattern=r"^[0-9]+(?:\.[0-9]+)?$",
        max_length=32,
    )
    fraction_basis: Literal[
        "neat",
        "mass_fraction",
        "volume_fraction",
        "mass_per_volume",
        "unspecified",
    ] | None = None
    carrier: str | None = Field(default=None, max_length=255)
    physical_form: str | None = Field(default=None, max_length=120)
    possession_confirmed: bool
    homogeneity: Literal[
        "NOT_APPLICABLE",
        "HOMOGENEOUS",
        "FULLY_DISSOLVED",
        "UNKNOWN",
        "NOT_HOMOGENEOUS",
    ]
    final_fraction_known: bool = False
    source_kind: Literal[
        "USER_LABEL_OR_RECIPE",
        "USER_MEASUREMENT",
        "SUPPLIER_LABEL",
        "PERSONAL_CONFIRMATION",
    ]
    user_note: str = Field(default="", max_length=1000)


class StockBasketChoiceCreate(LifecycleRequest):
    """Kenny's basket for one material; null means it sits in no basket."""

    normalized_identity: NonBlank = Field(max_length=255)
    basket: Annotated[StrictInt, Field(ge=1, le=17)] | None


class FormulaTextParseCreate(LifecycleRequest):
    """A pasted formula table, parsed read-only for the bench sheet."""

    text: NonBlank = Field(max_length=200_000)
    name: str | None = Field(default=None, max_length=200)


class PersonalInventoryAdditionCreate(LifecycleRequest):
    """One user-confirmed owned stock missing from the current inventory view."""

    schema_version: Literal["personal-inventory-addition-request-v1"] = (
        "personal-inventory-addition-request-v1"
    )
    expected_design_inventory_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    idempotency_key: NonBlank = Field(max_length=255)
    identity_name: NonBlank = Field(max_length=255)
    category: NonBlank = Field(max_length=255)
    fraction_percent_decimal: str = Field(
        default="100",
        pattern=r"^[0-9]+(?:\.[0-9]+)?$",
        max_length=32,
    )
    fraction_basis: Literal[
        "neat",
        "mass_fraction",
        "volume_fraction",
        "mass_per_volume",
    ] = "neat"
    carrier: str = Field(default="", max_length=255)
    physical_form: NonBlank = Field(default="as_supplied", max_length=120)
    possession_confirmed: bool
    homogeneity: Literal[
        "NOT_APPLICABLE",
        "HOMOGENEOUS",
        "FULLY_DISSOLVED",
        "UNKNOWN",
        "NOT_HOMOGENEOUS",
    ] = "NOT_APPLICABLE"
    source_kind: Literal[
        "USER_LABEL_OR_RECIPE",
        "USER_MEASUREMENT",
        "SUPPLIER_LABEL",
        "PERSONAL_CONFIRMATION",
    ] = "PERSONAL_CONFIRMATION"
    supplier_name: str = Field(default="", max_length=255)
    supplier_sku: str = Field(default="", max_length=120)
    user_note: str = Field(default="", max_length=1000)


class PreparedDilutionCreate(LifecycleRequest):
    """A dilution the user made from an owned bottle (DPG and w/w by default)."""

    schema_version: Literal["prepared-dilution-request-v1"] = (
        "prepared-dilution-request-v1"
    )
    parent_stock_id: NonBlank = Field(max_length=255)
    expected_effective_inventory_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    idempotency_key: NonBlank = Field(max_length=255)
    fraction_percent_decimal: str = Field(
        pattern=r"^[0-9]+(?:\.[0-9]+)?$",
        max_length=32,
    )
    fraction_basis: Literal["mass_fraction", "volume_fraction"] = "mass_fraction"
    carrier: NonBlank = Field(default="DPG", max_length=120)
    amount_made_g: str | None = Field(
        default=None,
        pattern=r"^[0-9]+(?:\.[0-9]+)?$",
        max_length=32,
    )
    prepared_on: date | None = None
    user_note: str = Field(default="", max_length=1000)


class BottleActionProposalCreate(LifecycleRequest):
    schema_version: NonBlank
    reservation_id: NonBlank
    bottle_id: NonBlank
    action_type: Literal["ADD_STOCK"]
    planned_mass_g: FinitePositive
    expected_sequence: int = Field(ge=0)
    idempotency_key: NonBlank
    actor: NonBlank
    rationale: NonBlank


class BottleActionConfirmationCreate(LifecycleRequest):
    decision: Literal["CONFIRMED", "REJECTED"]
    confirmer_pseudonym: NonBlank
    confirmed_at: AwareDatetime
    rationale: NonBlank


class BottleActionMeasurementCreate(LifecycleRequest):
    quantity_kind: Literal["mass"]
    value: FinitePositive
    unit: Literal["g"]
    standard_uncertainty: FiniteNonnegative | None = None
    method: NonBlank
    measured_at: AwareDatetime
    actor: NonBlank


class BottleActionCommitCreate(LifecycleRequest):
    actor: NonBlank
    rationale: NonBlank


class BottleActionEvaluationCreate(LifecycleRequest):
    schema_version: Literal["evolving-bottle-evaluation-v1"] = (
        "evolving-bottle-evaluation-v1"
    )
    bottle_id: NonBlank
    expected_sequence: int = Field(ge=0)
    command_id: NonBlank
    actor: NonBlank
    evaluated_at: AwareDatetime
    waited_seconds: FiniteNonnegative
    reaction: NonBlank
    decision: Literal["CONTINUE", "HOLD", "DILUTE", "STOP", "CANNOT_DETERMINE"]


class QuickBottleEvaluationCreate(LifecycleRequest):
    """Lightweight personal observation linked to exact freeform additions."""

    schema_version: Literal["quick-bottle-evaluation-v1"] = (
        "quick-bottle-evaluation-v1"
    )
    addition_event_ids: tuple[NonBlank, ...] = Field(min_length=1, max_length=24)
    goal_analysis_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    hypothesis_id: NonBlank
    hypothesis_variant: Literal["low_variant", "high_variant"]
    expected_sequence: int = Field(ge=0)
    command_id: NonBlank
    actor: NonBlank
    evaluated_at: AwareDatetime
    waited_seconds: FiniteNonnegative
    reaction: NonBlank
    decision: Literal["CONTINUE", "HOLD", "DILUTE", "STOP", "CANNOT_DETERMINE"]


class AnalyticalResultCreate(LifecycleRequest):
    method_version_id: NonBlank
    run_kind: Literal["GCMS", "HS_SPME_GCMS", "GC_O", "OTHER"]
    status: Literal[
        "ACQUIRED",
        "PROCESSED",
        "QC_ACCEPTED",
        "QC_REJECTED",
    ]
    instrument_identifier: NonBlank
    acquired_at: AwareDatetime
    parameters: dict
    deviations: tuple[NonBlank, ...] = ()
    processing_version: NonBlank
    experiment_id: NonBlank | None = None
    sample_id: NonBlank | None = None
    bottle_id: NonBlank | None = None
    formula_version_id: NonBlank | None = None
    build_plan_version_id: NonBlank | None = None


class SensoryResultCreate(LifecycleRequest):
    application_id: NonBlank
    elapsed_seconds: FiniteNonnegative
    observations: dict


class RegulatoryAssessmentCreate(LifecycleRequest):
    schema_version: NonBlank
    subject_type: Literal["FORMULA_VERSION", "BUILD_PLAN_VERSION", "BOTTLE"]
    subject_id: NonBlank
    standard_identifier: NonBlank
    standard_amendment: NonBlank | None = None
    standard_state: Literal["CURRENT", "SUPERSEDED", "UNKNOWN"]
    source_evidence_record_id: NonBlank | None = None
    jurisdiction: NonBlank
    product_category: NonBlank
    concentration_basis: NonBlank
    finished_product_concentration: FiniteNonnegative | None = None
    effective_date: date | None = None
    evaluated_at: AwareDatetime
    result_state: Literal["PASS", "FAIL", "UNKNOWN", "CONFLICT"]
    assumptions: tuple[NonBlank, ...] = ()
    unresolved: tuple[NonBlank, ...] = ()
    permitted_wording: NonBlank | None = None


class ReleaseReviewEvidenceCreate(LifecycleRequest):
    evidence_record_id: NonBlank
    role: Literal["DIRECT", "SUPPORTING", "CONTRADICTING", "LIMITATION"]


class ReleaseReviewCreate(LifecycleRequest):
    schema_version: NonBlank
    claim_type: NonBlank
    subject_type: Literal[
        "ANALYTICAL_RUN",
        "REGULATORY_ASSESSMENT",
        "FORMULA_VERSION",
        "BUILD_PLAN_VERSION",
        "BOTTLE",
        "EXPERIMENT",
    ]
    subject_id: NonBlank
    policy_version: NonBlank
    decision: Literal[
        "ALLOW_EXACT",
        "ALLOW_SCOPED",
        "ADVISORY_ONLY",
        "WITHHOLD_UNKNOWN",
        "BLOCK",
    ]
    authority: dict
    missing_evidence: tuple[NonBlank, ...] = ()
    conflicts: tuple[NonBlank, ...] = ()
    permitted_wording: NonBlank | None = None
    forbidden_wording: NonBlank | None = None
    human_review_state: Literal[
        "NOT_REQUIRED",
        "PENDING",
        "APPROVED",
        "REJECTED",
    ]
    reviewer_pseudonym: NonBlank | None = None
    reviewed_at: AwareDatetime | None = None
    evidence_links: tuple[ReleaseReviewEvidenceCreate, ...]
    parent_version_id: NonBlank | None = None


class ClaimAuthoritySupportCreate(LifecycleRequest):
    support_kind: Literal[
        "PROPERTY_ASSERTION",
        "OAV_ASSESSMENT",
        "KNOWLEDGE_RULE",
        "ANALYTICAL_ASSESSMENT",
        "COMPOSITION_PROFILE",
        "REGULATORY_SNAPSHOT",
    ]
    record_id: NonBlank
    role: Literal["SUPPORTING", "CONTRADICTING", "LIMITATION"] = (
        "SUPPORTING"
    )


class ClaimAuthorityReviewCreate(LifecycleRequest):
    """Strict B7 request; every authority-bearing field is server-owned."""

    schema_version: Literal["lab-claim-authority-request-v1"]
    legacy_claim_assessment_version_id: NonBlank
    claim_payload: dict
    identity_scope: dict
    condition_scope: dict
    supports: tuple[ClaimAuthoritySupportCreate, ...]
    reviewer_pseudonym: NonBlank
    reviewed_at: AwareDatetime
    parent_version_id: NonBlank | None = None


class LifecycleResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BottleActionProposalResponse(LifecycleResponse):
    id: str
    schema_version: str
    reservation_id: str
    reservation_event_id: str
    bottle_id: str
    action_type: str
    stock_solution_id: str
    planned_mass_g: float
    expected_sequence: int
    idempotency_key: str
    actor: str
    rationale: str
    content_sha256: str
    created_at: datetime


class BottleActionConfirmationResponse(LifecycleResponse):
    id: str
    proposal_id: str
    decision: str
    confirmer_pseudonym: str
    confirmed_at: datetime
    rationale: str
    content_sha256: str
    created_at: datetime


class BottleActionMeasurementResponse(LifecycleResponse):
    id: str
    bottle_event_id: str | None
    proposal_id: str | None
    quantity_kind: str
    value: float
    unit: str
    standard_uncertainty: float | None
    method: str | None
    measured_at: datetime | None
    actor: str | None
    created_at: datetime


class BottleActionCommitResponse(LifecycleResponse):
    id: str
    proposal_id: str
    bottle_event_id: str
    fulfilled_reservation_event_id: str
    actor: str
    rationale: str
    before_state: dict
    after_state: dict
    state_diff: dict
    content_sha256: str
    created_at: datetime


class BottleActionEvaluationResponse(LifecycleResponse):
    id: str
    bottle_id: str
    stream_sequence: int
    event_type: Literal["EVALUATE"]
    proposal_id: str
    action_commit_id: str
    addition_bottle_event_id: str
    evaluated_at: datetime
    waited_seconds: FiniteNonnegative
    reaction: str
    decision: str
    evidence_scope: Literal["SEQUENTIAL_PERSONAL_OBSERVATION"]
    controlled_causal_evidence: Literal[False]
    population_generalization_authorized: Literal[False]
    release_authority: Literal[False]
    safety_authority: Literal[False]
    compounding_authority: Literal[False]
    evidence_admission_authorized: Literal[False]
    created_at: datetime


class QuickBottleEvaluationResponse(LifecycleResponse):
    id: str
    bottle_id: str
    stream_sequence: int
    event_type: Literal["EVALUATE_PERSONAL_DELTA"]
    addition_event_ids: list[str]
    goal_analysis_sha256: str
    hypothesis_id: str
    hypothesis_variant: str
    evaluated_at: datetime
    waited_seconds: FiniteNonnegative
    reaction: str
    decision: str
    evidence_scope: Literal["SEQUENTIAL_PERSONAL_OBSERVATION"]
    controlled_causal_evidence: Literal[False]
    population_generalization_authorized: Literal[False]
    release_authority: Literal[False]
    safety_authority: Literal[False]
    compounding_authority: Literal[False]
    evidence_admission_authorized: Literal[False]
    created_at: datetime


class BottleReplayResponse(LifecycleResponse):
    bottle_id: str
    stream_sequence: int
    total_mass_g: float
    stock_masses_g: dict[str, float]
    solvent_mass_g: float
    tare_mass_g: float | None
    is_closed: bool


class AnalyticalResultResponse(LifecycleResponse):
    id: str
    run_id: str
    method_version_id: str
    run_kind: str
    status: str
    instrument_identifier: str
    acquired_at: datetime
    parameters: dict
    deviations: list[str]
    processing_version: str
    experiment_id: str | None
    sample_id: str | None
    bottle_id: str | None
    formula_version_id: str | None
    build_plan_version_id: str | None
    content_sha256: str
    created_at: datetime


class SensoryResultResponse(LifecycleResponse):
    id: str
    application_id: str
    elapsed_seconds: float
    observations: dict
    created_at: datetime


class RegulatoryAssessmentResponse(LifecycleResponse):
    id: str
    assessment_id: str
    version_number: int
    schema_version: str
    subject_type: str
    subject_id: str
    parent_version_id: str | None
    standard_identifier: str
    standard_amendment: str | None
    standard_state: str
    source_evidence_record_id: str | None
    jurisdiction: str
    product_category: str
    concentration_basis: str
    finished_product_concentration: float | None
    effective_date: date | None
    evaluated_at: datetime
    result_state: str
    assumptions: list[str]
    unresolved: list[str]
    permitted_wording: str | None
    content_sha256: str
    parent_sha256: str | None
    created_at: datetime


class ReleaseReviewResponse(LifecycleResponse):
    id: str
    claim_id: str
    version_number: int
    schema_version: str
    claim_type: str
    subject_type: str
    subject_id: str
    parent_version_id: str | None
    policy_version: str
    decision: str
    authority: dict
    missing_evidence: list[str]
    conflicts: list[str]
    permitted_wording: str | None
    forbidden_wording: str | None
    human_review_state: str
    reviewer_pseudonym: str | None
    reviewed_at: datetime | None
    content_sha256: str
    parent_sha256: str | None
    created_at: datetime


class ClaimAuthorityReviewResponse(LifecycleResponse):
    id: str
    authority_id: str
    version_number: int
    parent_version_id: str | None
    legacy_claim_assessment_version_id: str
    schema_version: str
    policy_version: str
    policy_sha256: str
    policy: dict
    claim_type: str
    subject_type: str
    subject_id: str
    claim_payload: dict
    identity_scope: dict
    identity_scope_sha256: str
    condition_scope: dict
    condition_scope_sha256: str
    claim_scope_sha256: str
    decision: str
    dimension_results: dict
    supporting_observations: list[dict]
    conflicts: list[str]
    missing_requirements: list[str]
    source_references: list[dict]
    uncertainty: dict
    permitted_wording: str
    forbidden_wording: str
    blocker_count: int
    conflict_count: int
    missing_requirement_count: int
    critical_unknown_count: int
    support_count: int
    source_reference_count: int
    upstream_hashes: dict
    reviewer_pseudonym: str
    reviewed_at: datetime
    content_sha256: str
    parent_sha256: str | None
    authority_scope: Literal["SCIENTIFIC_CLAIM_ONLY"]
    release_authority: Literal[False]
    safety_authority: Literal[False]
    compounding_authority: Literal[False]


__all__ = [name for name in globals() if name.endswith(("Create", "Response"))]
