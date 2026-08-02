"""Validated commands for canonical B2 property authority records."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import TYPE_CHECKING, Any

from engine.calibration.hashing import stable_json_hash

from app.models.lab_properties import (
    ASSERTION_AUTHORITY_STATES,
    ASSERTION_CANDIDATE_DECISIONS,
    ASSERTION_INTERPOLATION_STATES,
    ASSERTION_SELECTION_KINDS,
    PROPERTY_CENSORING_QUALIFIERS,
    PROPERTY_CONFLICT_MATERIALITIES,
    PROPERTY_CONFLICT_STATES,
    PROPERTY_EVIDENCE_CLASSES,
    PROPERTY_IDENTITY_SCOPES,
    PROPERTY_REVIEW_STATES,
    PROPERTY_VALUE_KINDS,
    LabPropertyConflictMember,
    LabPropertyConflictSet,
    LabPropertyObservation,
    LabSelectedAssertion,
    LabSelectedAssertionCandidate,
)

if TYPE_CHECKING:
    from contextlib import AbstractAsyncContextManager

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.repositories.lab import LabRepository


class PropertyAuthorityError(ValueError):
    """Base class for stable B2 property-authority rejections."""

    code = "PROPERTY_AUTHORITY_ERROR"


class PropertyAuthorityConflictError(PropertyAuthorityError):
    """A valid command that conflicts with immutable B2 history."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _text(value: str, field: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise PropertyAuthorityError(f"{field} must not be blank")
    return normalized


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _choice(value: str, field: str, allowed: tuple[str, ...]) -> str:
    normalized = _text(value, field)
    if normalized not in allowed:
        raise PropertyAuthorityError(
            f"{field} must be one of {', '.join(allowed)}"
        )
    return normalized


def _finite_or_none(value: float | None, field: str) -> float | None:
    if value is None:
        return None
    normalized = float(value)
    if not isfinite(normalized):
        raise PropertyAuthorityError(f"{field} must be finite")
    return normalized


IDENTITY_REQUIRED_DIMENSIONS = {
    "CHEMICAL_ENTITY": ("chemical_name", "cas"),
    "STEREOISOMER_OR_ISOMERIC_MIXTURE": (
        "chemical_name",
        "cas",
        "stereochemistry",
    ),
    "TRADE_GRADE": ("chemical_name", "cas", "grade"),
    "SUPPLIER_PRODUCT": (
        "supplier",
        "supplier_product",
        "supplier_product_code",
    ),
    "SUPPLIER_LOT": (
        "supplier",
        "supplier_product",
        "supplier_lot",
    ),
    "STOCK_SOLUTION": (
        "stock_solution",
        "concentration_fraction",
        "concentration_basis",
    ),
    "PHYSICAL_DOSE": (
        "stock_solution",
        "dose_quantity",
        "dose_unit",
    ),
    "NATURAL_MATERIAL": (
        "botanical_species",
        "plant_part",
        "chemotype",
        "geographic_origin",
        "harvest_or_production_period",
        "extraction_or_processing",
        "supplier_product",
        "supplier_lot",
        "analytical_profile",
        "stock_solution",
    ),
}


def _identity(
    scope: str,
    value: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    normalized = dict(value)
    required = IDENTITY_REQUIRED_DIMENSIONS[scope]
    missing = tuple(
        dimension
        for dimension in required
        if dimension not in normalized
        or normalized[dimension] is None
        or (
            isinstance(normalized[dimension], str)
            and not normalized[dimension].strip()
        )
    )
    if missing:
        raise PropertyAuthorityError(
            "subject_identity is missing required dimensions: "
            + ", ".join(missing)
        )
    return normalized, stable_json_hash(
        {
            "schema": "lab-property-identity-v1",
            "identity_scope": scope,
            "subject_identity": normalized,
        }
    )


@dataclass(frozen=True, slots=True)
class PropertyObservationInput:
    observation_id: str
    schema_version: str
    identity_scope: str
    subject_identity: dict[str, Any]
    property_type: str
    value_kind: str
    original_unit: str
    canonical_unit: str
    method: str
    source_version_id: str
    extraction_record_id: str
    source_locator: dict[str, Any]
    statistic: str
    evidence_class: str
    review_state: str
    required_scope: str
    numeric_value: float | None = None
    categorical_value: str | None = None
    interval_lower: float | None = None
    interval_upper: float | None = None
    distribution: dict[str, Any] | None = None
    censoring_qualifier: str | None = None
    censoring_limit: float | None = None
    temperature_k: float | None = None
    pressure_pa: float | None = None
    relative_humidity_percent: float | None = None
    matrix: str | None = None
    phase: str | None = None
    purity_fraction: float | None = None
    replicate_count: int = 1
    standard_uncertainty: float | None = None
    uncertainty_interval: dict[str, Any] | None = None
    quality_flags: tuple[str, ...] = ()
    applicability_domain: dict[str, Any] | None = None
    provenance_activity: dict[str, Any] | None = None
    supersedes_observation_id: str | None = None

    def __post_init__(self) -> None:
        for field in (
            "observation_id",
            "schema_version",
            "property_type",
            "original_unit",
            "canonical_unit",
            "method",
            "source_version_id",
            "extraction_record_id",
            "statistic",
            "required_scope",
        ):
            object.__setattr__(self, field, _text(getattr(self, field), field))
        scope = _choice(
            self.identity_scope,
            "identity_scope",
            PROPERTY_IDENTITY_SCOPES,
        )
        value_kind = _choice(
            self.value_kind,
            "value_kind",
            PROPERTY_VALUE_KINDS,
        )
        evidence_class = _choice(
            self.evidence_class,
            "evidence_class",
            PROPERTY_EVIDENCE_CLASSES,
        )
        review_state = _choice(
            self.review_state,
            "review_state",
            PROPERTY_REVIEW_STATES,
        )
        subject_identity, _ = _identity(scope, self.subject_identity)
        object.__setattr__(self, "identity_scope", scope)
        object.__setattr__(self, "subject_identity", subject_identity)
        object.__setattr__(self, "value_kind", value_kind)
        object.__setattr__(self, "evidence_class", evidence_class)
        object.__setattr__(self, "review_state", review_state)
        object.__setattr__(self, "source_locator", dict(self.source_locator))
        object.__setattr__(
            self,
            "uncertainty_interval",
            dict(self.uncertainty_interval or {}),
        )
        object.__setattr__(
            self,
            "applicability_domain",
            dict(self.applicability_domain or {}),
        )
        object.__setattr__(
            self,
            "provenance_activity",
            dict(self.provenance_activity or {}),
        )
        flags = tuple(_text(flag, "quality_flags") for flag in self.quality_flags)
        if len(flags) != len(set(flags)):
            raise PropertyAuthorityError(
                "quality_flags must not contain duplicates"
            )
        object.__setattr__(self, "quality_flags", flags)
        object.__setattr__(
            self,
            "categorical_value",
            _optional_text(self.categorical_value),
        )
        object.__setattr__(self, "matrix", _optional_text(self.matrix))
        object.__setattr__(self, "phase", _optional_text(self.phase))
        object.__setattr__(
            self,
            "supersedes_observation_id",
            _optional_text(self.supersedes_observation_id),
        )
        for field in (
            "numeric_value",
            "interval_lower",
            "interval_upper",
            "censoring_limit",
            "temperature_k",
            "pressure_pa",
            "relative_humidity_percent",
            "purity_fraction",
            "standard_uncertainty",
        ):
            object.__setattr__(
                self,
                field,
                _finite_or_none(getattr(self, field), field),
            )
        if self.temperature_k is not None and self.temperature_k <= 0:
            raise PropertyAuthorityError("temperature_k must be greater than zero")
        if self.pressure_pa is not None and self.pressure_pa <= 0:
            raise PropertyAuthorityError("pressure_pa must be greater than zero")
        if self.relative_humidity_percent is not None and not (
            0 <= self.relative_humidity_percent <= 100
        ):
            raise PropertyAuthorityError(
                "relative_humidity_percent must be between zero and 100"
            )
        if self.purity_fraction is not None and not 0 <= self.purity_fraction <= 1:
            raise PropertyAuthorityError(
                "purity_fraction must be between zero and one"
            )
        if self.standard_uncertainty is not None and self.standard_uncertainty < 0:
            raise PropertyAuthorityError(
                "standard_uncertainty must be nonnegative"
            )
        replicate_count = int(self.replicate_count)
        if replicate_count < 1 or replicate_count != self.replicate_count:
            raise PropertyAuthorityError(
                "replicate_count must be a positive integer"
            )
        object.__setattr__(self, "replicate_count", replicate_count)
        distribution = (
            dict(self.distribution) if self.distribution is not None else None
        )
        object.__setattr__(self, "distribution", distribution)
        qualifier = (
            _choice(
                self.censoring_qualifier,
                "censoring_qualifier",
                PROPERTY_CENSORING_QUALIFIERS,
            )
            if self.censoring_qualifier is not None
            else None
        )
        object.__setattr__(self, "censoring_qualifier", qualifier)
        self._validate_value_shape()

    def _validate_value_shape(self) -> None:
        typed = (
            self.numeric_value,
            self.categorical_value,
            self.interval_lower,
            self.interval_upper,
            self.distribution,
        )
        if self.value_kind == "NUMERIC":
            if self.numeric_value is None or any(
                value is not None for value in typed[1:]
            ):
                raise PropertyAuthorityError(
                    "NUMERIC requires only numeric_value"
                )
        elif self.value_kind == "CATEGORICAL":
            if self.categorical_value is None or any(
                value is not None
                for value in (
                    self.numeric_value,
                    self.interval_lower,
                    self.interval_upper,
                    self.distribution,
                )
            ):
                raise PropertyAuthorityError(
                    "CATEGORICAL requires only categorical_value"
                )
        elif self.value_kind == "INTERVAL":
            if (
                self.interval_lower is None
                or self.interval_upper is None
                or any(
                    value is not None
                    for value in (
                        self.numeric_value,
                        self.categorical_value,
                        self.distribution,
                    )
                )
            ):
                raise PropertyAuthorityError(
                    "INTERVAL requires only interval_lower and interval_upper"
                )
            if self.interval_lower > self.interval_upper:
                raise PropertyAuthorityError(
                    "interval_lower must not exceed interval_upper"
                )
        elif self.value_kind == "DISTRIBUTION":
            if not self.distribution or any(
                value is not None
                for value in (
                    self.numeric_value,
                    self.categorical_value,
                    self.interval_lower,
                    self.interval_upper,
                )
            ):
                raise PropertyAuthorityError(
                    "DISTRIBUTION requires only a nonempty distribution"
                )
        elif any(value is not None for value in typed):
            raise PropertyAuthorityError(
                "CENSORED must not contain typed values"
            )

        if self.value_kind != "CENSORED":
            if (
                self.censoring_qualifier is not None
                or self.censoring_limit is not None
            ):
                raise PropertyAuthorityError(
                    "censoring fields require value_kind CENSORED"
                )
            return
        if self.censoring_qualifier is None:
            raise PropertyAuthorityError(
                "censoring_qualifier is required for CENSORED"
            )
        if (
            self.censoring_qualifier
            in {"LT_LOD", "LT_LOQ", "GT_UPPER_RANGE"}
            and self.censoring_limit is None
        ):
            raise PropertyAuthorityError(
                "censoring_limit is required for bounded censoring"
            )


@dataclass(frozen=True, slots=True)
class PropertyConflictInput:
    conflict_set_id: str
    schema_version: str
    requested_identity_scope: str
    requested_identity: dict[str, Any]
    property_type: str
    requested_conditions: dict[str, Any]
    state: str
    materiality: str
    explanation: str

    def __post_init__(self) -> None:
        for field in (
            "conflict_set_id",
            "schema_version",
            "property_type",
            "explanation",
        ):
            object.__setattr__(self, field, _text(getattr(self, field), field))
        scope = _choice(
            self.requested_identity_scope,
            "requested_identity_scope",
            PROPERTY_IDENTITY_SCOPES,
        )
        identity, _ = _identity(scope, self.requested_identity)
        object.__setattr__(self, "requested_identity_scope", scope)
        object.__setattr__(self, "requested_identity", identity)
        object.__setattr__(
            self,
            "requested_conditions",
            dict(self.requested_conditions),
        )
        object.__setattr__(
            self,
            "state",
            _choice(self.state, "state", PROPERTY_CONFLICT_STATES),
        )
        object.__setattr__(
            self,
            "materiality",
            _choice(
                self.materiality,
                "materiality",
                PROPERTY_CONFLICT_MATERIALITIES,
            ),
        )


@dataclass(frozen=True, slots=True)
class AssertionCandidateInput:
    observation_id: str
    decision: str
    rationale: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "observation_id",
            _text(self.observation_id, "observation_id"),
        )
        object.__setattr__(
            self,
            "decision",
            _choice(
                self.decision,
                "decision",
                ASSERTION_CANDIDATE_DECISIONS,
            ),
        )
        object.__setattr__(
            self,
            "rationale",
            _text(self.rationale, "rationale"),
        )


@dataclass(frozen=True, slots=True)
class SelectedAssertionInput:
    assertion_id: str
    schema_version: str
    requested_identity_scope: str
    requested_identity: dict[str, Any]
    requested_property_type: str
    requested_conditions: dict[str, Any]
    conflict_set_id: str | None
    selection_policy_version: str
    selection_kind: str
    selected_observation_id: str | None
    selected_model: dict[str, Any] | None
    interpolation_state: str
    propagated_uncertainty: dict[str, Any]
    applicability: dict[str, Any]
    authority_state: str
    permitted_claim_wording: str
    candidates: tuple[AssertionCandidateInput, ...]

    def __post_init__(self) -> None:
        for field in (
            "assertion_id",
            "schema_version",
            "requested_property_type",
            "selection_policy_version",
            "permitted_claim_wording",
        ):
            object.__setattr__(self, field, _text(getattr(self, field), field))
        scope = _choice(
            self.requested_identity_scope,
            "requested_identity_scope",
            PROPERTY_IDENTITY_SCOPES,
        )
        identity, _ = _identity(scope, self.requested_identity)
        object.__setattr__(self, "requested_identity_scope", scope)
        object.__setattr__(self, "requested_identity", identity)
        object.__setattr__(
            self,
            "requested_conditions",
            dict(self.requested_conditions),
        )
        object.__setattr__(
            self,
            "conflict_set_id",
            _optional_text(self.conflict_set_id),
        )
        selection_kind = _choice(
            self.selection_kind,
            "selection_kind",
            ASSERTION_SELECTION_KINDS,
        )
        selected_observation_id = _optional_text(
            self.selected_observation_id
        )
        selected_model = (
            dict(self.selected_model)
            if self.selected_model is not None
            else None
        )
        if selection_kind == "MODEL" and not selected_model:
            raise PropertyAuthorityError("selected_model must not be empty")
        object.__setattr__(self, "selection_kind", selection_kind)
        object.__setattr__(
            self,
            "selected_observation_id",
            selected_observation_id,
        )
        object.__setattr__(self, "selected_model", selected_model)
        if selection_kind == "OBSERVATION" and (
            selected_observation_id is None or selected_model is not None
        ):
            raise PropertyAuthorityError(
                "OBSERVATION selection requires only selected_observation_id"
            )
        if selection_kind == "MODEL" and (
            selected_observation_id is not None or selected_model is None
        ):
            raise PropertyAuthorityError(
                "MODEL selection requires only selected_model"
            )
        if selection_kind == "NONE" and (
            selected_observation_id is not None or selected_model is not None
        ):
            raise PropertyAuthorityError(
                "NONE selection must not select an observation or model"
            )
        object.__setattr__(
            self,
            "interpolation_state",
            _choice(
                self.interpolation_state,
                "interpolation_state",
                ASSERTION_INTERPOLATION_STATES,
            ),
        )
        object.__setattr__(
            self,
            "propagated_uncertainty",
            dict(self.propagated_uncertainty),
        )
        object.__setattr__(self, "applicability", dict(self.applicability))
        object.__setattr__(
            self,
            "authority_state",
            _choice(
                self.authority_state,
                "authority_state",
                ASSERTION_AUTHORITY_STATES,
            ),
        )
        candidates = tuple(self.candidates)
        if not candidates:
            raise PropertyAuthorityError("candidates must not be empty")
        candidate_ids = tuple(
            candidate.observation_id for candidate in candidates
        )
        if len(candidate_ids) != len(set(candidate_ids)):
            raise PropertyAuthorityError(
                "candidates must not contain duplicates"
            )
        object.__setattr__(self, "candidates", candidates)


def _observation_payload(
    command: PropertyObservationInput,
    identity_sha256: str,
) -> dict[str, Any]:
    return {
        "schema": "lab-property-observation-v1",
        "observation_id": command.observation_id,
        "schema_version": command.schema_version,
        "identity_scope": command.identity_scope,
        "subject_identity": command.subject_identity,
        "subject_identity_sha256": identity_sha256,
        "property_type": command.property_type,
        "value_kind": command.value_kind,
        "numeric_value": command.numeric_value,
        "categorical_value": command.categorical_value,
        "interval_lower": command.interval_lower,
        "interval_upper": command.interval_upper,
        "distribution": command.distribution,
        "censoring_qualifier": command.censoring_qualifier,
        "censoring_limit": command.censoring_limit,
        "original_unit": command.original_unit,
        "canonical_unit": command.canonical_unit,
        "temperature_k": command.temperature_k,
        "pressure_pa": command.pressure_pa,
        "relative_humidity_percent": command.relative_humidity_percent,
        "matrix": command.matrix,
        "phase": command.phase,
        "purity_fraction": command.purity_fraction,
        "method": command.method,
        "source_version_id": command.source_version_id,
        "extraction_record_id": command.extraction_record_id,
        "source_locator": command.source_locator,
        "replicate_count": command.replicate_count,
        "statistic": command.statistic,
        "standard_uncertainty": command.standard_uncertainty,
        "uncertainty_interval": command.uncertainty_interval,
        "evidence_class": command.evidence_class,
        "review_state": command.review_state,
        "quality_flags": command.quality_flags,
        "applicability_domain": command.applicability_domain,
        "provenance_activity": command.provenance_activity,
        "supersedes_observation_id": command.supersedes_observation_id,
    }


def _typed_value(observation: LabPropertyObservation) -> dict[str, Any]:
    return {
        "value_kind": observation.value_kind,
        "numeric_value": observation.numeric_value,
        "categorical_value": observation.categorical_value,
        "interval_lower": observation.interval_lower,
        "interval_upper": observation.interval_upper,
        "distribution": observation.distribution_json,
        "censoring_qualifier": observation.censoring_qualifier,
        "censoring_limit": observation.censoring_limit,
    }


def _different(values: list[Any]) -> bool:
    return len({stable_json_hash({"value": value}) for value in values}) > 1


class LabPropertyServiceMixin:
    """Property commands using canonical B1 provenance and service transactions."""

    if TYPE_CHECKING:
        repository: LabRepository
        session: AsyncSession

        def _transaction(self) -> AbstractAsyncContextManager[None]: ...

        async def is_accepted_for_scoped_use(
            self,
            subject_type: str,
            subject_id: str,
            *,
            required_scope: str,
        ) -> bool: ...

        async def reconstruct_observation_derivation(
            self,
            observation_id: str,
            *,
            required_scope: str,
        ) -> dict[str, Any]: ...

    async def record_property_observation(
        self,
        command: PropertyObservationInput,
    ) -> LabPropertyObservation:
        async with self._transaction():
            existing_id = await self.repository.get_property_observation(
                command.observation_id
            )
            if existing_id is not None:
                raise PropertyAuthorityConflictError(
                    "PROPERTY_OBSERVATION_ALREADY_EXISTS",
                    "The immutable property observation identifier already exists.",
                )
            source = await self.repository.get_source_document_version(
                command.source_version_id
            )
            extraction = await self.repository.get_source_extraction(
                command.extraction_record_id
            )
            if source is None or extraction is None:
                raise PropertyAuthorityConflictError(
                    "PROPERTY_SOURCE_LINK_NOT_FOUND",
                    "The source version and extraction record must exist.",
                )
            if extraction.source_version_id != source.id:
                raise PropertyAuthorityConflictError(
                    "PROPERTY_EXTRACTION_SOURCE_MISMATCH",
                    "The extraction record does not belong to the source version.",
                )
            if extraction.output_observation_id != command.observation_id:
                raise PropertyAuthorityConflictError(
                    "PROPERTY_EXTRACTION_OBSERVATION_MISMATCH",
                    "The extraction record reserves a different observation.",
                )
            if extraction.locator_json != command.source_locator:
                raise PropertyAuthorityConflictError(
                    "PROPERTY_EXTRACTION_LOCATOR_MISMATCH",
                    "The observation locator must equal the accepted extraction locator.",
                )
            accepted = await self.is_accepted_for_scoped_use(
                "EXTRACTION_RECORD",
                extraction.id,
                required_scope=command.required_scope,
            )
            if not accepted:
                raise PropertyAuthorityConflictError(
                    "PROPERTY_EXTRACTION_SCOPE_NOT_ACCEPTED",
                    "The extraction record is not accepted for the required scope.",
                )
            if command.supersedes_observation_id is not None:
                superseded = await self.repository.get_property_observation(
                    command.supersedes_observation_id
                )
                if superseded is None:
                    raise PropertyAuthorityConflictError(
                        "PROPERTY_SUPERSEDED_OBSERVATION_NOT_FOUND",
                        "The superseded observation does not exist.",
                    )
            _, identity_sha256 = _identity(
                command.identity_scope,
                command.subject_identity,
            )
            content_sha256 = stable_json_hash(
                _observation_payload(command, identity_sha256)
            )
            duplicate = await self.repository.property_observation_by_hash(
                content_sha256
            )
            if duplicate is not None:
                raise PropertyAuthorityConflictError(
                    "PROPERTY_OBSERVATION_ALREADY_EXISTS",
                    "An identical immutable property observation already exists.",
                )
            return await self.repository.add(
                LabPropertyObservation(
                    id=command.observation_id,
                    schema_version=command.schema_version,
                    identity_scope=command.identity_scope,
                    subject_identity_json=dict(command.subject_identity),
                    subject_identity_sha256=identity_sha256,
                    property_type=command.property_type,
                    value_kind=command.value_kind,
                    numeric_value=command.numeric_value,
                    categorical_value=command.categorical_value,
                    interval_lower=command.interval_lower,
                    interval_upper=command.interval_upper,
                    distribution_json=(
                        dict(command.distribution)
                        if command.distribution is not None
                        else None
                    ),
                    censoring_qualifier=command.censoring_qualifier,
                    censoring_limit=command.censoring_limit,
                    original_unit=command.original_unit,
                    canonical_unit=command.canonical_unit,
                    temperature_k=command.temperature_k,
                    pressure_pa=command.pressure_pa,
                    relative_humidity_percent=command.relative_humidity_percent,
                    matrix=command.matrix,
                    phase=command.phase,
                    purity_fraction=command.purity_fraction,
                    method=command.method,
                    source_version_id=command.source_version_id,
                    extraction_record_id=command.extraction_record_id,
                    source_locator_json=dict(command.source_locator),
                    replicate_count=command.replicate_count,
                    statistic=command.statistic,
                    standard_uncertainty=command.standard_uncertainty,
                    uncertainty_interval_json=dict(
                        command.uncertainty_interval or {}
                    ),
                    evidence_class=command.evidence_class,
                    review_state=command.review_state,
                    quality_flags_json=list(command.quality_flags),
                    applicability_domain_json=dict(
                        command.applicability_domain or {}
                    ),
                    provenance_activity_json=dict(
                        command.provenance_activity or {}
                    ),
                    supersedes_observation_id=command.supersedes_observation_id,
                    content_sha256=content_sha256,
                )
            )

    async def record_property_conflict(
        self,
        command: PropertyConflictInput,
        *,
        observation_ids: tuple[str, ...],
    ) -> LabPropertyConflictSet:
        normalized_ids = tuple(
            _text(observation_id, "observation_ids")
            for observation_id in observation_ids
        )
        if len(normalized_ids) < 2:
            raise PropertyAuthorityError(
                "a property conflict requires at least two observations"
            )
        if len(normalized_ids) != len(set(normalized_ids)):
            raise PropertyAuthorityError(
                "observation_ids must not contain duplicates"
            )
        async with self._transaction():
            if (
                await self.repository.get_property_conflict_set(
                    command.conflict_set_id
                )
                is not None
            ):
                raise PropertyAuthorityConflictError(
                    "PROPERTY_CONFLICT_ALREADY_EXISTS",
                    "The immutable property conflict identifier already exists.",
                )
            observations = (
                await self.repository.property_observations_by_ids(
                    normalized_ids
                )
            )
            if len(observations) != len(normalized_ids):
                raise PropertyAuthorityConflictError(
                    "PROPERTY_CONFLICT_OBSERVATION_NOT_FOUND",
                    "Every property conflict observation must exist.",
                )
            if any(
                observation.property_type != command.property_type
                for observation in observations
            ):
                raise PropertyAuthorityConflictError(
                    "PROPERTY_CONFLICT_TYPE_MISMATCH",
                    "Conflict observations must match the requested property.",
                )
            sources = [
                await self.repository.get_source_document_version(
                    observation.source_version_id
                )
                for observation in observations
            ]
            if any(source is None for source in sources):
                raise PropertyAuthorityConflictError(
                    "PROPERTY_CONFLICT_SOURCE_NOT_FOUND",
                    "Every conflict observation source must exist.",
                )
            independence_groups = [
                source.independence_group
                for source in sources
                if source is not None
            ]
            dimension_values: dict[str, list[Any]] = {
                "identity_scope": [
                    observation.identity_scope
                    for observation in observations
                ],
                "subject_identity": [
                    observation.subject_identity_json
                    for observation in observations
                ],
                "property_type": [
                    observation.property_type for observation in observations
                ],
                "value": [_typed_value(observation) for observation in observations],
                "canonical_unit": [
                    observation.canonical_unit for observation in observations
                ],
                "method": [
                    observation.method for observation in observations
                ],
                "matrix": [
                    observation.matrix for observation in observations
                ],
                "temperature_k": [
                    observation.temperature_k for observation in observations
                ],
                "source_independence_group": independence_groups,
            }
            difference_dimensions = [
                dimension
                for dimension, values in dimension_values.items()
                if _different(values)
            ]
            if not difference_dimensions:
                raise PropertyAuthorityConflictError(
                    "PROPERTY_CONFLICT_NO_DIFFERENCE",
                    "A conflict requires at least one visible difference.",
                )
            requested_identity, requested_identity_sha256 = _identity(
                command.requested_identity_scope,
                command.requested_identity,
            )
            members = [
                {
                    "observation_id": observation.id,
                    "numeric_value": observation.numeric_value,
                    "typed_value": _typed_value(observation),
                    "identity_scope": observation.identity_scope,
                    "subject_identity_sha256": (
                        observation.subject_identity_sha256
                    ),
                    "canonical_unit": observation.canonical_unit,
                    "method": observation.method,
                    "matrix": observation.matrix,
                    "temperature_k": observation.temperature_k,
                    "source_independence_group": independence_group,
                    "difference_dimensions": difference_dimensions,
                }
                for observation, independence_group in zip(
                    observations,
                    independence_groups,
                    strict=True,
                )
            ]
            payload = {
                "schema": "lab-property-conflict-v1",
                "conflict_set_id": command.conflict_set_id,
                "schema_version": command.schema_version,
                "requested_identity_scope": command.requested_identity_scope,
                "requested_identity": requested_identity,
                "requested_identity_sha256": requested_identity_sha256,
                "property_type": command.property_type,
                "requested_conditions": command.requested_conditions,
                "state": command.state,
                "materiality": command.materiality,
                "difference_dimensions": difference_dimensions,
                "explanation": command.explanation,
                "members": members,
            }
            content_sha256 = stable_json_hash(payload)
            if (
                await self.repository.property_conflict_by_hash(
                    content_sha256
                )
                is not None
            ):
                raise PropertyAuthorityConflictError(
                    "PROPERTY_CONFLICT_ALREADY_EXISTS",
                    "An identical immutable property conflict already exists.",
                )
            conflict = await self.repository.add(
                LabPropertyConflictSet(
                    id=command.conflict_set_id,
                    schema_version=command.schema_version,
                    requested_identity_json={
                        "identity_scope": command.requested_identity_scope,
                        "subject_identity": requested_identity,
                    },
                    requested_identity_sha256=requested_identity_sha256,
                    property_type=command.property_type,
                    requested_conditions_json=dict(
                        command.requested_conditions
                    ),
                    state=command.state,
                    materiality=command.materiality,
                    difference_dimensions_json=difference_dimensions,
                    explanation=command.explanation,
                    content_sha256=content_sha256,
                )
            )
            for member in members:
                await self.repository.add(
                    LabPropertyConflictMember(
                        conflict_set_id=conflict.id,
                        observation_id=member["observation_id"],
                        differences_json=member,
                    )
                )
            return conflict

    async def record_selected_assertion(
        self,
        command: SelectedAssertionInput,
    ) -> LabSelectedAssertion:
        candidate_ids = tuple(
            candidate.observation_id for candidate in command.candidates
        )
        async with self._transaction():
            if (
                await self.repository.get_selected_assertion(
                    command.assertion_id
                )
                is not None
            ):
                raise PropertyAuthorityConflictError(
                    "PROPERTY_ASSERTION_ALREADY_EXISTS",
                    "The immutable selected assertion identifier already exists.",
                )
            observations = (
                await self.repository.property_observations_by_ids(
                    candidate_ids
                )
            )
            if len(observations) != len(candidate_ids):
                raise PropertyAuthorityConflictError(
                    "PROPERTY_ASSERTION_OBSERVATION_NOT_FOUND",
                    "Every selected-assertion candidate must exist.",
                )
            if any(
                observation.property_type
                != command.requested_property_type
                for observation in observations
            ):
                raise PropertyAuthorityConflictError(
                    "PROPERTY_ASSERTION_TYPE_MISMATCH",
                    "Every candidate must match the requested property.",
                )
            requested_identity, requested_identity_sha256 = _identity(
                command.requested_identity_scope,
                command.requested_identity,
            )
            conflict = None
            if command.conflict_set_id is not None:
                conflict = await self.repository.get_property_conflict_set(
                    command.conflict_set_id
                )
                if conflict is None:
                    raise PropertyAuthorityConflictError(
                        "PROPERTY_ASSERTION_CONFLICT_NOT_FOUND",
                        "The selected assertion conflict set does not exist.",
                    )
                if (
                    conflict.requested_identity_sha256
                    != requested_identity_sha256
                    or conflict.property_type
                    != command.requested_property_type
                    or conflict.requested_conditions_json
                    != command.requested_conditions
                ):
                    raise PropertyAuthorityConflictError(
                        "PROPERTY_ASSERTION_CONFLICT_SCOPE_MISMATCH",
                        "The conflict request must match the assertion request.",
                    )
                conflict_members = (
                    await self.repository.property_conflict_members(
                        conflict.id
                    )
                )
                conflict_observation_ids = {
                    member.observation_id for member in conflict_members
                }
                if conflict_observation_ids != set(candidate_ids):
                    raise PropertyAuthorityConflictError(
                        "PROPERTY_ASSERTION_CANDIDATES_INCOMPLETE",
                        "Candidates must enumerate every conflict observation.",
                    )
                if (
                    conflict.state == "UNRESOLVED"
                    and conflict.materiality == "BLOCKING"
                    and command.authority_state != "WITHHELD_CONFLICT"
                ):
                    raise PropertyAuthorityConflictError(
                        "PROPERTY_ASSERTION_BLOCKING_CONFLICT",
                        "An unresolved blocking conflict must withhold authority.",
                    )
            decisions = {
                candidate.observation_id: candidate.decision
                for candidate in command.candidates
            }
            selected_observation_id = command.selected_observation_id
            if command.selection_kind == "OBSERVATION" and (
                selected_observation_id is None
                or decisions.get(selected_observation_id) != "INCLUDE"
            ):
                raise PropertyAuthorityConflictError(
                    "PROPERTY_ASSERTION_SELECTION_INCONSISTENT",
                    "The selected observation must be an included candidate.",
                )
            if (
                command.authority_state
                == "AUTHORIZED_FOR_SCOPED_PROPERTY"
                and command.selection_kind == "NONE"
            ):
                raise PropertyAuthorityConflictError(
                    "PROPERTY_ASSERTION_SELECTION_INCONSISTENT",
                    "An authorized assertion must select evidence or a model.",
                )
            candidate_payload = [
                {
                    "observation_id": candidate.observation_id,
                    "content_sha256": observation.content_sha256,
                    "decision": candidate.decision,
                    "rationale": candidate.rationale,
                }
                for candidate, observation in zip(
                    command.candidates,
                    observations,
                    strict=True,
                )
            ]
            payload = {
                "schema": "lab-selected-assertion-v1",
                "assertion_id": command.assertion_id,
                "schema_version": command.schema_version,
                "requested_identity_scope": command.requested_identity_scope,
                "requested_identity": requested_identity,
                "requested_identity_sha256": requested_identity_sha256,
                "requested_property_type": command.requested_property_type,
                "requested_conditions": command.requested_conditions,
                "conflict_set_id": command.conflict_set_id,
                "selection_policy_version": (
                    command.selection_policy_version
                ),
                "selection_kind": command.selection_kind,
                "selected_observation_id": (
                    command.selected_observation_id
                ),
                "selected_model": command.selected_model,
                "interpolation_state": command.interpolation_state,
                "propagated_uncertainty": (
                    command.propagated_uncertainty
                ),
                "applicability": command.applicability,
                "authority_state": command.authority_state,
                "permitted_claim_wording": (
                    command.permitted_claim_wording
                ),
                "candidates": candidate_payload,
            }
            content_sha256 = stable_json_hash(payload)
            if (
                await self.repository.selected_assertion_by_hash(
                    content_sha256
                )
                is not None
            ):
                raise PropertyAuthorityConflictError(
                    "PROPERTY_ASSERTION_ALREADY_EXISTS",
                    "An identical immutable selected assertion already exists.",
                )
            assertion = await self.repository.add(
                LabSelectedAssertion(
                    id=command.assertion_id,
                    schema_version=command.schema_version,
                    requested_identity_json={
                        "identity_scope": command.requested_identity_scope,
                        "subject_identity": requested_identity,
                    },
                    requested_identity_sha256=requested_identity_sha256,
                    requested_property_type=(
                        command.requested_property_type
                    ),
                    requested_conditions_json=dict(
                        command.requested_conditions
                    ),
                    conflict_set_id=command.conflict_set_id,
                    selection_policy_version=(
                        command.selection_policy_version
                    ),
                    selection_kind=command.selection_kind,
                    selected_observation_id=(
                        command.selected_observation_id
                    ),
                    selected_model_json=(
                        dict(command.selected_model)
                        if command.selected_model is not None
                        else None
                    ),
                    interpolation_state=command.interpolation_state,
                    propagated_uncertainty_json=dict(
                        command.propagated_uncertainty
                    ),
                    applicability_json=dict(command.applicability),
                    authority_state=command.authority_state,
                    permitted_claim_wording=(
                        command.permitted_claim_wording
                    ),
                    content_sha256=content_sha256,
                )
            )
            for candidate in command.candidates:
                await self.repository.add(
                    LabSelectedAssertionCandidate(
                        selected_assertion_id=assertion.id,
                        observation_id=candidate.observation_id,
                        decision=candidate.decision,
                        rationale=candidate.rationale,
                    )
                )
            return assertion

    async def get_selected_assertion_by_id(
        self,
        assertion_id: str,
    ) -> LabSelectedAssertion | None:
        return await self.repository.get_selected_assertion(
            _text(assertion_id, "assertion_id")
        )

    async def reconstruct_selected_assertion(
        self,
        assertion_id: str,
        *,
        required_scope: str,
    ) -> dict[str, Any]:
        identifier = _text(assertion_id, "assertion_id")
        scope = _text(required_scope, "required_scope")
        assertion = await self.repository.get_selected_assertion(identifier)
        if assertion is None:
            return {
                "schema": "lab-selected-assertion-reconstruction-v1",
                "assertion": None,
                "candidates": [],
                "conflict": None,
                "complete": False,
            }
        candidate_records = (
            await self.repository.selected_assertion_candidates(identifier)
        )
        observations = (
            await self.repository.property_observations_by_ids(
                tuple(
                    candidate.observation_id
                    for candidate in candidate_records
                )
            )
        )
        candidates: list[dict[str, Any]] = []
        for candidate, observation in zip(
            candidate_records,
            observations,
            strict=True,
        ):
            derivation = await self.reconstruct_observation_derivation(
                observation.id,
                required_scope=scope,
            )
            candidates.append(
                {
                    "observation": {
                        "id": observation.id,
                        "identity_scope": observation.identity_scope,
                        "subject_identity": (
                            observation.subject_identity_json
                        ),
                        "property_type": observation.property_type,
                        **_typed_value(observation),
                        "original_unit": observation.original_unit,
                        "canonical_unit": observation.canonical_unit,
                        "temperature_k": observation.temperature_k,
                        "pressure_pa": observation.pressure_pa,
                        "relative_humidity_percent": (
                            observation.relative_humidity_percent
                        ),
                        "matrix": observation.matrix,
                        "phase": observation.phase,
                        "purity_fraction": observation.purity_fraction,
                        "method": observation.method,
                        "source_version_id": observation.source_version_id,
                        "extraction_record_id": (
                            observation.extraction_record_id
                        ),
                        "source_locator": observation.source_locator_json,
                        "replicate_count": observation.replicate_count,
                        "statistic": observation.statistic,
                        "standard_uncertainty": (
                            observation.standard_uncertainty
                        ),
                        "uncertainty_interval": (
                            observation.uncertainty_interval_json
                        ),
                        "evidence_class": observation.evidence_class,
                        "review_state": observation.review_state,
                        "applicability_domain": (
                            observation.applicability_domain_json
                        ),
                        "provenance_activity": (
                            observation.provenance_activity_json
                        ),
                        "content_sha256": observation.content_sha256,
                    },
                    "decision": candidate.decision,
                    "rationale": candidate.rationale,
                    "derivation": derivation,
                }
            )
        conflict_payload = None
        if assertion.conflict_set_id is not None:
            conflict = await self.repository.get_property_conflict_set(
                assertion.conflict_set_id
            )
            if conflict is not None:
                members = await self.repository.property_conflict_members(
                    conflict.id
                )
                conflict_payload = {
                    "id": conflict.id,
                    "state": conflict.state,
                    "materiality": conflict.materiality,
                    "difference_dimensions": (
                        conflict.difference_dimensions_json
                    ),
                    "explanation": conflict.explanation,
                    "members": [
                        {
                            "observation_id": member.observation_id,
                            "differences": member.differences_json,
                        }
                        for member in members
                    ],
                }
        return {
            "schema": "lab-selected-assertion-reconstruction-v1",
            "assertion": {
                "id": assertion.id,
                "requested_identity": assertion.requested_identity_json,
                "requested_property_type": (
                    assertion.requested_property_type
                ),
                "requested_conditions": (
                    assertion.requested_conditions_json
                ),
                "selection_policy_version": (
                    assertion.selection_policy_version
                ),
                "selection_kind": assertion.selection_kind,
                "selected_observation_id": (
                    assertion.selected_observation_id
                ),
                "selected_model": assertion.selected_model_json,
                "interpolation_state": assertion.interpolation_state,
                "propagated_uncertainty": (
                    assertion.propagated_uncertainty_json
                ),
                "applicability": assertion.applicability_json,
                "authority_state": assertion.authority_state,
                "permitted_claim_wording": (
                    assertion.permitted_claim_wording
                ),
                "content_sha256": assertion.content_sha256,
            },
            "candidates": candidates,
            "conflict": conflict_payload,
            "complete": bool(candidates)
            and all(
                candidate["derivation"]["complete"]
                for candidate in candidates
            ),
        }


__all__ = [
    "AssertionCandidateInput",
    "IDENTITY_REQUIRED_DIMENSIONS",
    "LabPropertyServiceMixin",
    "PropertyAuthorityConflictError",
    "PropertyAuthorityError",
    "PropertyConflictInput",
    "PropertyObservationInput",
    "SelectedAssertionInput",
]
