"""Fail-closed B6 safety and regulatory screening authority."""

from __future__ import annotations

import json
from collections.abc import Mapping
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import date, datetime, timezone
from hashlib import sha256
from math import isfinite
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lab_regulatory import (
    REGULATORY_AUTHORITY_FAMILIES,
    REGULATORY_COMPOSITION_BASES,
    REGULATORY_COMPOSITION_COMPLETENESS,
    REGULATORY_COMPOSITION_ORIGINS,
    REGULATORY_MARKET_ACTIONS,
    REGULATORY_RESULT_STATES,
    REGULATORY_RULE_FAMILIES,
    REGULATORY_RULE_KINDS,
    REGULATORY_SOURCE_STATUSES,
    REGULATORY_SUBJECT_TYPES,
    SUPPLIER_DOCUMENT_SCOPES,
    SUPPLIER_REGULATORY_DOCUMENT_TYPES,
    LabRegulatoryAuthorityFinding,
    LabRegulatoryCompositionEntry,
    LabRegulatoryCompositionProfile,
    LabRegulatoryRuleVersion,
    LabRegulatorySnapshotVersion,
    LabRegulatorySourceVersion,
    LabSupplierDocumentBinding,
)

if TYPE_CHECKING:
    from app.repositories.lab import LabRepository

FINAL_SOURCE_STATUSES = (
    "CURRENT_ENFORCED_OR_FORMALLY_NOTIFIED",
    "FUTURE_EFFECTIVE",
)
NONFINAL_SOURCE_STATUSES = ("DRAFT", "CONSULTATION", "WATCHLIST")
OFFICIAL_SOURCE_TYPES = ("REGULATION_OR_OFFICIAL_GUIDANCE", "STANDARD")


class RegulatoryAuthorityError(ValueError):
    """Raised when B6 input cannot satisfy the declared contract."""


class RegulatoryAuthorityConflictError(RegulatoryAuthorityError):
    """Raised when referenced canonical state cannot support a B6 command."""

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
        raise RegulatoryAuthorityError(
            "regulatory authority values must be finite canonical JSON"
        ) from exc


def canonical_json_sha256(value: Any) -> str:
    return sha256(_canonical(value).encode("utf-8")).hexdigest()


def _text(value: str, field: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise RegulatoryAuthorityError(f"{field} must not be empty")
    return normalized


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _choice(value: str, field: str, choices: tuple[str, ...]) -> str:
    normalized = _text(value, field).upper()
    if normalized not in choices:
        raise RegulatoryAuthorityError(
            f"{field} must be one of: {', '.join(choices)}"
        )
    return normalized


def _aware(value: datetime, field: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise RegulatoryAuthorityError(f"{field} must be timezone-aware")
    return value


def _date_value(value: date, field: str) -> date:
    if not isinstance(value, date) or isinstance(value, datetime):
        raise RegulatoryAuthorityError(f"{field} must be a date")
    return value


def _date_or_none(value: date | None, field: str) -> date | None:
    if value is None:
        return None
    return _date_value(value, field)


def _mapping(value: Mapping[str, Any], field: str) -> dict[str, Any]:
    normalized = dict(value)
    _canonical(normalized)
    return normalized


def _strings(values: tuple[str, ...], field: str) -> tuple[str, ...]:
    normalized = tuple(_text(value, field) for value in values)
    _canonical(normalized)
    return normalized


def _optional_id(value: str | None) -> str | None:
    return _optional_text(value)


def _fraction_or_none(
    value: float | None,
    field: str,
) -> float | None:
    if value is None:
        return None
    number = float(value)
    if not isfinite(number) or not 0 <= number <= 1:
        raise RegulatoryAuthorityError(
            f"{field} must be finite and between zero and one"
        )
    return number


def _validate_date_range(
    start: date | None,
    end: date | None,
    *,
    start_field: str,
    end_field: str,
) -> None:
    if start is not None and end is not None and end < start:
        raise RegulatoryAuthorityError(
            f"{end_field} must be on or after {start_field}"
        )


def _utc_date(value: datetime) -> date:
    return value.astimezone(timezone.utc).date()


def _unique_ids(values: tuple[str, ...], field: str) -> tuple[str, ...]:
    normalized = tuple(_text(value, field) for value in values)
    if len(normalized) != len(set(normalized)):
        raise RegulatoryAuthorityError(f"{field} must not contain duplicates")
    return tuple(sorted(normalized))


@dataclass(frozen=True, slots=True)
class RegulatorySourceInput:
    schema_version: str
    authority_family: str
    identifier: str
    published_version: str
    jurisdiction: str
    status: str
    notified_on: date | None
    effective_from: date | None
    effective_through: date | None
    checked_at: datetime
    official_source_document_version_id: str
    source_locator: Mapping[str, Any]
    notes: Mapping[str, Any]
    authority_id: str | None = None
    parent_version_id: str | None = None
    supersedes_source_version_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )
        object.__setattr__(
            self,
            "authority_family",
            _choice(
                self.authority_family,
                "authority_family",
                REGULATORY_AUTHORITY_FAMILIES,
            ),
        )
        object.__setattr__(self, "identifier", _text(self.identifier, "identifier"))
        object.__setattr__(
            self,
            "published_version",
            _text(self.published_version, "published_version"),
        )
        object.__setattr__(
            self, "jurisdiction", _text(self.jurisdiction, "jurisdiction")
        )
        object.__setattr__(
            self,
            "status",
            _choice(self.status, "status", REGULATORY_SOURCE_STATUSES),
        )
        for field in ("notified_on", "effective_from", "effective_through"):
            object.__setattr__(
                self,
                field,
                _date_or_none(getattr(self, field), field),
            )
        _validate_date_range(
            self.effective_from,
            self.effective_through,
            start_field="effective_from",
            end_field="effective_through",
        )
        object.__setattr__(
            self, "checked_at", _aware(self.checked_at, "checked_at")
        )
        object.__setattr__(
            self,
            "official_source_document_version_id",
            _text(
                self.official_source_document_version_id,
                "official_source_document_version_id",
            ),
        )
        object.__setattr__(
            self,
            "source_locator",
            _mapping(self.source_locator, "source_locator"),
        )
        object.__setattr__(self, "notes", _mapping(self.notes, "notes"))
        for field in (
            "authority_id",
            "parent_version_id",
            "supersedes_source_version_id",
        ):
            object.__setattr__(
                self,
                field,
                _optional_id(getattr(self, field)),
            )


@dataclass(frozen=True, slots=True)
class RegulatoryRuleInput:
    schema_version: str
    regulatory_source_version_id: str
    rule_family: str
    rule_identifier: str
    material_id: str | None
    substance_name: str
    cas_number: str | None
    jurisdiction: str
    product_category: str
    use_classification: str
    concentration_basis: str
    rule_kind: str
    threshold_fraction: float | None
    maximum_fraction: float | None
    declaration_wording: str | None
    effective_from: date | None
    effective_through: date | None
    placement_transition_end: date | None
    availability_transition_end: date | None
    transition_conditions: Mapping[str, Any]
    assumptions: tuple[str, ...]
    rule_id: str | None = None
    parent_version_id: str | None = None

    def __post_init__(self) -> None:
        for field in (
            "schema_version",
            "regulatory_source_version_id",
            "rule_identifier",
            "substance_name",
            "jurisdiction",
            "product_category",
            "use_classification",
            "concentration_basis",
        ):
            object.__setattr__(
                self,
                field,
                _text(getattr(self, field), field),
            )
        object.__setattr__(
            self,
            "rule_family",
            _choice(self.rule_family, "rule_family", REGULATORY_RULE_FAMILIES),
        )
        object.__setattr__(
            self,
            "rule_kind",
            _choice(self.rule_kind, "rule_kind", REGULATORY_RULE_KINDS),
        )
        for field in ("material_id", "cas_number", "rule_id", "parent_version_id"):
            object.__setattr__(
                self,
                field,
                _optional_text(getattr(self, field)),
            )
        object.__setattr__(
            self,
            "threshold_fraction",
            _fraction_or_none(self.threshold_fraction, "threshold_fraction"),
        )
        object.__setattr__(
            self,
            "maximum_fraction",
            _fraction_or_none(self.maximum_fraction, "maximum_fraction"),
        )
        object.__setattr__(
            self,
            "declaration_wording",
            _optional_text(self.declaration_wording),
        )
        if self.rule_kind == "MAXIMUM_FINISHED_FRACTION":
            if (
                self.maximum_fraction is None
                or self.threshold_fraction is not None
                or self.declaration_wording is not None
            ):
                raise RegulatoryAuthorityError(
                    "maximum rule requires only maximum_fraction"
                )
        elif (
            self.threshold_fraction is None
            or self.maximum_fraction is not None
            or self.declaration_wording is None
        ):
            raise RegulatoryAuthorityError(
                "declaration rule requires threshold_fraction and wording"
            )
        for field in (
            "effective_from",
            "effective_through",
            "placement_transition_end",
            "availability_transition_end",
        ):
            object.__setattr__(
                self,
                field,
                _date_or_none(getattr(self, field), field),
            )
        _validate_date_range(
            self.effective_from,
            self.effective_through,
            start_field="effective_from",
            end_field="effective_through",
        )
        _validate_date_range(
            self.placement_transition_end,
            self.availability_transition_end,
            start_field="placement_transition_end",
            end_field="availability_transition_end",
        )
        object.__setattr__(
            self,
            "transition_conditions",
            _mapping(self.transition_conditions, "transition_conditions"),
        )
        object.__setattr__(
            self,
            "assumptions",
            _strings(self.assumptions, "assumptions"),
        )


@dataclass(frozen=True, slots=True)
class SupplierDocumentBindingInput:
    stock_solution_id: str
    scope: str
    supplier: str
    supplier_product: str
    supplier_product_code: str
    grade: str
    document_type: str
    document_version: str
    lot_number: str | None
    effective_on: date
    expires_on: date | None
    source_document_version_id: str
    source_locator: Mapping[str, Any]

    def __post_init__(self) -> None:
        for field in (
            "stock_solution_id",
            "supplier",
            "supplier_product",
            "supplier_product_code",
            "grade",
            "document_version",
            "source_document_version_id",
        ):
            object.__setattr__(
                self,
                field,
                _text(getattr(self, field), field),
            )
        object.__setattr__(
            self,
            "scope",
            _choice(self.scope, "scope", SUPPLIER_DOCUMENT_SCOPES),
        )
        object.__setattr__(
            self,
            "document_type",
            _choice(
                self.document_type,
                "document_type",
                SUPPLIER_REGULATORY_DOCUMENT_TYPES,
            ),
        )
        object.__setattr__(
            self, "lot_number", _optional_text(self.lot_number)
        )
        if self.scope == "SUPPLIER_PRODUCT" and self.lot_number is not None:
            raise RegulatoryAuthorityError(
                "lot_number must be empty for SUPPLIER_PRODUCT scope"
            )
        if self.scope == "SUPPLIER_LOT" and self.lot_number is None:
            raise RegulatoryAuthorityError(
                "lot_number is required for SUPPLIER_LOT scope"
            )
        object.__setattr__(
            self,
            "effective_on",
            _date_value(self.effective_on, "effective_on"),
        )
        object.__setattr__(
            self,
            "expires_on",
            _date_or_none(self.expires_on, "expires_on"),
        )
        _validate_date_range(
            self.effective_on,
            self.expires_on,
            start_field="effective_on",
            end_field="expires_on",
        )
        object.__setattr__(
            self,
            "source_locator",
            _mapping(self.source_locator, "source_locator"),
        )


@dataclass(frozen=True, slots=True)
class RegulatoryCompositionEntryInput:
    position: int
    projection_family: str
    material_id: str | None
    constituent_name: str
    cas_number: str | None
    fraction: float
    fraction_basis: str
    standard_uncertainty: float | None
    source_locator: Mapping[str, Any]

    def __post_init__(self) -> None:
        position = int(self.position)
        if position < 1:
            raise RegulatoryAuthorityError("position must be positive")
        object.__setattr__(self, "position", position)
        projection = _choice(
            self.projection_family,
            "projection_family",
            ("REGULATORY",),
        )
        object.__setattr__(self, "projection_family", projection)
        object.__setattr__(
            self, "material_id", _optional_text(self.material_id)
        )
        object.__setattr__(
            self,
            "constituent_name",
            _text(self.constituent_name, "constituent_name"),
        )
        object.__setattr__(self, "cas_number", _optional_text(self.cas_number))
        fraction = _fraction_or_none(self.fraction, "fraction")
        assert fraction is not None
        object.__setattr__(self, "fraction", fraction)
        basis = _choice(
            self.fraction_basis,
            "fraction_basis",
            ("MASS_FRACTION",),
        )
        object.__setattr__(self, "fraction_basis", basis)
        if self.standard_uncertainty is not None:
            uncertainty = float(self.standard_uncertainty)
            if not isfinite(uncertainty) or uncertainty < 0:
                raise RegulatoryAuthorityError(
                    "standard_uncertainty must be finite and nonnegative"
                )
            object.__setattr__(
                self, "standard_uncertainty", uncertainty
            )
        object.__setattr__(
            self,
            "source_locator",
            _mapping(self.source_locator, "source_locator"),
        )


@dataclass(frozen=True, slots=True)
class RegulatoryCompositionProfileInput:
    stock_solution_id: str
    schema_version: str
    origin: str
    composition_basis: str
    completeness: str
    supplier_document_binding_id: str | None
    entries: tuple[RegulatoryCompositionEntryInput, ...]
    assumptions: tuple[str, ...]
    limitations: tuple[str, ...]
    reviewer_pseudonym: str
    reviewed_at: datetime
    profile_id: str | None = None
    parent_version_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "stock_solution_id",
            _text(self.stock_solution_id, "stock_solution_id"),
        )
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )
        object.__setattr__(
            self,
            "origin",
            _choice(self.origin, "origin", REGULATORY_COMPOSITION_ORIGINS),
        )
        object.__setattr__(
            self,
            "composition_basis",
            _choice(
                self.composition_basis,
                "composition_basis",
                REGULATORY_COMPOSITION_BASES,
            ),
        )
        object.__setattr__(
            self,
            "completeness",
            _choice(
                self.completeness,
                "completeness",
                REGULATORY_COMPOSITION_COMPLETENESS,
            ),
        )
        object.__setattr__(
            self,
            "supplier_document_binding_id",
            _optional_text(self.supplier_document_binding_id),
        )
        entries = tuple(self.entries)
        if any(
            not isinstance(entry, RegulatoryCompositionEntryInput)
            for entry in entries
        ):
            raise RegulatoryAuthorityError(
                "entries must contain regulatory composition inputs"
            )
        positions = tuple(entry.position for entry in entries)
        if positions != tuple(range(1, len(entries) + 1)):
            raise RegulatoryAuthorityError(
                "entries must use contiguous positions starting at one"
            )
        if self.composition_basis == "UNKNOWN":
            if (
                self.completeness != "UNKNOWN"
                or self.supplier_document_binding_id is not None
                or entries
            ):
                raise RegulatoryAuthorityError(
                    "UNKNOWN composition requires no binding or entries"
                )
        elif (
            self.completeness not in {"COMPLETE", "PARTIAL"}
            or self.supplier_document_binding_id is None
            or not entries
        ):
            raise RegulatoryAuthorityError(
                "known composition requires a binding and entries"
            )
        object.__setattr__(self, "entries", entries)
        object.__setattr__(
            self, "assumptions", _strings(self.assumptions, "assumptions")
        )
        object.__setattr__(
            self, "limitations", _strings(self.limitations, "limitations")
        )
        object.__setattr__(
            self,
            "reviewer_pseudonym",
            _text(self.reviewer_pseudonym, "reviewer_pseudonym"),
        )
        object.__setattr__(
            self, "reviewed_at", _aware(self.reviewed_at, "reviewed_at")
        )
        object.__setattr__(self, "profile_id", _optional_text(self.profile_id))
        object.__setattr__(
            self,
            "parent_version_id",
            _optional_text(self.parent_version_id),
        )


@dataclass(frozen=True, slots=True)
class RegulatoryEvaluationInput:
    schema_version: str
    subject_type: str
    subject_id: str
    legacy_assessment_version_id: str | None
    primary_source_version_id: str
    jurisdiction: str
    product_category: str
    use_classification: str
    finished_product_concentration: float
    constituent_basis: str
    natural_material_assumptions: tuple[str, ...]
    effective_on: date
    evaluated_at: datetime
    evaluator_software_version: str
    market_action: str
    market_action_on: date
    current_state_source_version_ids: tuple[str, ...]
    watch_source_version_ids: tuple[str, ...]
    rule_version_ids: tuple[str, ...]
    supplier_binding_ids: tuple[str, ...]
    composition_profile_ids: tuple[str, ...]
    declared_allergen_labels: tuple[str, ...]
    reviewer_pseudonym: str
    reviewed_at: datetime
    snapshot_id: str | None = None
    parent_version_id: str | None = None

    def __post_init__(self) -> None:
        for field in (
            "schema_version",
            "subject_id",
            "primary_source_version_id",
            "jurisdiction",
            "product_category",
            "use_classification",
            "constituent_basis",
            "evaluator_software_version",
            "reviewer_pseudonym",
        ):
            object.__setattr__(
                self,
                field,
                _text(getattr(self, field), field),
            )
        object.__setattr__(
            self,
            "subject_type",
            _choice(
                self.subject_type,
                "subject_type",
                REGULATORY_SUBJECT_TYPES,
            ),
        )
        object.__setattr__(
            self,
            "legacy_assessment_version_id",
            _optional_id(self.legacy_assessment_version_id),
        )
        concentration = _fraction_or_none(
            self.finished_product_concentration,
            "finished_product_concentration",
        )
        assert concentration is not None
        object.__setattr__(
            self,
            "finished_product_concentration",
            concentration,
        )
        if self.constituent_basis != "FINISHED_PRODUCT_MASS_FRACTION":
            raise RegulatoryAuthorityError(
                "constituent_basis must be FINISHED_PRODUCT_MASS_FRACTION"
            )
        object.__setattr__(
            self,
            "natural_material_assumptions",
            tuple(
                sorted(
                    _strings(
                        self.natural_material_assumptions,
                        "natural_material_assumptions",
                    )
                )
            ),
        )
        object.__setattr__(
            self,
            "effective_on",
            _date_value(self.effective_on, "effective_on"),
        )
        object.__setattr__(
            self,
            "evaluated_at",
            _aware(self.evaluated_at, "evaluated_at"),
        )
        object.__setattr__(
            self,
            "market_action",
            _choice(
                self.market_action,
                "market_action",
                REGULATORY_MARKET_ACTIONS,
            ),
        )
        object.__setattr__(
            self,
            "market_action_on",
            _date_value(self.market_action_on, "market_action_on"),
        )
        for field in (
            "current_state_source_version_ids",
            "watch_source_version_ids",
            "rule_version_ids",
            "supplier_binding_ids",
            "composition_profile_ids",
        ):
            object.__setattr__(
                self,
                field,
                _unique_ids(getattr(self, field), field),
            )
        if not self.current_state_source_version_ids:
            raise RegulatoryAuthorityError(
                "current_state_source_version_ids must not be empty"
            )
        if (
            self.primary_source_version_id
            not in self.current_state_source_version_ids
        ):
            raise RegulatoryAuthorityError(
                "primary_source_version_id must be a current-state source"
            )
        overlap = set(self.current_state_source_version_ids).intersection(
            self.watch_source_version_ids
        )
        if overlap:
            raise RegulatoryAuthorityError(
                "current-state and watch source IDs must not overlap"
            )
        object.__setattr__(
            self,
            "declared_allergen_labels",
            tuple(
                sorted(
                    _strings(
                        self.declared_allergen_labels,
                        "declared_allergen_labels",
                    ),
                    key=str.casefold,
                )
            ),
        )
        object.__setattr__(
            self,
            "reviewed_at",
            _aware(self.reviewed_at, "reviewed_at"),
        )
        if self.reviewed_at < self.evaluated_at:
            raise RegulatoryAuthorityError(
                "reviewed_at must be on or after evaluated_at"
            )
        object.__setattr__(
            self,
            "snapshot_id",
            _optional_id(self.snapshot_id),
        )
        object.__setattr__(
            self,
            "parent_version_id",
            _optional_id(self.parent_version_id),
        )
        if self.snapshot_id is None and self.parent_version_id is not None:
            raise RegulatoryAuthorityError(
                "a first snapshot cannot have a parent_version_id"
            )


@dataclass(frozen=True, slots=True)
class _RegulatoryStockDose:
    stock_id: str
    active_concentrate_fraction: float
    lineage: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class _RegulatoryContribution:
    material_id: str | None
    substance_name: str
    cas_number: str | None
    observed_fraction: float
    lineage: Mapping[str, Any]


def _same_identity(left: str | None, right: str) -> bool:
    return str(left or "").strip().casefold() == right.strip().casefold()


def _jurisdiction_applies(rule_jurisdiction: str, declared: str) -> bool:
    return _same_identity(rule_jurisdiction, declared) or _same_identity(
        rule_jurisdiction,
        "GLOBAL",
    )


def _rule_matches_contribution(
    rule: LabRegulatoryRuleVersion,
    contribution: _RegulatoryContribution,
) -> bool:
    if rule.material_id is not None:
        return rule.material_id == contribution.material_id
    if rule.cas_number is not None:
        return _same_identity(contribution.cas_number, rule.cas_number)
    return _same_identity(contribution.substance_name, rule.substance_name)


class LabRegulatoryAuthorityServiceMixin:
    """B6 authority commands using the canonical transaction owner."""

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

    async def register_regulatory_source_version(
        self,
        command: RegulatorySourceInput,
    ) -> LabRegulatorySourceVersion:
        async with self._transaction():
            source = await self.repository.get_source_document_version(
                command.official_source_document_version_id
            )
            if source is None:
                raise RegulatoryAuthorityConflictError(
                    "REGULATORY_SOURCE_DOCUMENT_NOT_FOUND",
                    "The B1 official source document version was not found.",
                )
            if source.source_type not in OFFICIAL_SOURCE_TYPES:
                raise RegulatoryAuthorityConflictError(
                    "REGULATORY_SOURCE_TYPE_INVALID",
                    "Regulatory authority requires an official or standards source.",
                )
            if not await self.is_accepted_for_scoped_use(
                "SOURCE_VERSION",
                source.id,
                required_scope="regulatory_authority",
            ):
                raise RegulatoryAuthorityConflictError(
                    "REGULATORY_SOURCE_SCOPE_NOT_ACCEPTED",
                    "The official source is not accepted for regulatory authority.",
                )
            if (
                command.status == "FUTURE_EFFECTIVE"
                and (
                    command.effective_from is None
                    or command.effective_from <= command.checked_at.date()
                )
            ):
                raise RegulatoryAuthorityConflictError(
                    "FUTURE_SOURCE_DATE_INVALID",
                    "A future-effective source requires a future effective date.",
                )
            if (
                command.supersedes_source_version_id is not None
                and command.status in NONFINAL_SOURCE_STATUSES
            ):
                raise RegulatoryAuthorityConflictError(
                    "NONFINAL_SOURCE_CANNOT_SUPERSEDE",
                    "Draft, consultation, and watchlist sources cannot supersede.",
                )

            if command.authority_id is None:
                if command.parent_version_id is not None:
                    raise RegulatoryAuthorityConflictError(
                        "REGULATORY_SOURCE_PARENT_UNEXPECTED",
                        "A first source revision cannot have a parent.",
                    )
                authority_id = str(uuid4())
                revision_number = 1
                parent = None
            else:
                authority_id = command.authority_id
                latest = await self.repository.latest_regulatory_source_version(
                    authority_id
                )
                if latest is None:
                    raise RegulatoryAuthorityConflictError(
                        "REGULATORY_SOURCE_AUTHORITY_NOT_FOUND",
                        "The source authority chain was not found.",
                    )
                if command.parent_version_id != latest.id:
                    raise RegulatoryAuthorityConflictError(
                        "REGULATORY_SOURCE_PARENT_NOT_LATEST",
                        "The source parent must be the latest authority revision.",
                    )
                revision_number = latest.revision_number + 1
                parent = latest

            superseded = None
            if command.supersedes_source_version_id is not None:
                superseded = await self.repository.get_regulatory_source_version(
                    command.supersedes_source_version_id
                )
                if (
                    superseded is None
                    or superseded.authority_id != authority_id
                    or superseded.status not in FINAL_SOURCE_STATUSES
                ):
                    raise RegulatoryAuthorityConflictError(
                        "REGULATORY_SUPERSESSION_INVALID",
                        "Supersession must target a final source in the same authority.",
                    )

            payload = {
                "schema": "lab-regulatory-source-v1",
                "authority_id": authority_id,
                "revision_number": revision_number,
                "parent_version_id": parent.id if parent else None,
                "parent_sha256": parent.content_sha256 if parent else None,
                "authority_family": command.authority_family,
                "identifier": command.identifier,
                "published_version": command.published_version,
                "jurisdiction": command.jurisdiction,
                "status": command.status,
                "notified_on": (
                    command.notified_on.isoformat()
                    if command.notified_on is not None
                    else None
                ),
                "effective_from": (
                    command.effective_from.isoformat()
                    if command.effective_from is not None
                    else None
                ),
                "effective_through": (
                    command.effective_through.isoformat()
                    if command.effective_through is not None
                    else None
                ),
                "checked_at": command.checked_at.isoformat(),
                "supersedes_source_version_id": (
                    superseded.id if superseded is not None else None
                ),
                "official_source_document_version_id": source.id,
                "official_source_record_sha256": source.record_sha256,
                "official_source_sha256": source.artifact_sha256,
                "source_locator": command.source_locator,
                "notes": command.notes,
            }
            return await self.repository.add(
                LabRegulatorySourceVersion(
                    authority_id=authority_id,
                    revision_number=revision_number,
                    parent_version_id=parent.id if parent else None,
                    schema_version=command.schema_version,
                    authority_family=command.authority_family,
                    identifier=command.identifier,
                    published_version=command.published_version,
                    jurisdiction=command.jurisdiction,
                    status=command.status,
                    notified_on=command.notified_on,
                    effective_from=command.effective_from,
                    effective_through=command.effective_through,
                    checked_at=command.checked_at,
                    supersedes_source_version_id=(
                        superseded.id if superseded is not None else None
                    ),
                    official_source_document_version_id=source.id,
                    source_locator_json=dict(command.source_locator),
                    official_source_sha256=source.artifact_sha256,
                    notes_json=dict(command.notes),
                    content_sha256=canonical_json_sha256(payload),
                )
            )

    async def is_regulatory_source_selectable(
        self,
        source_version_id: str,
        *,
        evaluated_at: datetime,
    ) -> bool:
        evaluated = _aware(evaluated_at, "evaluated_at")
        source = await self.repository.get_regulatory_source_version(
            _text(source_version_id, "source_version_id")
        )
        if source is None or source.status not in FINAL_SOURCE_STATUSES:
            return False
        if source.checked_at.date() != evaluated.date():
            return False
        return (
            await self.repository.superseding_regulatory_source(source.id)
            is None
        )

    async def register_regulatory_rule_version(
        self,
        command: RegulatoryRuleInput,
    ) -> LabRegulatoryRuleVersion:
        async with self._transaction():
            source = await self.repository.get_regulatory_source_version(
                command.regulatory_source_version_id
            )
            if source is None:
                raise RegulatoryAuthorityConflictError(
                    "RULE_SOURCE_NOT_FOUND",
                    "The regulatory source version was not found.",
                )
            if (
                await self.repository.superseding_regulatory_source(source.id)
                is not None
            ):
                raise RegulatoryAuthorityConflictError(
                    "RULE_SOURCE_SUPERSEDED",
                    "New rules cannot bind to a superseded source version.",
                )
            if not _same_identity(source.jurisdiction, command.jurisdiction):
                raise RegulatoryAuthorityConflictError(
                    "RULE_SOURCE_JURISDICTION_MISMATCH",
                    "Rule and source jurisdictions must match.",
                )
            if command.material_id is not None and (
                await self.repository.get_material(command.material_id) is None
            ):
                raise RegulatoryAuthorityConflictError(
                    "RULE_MATERIAL_NOT_FOUND",
                    "The canonical rule material was not found.",
                )

            if command.rule_id is None:
                if command.parent_version_id is not None:
                    raise RegulatoryAuthorityConflictError(
                        "REGULATORY_RULE_PARENT_UNEXPECTED",
                        "A first rule revision cannot have a parent.",
                    )
                rule_id = str(uuid4())
                revision_number = 1
                parent = None
            else:
                latest = await self.repository.latest_regulatory_rule_version(
                    command.rule_id
                )
                if latest is None:
                    if command.parent_version_id is not None:
                        raise RegulatoryAuthorityConflictError(
                            "REGULATORY_RULE_PARENT_NOT_FOUND",
                            "A new rule identity cannot have a parent.",
                        )
                    rule_id = command.rule_id
                    revision_number = 1
                    parent = None
                else:
                    if command.parent_version_id != latest.id:
                        raise RegulatoryAuthorityConflictError(
                            "REGULATORY_RULE_PARENT_NOT_LATEST",
                            "The rule parent must be the latest revision.",
                        )
                    rule_id = latest.rule_id
                    revision_number = latest.revision_number + 1
                    parent = latest

            payload = {
                "schema": "lab-regulatory-rule-v1",
                "rule_id": rule_id,
                "revision_number": revision_number,
                "parent_version_id": parent.id if parent else None,
                "parent_sha256": parent.content_sha256 if parent else None,
                "regulatory_source_version_id": source.id,
                "regulatory_source_sha256": source.content_sha256,
                "rule_family": command.rule_family,
                "rule_identifier": command.rule_identifier,
                "material_id": command.material_id,
                "substance_name": command.substance_name,
                "cas_number": command.cas_number,
                "jurisdiction": command.jurisdiction,
                "product_category": command.product_category,
                "use_classification": command.use_classification,
                "concentration_basis": command.concentration_basis,
                "rule_kind": command.rule_kind,
                "threshold_fraction": command.threshold_fraction,
                "maximum_fraction": command.maximum_fraction,
                "declaration_wording": command.declaration_wording,
                "effective_from": (
                    command.effective_from.isoformat()
                    if command.effective_from is not None
                    else None
                ),
                "effective_through": (
                    command.effective_through.isoformat()
                    if command.effective_through is not None
                    else None
                ),
                "placement_transition_end": (
                    command.placement_transition_end.isoformat()
                    if command.placement_transition_end is not None
                    else None
                ),
                "availability_transition_end": (
                    command.availability_transition_end.isoformat()
                    if command.availability_transition_end is not None
                    else None
                ),
                "transition_conditions": command.transition_conditions,
                "assumptions": command.assumptions,
            }
            return await self.repository.add(
                LabRegulatoryRuleVersion(
                    rule_id=rule_id,
                    revision_number=revision_number,
                    parent_version_id=parent.id if parent else None,
                    schema_version=command.schema_version,
                    regulatory_source_version_id=source.id,
                    rule_family=command.rule_family,
                    rule_identifier=command.rule_identifier,
                    material_id=command.material_id,
                    substance_name=command.substance_name,
                    cas_number=command.cas_number,
                    jurisdiction=command.jurisdiction,
                    product_category=command.product_category,
                    use_classification=command.use_classification,
                    concentration_basis=command.concentration_basis,
                    rule_kind=command.rule_kind,
                    threshold_fraction=command.threshold_fraction,
                    maximum_fraction=command.maximum_fraction,
                    declaration_wording=command.declaration_wording,
                    effective_from=command.effective_from,
                    effective_through=command.effective_through,
                    placement_transition_end=command.placement_transition_end,
                    availability_transition_end=(
                        command.availability_transition_end
                    ),
                    transition_conditions_json=dict(
                        command.transition_conditions
                    ),
                    assumptions_json=list(command.assumptions),
                    content_sha256=canonical_json_sha256(payload),
                )
            )

    async def is_regulatory_rule_enforceable(
        self,
        rule_version_id: str,
        *,
        evaluated_at: datetime,
        market_action: str,
        market_action_on: date,
    ) -> bool:
        _aware(evaluated_at, "evaluated_at")
        action = _choice(
            market_action,
            "market_action",
            REGULATORY_MARKET_ACTIONS,
        )
        action_on = _date_value(market_action_on, "market_action_on")
        rule = await self.repository.get_regulatory_rule_version(
            _text(rule_version_id, "rule_version_id")
        )
        if rule is None:
            return False
        source = await self.repository.get_regulatory_source_version(
            rule.regulatory_source_version_id
        )
        if source is None or source.status not in FINAL_SOURCE_STATUSES:
            return False
        if (
            await self.repository.superseding_regulatory_source(source.id)
            is not None
        ):
            return False
        if source.effective_from is not None and action_on < source.effective_from:
            return False
        if (
            source.effective_through is not None
            and action_on > source.effective_through
        ):
            return False
        if rule.effective_from is not None and action_on < rule.effective_from:
            return False
        if rule.effective_through is not None and action_on > rule.effective_through:
            return False
        if (
            action == "PLACE_ON_MARKET"
            and rule.placement_transition_end is not None
            and action_on <= rule.placement_transition_end
        ):
            return False
        if (
            action == "MAKE_AVAILABLE"
            and rule.availability_transition_end is not None
            and action_on <= rule.availability_transition_end
        ):
            return False
        return True

    async def bind_supplier_regulatory_document(
        self,
        command: SupplierDocumentBindingInput,
    ) -> LabSupplierDocumentBinding:
        async with self._transaction():
            stock = await self.repository.get_stock(command.stock_solution_id)
            if stock is None:
                raise RegulatoryAuthorityConflictError(
                    "SUPPLIER_STOCK_NOT_FOUND",
                    "The exact stock solution was not found.",
                )
            source = await self.repository.get_source_document_version(
                command.source_document_version_id
            )
            if source is None:
                raise RegulatoryAuthorityConflictError(
                    "SUPPLIER_DOCUMENT_SOURCE_NOT_FOUND",
                    "The B1 supplier document version was not found.",
                )
            if source.source_type != command.document_type:
                raise RegulatoryAuthorityConflictError(
                    "SUPPLIER_DOCUMENT_TYPE_MISMATCH",
                    "The declared document type does not match the B1 source.",
                )
            if not await self.is_accepted_for_scoped_use(
                "SOURCE_VERSION",
                source.id,
                required_scope="supplier_regulatory_document",
            ):
                raise RegulatoryAuthorityConflictError(
                    "SUPPLIER_DOCUMENT_SCOPE_NOT_ACCEPTED",
                    "The supplier document is not accepted for regulatory use.",
                )
            if not _same_identity(
                source.edition_or_amendment,
                command.document_version,
            ):
                raise RegulatoryAuthorityConflictError(
                    "SUPPLIER_DOCUMENT_VERSION_MISMATCH",
                    "The declared version does not match the exact B1 source.",
                )

            source_identity = dict(stock.source_json or {})
            expected_identity = {
                "supplier": stock.supplier,
                "supplier_product": source_identity.get("supplier_product"),
                "supplier_product_code": source_identity.get(
                    "supplier_product_code"
                ),
                "grade": source_identity.get("grade"),
            }
            declared_identity = {
                "supplier": command.supplier,
                "supplier_product": command.supplier_product,
                "supplier_product_code": command.supplier_product_code,
                "grade": command.grade,
            }
            if any(
                not _same_identity(expected_identity[key], declared_identity[key])
                for key in declared_identity
            ):
                raise RegulatoryAuthorityConflictError(
                    "SUPPLIER_IDENTITY_MISMATCH",
                    "Supplier product, code, and grade must match the stock.",
                )
            if (
                command.scope == "SUPPLIER_LOT"
                and not _same_identity(stock.lot_number, command.lot_number or "")
            ):
                raise RegulatoryAuthorityConflictError(
                    "SUPPLIER_LOT_MISMATCH",
                    "The supplier document lot must match the stock lot.",
                )

            normalized_identity: dict[str, str | None] = {
                key: str(value).strip().casefold()
                for key, value in declared_identity.items()
            }
            normalized_identity["lot_number"] = (
                command.lot_number.casefold()
                if command.lot_number is not None
                else None
            )
            normalized_identity["scope"] = command.scope
            identity_sha256 = canonical_json_sha256(normalized_identity)
            payload = {
                "schema": "lab-supplier-document-binding-v1",
                "stock_solution_id": stock.id,
                "stock_material_id": stock.material_id,
                "scope": command.scope,
                "identity": normalized_identity,
                "document_type": command.document_type,
                "document_version": command.document_version,
                "effective_on": command.effective_on.isoformat(),
                "expires_on": (
                    command.expires_on.isoformat()
                    if command.expires_on is not None
                    else None
                ),
                "source_document_version_id": source.id,
                "source_record_sha256": source.record_sha256,
                "source_artifact_sha256": source.artifact_sha256,
                "source_locator": command.source_locator,
            }
            return await self.repository.add(
                LabSupplierDocumentBinding(
                    stock_solution_id=stock.id,
                    scope=command.scope,
                    supplier=command.supplier,
                    supplier_product=command.supplier_product,
                    supplier_product_code=command.supplier_product_code,
                    grade=command.grade,
                    document_type=command.document_type,
                    document_version=command.document_version,
                    lot_number=command.lot_number,
                    effective_on=command.effective_on,
                    expires_on=command.expires_on,
                    source_document_version_id=source.id,
                    source_locator_json=dict(command.source_locator),
                    source_artifact_sha256=source.artifact_sha256,
                    supplier_identity_sha256=identity_sha256,
                    content_sha256=canonical_json_sha256(payload),
                )
            )

    async def record_regulatory_composition_profile(
        self,
        command: RegulatoryCompositionProfileInput,
    ) -> LabRegulatoryCompositionProfile:
        async with self._transaction():
            stock = await self.repository.get_stock(command.stock_solution_id)
            if stock is None:
                raise RegulatoryAuthorityConflictError(
                    "COMPOSITION_STOCK_NOT_FOUND",
                    "The exact composition stock was not found.",
                )
            declared_origin = str(
                (stock.source_json or {}).get("origin") or ""
            ).strip()
            if not _same_identity(declared_origin, command.origin):
                raise RegulatoryAuthorityConflictError(
                    "COMPOSITION_ORIGIN_MISMATCH",
                    "Composition origin must match the exact stock identity.",
                )

            binding = None
            if command.supplier_document_binding_id is not None:
                binding = await self.repository.get_supplier_document_binding(
                    command.supplier_document_binding_id
                )
                if binding is None or binding.stock_solution_id != stock.id:
                    raise RegulatoryAuthorityConflictError(
                        "COMPOSITION_DOCUMENT_BINDING_INVALID",
                        "Composition document must bind the exact stock.",
                    )
                if binding.document_type not in {
                    "SUPPLIER_COA",
                    "SUPPLIER_SPECIFICATION",
                    "SUPPLIER_ALLERGEN_DECLARATION",
                }:
                    raise RegulatoryAuthorityConflictError(
                        "COMPOSITION_DOCUMENT_TYPE_INVALID",
                        "Composition requires a COA, specification, or declaration.",
                    )
                review_date = command.reviewed_at.date()
                if review_date < binding.effective_on or (
                    binding.expires_on is not None
                    and review_date > binding.expires_on
                ):
                    raise RegulatoryAuthorityConflictError(
                        "COMPOSITION_DOCUMENT_NOT_CURRENT",
                        "Composition document is not current at review.",
                    )

            if command.composition_basis == "LOT_SPECIFIC" and (
                binding is None or binding.scope != "SUPPLIER_LOT"
            ):
                raise RegulatoryAuthorityConflictError(
                    "LOT_PROFILE_DOCUMENT_SCOPE_INVALID",
                    "Lot-specific composition requires a lot-scoped document.",
                )
            if command.composition_basis == "DOCUMENTED_PROXY":
                if binding is None or binding.scope != "SUPPLIER_PRODUCT":
                    raise RegulatoryAuthorityConflictError(
                        "PROXY_DOCUMENT_SCOPE_INVALID",
                        "A documented proxy requires a product-scoped document.",
                    )
                if not command.assumptions:
                    raise RegulatoryAuthorityConflictError(
                        "DOCUMENTED_PROXY_ASSUMPTIONS_REQUIRED",
                        "A documented proxy requires explicit assumptions.",
                    )
            for entry in command.entries:
                if entry.material_id is not None and (
                    await self.repository.get_material(entry.material_id) is None
                ):
                    raise RegulatoryAuthorityConflictError(
                        "COMPOSITION_ENTRY_MATERIAL_NOT_FOUND",
                        "A composition entry material was not found.",
                    )

            if command.profile_id is None:
                if command.parent_version_id is not None:
                    raise RegulatoryAuthorityConflictError(
                        "COMPOSITION_PARENT_UNEXPECTED",
                        "A first composition profile cannot have a parent.",
                    )
                profile_id = str(uuid4())
                version_number = 1
                parent = None
            else:
                latest = (
                    await self.repository.latest_regulatory_composition_profile(
                        command.profile_id
                    )
                )
                if latest is None:
                    raise RegulatoryAuthorityConflictError(
                        "COMPOSITION_PROFILE_NOT_FOUND",
                        "The composition profile chain was not found.",
                    )
                if (
                    command.parent_version_id != latest.id
                    or latest.stock_solution_id != stock.id
                ):
                    raise RegulatoryAuthorityConflictError(
                        "COMPOSITION_PARENT_NOT_LATEST",
                        "The parent must be the latest exact-stock profile.",
                    )
                profile_id = latest.profile_id
                version_number = latest.version_number + 1
                parent = latest

            entry_payloads = [
                {
                    "position": entry.position,
                    "projection_family": entry.projection_family,
                    "material_id": entry.material_id,
                    "constituent_name": entry.constituent_name,
                    "cas_number": entry.cas_number,
                    "fraction": entry.fraction,
                    "fraction_basis": entry.fraction_basis,
                    "standard_uncertainty": entry.standard_uncertainty,
                    "source_locator": entry.source_locator,
                }
                for entry in command.entries
            ]
            payload = {
                "schema": "lab-regulatory-composition-v1",
                "profile_id": profile_id,
                "version_number": version_number,
                "parent_version_id": parent.id if parent else None,
                "parent_sha256": parent.content_sha256 if parent else None,
                "stock_solution_id": stock.id,
                "stock_material_id": stock.material_id,
                "origin": command.origin,
                "composition_basis": command.composition_basis,
                "completeness": command.completeness,
                "supplier_document_binding_id": (
                    binding.id if binding is not None else None
                ),
                "supplier_document_sha256": (
                    binding.content_sha256 if binding is not None else None
                ),
                "entries": entry_payloads,
                "assumptions": command.assumptions,
                "limitations": command.limitations,
                "reviewer_pseudonym": command.reviewer_pseudonym,
                "reviewed_at": command.reviewed_at.isoformat(),
            }
            profile = await self.repository.add(
                LabRegulatoryCompositionProfile(
                    profile_id=profile_id,
                    version_number=version_number,
                    parent_version_id=parent.id if parent else None,
                    stock_solution_id=stock.id,
                    schema_version=command.schema_version,
                    origin=command.origin,
                    composition_basis=command.composition_basis,
                    completeness=command.completeness,
                    supplier_document_binding_id=(
                        binding.id if binding is not None else None
                    ),
                    assumptions_json=list(command.assumptions),
                    limitations_json=list(command.limitations),
                    reviewer_pseudonym=command.reviewer_pseudonym,
                    reviewed_at=command.reviewed_at,
                    content_sha256=canonical_json_sha256(payload),
                )
            )
            for entry, entry_payload in zip(
                command.entries,
                entry_payloads,
                strict=True,
            ):
                await self.repository.add(
                    LabRegulatoryCompositionEntry(
                        composition_profile_id=profile.id,
                        position=entry.position,
                        projection_family=entry.projection_family,
                        material_id=entry.material_id,
                        constituent_name=entry.constituent_name,
                        cas_number=entry.cas_number,
                        fraction=entry.fraction,
                        fraction_basis=entry.fraction_basis,
                        standard_uncertainty=entry.standard_uncertainty,
                        source_locator_json=dict(entry.source_locator),
                        content_sha256=canonical_json_sha256(
                            {
                                "schema": "lab-regulatory-composition-entry-v1",
                                "profile_content_sha256": profile.content_sha256,
                                **entry_payload,
                            }
                        ),
                    )
                )
            return profile

    async def is_regulatory_composition_complete(
        self,
        profile_version_id: str,
    ) -> bool:
        profile = await self.repository.get_regulatory_composition_profile(
            _text(profile_version_id, "profile_version_id")
        )
        if (
            profile is None
            or profile.completeness != "COMPLETE"
            or profile.composition_basis == "UNKNOWN"
        ):
            return False
        entries = await self.repository.regulatory_composition_entries(
            profile.id
        )
        return bool(entries) and all(
            entry.projection_family == "REGULATORY" for entry in entries
        )

    async def _resolve_regulatory_subject(
        self,
        command: RegulatoryEvaluationInput,
    ) -> tuple[tuple[_RegulatoryStockDose, ...], str]:
        if command.subject_type == "FORMULA_VERSION":
            formula = await self.repository.get_formula_version(
                command.subject_id
            )
            if formula is None:
                raise RegulatoryAuthorityConflictError(
                    "REGULATORY_FORMULA_NOT_FOUND",
                    "The exact formula version was not found.",
                )
            if (
                formula.concentration_fraction is not None
                and abs(
                    float(formula.concentration_fraction)
                    - command.finished_product_concentration
                )
                > 1e-12
            ):
                raise RegulatoryAuthorityConflictError(
                    "FINISHED_CONCENTRATION_MISMATCH",
                    "The declared concentration differs from the formula version.",
                )
            if (
                formula.concentration_basis is not None
                and not _same_identity(
                    formula.concentration_basis,
                    "mass_fraction",
                )
            ):
                raise RegulatoryAuthorityConflictError(
                    "FORMULA_CONCENTRATION_BASIS_UNSUPPORTED",
                    "Formula regulatory evaluation requires mass fraction.",
                )
            components = await self.repository.formula_components(formula.id)
            if not components:
                raise RegulatoryAuthorityConflictError(
                    "REGULATORY_SUBJECT_EMPTY",
                    "The formula version has no stock components.",
                )
            total_raw = sum(float(item.requested_mass_g) for item in components)
            if not isfinite(total_raw) or total_raw <= 0:
                raise RegulatoryAuthorityConflictError(
                    "REGULATORY_TOTAL_QUANTITY_INVALID",
                    "The formula total raw quantity must be finite and positive.",
                )
            doses: list[_RegulatoryStockDose] = []
            component_payloads: list[dict[str, Any]] = []
            for component in components:
                if component.unit not in {None, "g"}:
                    raise RegulatoryAuthorityConflictError(
                        "FORMULA_COMPONENT_BASIS_UNSUPPORTED",
                        "Formula regulatory evaluation requires gram quantities.",
                    )
                stock = await self.repository.get_stock(
                    component.stock_solution_id
                )
                if stock is None:
                    raise RegulatoryAuthorityConflictError(
                        "REGULATORY_STOCK_NOT_FOUND",
                        "A formula stock solution was not found.",
                    )
                active_fraction = float(stock.active_fraction)
                if (
                    not isfinite(active_fraction)
                    or active_fraction <= 0
                    or active_fraction > 1
                ):
                    raise RegulatoryAuthorityConflictError(
                        "STOCK_ACTIVE_FRACTION_INVALID",
                        "A stock active fraction is outside the supported range.",
                    )
                raw_fraction = float(component.requested_mass_g) / total_raw
                lineage = {
                    "subject_type": command.subject_type,
                    "subject_id": formula.id,
                    "line_id": component.id,
                    "position": component.position,
                    "stock_solution_id": stock.id,
                    "raw_fraction": raw_fraction,
                    "stock_active_fraction": active_fraction,
                }
                doses.append(
                    _RegulatoryStockDose(
                        stock_id=stock.id,
                        active_concentrate_fraction=(
                            raw_fraction * active_fraction
                        ),
                        lineage=lineage,
                    )
                )
                component_payloads.append(
                    {
                        **lineage,
                        "requested_mass_g": component.requested_mass_g,
                    }
                )
            subject_hash = canonical_json_sha256(
                {
                    "schema": "b6-formula-evaluation-subject-v1",
                    "formula_version_id": formula.id,
                    "formula_id": formula.formula_id,
                    "version_number": formula.version_number,
                    "brief": formula.brief_json,
                    "constraints": formula.constraints_json,
                    "concentration_fraction": formula.concentration_fraction,
                    "concentration_basis": formula.concentration_basis,
                    "source": formula.source_json,
                    "components": component_payloads,
                }
            )
            return tuple(doses), subject_hash

        plan = await self.repository.get_build_plan_version(command.subject_id)
        if plan is None:
            raise RegulatoryAuthorityConflictError(
                "REGULATORY_BUILD_PLAN_NOT_FOUND",
                "The exact build-plan version was not found.",
            )
        lines = await self.repository.build_plan_lines(plan.id)
        if not lines:
            raise RegulatoryAuthorityConflictError(
                "REGULATORY_SUBJECT_EMPTY",
                "The build-plan version has no stock lines.",
            )
        total_raw = sum(float(item.planned_raw_quantity) for item in lines)
        if not isfinite(total_raw) or total_raw <= 0:
            raise RegulatoryAuthorityConflictError(
                "REGULATORY_TOTAL_QUANTITY_INVALID",
                "The build-plan total raw quantity must be finite and positive.",
            )
        doses = []
        for line in lines:
            if line.unit != "g" or not _same_identity(
                line.concentration_basis,
                "mass_fraction",
            ):
                raise RegulatoryAuthorityConflictError(
                    "BUILD_PLAN_BASIS_UNSUPPORTED",
                    "Build-plan regulatory evaluation requires mass quantities.",
                )
            stock = await self.repository.get_stock(line.stock_solution_id)
            if stock is None:
                raise RegulatoryAuthorityConflictError(
                    "REGULATORY_STOCK_NOT_FOUND",
                    "A build-plan stock solution was not found.",
                )
            active_fraction = float(stock.active_fraction)
            planned_raw = float(line.planned_raw_quantity)
            planned_active = float(line.planned_active_quantity)
            if (
                not isfinite(active_fraction)
                or active_fraction <= 0
                or active_fraction > 1
                or not isfinite(planned_raw)
                or not isfinite(planned_active)
                or planned_raw <= 0
                or planned_active < 0
                or planned_active > planned_raw
            ):
                raise RegulatoryAuthorityConflictError(
                    "BUILD_PLAN_QUANTITY_INVALID",
                    "A build-plan regulatory quantity is invalid.",
                )
            if abs(planned_active - planned_raw * active_fraction) > 1e-9:
                raise RegulatoryAuthorityConflictError(
                    "BUILD_PLAN_ACTIVE_FRACTION_MISMATCH",
                    "Planned active quantity differs from the exact stock fraction.",
                )
            doses.append(
                _RegulatoryStockDose(
                    stock_id=stock.id,
                    active_concentrate_fraction=planned_active / total_raw,
                    lineage={
                        "subject_type": command.subject_type,
                        "subject_id": plan.id,
                        "line_id": line.id,
                        "position": line.position,
                        "stock_solution_id": stock.id,
                        "planned_raw_quantity": planned_raw,
                        "planned_active_quantity": planned_active,
                        "total_planned_raw_quantity": total_raw,
                    },
                )
            )
        return tuple(doses), plan.content_sha256

    async def evaluate_regulatory_snapshot(
        self,
        command: RegulatoryEvaluationInput,
    ) -> LabRegulatorySnapshotVersion:
        """Evaluate one exact immutable formula or build-plan regulatory graph."""

        async with self._transaction():
            doses, subject_hash = await self._resolve_regulatory_subject(command)
            evaluation_date = _utc_date(command.evaluated_at)
            unresolved: set[str] = set()
            result_reasons: set[str] = set()
            upstream_hashes: dict[str, str] = {
                f"subject:{command.subject_type}:{command.subject_id}": (
                    subject_hash
                )
            }

            legacy = None
            if command.legacy_assessment_version_id is not None:
                legacy = (
                    await self.repository.get_regulatory_assessment_version(
                        command.legacy_assessment_version_id
                    )
                )
                if (
                    legacy is None
                    or legacy.subject_type != command.subject_type
                    or legacy.subject_id != command.subject_id
                ):
                    raise RegulatoryAuthorityConflictError(
                        "LEGACY_ASSESSMENT_SCOPE_INVALID",
                        "The A2 assessment does not match the exact B6 subject.",
                    )
                upstream_hashes[f"legacy_assessment:{legacy.id}"] = (
                    legacy.content_sha256
                )

            all_source_ids = (
                command.current_state_source_version_ids
                + command.watch_source_version_ids
            )
            sources: dict[str, LabRegulatorySourceVersion] = {}
            current_source_validity: dict[str, bool] = {}
            for source_id in all_source_ids:
                source = (
                    await self.repository.get_regulatory_source_version(
                        source_id
                    )
                )
                if source is None:
                    raise RegulatoryAuthorityConflictError(
                        "REGULATORY_SOURCE_NOT_FOUND",
                        "A selected B6 regulatory source was not found.",
                    )
                sources[source.id] = source
                upstream_hashes[f"source:{source.id}"] = source.content_sha256

            for source_id in command.current_state_source_version_ids:
                source = sources[source_id]
                valid = True
                if source.status not in FINAL_SOURCE_STATUSES:
                    unresolved.add("CURRENT_SOURCE_STATUS_INVALID")
                    valid = False
                if _utc_date(source.checked_at) != evaluation_date:
                    unresolved.add("CURRENT_SOURCE_CHECK_NOT_SAME_DAY")
                    valid = False
                if not _jurisdiction_applies(
                    source.jurisdiction,
                    command.jurisdiction,
                ):
                    unresolved.add("CURRENT_SOURCE_JURISDICTION_MISMATCH")
                    valid = False
                if (
                    await self.repository.superseding_regulatory_source(
                        source.id
                    )
                    is not None
                ):
                    unresolved.add("CURRENT_SOURCE_SUPERSEDED")
                    valid = False
                current_source_validity[source.id] = valid

            for source_id in command.watch_source_version_ids:
                source = sources[source_id]
                if _utc_date(source.checked_at) != evaluation_date:
                    unresolved.add("WATCH_SOURCE_CHECK_NOT_SAME_DAY")
                if source.status not in (
                    *NONFINAL_SOURCE_STATUSES,
                    "FUTURE_EFFECTIVE",
                    "SUPERSEDED",
                ):
                    unresolved.add("WATCH_SOURCE_STATUS_INVALID")

            primary = sources[command.primary_source_version_id]
            if not current_source_validity.get(primary.id, False):
                unresolved.add("PRIMARY_SOURCE_NOT_SELECTABLE")

            bindings: dict[str, LabSupplierDocumentBinding] = {}
            bindings_by_stock: dict[
                str,
                list[LabSupplierDocumentBinding],
            ] = {}
            for binding_id in command.supplier_binding_ids:
                binding = (
                    await self.repository.get_supplier_document_binding(
                        binding_id
                    )
                )
                if binding is None:
                    raise RegulatoryAuthorityConflictError(
                        "SUPPLIER_BINDING_NOT_FOUND",
                        "A selected supplier binding was not found.",
                    )
                bindings[binding.id] = binding
                bindings_by_stock.setdefault(
                    binding.stock_solution_id,
                    [],
                ).append(binding)
                upstream_hashes[f"supplier_binding:{binding.id}"] = (
                    binding.content_sha256
                )

            profiles: dict[str, LabRegulatoryCompositionProfile] = {}
            profiles_by_stock: dict[
                str,
                LabRegulatoryCompositionProfile,
            ] = {}
            for profile_id in command.composition_profile_ids:
                profile = (
                    await self.repository.get_regulatory_composition_profile(
                        profile_id
                    )
                )
                if profile is None:
                    raise RegulatoryAuthorityConflictError(
                        "COMPOSITION_PROFILE_NOT_FOUND",
                        "A selected composition profile was not found.",
                    )
                if profile.stock_solution_id in profiles_by_stock:
                    raise RegulatoryAuthorityConflictError(
                        "COMPOSITION_PROFILE_AMBIGUOUS",
                        "Only one composition profile may be selected per stock.",
                    )
                profiles[profile.id] = profile
                profiles_by_stock[profile.stock_solution_id] = profile
                upstream_hashes[f"composition_profile:{profile.id}"] = (
                    profile.content_sha256
                )

            subject_stock_ids = {dose.stock_id for dose in doses}
            if any(
                binding.stock_solution_id not in subject_stock_ids
                for binding in bindings.values()
            ):
                raise RegulatoryAuthorityConflictError(
                    "SUPPLIER_BINDING_OUT_OF_SCOPE",
                    "A supplier binding does not belong to the exact subject.",
                )
            if any(
                profile.stock_solution_id not in subject_stock_ids
                for profile in profiles.values()
            ):
                raise RegulatoryAuthorityConflictError(
                    "COMPOSITION_PROFILE_OUT_OF_SCOPE",
                    "A composition profile does not belong to the exact subject.",
                )

            contributions: list[_RegulatoryContribution] = []
            unknown_natural_composition = False
            required_document_types = {
                "SUPPLIER_SDS",
                "SUPPLIER_IFRA_CERTIFICATE",
                "SUPPLIER_ALLERGEN_DECLARATION",
            }
            for dose in doses:
                stock = await self.repository.get_stock(dose.stock_id)
                if stock is None:
                    raise RegulatoryAuthorityConflictError(
                        "REGULATORY_STOCK_NOT_FOUND",
                        "A subject stock solution was not found.",
                    )
                material = await self.repository.get_material(
                    stock.material_id
                )
                if material is None:
                    raise RegulatoryAuthorityConflictError(
                        "REGULATORY_MATERIAL_NOT_FOUND",
                        "A subject material was not found.",
                    )
                stock_source = dict(stock.source_json or {})
                stock_payload = {
                    "material_id": stock.material_id,
                    "supplier": stock.supplier,
                    "lot_number": stock.lot_number,
                    "active_fraction": stock.active_fraction,
                    "fraction_basis": stock.fraction_basis,
                    "source": stock_source,
                }
                upstream_hashes[f"stock:{stock.id}"] = canonical_json_sha256(
                    stock_payload
                )

                valid_types: set[str] = set()
                for binding in bindings_by_stock.get(stock.id, []):
                    identity_matches = all(
                        (
                            _same_identity(binding.supplier, stock.supplier or ""),
                            _same_identity(
                                binding.supplier_product,
                                str(stock_source.get("supplier_product") or ""),
                            ),
                            _same_identity(
                                binding.supplier_product_code,
                                str(
                                    stock_source.get("supplier_product_code")
                                    or ""
                                ),
                            ),
                            _same_identity(
                                binding.grade,
                                str(stock_source.get("grade") or ""),
                            ),
                        )
                    )
                    lot_matches = (
                        binding.scope != "SUPPLIER_LOT"
                        or _same_identity(
                            binding.lot_number,
                            stock.lot_number or "",
                        )
                    )
                    current = (
                        binding.effective_on <= evaluation_date
                        and (
                            binding.expires_on is None
                            or evaluation_date <= binding.expires_on
                        )
                    )
                    if identity_matches and lot_matches and current:
                        valid_types.add(binding.document_type)
                    else:
                        unresolved.add("SUPPLIER_BINDING_NOT_CURRENT_EXACT")
                if not required_document_types.issubset(valid_types):
                    unresolved.add("REQUIRED_SUPPLIER_DOCUMENT_MISSING")

                origin = str(stock_source.get("origin") or "").strip().upper()
                finished_stock_fraction = (
                    dose.active_concentrate_fraction
                    * command.finished_product_concentration
                )
                if origin == "SYNTHETIC":
                    contributions.append(
                        _RegulatoryContribution(
                            material_id=material.id,
                            substance_name=material.canonical_name,
                            cas_number=material.cas_number,
                            observed_fraction=finished_stock_fraction,
                            lineage={
                                **dict(dose.lineage),
                                "origin": origin,
                                "finished_product_fraction": (
                                    finished_stock_fraction
                                ),
                            },
                        )
                    )
                    continue

                if origin not in {"NATURAL", "TRADE_GRADE"}:
                    unresolved.add("STOCK_ORIGIN_UNKNOWN")
                    unknown_natural_composition = True
                    continue

                profile = profiles_by_stock.get(stock.id)
                profile_valid = profile is not None
                if profile is None:
                    unresolved.add("NATURAL_COMPOSITION_UNKNOWN")
                    unknown_natural_composition = True
                    continue
                if (
                    profile.origin != origin
                    or profile.completeness != "COMPLETE"
                    or profile.composition_basis == "UNKNOWN"
                ):
                    profile_valid = False
                latest_profile = (
                    await self.repository.latest_regulatory_composition_profile(
                        profile.profile_id
                    )
                )
                if latest_profile is None or latest_profile.id != profile.id:
                    profile_valid = False
                    unresolved.add("COMPOSITION_PROFILE_NOT_LATEST")

                profile_binding = None
                if profile.supplier_document_binding_id is not None:
                    profile_binding = bindings.get(
                        profile.supplier_document_binding_id
                    )
                if (
                    profile_binding is None
                    or profile_binding.stock_solution_id != stock.id
                    or profile_binding.document_type
                    not in {
                        "SUPPLIER_COA",
                        "SUPPLIER_SPECIFICATION",
                        "SUPPLIER_ALLERGEN_DECLARATION",
                    }
                    or profile_binding.effective_on > evaluation_date
                    or (
                        profile_binding.expires_on is not None
                        and evaluation_date > profile_binding.expires_on
                    )
                ):
                    profile_valid = False
                    unresolved.add("COMPOSITION_DOCUMENT_NOT_CURRENT_EXACT")

                entries = (
                    await self.repository.regulatory_composition_entries(
                        profile.id
                    )
                )
                if not entries:
                    profile_valid = False
                for entry in entries:
                    if entry.projection_family != "REGULATORY":
                        profile_valid = False
                        continue
                    contribution_fraction = (
                        finished_stock_fraction * float(entry.fraction)
                    )
                    contributions.append(
                        _RegulatoryContribution(
                            material_id=entry.material_id,
                            substance_name=entry.constituent_name,
                            cas_number=entry.cas_number,
                            observed_fraction=contribution_fraction,
                            lineage={
                                **dict(dose.lineage),
                                "origin": origin,
                                "composition_profile_id": profile.id,
                                "composition_entry_id": entry.id,
                                "composition_fraction": entry.fraction,
                                "finished_product_fraction": (
                                    contribution_fraction
                                ),
                            },
                        )
                    )
                if not profile_valid:
                    unresolved.add("NATURAL_COMPOSITION_UNKNOWN")
                    unknown_natural_composition = True

            rules: list[LabRegulatoryRuleVersion] = []
            for rule_id in command.rule_version_ids:
                rule = await self.repository.get_regulatory_rule_version(
                    rule_id
                )
                if rule is None:
                    raise RegulatoryAuthorityConflictError(
                        "REGULATORY_RULE_NOT_FOUND",
                        "A selected B6 regulatory rule was not found.",
                    )
                if rule.regulatory_source_version_id not in sources:
                    unresolved.add("RULE_SOURCE_NOT_SELECTED")
                rules.append(rule)
                upstream_hashes[f"rule:{rule.id}"] = rule.content_sha256
            if not rules:
                unresolved.add("NO_REGULATORY_RULES_SELECTED")

            labels = {
                value.strip().casefold()
                for value in command.declared_allergen_labels
            }
            finding_payloads: list[dict[str, Any]] = []
            enforced_results: list[str] = []
            for rule in rules:
                source = sources.get(rule.regulatory_source_version_id)
                if source is None:
                    raise RegulatoryAuthorityConflictError(
                        "RULE_SOURCE_NOT_FOUND",
                        "A selected rule source was not found.",
                    )
                selected_current = (
                    source.id in command.current_state_source_version_ids
                )
                scope_matches = (
                    _jurisdiction_applies(
                        rule.jurisdiction,
                        command.jurisdiction,
                    )
                    and _same_identity(
                        rule.product_category,
                        command.product_category,
                    )
                    and _same_identity(
                        rule.use_classification,
                        command.use_classification,
                    )
                    and _same_identity(
                        rule.concentration_basis,
                        command.constituent_basis,
                    )
                )
                if selected_current and not scope_matches:
                    unresolved.add("RULE_SCOPE_MISMATCH")
                temporal = await self.is_regulatory_rule_enforceable(
                    rule.id,
                    evaluated_at=command.evaluated_at,
                    market_action=command.market_action,
                    market_action_on=command.market_action_on,
                )
                enforced = bool(
                    selected_current
                    and current_source_validity.get(source.id, False)
                    and scope_matches
                    and temporal
                )
                matching = [
                    item
                    for item in contributions
                    if _rule_matches_contribution(rule, item)
                ]
                observed = sum(
                    item.observed_fraction for item in matching
                )
                limit = (
                    rule.maximum_fraction
                    if rule.rule_kind
                    == "MAXIMUM_FINISHED_FRACTION"
                    else rule.threshold_fraction
                )
                reason_codes: list[str]
                if not enforced:
                    finding_state = "NOT_EVALUATED"
                    reason_codes = ["RULE_NOT_ENFORCED_FOR_DECLARED_SCOPE"]
                elif rule.rule_kind == "MAXIMUM_FINISHED_FRACTION":
                    assert limit is not None
                    if observed > float(limit) + 1e-15:
                        finding_state = "FAIL"
                        reason_codes = ["MAXIMUM_FINISHED_FRACTION_EXCEEDED"]
                    elif unknown_natural_composition:
                        finding_state = "UNKNOWN"
                        reason_codes = ["CONSTITUENT_FRACTION_UNKNOWN"]
                    else:
                        finding_state = "PASS_FOR_DECLARED_SCOPE"
                        reason_codes = ["MAXIMUM_FINISHED_FRACTION_MET"]
                else:
                    assert limit is not None
                    declaration = str(
                        rule.declaration_wording or ""
                    ).strip()
                    if observed > float(limit):
                        if declaration.casefold() in labels:
                            finding_state = "PASS_FOR_DECLARED_SCOPE"
                            reason_codes = ["REQUIRED_DECLARATION_PRESENT"]
                        else:
                            finding_state = "FAIL"
                            reason_codes = ["REQUIRED_DECLARATION_MISSING"]
                    elif unknown_natural_composition:
                        finding_state = "UNKNOWN"
                        reason_codes = ["CONSTITUENT_FRACTION_UNKNOWN"]
                    else:
                        finding_state = "PASS_FOR_DECLARED_SCOPE"
                        reason_codes = ["DECLARATION_THRESHOLD_NOT_EXCEEDED"]
                if enforced:
                    enforced_results.append(finding_state)
                result_reasons.update(reason_codes)
                finding_payloads.append(
                    {
                        "rule": rule,
                        "source": source,
                        "observed_fraction": observed,
                        "limit_fraction": limit,
                        "enforced": enforced,
                        "contribution_lineage": [
                            dict(item.lineage) for item in matching
                        ],
                        "reason_codes": reason_codes,
                        "detail": {
                            "rule_identifier": rule.rule_identifier,
                            "rule_family": rule.rule_family,
                            "rule_kind": rule.rule_kind,
                            "regulatory_source_version_id": source.id,
                            "declared_scope": {
                                "jurisdiction": command.jurisdiction,
                                "product_category": command.product_category,
                                "use_classification": (
                                    command.use_classification
                                ),
                                "market_action": command.market_action,
                                "market_action_on": (
                                    command.market_action_on.isoformat()
                                ),
                            },
                        },
                        "result_state": finding_state,
                    }
                )

            if "FAIL" in enforced_results:
                result_state = "FAIL"
                result_reasons.add("ENFORCED_RULE_FAILURE")
            elif unresolved or "UNKNOWN" in enforced_results:
                result_state = "UNKNOWN"
                result_reasons.add("UNRESOLVED_REGULATORY_INPUT")
            elif enforced_results:
                result_state = "PASS_FOR_DECLARED_SCOPE"
                result_reasons.add("ALL_ENFORCED_RULES_PASSED")
            else:
                result_state = "NOT_EVALUATED"
                result_reasons.add("NO_RULE_ENFORCED_FOR_DECLARED_SCOPE")
            if result_state not in REGULATORY_RESULT_STATES:
                raise AssertionError("invalid internal regulatory result state")

            if command.snapshot_id is None:
                snapshot_id = str(uuid4())
                version_number = 1
                parent = None
            else:
                parent = (
                    await self.repository.latest_regulatory_snapshot_version(
                        command.snapshot_id
                    )
                )
                if (
                    parent is None
                    or command.parent_version_id != parent.id
                    or parent.subject_type != command.subject_type
                    or parent.subject_id != command.subject_id
                ):
                    raise RegulatoryAuthorityConflictError(
                        "REGULATORY_SNAPSHOT_PARENT_NOT_LATEST",
                        "The parent must be the latest snapshot for this subject.",
                    )
                snapshot_id = parent.snapshot_id
                version_number = parent.version_number + 1

            permitted_wording = None
            if result_state == "PASS_FOR_DECLARED_SCOPE":
                permitted_wording = (
                    "Regulatory screening passed for the declared "
                    f"{command.jurisdiction} jurisdiction, "
                    f"{command.product_category} product category, "
                    f"{command.use_classification} use, and "
                    f"{command.market_action} action on "
                    f"{command.market_action_on.isoformat()} for "
                    f"{command.subject_type} {command.subject_id}, using only "
                    "the recorded source versions."
                )

            unresolved_items = sorted(unresolved)
            reasons = sorted(result_reasons)
            payload = {
                "schema": "lab-regulatory-snapshot-v1",
                "snapshot_id": snapshot_id,
                "version_number": version_number,
                "parent_version_id": parent.id if parent is not None else None,
                "parent_sha256": (
                    parent.content_sha256 if parent is not None else None
                ),
                "subject_type": command.subject_type,
                "subject_id": command.subject_id,
                "legacy_assessment_version_id": (
                    legacy.id if legacy is not None else None
                ),
                "primary_source_version_id": primary.id,
                "standard_identifier": primary.identifier,
                "standard_version": primary.published_version,
                "official_source_sha256": primary.official_source_sha256,
                "jurisdiction": command.jurisdiction,
                "product_category": command.product_category,
                "use_classification": command.use_classification,
                "finished_product_concentration": (
                    command.finished_product_concentration
                ),
                "constituent_basis": command.constituent_basis,
                "natural_material_assumptions": (
                    command.natural_material_assumptions
                ),
                "effective_on": command.effective_on.isoformat(),
                "evaluated_at": command.evaluated_at.isoformat(),
                "evaluator_software_version": (
                    command.evaluator_software_version
                ),
                "market_action": command.market_action,
                "market_action_on": command.market_action_on.isoformat(),
                "current_state_source_ids": (
                    command.current_state_source_version_ids
                ),
                "watch_source_ids": command.watch_source_version_ids,
                "rule_version_ids": command.rule_version_ids,
                "supplier_binding_ids": command.supplier_binding_ids,
                "composition_profile_ids": command.composition_profile_ids,
                "upstream_hashes": upstream_hashes,
                "unresolved_items": unresolved_items,
                "result_reasons": reasons,
                "result_state": result_state,
                "permitted_wording": permitted_wording,
                "reviewer_pseudonym": command.reviewer_pseudonym,
                "reviewed_at": command.reviewed_at.isoformat(),
            }
            snapshot = await self.repository.add(
                LabRegulatorySnapshotVersion(
                    snapshot_id=snapshot_id,
                    version_number=version_number,
                    parent_version_id=(
                        parent.id if parent is not None else None
                    ),
                    schema_version=command.schema_version,
                    subject_type=command.subject_type,
                    subject_id=command.subject_id,
                    legacy_assessment_version_id=(
                        legacy.id if legacy is not None else None
                    ),
                    primary_source_version_id=primary.id,
                    standard_identifier=primary.identifier,
                    standard_version=primary.published_version,
                    official_source_sha256=primary.official_source_sha256,
                    jurisdiction=command.jurisdiction,
                    product_category=command.product_category,
                    use_classification=command.use_classification,
                    finished_product_concentration=(
                        command.finished_product_concentration
                    ),
                    constituent_basis=command.constituent_basis,
                    natural_material_assumptions_json=list(
                        command.natural_material_assumptions
                    ),
                    effective_on=command.effective_on,
                    evaluated_at=command.evaluated_at,
                    evaluator_software_version=(
                        command.evaluator_software_version
                    ),
                    market_action=command.market_action,
                    market_action_on=command.market_action_on,
                    current_state_source_ids_json=list(
                        command.current_state_source_version_ids
                    ),
                    watch_source_ids_json=list(
                        command.watch_source_version_ids
                    ),
                    rule_version_ids_json=list(command.rule_version_ids),
                    supplier_binding_ids_json=list(
                        command.supplier_binding_ids
                    ),
                    composition_profile_ids_json=list(
                        command.composition_profile_ids
                    ),
                    upstream_hashes_json=upstream_hashes,
                    unresolved_items_json=unresolved_items,
                    result_reasons_json=reasons,
                    result_state=result_state,
                    permitted_wording=permitted_wording,
                    reviewer_pseudonym=command.reviewer_pseudonym,
                    reviewed_at=command.reviewed_at,
                    content_sha256=canonical_json_sha256(payload),
                    parent_sha256=(
                        parent.content_sha256
                        if parent is not None
                        else None
                    ),
                )
            )

            for item in finding_payloads:
                rule = item["rule"]
                source = item["source"]
                finding_content = {
                    "schema": "lab-regulatory-authority-finding-v1",
                    "snapshot_content_sha256": snapshot.content_sha256,
                    "rule_version_id": rule.id,
                    "rule_content_sha256": rule.content_sha256,
                    "source_content_sha256": source.content_sha256,
                    "substance_name": rule.substance_name,
                    "cas_number": rule.cas_number,
                    "observed_fraction": item["observed_fraction"],
                    "limit_fraction": item["limit_fraction"],
                    "concentration_basis": rule.concentration_basis,
                    "source_status": source.status,
                    "enforced": item["enforced"],
                    "contribution_lineage": item[
                        "contribution_lineage"
                    ],
                    "reason_codes": item["reason_codes"],
                    "detail": item["detail"],
                    "result_state": item["result_state"],
                }
                await self.repository.add(
                    LabRegulatoryAuthorityFinding(
                        snapshot_version_id=snapshot.id,
                        rule_version_id=rule.id,
                        substance_name=rule.substance_name,
                        cas_number=rule.cas_number,
                        observed_fraction=item["observed_fraction"],
                        limit_fraction=item["limit_fraction"],
                        concentration_basis=rule.concentration_basis,
                        source_status=source.status,
                        enforced=item["enforced"],
                        contribution_lineage_json=item[
                            "contribution_lineage"
                        ],
                        reason_codes_json=item["reason_codes"],
                        detail_json=item["detail"],
                        result_state=item["result_state"],
                        content_sha256=canonical_json_sha256(
                            finding_content
                        ),
                    )
                )
            return snapshot

    async def is_b6_authoritative_assessment(
        self,
        legacy_assessment_version_id: str,
    ) -> bool:
        snapshot = (
            await self.repository.passed_snapshot_for_legacy_assessment(
                _text(
                    legacy_assessment_version_id,
                    "legacy_assessment_version_id",
                )
            )
        )
        return snapshot is not None


__all__ = [
    "RegulatoryAuthorityConflictError",
    "RegulatoryAuthorityError",
    "RegulatoryCompositionEntryInput",
    "RegulatoryCompositionProfileInput",
    "RegulatoryEvaluationInput",
    "RegulatoryRuleInput",
    "RegulatorySourceInput",
    "SupplierDocumentBindingInput",
    "canonical_json_sha256",
]
