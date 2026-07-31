"""Fail-closed B7 claim-specific scientific authority."""

from __future__ import annotations

import json
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from types import MappingProxyType
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lab_claims import (
    CLAIM_AUTHORITY_DECISIONS,
    CLAIM_AUTHORITY_SUPPORT_KINDS,
    CLAIM_AUTHORITY_SUPPORT_ROLES,
    LabClaimAuthoritySupportLink,
    LabClaimAuthorityVersion,
)

if TYPE_CHECKING:
    from app.repositories.lab import LabRepository


class ClaimAuthorityError(ValueError):
    """Raised when B7 input cannot satisfy the declared contract."""


class ClaimAuthorityConflictError(ClaimAuthorityError):
    """Raised when canonical state cannot support a B7 command."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


def _canonical(value: Any) -> str:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise ClaimAuthorityError(
            "claim authority values must be finite canonical JSON"
        ) from exc


def canonical_json_sha256(value: Any) -> str:
    return sha256(_canonical(value).encode("utf-8")).hexdigest()


def _text(value: str, field: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ClaimAuthorityError(f"{field} must not be empty")
    return normalized


def _choice(
    value: str,
    field: str,
    choices: tuple[str, ...],
) -> str:
    normalized = _text(value, field).upper()
    if normalized not in choices:
        raise ClaimAuthorityError(
            f"{field} must be one of: {', '.join(choices)}"
        )
    return normalized


def _aware(value: datetime, field: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ClaimAuthorityError(f"{field} must be timezone-aware")
    return value


@dataclass(frozen=True, slots=True)
class ClaimAuthoritySupportInput:
    support_kind: str
    record_id: str
    role: str = "SUPPORTING"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "support_kind",
            _choice(
                self.support_kind,
                "support_kind",
                CLAIM_AUTHORITY_SUPPORT_KINDS,
            ),
        )
        object.__setattr__(
            self,
            "record_id",
            _text(self.record_id, "record_id"),
        )
        object.__setattr__(
            self,
            "role",
            _choice(
                self.role,
                "role",
                CLAIM_AUTHORITY_SUPPORT_ROLES,
            ),
        )


@dataclass(frozen=True, slots=True)
class ClaimAuthorityEvaluationInput:
    legacy_claim_assessment_version_id: str
    claim_payload: dict[str, Any]
    identity_scope: dict[str, Any]
    condition_scope: dict[str, Any]
    supports: tuple[ClaimAuthoritySupportInput, ...]
    reviewer_pseudonym: str
    reviewed_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "legacy_claim_assessment_version_id",
            _text(
                self.legacy_claim_assessment_version_id,
                "legacy_claim_assessment_version_id",
            ),
        )
        for field in ("claim_payload", "identity_scope", "condition_scope"):
            value = dict(getattr(self, field))
            _canonical(value)
            object.__setattr__(self, field, value)
        supports = tuple(self.supports)
        keys = {
            (support.support_kind, support.record_id, support.role)
            for support in supports
        }
        if len(keys) != len(supports):
            raise ClaimAuthorityError("supports must not contain duplicates")
        object.__setattr__(self, "supports", supports)
        object.__setattr__(
            self,
            "reviewer_pseudonym",
            _text(self.reviewer_pseudonym, "reviewer_pseudonym"),
        )
        object.__setattr__(
            self,
            "reviewed_at",
            _aware(self.reviewed_at, "reviewed_at"),
        )


@dataclass(frozen=True, slots=True)
class _ResolvedSupport:
    command: ClaimAuthoritySupportInput
    upstream_content_sha256: str
    derived_facts: dict[str, Any]
    source_references: tuple[dict[str, Any], ...]
    foreign_keys: dict[str, str | None]


@dataclass(frozen=True, slots=True)
class ClaimAuthorityPolicy:
    claim_type: str
    required_fields: tuple[str, ...]
    accepted_evidence_classes: tuple[str, ...]
    accepted_support_kinds: tuple[str, ...]
    identity_scope: dict[str, Any]
    condition_match: dict[str, Any]
    minimum_coverage: float
    minimum_independent_sources: int
    contradiction_handling: str
    uncertainty_limit: dict[str, Any]
    method_validation_requirement: str
    model_applicability_requirement: str
    safety_requirement: str
    maximum_decision: str
    permitted_wording: tuple[tuple[str, str], ...]
    forbidden_wording: tuple[str, ...]


_PERMITTED_WORDING = (
    (
        "ALLOW_EXACT",
        "The claim may be stated exactly for the recorded identity and "
        "condition scope only.",
    ),
    (
        "ALLOW_SCOPED",
        "The claim may be stated only with the recorded scope and "
        "qualifications.",
    ),
    (
        "ADVISORY_ONLY",
        "The observation may be described as preliminary advisory evidence.",
    ),
    (
        "WITHHOLD_UNKNOWN",
        "No affirmative scientific claim is permitted while critical "
        "requirements remain unknown.",
    ),
    (
        "BLOCK",
        "No affirmative scientific claim is permitted because a blocking "
        "condition is present.",
    ),
)
_FORBIDDEN_WORDING = (
    "release-grade",
    "certified",
    "universally safe",
    "unscoped equivalence",
)


def _policy(
    claim_type: str,
    *,
    required_fields: tuple[str, ...],
    accepted_evidence_classes: tuple[str, ...],
    accepted_support_kinds: tuple[str, ...],
    identity_scope: dict[str, Any],
    condition_match: dict[str, Any],
    minimum_independent_sources: int,
    uncertainty_limit: dict[str, Any],
    method_validation_requirement: str = "NOT_REQUIRED",
    model_applicability_requirement: str = "NOT_REQUIRED",
    safety_requirement: str = "NOT_REQUIRED",
    maximum_decision: str = "ALLOW_EXACT",
) -> ClaimAuthorityPolicy:
    return ClaimAuthorityPolicy(
        claim_type=claim_type,
        required_fields=required_fields,
        accepted_evidence_classes=accepted_evidence_classes,
        accepted_support_kinds=accepted_support_kinds,
        identity_scope=identity_scope,
        condition_match=condition_match,
        minimum_coverage=1.0,
        minimum_independent_sources=minimum_independent_sources,
        contradiction_handling="BLOCK_ANY_UNRESOLVED",
        uncertainty_limit=uncertainty_limit,
        method_validation_requirement=method_validation_requirement,
        model_applicability_requirement=model_applicability_requirement,
        safety_requirement=safety_requirement,
        maximum_decision=maximum_decision,
        permitted_wording=_PERMITTED_WORDING,
        forbidden_wording=_FORBIDDEN_WORDING,
    )


_POLICIES = {
    "EXACT_CHEMICAL_IDENTITY": _policy(
        "EXACT_CHEMICAL_IDENTITY",
        required_fields=("chemical_name", "identifier"),
        accepted_evidence_classes=("MEASURED", "LITERATURE_DERIVED"),
        accepted_support_kinds=(
            "PROPERTY_ASSERTION",
            "ANALYTICAL_ASSESSMENT",
        ),
        identity_scope={
            "required": True,
            "accepted": (
                "CHEMICAL_ENTITY",
                "STEREOISOMER_OR_ISOMERIC_MIXTURE",
            ),
            "match": "EXACT",
        },
        condition_match={"required": False, "mode": "NOT_APPLICABLE"},
        minimum_independent_sources=2,
        uncertainty_limit={"mode": "NOT_APPLICABLE"},
    ),
    "GRADE_IDENTITY": _policy(
        "GRADE_IDENTITY",
        required_fields=("grade_name", "supplier_or_standard"),
        accepted_evidence_classes=("MEASURED", "SUPPLIER_PROVIDED"),
        accepted_support_kinds=(
            "PROPERTY_ASSERTION",
            "COMPOSITION_PROFILE",
        ),
        identity_scope={
            "required": True,
            "accepted": (
                "TRADE_GRADE",
                "SUPPLIER_PRODUCT",
                "SUPPLIER_LOT",
            ),
            "match": "EXACT",
        },
        condition_match={"required": False, "mode": "NOT_APPLICABLE"},
        minimum_independent_sources=1,
        uncertainty_limit={"mode": "NOT_APPLICABLE"},
    ),
    "PROPERTY_VALUE": _policy(
        "PROPERTY_VALUE",
        required_fields=("property_type", "value", "unit"),
        accepted_evidence_classes=(
            "MEASURED",
            "LITERATURE_DERIVED",
            "SUPPLIER_PROVIDED",
            "EMPIRICALLY_CALIBRATED",
        ),
        accepted_support_kinds=("PROPERTY_ASSERTION",),
        identity_scope={
            "required": True,
            "accepted": "DECLARED_CANONICAL_SCOPE",
            "match": "EXACT",
        },
        condition_match={"required": True, "mode": "EXACT"},
        minimum_independent_sources=1,
        uncertainty_limit={
            "mode": "RELATIVE_STANDARD_UNCERTAINTY",
            "maximum": 0.25,
        },
    ),
    "THRESHOLD": _policy(
        "THRESHOLD",
        required_fields=(
            "threshold_value",
            "unit",
            "endpoint",
            "route",
            "medium",
        ),
        accepted_evidence_classes=("MEASURED", "LITERATURE_DERIVED"),
        accepted_support_kinds=("PROPERTY_ASSERTION",),
        identity_scope={
            "required": True,
            "accepted": "DECLARED_CANONICAL_SCOPE",
            "match": "EXACT",
        },
        condition_match={"required": True, "mode": "EXACT_THRESHOLD_CONTEXT"},
        minimum_independent_sources=1,
        uncertainty_limit={
            "mode": "RELATIVE_STANDARD_UNCERTAINTY",
            "maximum": 0.5,
        },
    ),
    "ABOVE_THRESHOLD_SCREENING": _policy(
        "ABOVE_THRESHOLD_SCREENING",
        required_fields=(
            "concentration",
            "threshold",
            "basis",
            "endpoint",
            "route",
        ),
        accepted_evidence_classes=(
            "MEASURED",
            "EMPIRICALLY_CALIBRATED",
            "LITERATURE_DERIVED",
        ),
        accepted_support_kinds=("OAV_ASSESSMENT",),
        identity_scope={
            "required": True,
            "accepted": "DECLARED_CANONICAL_SCOPE",
            "match": "EXACT",
        },
        condition_match={"required": True, "mode": "EXACT_OAV_CONTEXT"},
        minimum_independent_sources=1,
        uncertainty_limit={"mode": "BOUNDED_PROPAGATED"},
        model_applicability_requirement="REQUIRED",
        maximum_decision="ALLOW_SCOPED",
    ),
    "ANALYTICAL_IDENTIFICATION": _policy(
        "ANALYTICAL_IDENTIFICATION",
        required_fields=("analyte", "identity_label"),
        accepted_evidence_classes=("MEASURED", "EMPIRICALLY_CALIBRATED"),
        accepted_support_kinds=("ANALYTICAL_ASSESSMENT",),
        identity_scope={
            "required": True,
            "accepted": "ANALYTE_AND_SAMPLE_SCOPE",
            "match": "EXACT",
        },
        condition_match={"required": True, "mode": "EXACT_METHOD_SCOPE"},
        minimum_independent_sources=1,
        uncertainty_limit={"mode": "NOT_APPLICABLE"},
        method_validation_requirement="REQUIRED_FOR_SCOPE",
    ),
    "ANALYTICAL_QUANTITATION": _policy(
        "ANALYTICAL_QUANTITATION",
        required_fields=("analyte", "value", "unit"),
        accepted_evidence_classes=("MEASURED", "EMPIRICALLY_CALIBRATED"),
        accepted_support_kinds=("ANALYTICAL_ASSESSMENT",),
        identity_scope={
            "required": True,
            "accepted": "ANALYTE_AND_SAMPLE_SCOPE",
            "match": "EXACT",
        },
        condition_match={"required": True, "mode": "EXACT_METHOD_SCOPE"},
        minimum_independent_sources=1,
        uncertainty_limit={
            "mode": "RELATIVE_STANDARD_UNCERTAINTY",
            "maximum": 0.2,
        },
        method_validation_requirement="REQUIRED_FOR_SCOPE",
    ),
    "NATURAL_CONSTITUENT_PROFILE": _policy(
        "NATURAL_CONSTITUENT_PROFILE",
        required_fields=("stock_solution_id", "composition_basis"),
        accepted_evidence_classes=("MEASURED", "SUPPLIER_PROVIDED"),
        accepted_support_kinds=("COMPOSITION_PROFILE",),
        identity_scope={
            "required": True,
            "accepted": ("SUPPLIER_LOT", "STOCK_SOLUTION"),
            "match": "EXACT",
        },
        condition_match={"required": True, "mode": "EXACT_LOT_SCOPE"},
        minimum_independent_sources=1,
        uncertainty_limit={
            "mode": "RELATIVE_STANDARD_UNCERTAINTY",
            "maximum": 0.25,
        },
    ),
    "KNOWLEDGE_RULE_RECOMMENDATION": _policy(
        "KNOWLEDGE_RULE_RECOMMENDATION",
        required_fields=("rule_key", "recommendation"),
        accepted_evidence_classes=(
            "MEASURED",
            "LITERATURE_DERIVED",
            "EMPIRICALLY_CALIBRATED",
        ),
        accepted_support_kinds=("KNOWLEDGE_RULE",),
        identity_scope={
            "required": True,
            "accepted": "RULE_SUBJECT_AND_OBJECT_SCOPE",
            "match": "EXACT",
        },
        condition_match={"required": True, "mode": "EXACT_RULE_DOMAIN"},
        minimum_independent_sources=1,
        uncertainty_limit={"mode": "DECLARED"},
        model_applicability_requirement="REQUIRED_IF_MODEL",
        maximum_decision="ALLOW_SCOPED",
    ),
    "REGULATORY_SCREENING": _policy(
        "REGULATORY_SCREENING",
        required_fields=("jurisdiction", "product_category", "effective_on"),
        accepted_evidence_classes=(
            "LITERATURE_DERIVED",
            "SUPPLIER_PROVIDED",
        ),
        accepted_support_kinds=("REGULATORY_SNAPSHOT",),
        identity_scope={
            "required": True,
            "accepted": "EXACT_REGULATORY_SUBJECT",
            "match": "EXACT",
        },
        condition_match={"required": True, "mode": "EXACT_REGULATORY_SCOPE"},
        minimum_independent_sources=1,
        uncertainty_limit={"mode": "NOT_APPLICABLE"},
        safety_requirement="PASS_FOR_DECLARED_SCOPE",
        maximum_decision="ALLOW_SCOPED",
    ),
    "FORMULA_OR_MODEL_COMPARISON": _policy(
        "FORMULA_OR_MODEL_COMPARISON",
        required_fields=(
            "left_subject",
            "right_subject",
            "comparison_metric",
        ),
        accepted_evidence_classes=(
            "MEASURED",
            "EMPIRICALLY_CALIBRATED",
            "MODEL_ESTIMATED",
        ),
        accepted_support_kinds=(
            "PROPERTY_ASSERTION",
            "OAV_ASSESSMENT",
            "KNOWLEDGE_RULE",
            "ANALYTICAL_ASSESSMENT",
        ),
        identity_scope={
            "required": True,
            "accepted": "EXACT_COMPARISON_SUBJECTS",
            "match": "EXACT",
        },
        condition_match={"required": True, "mode": "EXACT_COMPARISON_DOMAIN"},
        minimum_independent_sources=2,
        uncertainty_limit={
            "mode": "RELATIVE_STANDARD_UNCERTAINTY",
            "maximum": 0.25,
        },
        method_validation_requirement="REQUIRED_IF_MEASURED",
        model_applicability_requirement="REQUIRED_IF_MODEL",
        maximum_decision="ALLOW_SCOPED",
    ),
}

CLAIM_AUTHORITY_POLICIES = MappingProxyType(_POLICIES)

_CLAIM_TYPE_ALIASES = {
    "IDENTITY": "EXACT_CHEMICAL_IDENTITY",
    "ANALYTICAL_IDENTITY": "ANALYTICAL_IDENTIFICATION",
    "ANALYTICAL_QUANTITY": "ANALYTICAL_QUANTITATION",
    "ABOVE_THRESHOLD_LIKELIHOOD": "ABOVE_THRESHOLD_SCREENING",
    "REGULATORY_SCREEN": "REGULATORY_SCREENING",
    "TARGET_SIMILARITY": "FORMULA_OR_MODEL_COMPARISON",
    "FAMILY_PRESERVATION": "FORMULA_OR_MODEL_COMPARISON",
}


def policy_snapshot(policy: ClaimAuthorityPolicy) -> dict[str, Any]:
    return {
        "claim_type": policy.claim_type,
        "required_fields": list(policy.required_fields),
        "accepted_evidence_classes": list(
            policy.accepted_evidence_classes
        ),
        "accepted_support_kinds": list(policy.accepted_support_kinds),
        "identity_scope": json.loads(_canonical(policy.identity_scope)),
        "condition_match": json.loads(_canonical(policy.condition_match)),
        "minimum_coverage": policy.minimum_coverage,
        "minimum_independent_sources": policy.minimum_independent_sources,
        "contradiction_handling": policy.contradiction_handling,
        "uncertainty_limit": json.loads(_canonical(policy.uncertainty_limit)),
        "method_validation_requirement": (
            policy.method_validation_requirement
        ),
        "model_applicability_requirement": (
            policy.model_applicability_requirement
        ),
        "safety_requirement": policy.safety_requirement,
        "maximum_decision": policy.maximum_decision,
        "permitted_wording": dict(policy.permitted_wording),
        "forbidden_wording": list(policy.forbidden_wording),
    }


def claim_policy_hash(policy: ClaimAuthorityPolicy) -> str:
    return canonical_json_sha256(policy_snapshot(policy))


def normalize_claim_authority_type(value: str) -> str:
    normalized = str(value or "").strip().upper()
    normalized = _CLAIM_TYPE_ALIASES.get(normalized, normalized)
    if normalized not in CLAIM_AUTHORITY_POLICIES:
        raise ClaimAuthorityConflictError(
            "CLAIM_AUTHORITY_TYPE_UNKNOWN",
            f"Unsupported B7 claim type: {value!r}.",
        )
    return normalized


def wording_for_decision(
    policy: ClaimAuthorityPolicy,
    decision: str,
) -> tuple[str, str]:
    normalized = str(decision or "").strip().upper()
    if normalized not in CLAIM_AUTHORITY_DECISIONS:
        raise ClaimAuthorityError(
            "decision must be one of: "
            + ", ".join(CLAIM_AUTHORITY_DECISIONS)
        )
    permitted = dict(policy.permitted_wording)[normalized]
    forbidden = "; ".join(policy.forbidden_wording)
    return permitted, forbidden


def _relative_uncertainty(
    value: float | None,
    uncertainty: float | None,
) -> float | None:
    if value is None or uncertainty is None:
        return None
    numeric_value = abs(float(value))
    numeric_uncertainty = float(uncertainty)
    if numeric_uncertainty < 0:
        return None
    if numeric_value == 0:
        return 0.0 if numeric_uncertainty == 0 else None
    return numeric_uncertainty / numeric_value


def _float_from_mapping(
    mapping: dict[str, Any],
    keys: tuple[str, ...],
) -> float | None:
    for key in keys:
        value = mapping.get(key)
        if value is None:
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        if numeric >= 0:
            return numeric
    return None


def _support_foreign_keys(
    support_kind: str,
    record_id: str,
) -> dict[str, str | None]:
    fields: dict[str, str | None] = {
        "property_assertion_id": None,
        "oav_assessment_id": None,
        "knowledge_rule_id": None,
        "analytical_assessment_id": None,
        "composition_profile_id": None,
        "regulatory_snapshot_version_id": None,
    }
    target = {
        "PROPERTY_ASSERTION": "property_assertion_id",
        "OAV_ASSESSMENT": "oav_assessment_id",
        "KNOWLEDGE_RULE": "knowledge_rule_id",
        "ANALYTICAL_ASSESSMENT": "analytical_assessment_id",
        "COMPOSITION_PROFILE": "composition_profile_id",
        "REGULATORY_SNAPSHOT": "regulatory_snapshot_version_id",
    }[support_kind]
    fields[target] = record_id
    return fields


def _claim_values_equal(left: Any, right: Any) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return left is right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return abs(float(left) - float(right)) <= 1e-12
    if isinstance(left, str) and isinstance(right, str):
        return left.strip().casefold() == right.strip().casefold()
    return _canonical(left) == _canonical(right)


class LabClaimAuthorityServiceMixin:
    """B7 authority commands using the canonical transaction owner."""

    if TYPE_CHECKING:
        repository: LabRepository
        session: AsyncSession

        def _transaction(self) -> AbstractAsyncContextManager[None]: ...

    async def _claim_authority_subject_exists(
        self,
        subject_type: str,
        subject_id: str,
    ) -> bool:
        getters = {
            "ANALYTICAL_RUN": self.repository.get_analytical_run,
            "REGULATORY_ASSESSMENT": (
                self.repository.get_regulatory_assessment_version
            ),
            "FORMULA_VERSION": self.repository.get_formula_version,
            "BUILD_PLAN_VERSION": self.repository.get_build_plan_version,
            "BOTTLE": self.repository.get_bottle,
            "EXPERIMENT": self.repository.get_experiment,
        }
        getter = getters.get(subject_type)
        return getter is not None and await getter(subject_id) is not None

    async def _claim_source_reference(
        self,
        source_version_id: str,
        locator: dict[str, Any],
    ) -> dict[str, Any]:
        source = await self.repository.get_source_document_version(
            source_version_id
        )
        if source is None:
            raise ClaimAuthorityConflictError(
                "CLAIM_SOURCE_NOT_FOUND",
                f"Canonical source version not found: {source_version_id}.",
            )
        return {
            "source_version_id": source.id,
            "source_type": source.source_type,
            "source_record_sha256": source.record_sha256,
            "artifact_sha256": source.artifact_sha256,
            "independence_group": source.independence_group,
            "review_state": source.review_state,
            "locator": dict(locator),
        }

    async def _property_observation_reference(
        self,
        observation,
    ) -> dict[str, Any]:
        return await self._claim_source_reference(
            observation.source_version_id,
            dict(observation.source_locator_json),
        )

    async def _resolve_property_support(
        self,
        command: ClaimAuthoritySupportInput,
        claim_type: str,
    ) -> _ResolvedSupport:
        assertion = await self.repository.get_selected_assertion(
            command.record_id
        )
        if assertion is None:
            raise ClaimAuthorityConflictError(
                "CLAIM_SUPPORT_NOT_FOUND",
                f"B2 selected assertion not found: {command.record_id}.",
            )
        observation = None
        source_references: list[dict[str, Any]] = []
        evidence_classes: list[str] = []
        relative_uncertainty = _float_from_mapping(
            dict(assertion.propagated_uncertainty_json),
            (
                "relative_standard_uncertainty",
                "relative_uncertainty",
            ),
        )
        blockers: list[str] = []
        missing: list[str] = []
        condition_scope = dict(assertion.requested_conditions_json)
        observation_review_state = None
        selected_value: Any = None
        selected_unit: str | None = None
        threshold_context = None

        if assertion.selection_kind == "OBSERVATION":
            observation = await self.repository.get_property_observation(
                str(assertion.selected_observation_id)
            )
            if observation is None:
                raise ClaimAuthorityConflictError(
                    "CLAIM_PROPERTY_OBSERVATION_NOT_FOUND",
                    "The selected B2 observation does not exist.",
                )
            evidence_classes.append(observation.evidence_class)
            observation_review_state = observation.review_state
            if observation.value_kind == "NUMERIC":
                selected_value = observation.numeric_value
            elif observation.value_kind == "CATEGORICAL":
                selected_value = observation.categorical_value
            elif observation.value_kind == "INTERVAL":
                selected_value = {
                    "lower": observation.interval_lower,
                    "upper": observation.interval_upper,
                }
            elif observation.value_kind == "DISTRIBUTION":
                selected_value = observation.distribution_json
            else:
                selected_value = {
                    "qualifier": observation.censoring_qualifier,
                    "limit": observation.censoring_limit,
                }
            selected_unit = observation.canonical_unit
            source_references.append(
                await self._property_observation_reference(observation)
            )
            if relative_uncertainty is None:
                relative_uncertainty = _relative_uncertainty(
                    observation.numeric_value,
                    observation.standard_uncertainty,
                )
            if claim_type == "THRESHOLD":
                threshold_context = (
                    await self.repository.threshold_context_for_observation(
                        observation.id
                    )
                )
                if threshold_context is None:
                    missing.append("THRESHOLD_CONTEXT_MISSING")
                else:
                    condition_scope = {
                        "endpoint": threshold_context.endpoint,
                        "route": threshold_context.route,
                        "medium": threshold_context.medium,
                        "matrix_specification_state": (
                            threshold_context.matrix_specification_state
                        ),
                        "matrix_composition": dict(
                            threshold_context.matrix_composition_json
                        ),
                        "concentration_basis": (
                            threshold_context.concentration_basis
                        ),
                        "temperature_k": observation.temperature_k,
                        "pressure_pa": observation.pressure_pa,
                        "relative_humidity_percent": (
                            observation.relative_humidity_percent
                        ),
                    }
        elif assertion.selection_kind == "MODEL":
            evidence_classes.append("MODEL_ESTIMATED")
            missing.append("MODEL_SOURCE_REFERENCES_NOT_CANONICAL")
        else:
            evidence_classes.append("UNKNOWN")
            missing.append("SELECTED_ASSERTION_WITHHELD")

        if assertion.conflict_set_id is not None:
            conflict = await self.repository.get_property_conflict_set(
                assertion.conflict_set_id
            )
            if (
                conflict is not None
                and conflict.state == "UNRESOLVED"
                and conflict.materiality == "BLOCKING"
            ):
                blockers.append("UNRESOLVED_PROPERTY_CONFLICT")

        authoritative = (
            assertion.authority_state == "AUTHORIZED_FOR_SCOPED_PROPERTY"
            and assertion.selection_kind in {"OBSERVATION", "MODEL"}
            and not blockers
            and (
                observation is None
                or observation_review_state
                in {"REVIEWED", "ACCEPTED_FOR_SCOPED_USE"}
            )
        )
        exact_capable = (
            authoritative
            and assertion.selection_kind == "OBSERVATION"
            and assertion.interpolation_state in {"EXACT", "NOT_APPLICABLE"}
        )
        identity = dict(assertion.requested_identity_json)
        claim_values = {
            "property_type": assertion.requested_property_type,
            "value": selected_value,
            "unit": selected_unit,
            "chemical_name": (
                identity.get("chemical_name")
                or identity.get("canonical_name")
                or identity.get("material_key")
            ),
            "identifier": (
                identity.get("identifier")
                or identity.get("cas_number")
                or identity.get("inchi_key")
            ),
            "grade_name": (
                identity.get("grade_name") or identity.get("grade")
            ),
            "supplier_or_standard": (
                identity.get("supplier_or_standard")
                or identity.get("supplier")
                or identity.get("standard")
            ),
        }
        if threshold_context is not None:
            claim_values.update(
                {
                    "threshold_value": selected_value,
                    "endpoint": threshold_context.endpoint,
                    "route": threshold_context.route,
                    "medium": threshold_context.medium,
                }
            )
        facts = {
            "record_type": "PROPERTY_ASSERTION",
            "record_id": assertion.id,
            "property_type": assertion.requested_property_type,
            "claim_values": claim_values,
            "identity_scope": identity,
            "condition_scope": condition_scope,
            "evidence_classes": sorted(set(evidence_classes)),
            "identity_scope_sha256": assertion.requested_identity_sha256,
            "condition_scope_sha256": canonical_json_sha256(condition_scope),
            "source_independence_groups": sorted(
                {
                    reference["independence_group"]
                    for reference in source_references
                }
            ),
            "authority_state": assertion.authority_state,
            "authoritative": authoritative,
            "exact_capable": exact_capable,
            "uncertainty_state": (
                "BOUNDED"
                if relative_uncertainty is not None
                else "UNKNOWN"
            ),
            "relative_standard_uncertainty": relative_uncertainty,
            "method_validated": None,
            "model_based": assertion.selection_kind == "MODEL",
            "model_applicable": (
                bool(assertion.applicability_json.get("applicable"))
                if assertion.selection_kind == "MODEL"
                else None
            ),
            "safety_state": None,
            "blockers": blockers,
            "missing_reasons": missing,
        }
        return _ResolvedSupport(
            command=command,
            upstream_content_sha256=assertion.content_sha256,
            derived_facts=facts,
            source_references=tuple(source_references),
            foreign_keys=_support_foreign_keys(
                command.support_kind,
                assertion.id,
            ),
        )

    async def _resolve_oav_support(
        self,
        command: ClaimAuthoritySupportInput,
    ) -> _ResolvedSupport:
        assessment = await self.repository.get_oav_assessment(
            command.record_id
        )
        if assessment is None:
            raise ClaimAuthorityConflictError(
                "CLAIM_SUPPORT_NOT_FOUND",
                f"B3 OAV assessment not found: {command.record_id}.",
            )
        concentration = await self.repository.get_property_observation(
            assessment.concentration_observation_id
        )
        if concentration is None:
            raise ClaimAuthorityConflictError(
                "CLAIM_OAV_CONCENTRATION_NOT_FOUND",
                "The B3 OAV concentration observation does not exist.",
            )
        source_references = [
            await self._property_observation_reference(concentration)
        ]
        evidence_classes = [concentration.evidence_class]
        relative_values = [
            _relative_uncertainty(
                concentration.numeric_value,
                concentration.standard_uncertainty,
            )
        ]
        threshold_identity_sha256 = concentration.subject_identity_sha256
        threshold = None
        if assessment.threshold_assertion_id is not None:
            assertion = await self.repository.get_selected_assertion(
                assessment.threshold_assertion_id
            )
            if assertion is not None and assertion.selected_observation_id:
                threshold = await self.repository.get_property_observation(
                    assertion.selected_observation_id
                )
                if threshold is not None:
                    threshold_identity_sha256 = (
                        threshold.subject_identity_sha256
                    )
                    evidence_classes.append(threshold.evidence_class)
                    source_references.append(
                        await self._property_observation_reference(threshold)
                    )
                    relative_values.append(
                        _relative_uncertainty(
                            threshold.numeric_value,
                            threshold.standard_uncertainty,
                        )
                    )
        condition_scope = dict(
            assessment.input_snapshot_json.get("condition_scope")
            or {
                "endpoint": assessment.requested_endpoint,
                "route": assessment.requested_route,
                "concentration_context": dict(
                    concentration.applicability_domain_json
                ),
                "threshold_assertion_id": (
                    assessment.threshold_assertion_id
                ),
            }
        )
        bounded_values = [
            value for value in relative_values if value is not None
        ]
        authoritative = (
            assessment.strict_science_mode
            and assessment.status == "COMPUTED"
            and assessment.mismatch_count == 0
            and threshold_identity_sha256
            == concentration.subject_identity_sha256
        )
        input_snapshot = dict(assessment.input_snapshot_json)
        claim_values = {
            "concentration": input_snapshot.get(
                "concentration",
                concentration.numeric_value,
            ),
            "threshold": input_snapshot.get(
                "threshold",
                threshold.numeric_value if threshold is not None else None,
            ),
            "basis": input_snapshot.get(
                "basis",
                concentration.applicability_domain_json.get(
                    "concentration_basis"
                ),
            ),
            "endpoint": assessment.requested_endpoint,
            "route": assessment.requested_route,
        }
        missing = (
            list(assessment.mismatch_codes_json)
            if not authoritative
            else []
        )
        facts = {
            "record_type": "OAV_ASSESSMENT",
            "record_id": assessment.id,
            "claim_values": claim_values,
            "identity_scope": dict(concentration.subject_identity_json),
            "condition_scope": condition_scope,
            "evidence_classes": sorted(set(evidence_classes)),
            "identity_scope_sha256": (
                concentration.subject_identity_sha256
            ),
            "condition_scope_sha256": canonical_json_sha256(condition_scope),
            "source_independence_groups": sorted(
                {
                    reference["independence_group"]
                    for reference in source_references
                }
            ),
            "authority_state": assessment.status,
            "authoritative": authoritative,
            "exact_capable": False,
            "uncertainty_state": (
                "BOUNDED"
                if len(bounded_values) == len(relative_values)
                else "UNKNOWN"
            ),
            "relative_standard_uncertainty": (
                max(bounded_values) if bounded_values else None
            ),
            "method_validated": None,
            "model_based": True,
            "model_applicable": authoritative,
            "safety_state": None,
            "blockers": [],
            "missing_reasons": missing,
        }
        return _ResolvedSupport(
            command=command,
            upstream_content_sha256=assessment.content_sha256,
            derived_facts=facts,
            source_references=tuple(source_references),
            foreign_keys=_support_foreign_keys(
                command.support_kind,
                assessment.id,
            ),
        )

    async def _resolve_rule_support(
        self,
        command: ClaimAuthoritySupportInput,
    ) -> _ResolvedSupport:
        rule = await self.repository.get_knowledge_rule(command.record_id)
        if rule is None:
            raise ClaimAuthorityConflictError(
                "CLAIM_SUPPORT_NOT_FOUND",
                f"B4 knowledge rule not found: {command.record_id}.",
            )
        source_references: list[dict[str, Any]] = []
        if rule.source_document_version_id is not None:
            source_references.append(
                await self._claim_source_reference(
                    rule.source_document_version_id,
                    {"source_locator": rule.source_locator},
                )
            )
        identity_scope = {
            "subject_identity_scope_sha256": (
                rule.subject_identity_scope_sha256
            ),
            "object_identity_scope_sha256": (
                rule.object_identity_scope_sha256
            ),
        }
        condition_scope = {
            "matrix_context": dict(rule.matrix_context_json),
            "dose_domain": dict(rule.dose_domain_json),
            "temporal_domain": dict(rule.temporal_domain_json),
        }
        contradictions = await self.repository.contradictions_for_rule(rule.id)
        blockers = sorted(
            {
                f"RULE_CONTRADICTION:{item.reason_code}"
                for item in contradictions
                if item.blocking
            }
        )
        model_based = rule.numerical_model_ref is not None
        uncertainty = dict(rule.uncertainty_json)
        authoritative = (
            rule.status in {"AUTHORITATIVE", "SUPPORTED"}
            and rule.review_state == "APPROVED"
            and not blockers
        )
        facts = {
            "record_type": "KNOWLEDGE_RULE",
            "record_id": rule.id,
            "claim_values": {
                "rule_key": rule.rule_key,
                "recommendation": rule.relation,
                "left_subject": rule.subject_identity_scope_sha256,
                "right_subject": rule.object_identity_scope_sha256,
                "comparison_metric": rule.attribute,
            },
            "identity_scope": identity_scope,
            "condition_scope": condition_scope,
            "evidence_classes": [rule.evidence_class],
            "identity_scope_sha256": canonical_json_sha256(identity_scope),
            "condition_scope_sha256": canonical_json_sha256(condition_scope),
            "source_independence_groups": sorted(
                {
                    reference["independence_group"]
                    for reference in source_references
                }
            ),
            "authority_state": rule.status,
            "authoritative": authoritative,
            "exact_capable": False,
            "uncertainty_state": (
                "DECLARED" if uncertainty else "UNKNOWN"
            ),
            "relative_standard_uncertainty": _float_from_mapping(
                uncertainty,
                (
                    "relative_standard_uncertainty",
                    "relative_uncertainty",
                ),
            ),
            "method_validated": None,
            "model_based": model_based,
            "model_applicable": (
                bool(uncertainty.get("applicable"))
                if model_based
                else None
            ),
            "safety_state": None,
            "blockers": blockers,
            "missing_reasons": (
                [] if authoritative else ["KNOWLEDGE_RULE_NOT_AUTHORITATIVE"]
            ),
        }
        return _ResolvedSupport(
            command=command,
            upstream_content_sha256=rule.content_sha256,
            derived_facts=facts,
            source_references=tuple(source_references),
            foreign_keys=_support_foreign_keys(
                command.support_kind,
                rule.id,
            ),
        )

    async def _resolve_analytical_support(
        self,
        command: ClaimAuthoritySupportInput,
        claim_type: str,
    ) -> _ResolvedSupport:
        assessment = await self.repository.get_analytical_claim_assessment(
            command.record_id
        )
        if assessment is None:
            raise ClaimAuthorityConflictError(
                "CLAIM_SUPPORT_NOT_FOUND",
                f"B5 analytical assessment not found: {command.record_id}.",
            )
        run_authority = await self.repository.get_analytical_run_authority(
            assessment.run_authority_id
        )
        peak_authority = await self.repository.get_analytical_peak_authority(
            assessment.peak_authority_id
        )
        method_authority = None
        validations = []
        source_references: list[dict[str, Any]] = []
        if run_authority is not None:
            method_authority = (
                await self.repository.get_analytical_method_authority(
                    run_authority.method_authority_id
                )
            )
        if method_authority is not None:
            source_references.append(
                await self._claim_source_reference(
                    method_authority.source_document_version_id,
                    dict(method_authority.source_locator_json),
                )
            )
            validations = await self.repository.method_validation_records(
                method_authority.id
            )
            for validation in validations:
                source_references.append(
                    await self._claim_source_reference(
                        validation.source_document_version_id,
                        dict(validation.source_locator_json),
                    )
                )
        passing_validation = any(
            validation.result == "PASS" for validation in validations
        )
        failed_validation = any(
            validation.result == "FAIL" for validation in validations
        )
        scope = dict(assessment.scope_json)
        identity_scope = dict(
            scope.get("identity_scope")
            or {
                "analytical_run_id": assessment.analytical_run_id,
                "identity_label": (
                    peak_authority.identity_label
                    if peak_authority is not None
                    else None
                ),
            }
        )
        condition_scope = dict(
            scope.get("condition_scope")
            or scope.get("matrix_scope")
            or {}
        )
        expected_claim = {
            "ANALYTICAL_IDENTIFICATION": "IDENTITY",
            "ANALYTICAL_QUANTITATION": "QUANTITY",
        }.get(claim_type)
        claim_matches = (
            expected_claim is None
            or assessment.claim_type == expected_claim
        )
        run_accepted = (
            run_authority is not None
            and run_authority.disposition == "ACCEPTED"
        )
        authoritative = (
            assessment.decision == "SUPPORTED_FOR_SCOPE"
            and claim_matches
            and run_accepted
            and peak_authority is not None
        )
        exact_capable = False
        if authoritative and peak_authority is not None:
            if assessment.claim_type == "IDENTITY":
                exact_capable = (
                    peak_authority.identity_state
                    == "CONFIRMED_AUTHENTIC_STANDARD"
                    and passing_validation
                )
            elif assessment.claim_type == "QUANTITY":
                exact_capable = (
                    peak_authority.quantitation_state
                    == "CALIBRATED_CONCENTRATION"
                    and passing_validation
                )
        details = dict(assessment.details_json)
        relative_uncertainty = _float_from_mapping(
            details,
            (
                "relative_standard_uncertainty",
                "relative_uncertainty",
            ),
        )
        if relative_uncertainty is None:
            for validation in validations:
                measurement_uncertainty = dict(
                    validation.measurement_uncertainty_json
                )
                relative_uncertainty = _float_from_mapping(
                    measurement_uncertainty,
                    (
                        "relative_standard_uncertainty",
                        "relative_uncertainty",
                    ),
                )
                if relative_uncertainty is None:
                    expanded = _float_from_mapping(
                        measurement_uncertainty,
                        ("expanded_uncertainty",),
                    )
                    coverage_factor = _float_from_mapping(
                        measurement_uncertainty,
                        ("coverage_factor",),
                    )
                    if (
                        expanded is not None
                        and coverage_factor is not None
                        and coverage_factor > 0
                        and str(
                            measurement_uncertainty.get("unit", "")
                        ).casefold()
                        == "relative"
                    ):
                        relative_uncertainty = expanded / coverage_factor
                if relative_uncertainty is not None:
                    break
        blockers = []
        if failed_validation:
            blockers.append("METHOD_VALIDATION_FAILED")
        if (
            run_authority is not None
            and run_authority.disposition == "REJECTED"
        ):
            blockers.append("ANALYTICAL_RUN_REJECTED")
        missing = list(assessment.missing_requirements_json)
        if not authoritative:
            missing.append("ANALYTICAL_ASSESSMENT_NOT_SUPPORTED")
        result = dict(assessment.result_json or {})
        quantitation = (
            dict(peak_authority.quantitation_json)
            if peak_authority is not None
            else {}
        )
        identity_label = (
            peak_authority.identity_label
            if peak_authority is not None
            else None
        )
        facts = {
            "record_type": "ANALYTICAL_ASSESSMENT",
            "record_id": assessment.id,
            "claim_values": {
                "analyte": (
                    result.get("analyte")
                    or result.get("identity_label")
                    or identity_label
                ),
                "identity_label": (
                    result.get("identity_label") or identity_label
                ),
                "value": (
                    result.get("quantity")
                    if "quantity" in result
                    else quantitation.get("quantity")
                ),
                "unit": (
                    result.get("quantity_unit")
                    or quantitation.get("quantity_unit")
                ),
            },
            "identity_scope": identity_scope,
            "condition_scope": condition_scope,
            "subject_type": "ANALYTICAL_RUN",
            "subject_id": assessment.analytical_run_id,
            "evidence_classes": ["MEASURED"],
            "identity_scope_sha256": canonical_json_sha256(identity_scope),
            "condition_scope_sha256": canonical_json_sha256(condition_scope),
            "source_independence_groups": sorted(
                {
                    reference["independence_group"]
                    for reference in source_references
                }
            ),
            "authority_state": assessment.decision,
            "authoritative": authoritative,
            "exact_capable": exact_capable,
            "uncertainty_state": (
                "BOUNDED"
                if relative_uncertainty is not None
                else "UNKNOWN"
            ),
            "relative_standard_uncertainty": relative_uncertainty,
            "method_validated": passing_validation,
            "model_based": False,
            "model_applicable": None,
            "safety_state": None,
            "blockers": blockers,
            "missing_reasons": sorted(set(missing)),
        }
        return _ResolvedSupport(
            command=command,
            upstream_content_sha256=assessment.content_sha256,
            derived_facts=facts,
            source_references=tuple(source_references),
            foreign_keys=_support_foreign_keys(
                command.support_kind,
                assessment.id,
            ),
        )

    async def _resolve_composition_support(
        self,
        command: ClaimAuthoritySupportInput,
    ) -> _ResolvedSupport:
        profile = await self.repository.get_regulatory_composition_profile(
            command.record_id
        )
        if profile is None:
            raise ClaimAuthorityConflictError(
                "CLAIM_SUPPORT_NOT_FOUND",
                f"B6 composition profile not found: {command.record_id}.",
            )
        binding = None
        source_references: list[dict[str, Any]] = []
        if profile.supplier_document_binding_id is not None:
            binding = await self.repository.get_supplier_document_binding(
                profile.supplier_document_binding_id
            )
            if binding is not None:
                source_references.append(
                    await self._claim_source_reference(
                        binding.source_document_version_id,
                        dict(binding.source_locator_json),
                    )
                )
        entries = await self.repository.regulatory_composition_entries(
            profile.id
        )
        identity_scope = {
            "stock_solution_id": profile.stock_solution_id,
            "supplier_identity_sha256": (
                binding.supplier_identity_sha256
                if binding is not None
                else None
            ),
        }
        condition_scope = {
            "stock_solution_id": profile.stock_solution_id,
            "scope": binding.scope if binding is not None else None,
            "lot_number": (
                binding.lot_number if binding is not None else None
            ),
        }
        relative_values = [
            _relative_uncertainty(entry.fraction, entry.standard_uncertainty)
            for entry in entries
        ]
        bounded_values = [
            value for value in relative_values if value is not None
        ]
        known = (
            profile.composition_basis != "UNKNOWN"
            and profile.completeness == "COMPLETE"
            and binding is not None
            and bool(entries)
        )
        exact_capable = (
            known
            and profile.composition_basis == "LOT_SPECIFIC"
            and profile.completeness == "COMPLETE"
            and binding is not None
            and binding.scope == "SUPPLIER_LOT"
        )
        missing = []
        if profile.composition_basis == "UNKNOWN":
            missing.append("NATURAL_COMPOSITION_UNKNOWN")
        if profile.completeness != "COMPLETE":
            missing.append("COMPOSITION_INCOMPLETE")
        if binding is None:
            missing.append("SUPPLIER_BINDING_MISSING")
        facts = {
            "record_type": "COMPOSITION_PROFILE",
            "record_id": profile.id,
            "claim_values": {
                "stock_solution_id": profile.stock_solution_id,
                "composition_basis": profile.composition_basis,
            },
            "identity_scope": identity_scope,
            "condition_scope": condition_scope,
            "evidence_classes": ["SUPPLIER_PROVIDED"],
            "identity_scope_sha256": canonical_json_sha256(identity_scope),
            "condition_scope_sha256": canonical_json_sha256(condition_scope),
            "source_independence_groups": sorted(
                {
                    reference["independence_group"]
                    for reference in source_references
                }
            ),
            "authority_state": profile.completeness,
            "authoritative": known,
            "exact_capable": exact_capable,
            "uncertainty_state": (
                "BOUNDED"
                if relative_values
                and len(bounded_values) == len(relative_values)
                else "UNKNOWN"
            ),
            "relative_standard_uncertainty": (
                max(bounded_values) if bounded_values else None
            ),
            "method_validated": None,
            "model_based": False,
            "model_applicable": None,
            "safety_state": None,
            "blockers": [],
            "missing_reasons": missing,
        }
        return _ResolvedSupport(
            command=command,
            upstream_content_sha256=profile.content_sha256,
            derived_facts=facts,
            source_references=tuple(source_references),
            foreign_keys=_support_foreign_keys(
                command.support_kind,
                profile.id,
            ),
        )

    async def _resolve_regulatory_support(
        self,
        command: ClaimAuthoritySupportInput,
    ) -> _ResolvedSupport:
        snapshot = await self.repository.get_regulatory_snapshot_version(
            command.record_id
        )
        if snapshot is None:
            raise ClaimAuthorityConflictError(
                "CLAIM_SUPPORT_NOT_FOUND",
                f"B6 regulatory snapshot not found: {command.record_id}.",
            )
        source_ids = tuple(
            sorted(
                set(snapshot.current_state_source_ids_json)
                | {snapshot.primary_source_version_id}
            )
        )
        source_references = []
        for source_id in source_ids:
            source = await self.repository.get_regulatory_source_version(
                source_id
            )
            if source is None:
                raise ClaimAuthorityConflictError(
                    "CLAIM_REGULATORY_SOURCE_NOT_FOUND",
                    f"B6 regulatory source not found: {source_id}.",
                )
            source_references.append(
                await self._claim_source_reference(
                    source.official_source_document_version_id,
                    dict(source.source_locator_json),
                )
            )
        identity_scope = {
            "subject_type": snapshot.subject_type,
            "subject_id": snapshot.subject_id,
        }
        condition_scope = {
            "jurisdiction": snapshot.jurisdiction,
            "product_category": snapshot.product_category,
            "use_classification": snapshot.use_classification,
            "finished_product_concentration": (
                snapshot.finished_product_concentration
            ),
            "effective_on": snapshot.effective_on.isoformat(),
        }
        blockers = (
            ["REGULATORY_SCREEN_FAILED"]
            if snapshot.result_state == "FAIL"
            else []
        )
        missing = list(snapshot.unresolved_items_json)
        if snapshot.result_state in {"UNKNOWN", "NOT_EVALUATED"}:
            missing.append("REGULATORY_STATE_UNKNOWN")
        facts = {
            "record_type": "REGULATORY_SNAPSHOT",
            "record_id": snapshot.id,
            "claim_values": {
                "jurisdiction": snapshot.jurisdiction,
                "product_category": snapshot.product_category,
                "effective_on": snapshot.effective_on.isoformat(),
            },
            "identity_scope": identity_scope,
            "condition_scope": condition_scope,
            "subject_type": snapshot.subject_type,
            "subject_id": snapshot.subject_id,
            "evidence_classes": ["LITERATURE_DERIVED"],
            "identity_scope_sha256": canonical_json_sha256(identity_scope),
            "condition_scope_sha256": canonical_json_sha256(condition_scope),
            "source_independence_groups": sorted(
                {
                    reference["independence_group"]
                    for reference in source_references
                }
            ),
            "authority_state": snapshot.result_state,
            "authoritative": (
                snapshot.result_state == "PASS_FOR_DECLARED_SCOPE"
            ),
            "exact_capable": False,
            "uncertainty_state": "NOT_APPLICABLE",
            "relative_standard_uncertainty": None,
            "method_validated": None,
            "model_based": False,
            "model_applicable": None,
            "safety_state": snapshot.result_state,
            "blockers": blockers,
            "missing_reasons": sorted(set(missing)),
        }
        return _ResolvedSupport(
            command=command,
            upstream_content_sha256=snapshot.content_sha256,
            derived_facts=facts,
            source_references=tuple(source_references),
            foreign_keys=_support_foreign_keys(
                command.support_kind,
                snapshot.id,
            ),
        )

    async def _resolve_claim_support(
        self,
        command: ClaimAuthoritySupportInput,
        claim_type: str,
    ) -> _ResolvedSupport:
        if command.support_kind == "PROPERTY_ASSERTION":
            return await self._resolve_property_support(command, claim_type)
        if command.support_kind == "OAV_ASSESSMENT":
            return await self._resolve_oav_support(command)
        if command.support_kind == "KNOWLEDGE_RULE":
            return await self._resolve_rule_support(command)
        if command.support_kind == "ANALYTICAL_ASSESSMENT":
            return await self._resolve_analytical_support(
                command,
                claim_type,
            )
        if command.support_kind == "COMPOSITION_PROFILE":
            return await self._resolve_composition_support(command)
        return await self._resolve_regulatory_support(command)

    @staticmethod
    def _deduplicate_source_references(
        supports: tuple[_ResolvedSupport, ...],
    ) -> list[dict[str, Any]]:
        references: dict[str, dict[str, Any]] = {}
        for support in supports:
            for reference in support.source_references:
                key = canonical_json_sha256(reference)
                references[key] = reference
        return [references[key] for key in sorted(references)]

    @staticmethod
    def _evaluate_claim_dimensions(
        policy: ClaimAuthorityPolicy,
        command: ClaimAuthorityEvaluationInput,
        supports: tuple[_ResolvedSupport, ...],
        subject_type: str,
        subject_id: str,
    ) -> tuple[
        str,
        dict[str, str],
        list[str],
        list[str],
        list[str],
    ]:
        missing: set[str] = set()
        critical: set[str] = set()
        blockers: set[str] = set()
        conflicts: set[str] = set()
        dimensions: dict[str, str] = {}

        missing_fields = [
            field
            for field in policy.required_fields
            if field not in command.claim_payload
            or command.claim_payload[field] is None
            or command.claim_payload[field] == ""
        ]
        if missing_fields:
            for field in missing_fields:
                missing.add(f"REQUIRED_FIELD_MISSING:{field}")
            critical.add("REQUIRED_FIELDS_INCOMPLETE")
            dimensions["required_fields"] = "UNKNOWN"
        else:
            dimensions["required_fields"] = "PASS"

        for support in supports:
            for reason in support.derived_facts.get("blockers", []):
                blockers.add(str(reason))
                conflicts.add(str(reason))
            if support.command.role == "CONTRADICTING":
                blockers.add("CONTRADICTING_SUPPORT")
                conflicts.add("CONTRADICTING_SUPPORT")
            elif support.command.role == "LIMITATION":
                missing.add("LIMITATION_SUPPORT")
                critical.add("LIMITATION_SUPPORT")

        promoting = tuple(
            support
            for support in supports
            if support.command.role == "SUPPORTING"
        )
        if not promoting:
            missing.add("SUPPORTING_OBSERVATION_MISSING")
            critical.add("SUPPORTING_OBSERVATION_MISSING")

        subject_bound_supports = [
            support
            for support in promoting
            if support.derived_facts.get("subject_type") is not None
        ]
        subject_scope_ok = all(
            support.derived_facts.get("subject_type") == subject_type
            and support.derived_facts.get("subject_id") == subject_id
            for support in subject_bound_supports
        )
        dimensions["subject_scope"] = (
            "PASS" if subject_bound_supports and subject_scope_ok else (
                "NOT_APPLICABLE"
                if not subject_bound_supports
                else "FAIL"
            )
        )
        if not subject_scope_ok:
            missing.add("SUBJECT_SCOPE_MISMATCH")
            critical.add("SUBJECT_SCOPE_MISMATCH")

        payload_mismatches = []
        if not missing_fields:
            for field in policy.required_fields:
                canonical_values = [
                    support.derived_facts.get("claim_values", {}).get(field)
                    for support in promoting
                    if field
                    in support.derived_facts.get("claim_values", {})
                    and support.derived_facts.get("claim_values", {}).get(
                        field
                    )
                    is not None
                ]
                if not canonical_values or any(
                    not _claim_values_equal(
                        command.claim_payload[field],
                        canonical_value,
                    )
                    for canonical_value in canonical_values
                ):
                    payload_mismatches.append(field)
        if payload_mismatches:
            for field in payload_mismatches:
                missing.add(f"CLAIM_PAYLOAD_MISMATCH:{field}")
            critical.add("CLAIM_PAYLOAD_MISMATCH")
            dimensions["claim_payload"] = "FAIL"
        elif missing_fields:
            dimensions["claim_payload"] = "UNKNOWN"
        else:
            dimensions["claim_payload"] = "PASS"

        kind_ok = bool(promoting) and all(
            support.command.support_kind in policy.accepted_support_kinds
            for support in promoting
        )
        if not kind_ok:
            missing.add("SUPPORT_KIND_NOT_ACCEPTED")
            critical.add("SUPPORT_KIND_NOT_ACCEPTED")

        accepted_classes = set(policy.accepted_evidence_classes)
        evidence_ok = bool(promoting) and all(
            bool(
                accepted_classes
                & set(support.derived_facts.get("evidence_classes", []))
            )
            for support in promoting
        )
        dimensions["evidence_class"] = "PASS" if evidence_ok else "FAIL"
        if not evidence_ok:
            missing.add("EVIDENCE_CLASS_NOT_PROMOTING")

        expected_identity = canonical_json_sha256(command.identity_scope)
        identity_required = bool(policy.identity_scope.get("required"))
        identity_ok = (
            not identity_required
            or (
                bool(promoting)
                and all(
                    support.derived_facts.get("identity_scope_sha256")
                    == expected_identity
                    for support in promoting
                )
            )
        )
        dimensions["identity_scope"] = (
            "PASS"
            if identity_ok
            else ("NOT_APPLICABLE" if not identity_required else "FAIL")
        )
        if not identity_ok:
            missing.add("IDENTITY_SCOPE_MISMATCH")
            critical.add("IDENTITY_SCOPE_MISMATCH")

        condition_required = bool(policy.condition_match.get("required"))
        expected_condition = canonical_json_sha256(command.condition_scope)
        condition_ok = (
            not condition_required
            or (
                bool(promoting)
                and all(
                    support.derived_facts.get("condition_scope_sha256")
                    == expected_condition
                    for support in promoting
                )
            )
        )
        dimensions["condition_match"] = (
            "PASS"
            if condition_ok
            else ("NOT_APPLICABLE" if not condition_required else "FAIL")
        )
        if not condition_ok:
            missing.add("CONDITION_SCOPE_MISMATCH")
            critical.add("CONDITION_SCOPE_MISMATCH")

        authoritative_ok = bool(promoting) and all(
            support.derived_facts.get("authoritative") is True
            for support in promoting
        )
        if not authoritative_ok:
            missing.add("UPSTREAM_AUTHORITY_NOT_PROMOTING")
            for support in promoting:
                missing.update(
                    str(reason)
                    for reason in support.derived_facts.get(
                        "missing_reasons",
                        [],
                    )
                )

        denominator = max(len(promoting), 1)
        covered = sum(
            1
            for support in promoting
            if (
                support.command.support_kind
                in policy.accepted_support_kinds
                and bool(
                    accepted_classes
                    & set(
                        support.derived_facts.get("evidence_classes", [])
                    )
                )
                and support.derived_facts.get("authoritative") is True
                and (
                    not identity_required
                    or support.derived_facts.get("identity_scope_sha256")
                    == expected_identity
                )
                and (
                    not condition_required
                    or support.derived_facts.get("condition_scope_sha256")
                    == expected_condition
                )
            )
        )
        coverage = covered / denominator
        coverage_ok = (
            bool(promoting) and coverage >= policy.minimum_coverage
        )
        dimensions["coverage"] = "PASS" if coverage_ok else "UNKNOWN"
        if not coverage_ok:
            missing.add("MINIMUM_COVERAGE_NOT_MET")
            if evidence_ok:
                critical.add("MINIMUM_COVERAGE_NOT_MET")

        independence_groups = {
            group
            for support in promoting
            for group in support.derived_facts.get(
                "source_independence_groups",
                [],
            )
        }
        independence_ok = (
            len(independence_groups)
            >= policy.minimum_independent_sources
        )
        dimensions["source_independence"] = (
            "PASS" if independence_ok else "UNKNOWN"
        )
        if not independence_ok:
            missing.add("SOURCE_INDEPENDENCE_NOT_MET")
            critical.add("SOURCE_INDEPENDENCE_NOT_MET")

        dimensions["contradiction"] = (
            "FAIL" if blockers else "PASS"
        )

        uncertainty_mode = str(policy.uncertainty_limit.get("mode"))
        if uncertainty_mode == "NOT_APPLICABLE":
            uncertainty_ok = True
            dimensions["uncertainty"] = "NOT_APPLICABLE"
        elif uncertainty_mode == "DECLARED":
            uncertainty_ok = bool(promoting) and all(
                support.derived_facts.get("uncertainty_state")
                in {"DECLARED", "BOUNDED"}
                for support in promoting
            )
            dimensions["uncertainty"] = (
                "PASS" if uncertainty_ok else "UNKNOWN"
            )
        elif uncertainty_mode == "BOUNDED_PROPAGATED":
            uncertainty_ok = bool(promoting) and all(
                support.derived_facts.get("uncertainty_state") == "BOUNDED"
                for support in promoting
            )
            dimensions["uncertainty"] = (
                "PASS" if uncertainty_ok else "UNKNOWN"
            )
        else:
            maximum = float(policy.uncertainty_limit["maximum"])
            values = [
                support.derived_facts.get(
                    "relative_standard_uncertainty"
                )
                for support in promoting
            ]
            uncertainty_ok = bool(values) and all(
                value is not None and float(value) <= maximum
                for value in values
            )
            dimensions["uncertainty"] = (
                "PASS" if uncertainty_ok else "UNKNOWN"
            )
        if not uncertainty_ok:
            missing.add("UNCERTAINTY_LIMIT_NOT_MET")
            critical.add("UNCERTAINTY_LIMIT_NOT_MET")

        method_requirement = policy.method_validation_requirement
        measured = any(
            "MEASURED"
            in support.derived_facts.get("evidence_classes", [])
            for support in promoting
        )
        method_required = method_requirement == "REQUIRED_FOR_SCOPE" or (
            method_requirement == "REQUIRED_IF_MEASURED" and measured
        )
        if not method_required:
            method_ok = True
            dimensions["method_validation"] = "NOT_APPLICABLE"
        else:
            relevant = [
                support.derived_facts.get("method_validated")
                for support in promoting
                if support.command.support_kind
                == "ANALYTICAL_ASSESSMENT"
            ]
            method_ok = bool(relevant) and all(
                value is True for value in relevant
            )
            dimensions["method_validation"] = (
                "PASS" if method_ok else "UNKNOWN"
            )
        if not method_ok:
            missing.add("METHOD_VALIDATION_REQUIRED")
            critical.add("METHOD_VALIDATION_REQUIRED")

        model_requirement = policy.model_applicability_requirement
        model_supports = [
            support
            for support in promoting
            if support.derived_facts.get("model_based") is True
        ]
        model_required = model_requirement == "REQUIRED" or (
            model_requirement == "REQUIRED_IF_MODEL"
            and bool(model_supports)
        )
        if not model_required:
            model_ok = True
            dimensions["model_applicability"] = "NOT_APPLICABLE"
        else:
            relevant_models = model_supports or list(promoting)
            model_ok = bool(relevant_models) and all(
                support.derived_facts.get("model_applicable") is True
                for support in relevant_models
            )
            dimensions["model_applicability"] = (
                "PASS" if model_ok else "UNKNOWN"
            )
        if not model_ok:
            missing.add("MODEL_APPLICABILITY_REQUIRED")
            critical.add("MODEL_APPLICABILITY_REQUIRED")

        if policy.safety_requirement == "NOT_REQUIRED":
            safety_ok = True
            dimensions["safety"] = "NOT_APPLICABLE"
        else:
            safety_states = [
                support.derived_facts.get("safety_state")
                for support in promoting
            ]
            safety_ok = bool(safety_states) and all(
                state == policy.safety_requirement
                for state in safety_states
            )
            dimensions["safety"] = "PASS" if safety_ok else "UNKNOWN"
            if "FAIL" in safety_states:
                blockers.add("SAFETY_REQUIREMENT_FAILED")
                conflicts.add("SAFETY_REQUIREMENT_FAILED")
        if not safety_ok and not blockers:
            missing.add("SAFETY_REQUIREMENT_UNKNOWN")
            critical.add("SAFETY_REQUIREMENT_UNKNOWN")

        if blockers:
            decision = "BLOCK"
        elif critical:
            advisory_reasons = {
                "EVIDENCE_CLASS_NOT_PROMOTING",
                "UPSTREAM_AUTHORITY_NOT_PROMOTING",
                "MINIMUM_COVERAGE_NOT_MET",
            }
            if (
                promoting
                and not missing_fields
                and identity_ok
                and condition_ok
                and set(missing) <= advisory_reasons
            ):
                decision = "ADVISORY_ONLY"
                critical.clear()
            else:
                decision = "WITHHOLD_UNKNOWN"
        elif missing:
            decision = "ADVISORY_ONLY"
        elif policy.maximum_decision == "ALLOW_EXACT" and all(
            support.derived_facts.get("exact_capable") is True
            for support in promoting
        ):
            decision = "ALLOW_EXACT"
        else:
            decision = "ALLOW_SCOPED"

        return (
            decision,
            dimensions,
            sorted(missing),
            sorted(conflicts),
            sorted(critical),
        )

    async def create_claim_authority_version(
        self,
        command: ClaimAuthorityEvaluationInput,
        *,
        parent_version_id: str | None = None,
    ) -> LabClaimAuthorityVersion:
        async with self._transaction():
            legacy = await self.repository.get_claim_assessment_version(
                command.legacy_claim_assessment_version_id
            )
            if legacy is None:
                raise ClaimAuthorityConflictError(
                    "CLAIM_LEGACY_ASSESSMENT_NOT_FOUND",
                    "The referenced A2 claim assessment does not exist.",
                )
            latest_legacy = (
                await self.repository.latest_claim_assessment_version(
                    legacy.claim_id
                )
            )
            if latest_legacy is None or latest_legacy.id != legacy.id:
                raise ClaimAuthorityConflictError(
                    "CLAIM_AUTHORITY_A2_VERSION_NOT_LATEST",
                    "B7 authority must use the latest A2 claim version.",
                )
            if not await self._claim_authority_subject_exists(
                legacy.subject_type,
                legacy.subject_id,
            ):
                raise ClaimAuthorityConflictError(
                    "CLAIM_AUTHORITY_SUBJECT_NOT_FOUND",
                    "The A2 claim subject no longer exists.",
                )
            claim_type = normalize_claim_authority_type(legacy.claim_type)
            policy = CLAIM_AUTHORITY_POLICIES[claim_type]
            resolved = tuple(
                [
                    await self._resolve_claim_support(support, claim_type)
                    for support in command.supports
                ]
            )
            (
                decision,
                dimensions,
                missing_requirements,
                conflicts,
                critical_unknowns,
            ) = self._evaluate_claim_dimensions(
                policy,
                command,
                resolved,
                legacy.subject_type,
                legacy.subject_id,
            )
            blockers = sorted(
                {
                    str(reason)
                    for support in resolved
                    for reason in support.derived_facts.get("blockers", [])
                }
                | (
                    {"CONTRADICTING_SUPPORT"}
                    if any(
                        support.command.role == "CONTRADICTING"
                        for support in resolved
                    )
                    else set()
                )
                | (
                    {"SAFETY_REQUIREMENT_FAILED"}
                    if "SAFETY_REQUIREMENT_FAILED" in conflicts
                    else set()
                )
            )
            source_references = self._deduplicate_source_references(resolved)
            policy_json = policy_snapshot(policy)
            policy_sha256 = claim_policy_hash(policy)
            identity_sha256 = canonical_json_sha256(command.identity_scope)
            condition_sha256 = canonical_json_sha256(
                command.condition_scope
            )
            claim_scope = {
                "claim_type": claim_type,
                "subject_type": legacy.subject_type,
                "subject_id": legacy.subject_id,
                "claim_payload": command.claim_payload,
                "identity_scope": command.identity_scope,
                "condition_scope": command.condition_scope,
            }
            claim_scope_sha256 = canonical_json_sha256(claim_scope)

            parent = None
            if parent_version_id is None:
                authority_id = str(uuid4())
                version_number = 1
            else:
                parent = await self.repository.get_claim_authority_version(
                    parent_version_id
                )
                if parent is None:
                    raise ClaimAuthorityConflictError(
                        "CLAIM_AUTHORITY_PARENT_NOT_FOUND",
                        "The B7 parent authority version does not exist.",
                    )
                latest = (
                    await self.repository.latest_claim_authority_version(
                        parent.authority_id
                    )
                )
                if latest is None or latest.id != parent.id:
                    raise ClaimAuthorityConflictError(
                        "CLAIM_AUTHORITY_PARENT_NOT_LATEST",
                        "A B7 revision must use the latest parent.",
                    )
                parent_legacy = (
                    await self.repository.get_claim_assessment_version(
                        parent.legacy_claim_assessment_version_id
                    )
                )
                if (
                    parent_legacy is None
                    or parent_legacy.claim_id != legacy.claim_id
                ):
                    raise ClaimAuthorityConflictError(
                        "CLAIM_AUTHORITY_A2_CHAIN_CHANGED",
                        "A B7 revision must remain in the same A2 claim chain.",
                    )
                if (
                    parent.claim_type != claim_type
                    or parent.subject_type != legacy.subject_type
                    or parent.subject_id != legacy.subject_id
                    or parent.claim_scope_sha256 != claim_scope_sha256
                    or parent.identity_scope_sha256 != identity_sha256
                    or parent.condition_scope_sha256 != condition_sha256
                ):
                    raise ClaimAuthorityConflictError(
                        "CLAIM_AUTHORITY_SCOPE_CHANGED",
                        "A B7 revision cannot change its scoped claim.",
                    )
                authority_id = parent.authority_id
                version_number = parent.version_number + 1

            permitted_wording, forbidden_wording = wording_for_decision(
                policy,
                decision,
            )
            observations = [
                {
                    "support_kind": support.command.support_kind,
                    "record_id": support.command.record_id,
                    "role": support.command.role,
                    "upstream_content_sha256": (
                        support.upstream_content_sha256
                    ),
                }
                for support in resolved
            ]
            upstream_hashes = {
                f"{support.command.support_kind}:{support.command.record_id}": (
                    support.upstream_content_sha256
                )
                for support in resolved
            }
            uncertainty = {
                f"{support.command.support_kind}:{support.command.record_id}": {
                    "state": support.derived_facts.get("uncertainty_state"),
                    "relative_standard_uncertainty": (
                        support.derived_facts.get(
                            "relative_standard_uncertainty"
                        )
                    ),
                }
                for support in resolved
            }
            payload = {
                "schema": "lab-claim-authority-v1",
                "authority_id": authority_id,
                "version_number": version_number,
                "legacy_claim_assessment_version_id": legacy.id,
                "policy_version": "b7-policy-v1",
                "policy_sha256": policy_sha256,
                "policy": policy_json,
                "claim_type": claim_type,
                "subject_type": legacy.subject_type,
                "subject_id": legacy.subject_id,
                "claim_payload": command.claim_payload,
                "identity_scope": command.identity_scope,
                "identity_scope_sha256": identity_sha256,
                "condition_scope": command.condition_scope,
                "condition_scope_sha256": condition_sha256,
                "claim_scope_sha256": claim_scope_sha256,
                "decision": decision,
                "dimension_results": dimensions,
                "supporting_observations": observations,
                "conflicts": conflicts,
                "missing_requirements": missing_requirements,
                "source_references": source_references,
                "uncertainty": uncertainty,
                "permitted_wording": permitted_wording,
                "forbidden_wording": forbidden_wording,
                "blocker_count": len(blockers),
                "conflict_count": len(conflicts),
                "missing_requirement_count": len(missing_requirements),
                "critical_unknown_count": len(critical_unknowns),
                "support_count": len(resolved),
                "source_reference_count": len(source_references),
                "release_authority": False,
                "upstream_hashes": upstream_hashes,
                "reviewer_pseudonym": command.reviewer_pseudonym,
                "reviewed_at": command.reviewed_at.isoformat(),
                "parent_sha256": parent.content_sha256 if parent else None,
            }
            content_sha256 = canonical_json_sha256(payload)
            if (
                await self.repository.claim_authority_by_hash(content_sha256)
                is not None
            ):
                raise ClaimAuthorityConflictError(
                    "CLAIM_AUTHORITY_ALREADY_EXISTS",
                    "An identical B7 authority version already exists.",
                )
            authority = await self.repository.add(
                LabClaimAuthorityVersion(
                    authority_id=authority_id,
                    version_number=version_number,
                    parent_version_id=parent.id if parent else None,
                    legacy_claim_assessment_version_id=legacy.id,
                    schema_version="lab-claim-authority-v1",
                    policy_version="b7-policy-v1",
                    policy_sha256=policy_sha256,
                    policy_json=policy_json,
                    claim_type=claim_type,
                    subject_type=legacy.subject_type,
                    subject_id=legacy.subject_id,
                    claim_payload_json=dict(command.claim_payload),
                    identity_scope_json=dict(command.identity_scope),
                    identity_scope_sha256=identity_sha256,
                    condition_scope_json=dict(command.condition_scope),
                    condition_scope_sha256=condition_sha256,
                    claim_scope_sha256=claim_scope_sha256,
                    decision=decision,
                    dimension_results_json=dimensions,
                    supporting_observations_json=observations,
                    conflicts_json=conflicts,
                    missing_requirements_json=missing_requirements,
                    source_references_json=source_references,
                    uncertainty_json=uncertainty,
                    permitted_wording=permitted_wording,
                    forbidden_wording=forbidden_wording,
                    blocker_count=len(blockers),
                    conflict_count=len(conflicts),
                    missing_requirement_count=len(missing_requirements),
                    critical_unknown_count=len(critical_unknowns),
                    support_count=len(resolved),
                    source_reference_count=len(source_references),
                    release_authority=False,
                    upstream_hashes_json=upstream_hashes,
                    reviewer_pseudonym=command.reviewer_pseudonym,
                    reviewed_at=command.reviewed_at,
                    content_sha256=content_sha256,
                    parent_sha256=(
                        parent.content_sha256 if parent else None
                    ),
                )
            )
            for support in resolved:
                link_payload = {
                    "schema": "lab-claim-authority-support-v1",
                    "claim_authority_version_id": authority.id,
                    "support_kind": support.command.support_kind,
                    "record_id": support.command.record_id,
                    "role": support.command.role,
                    "upstream_content_sha256": (
                        support.upstream_content_sha256
                    ),
                    "derived_facts": support.derived_facts,
                    "source_references": support.source_references,
                }
                await self.repository.add(
                    LabClaimAuthoritySupportLink(
                        claim_authority_version_id=authority.id,
                        support_kind=support.command.support_kind,
                        role=support.command.role,
                        upstream_content_sha256=(
                            support.upstream_content_sha256
                        ),
                        derived_facts_json=support.derived_facts,
                        source_references_json=list(
                            support.source_references
                        ),
                        content_sha256=canonical_json_sha256(link_payload),
                        **support.foreign_keys,
                    )
                )
            return authority

    async def _current_claim_support_hash(
        self,
        link: LabClaimAuthoritySupportLink,
    ) -> tuple[str, str]:
        record: Any
        if link.support_kind == "PROPERTY_ASSERTION":
            record_id = str(link.property_assertion_id)
            record = await self.repository.get_selected_assertion(record_id)
        elif link.support_kind == "OAV_ASSESSMENT":
            record_id = str(link.oav_assessment_id)
            record = await self.repository.get_oav_assessment(record_id)
        elif link.support_kind == "KNOWLEDGE_RULE":
            record_id = str(link.knowledge_rule_id)
            record = await self.repository.get_knowledge_rule(record_id)
        elif link.support_kind == "ANALYTICAL_ASSESSMENT":
            record_id = str(link.analytical_assessment_id)
            record = (
                await self.repository.get_analytical_claim_assessment(
                    record_id
                )
            )
        elif link.support_kind == "COMPOSITION_PROFILE":
            record_id = str(link.composition_profile_id)
            record = (
                await self.repository.get_regulatory_composition_profile(
                    record_id
                )
            )
        else:
            record_id = str(link.regulatory_snapshot_version_id)
            record = await self.repository.get_regulatory_snapshot_version(
                record_id
            )
        if record is None:
            raise ClaimAuthorityConflictError(
                "CLAIM_SUPPORT_NOT_FOUND",
                "A persisted B7 support record no longer resolves.",
            )
        return record_id, str(record.content_sha256)

    async def reconstruct_claim_authority(
        self,
        version_id: str,
    ) -> dict[str, Any]:
        authority = await self.repository.get_claim_authority_version(
            _text(version_id, "version_id")
        )
        if authority is None:
            raise ClaimAuthorityConflictError(
                "CLAIM_AUTHORITY_NOT_FOUND",
                f"B7 authority version not found: {version_id}.",
            )
        if canonical_json_sha256(authority.policy_json) != (
            authority.policy_sha256
        ):
            raise ClaimAuthorityConflictError(
                "CLAIM_AUTHORITY_POLICY_HASH_MISMATCH",
                "The persisted B7 policy snapshot does not match its hash.",
            )
        current_policy = CLAIM_AUTHORITY_POLICIES.get(authority.claim_type)
        if (
            authority.policy_version == "b7-policy-v1"
            and (
                current_policy is None
                or claim_policy_hash(current_policy)
                != authority.policy_sha256
            )
        ):
            raise ClaimAuthorityConflictError(
                "CLAIM_AUTHORITY_POLICY_DRIFT",
                "The persisted B7 policy differs from the code-owned version.",
            )
        links = await self.repository.claim_authority_support_links(
            authority.id
        )
        reconstructed_links = []
        for link in links:
            record_id, current_hash = await self._current_claim_support_hash(
                link
            )
            if current_hash != link.upstream_content_sha256:
                raise ClaimAuthorityConflictError(
                    "CLAIM_AUTHORITY_UPSTREAM_HASH_MISMATCH",
                    "A B7 support hash no longer matches its canonical row.",
                )
            link_payload = {
                "schema": "lab-claim-authority-support-v1",
                "claim_authority_version_id": authority.id,
                "support_kind": link.support_kind,
                "record_id": record_id,
                "role": link.role,
                "upstream_content_sha256": link.upstream_content_sha256,
                "derived_facts": link.derived_facts_json,
                "source_references": link.source_references_json,
            }
            if canonical_json_sha256(link_payload) != link.content_sha256:
                raise ClaimAuthorityConflictError(
                    "CLAIM_AUTHORITY_LINK_HASH_MISMATCH",
                    "A B7 support-link payload does not match its hash.",
                )
            reconstructed_links.append(
                {
                    **link_payload,
                    "content_sha256": link.content_sha256,
                }
            )
        payload = {
            "schema": "lab-claim-authority-v1",
            "authority_id": authority.authority_id,
            "version_number": authority.version_number,
            "legacy_claim_assessment_version_id": (
                authority.legacy_claim_assessment_version_id
            ),
            "policy_version": authority.policy_version,
            "policy_sha256": authority.policy_sha256,
            "policy": authority.policy_json,
            "claim_type": authority.claim_type,
            "subject_type": authority.subject_type,
            "subject_id": authority.subject_id,
            "claim_payload": authority.claim_payload_json,
            "identity_scope": authority.identity_scope_json,
            "identity_scope_sha256": authority.identity_scope_sha256,
            "condition_scope": authority.condition_scope_json,
            "condition_scope_sha256": authority.condition_scope_sha256,
            "claim_scope_sha256": authority.claim_scope_sha256,
            "decision": authority.decision,
            "dimension_results": authority.dimension_results_json,
            "supporting_observations": (
                authority.supporting_observations_json
            ),
            "conflicts": authority.conflicts_json,
            "missing_requirements": authority.missing_requirements_json,
            "source_references": authority.source_references_json,
            "uncertainty": authority.uncertainty_json,
            "permitted_wording": authority.permitted_wording,
            "forbidden_wording": authority.forbidden_wording,
            "blocker_count": authority.blocker_count,
            "conflict_count": authority.conflict_count,
            "missing_requirement_count": (
                authority.missing_requirement_count
            ),
            "critical_unknown_count": authority.critical_unknown_count,
            "support_count": authority.support_count,
            "source_reference_count": authority.source_reference_count,
            "release_authority": authority.release_authority,
            "upstream_hashes": authority.upstream_hashes_json,
            "reviewer_pseudonym": authority.reviewer_pseudonym,
            "reviewed_at": authority.reviewed_at.isoformat(),
            "parent_sha256": authority.parent_sha256,
        }
        if canonical_json_sha256(payload) != authority.content_sha256:
            raise ClaimAuthorityConflictError(
                "CLAIM_AUTHORITY_HASH_MISMATCH",
                "The B7 authority payload does not match its content hash.",
            )
        return {
            **payload,
            "version_id": authority.id,
            "content_sha256": authority.content_sha256,
            "support_links": reconstructed_links,
            "integrity_verified": True,
        }


__all__ = [
    "CLAIM_AUTHORITY_POLICIES",
    "ClaimAuthorityEvaluationInput",
    "ClaimAuthorityConflictError",
    "ClaimAuthorityError",
    "ClaimAuthorityPolicy",
    "ClaimAuthoritySupportInput",
    "LabClaimAuthorityServiceMixin",
    "canonical_json_sha256",
    "claim_policy_hash",
    "normalize_claim_authority_type",
    "policy_snapshot",
    "wording_for_decision",
]
