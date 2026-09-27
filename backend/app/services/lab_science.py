"""Immutable commands for analytical, regulatory, and claim authority."""

from __future__ import annotations

from dataclasses import dataclass, replace
from dataclasses import fields as dataclass_fields
from datetime import date, datetime
from math import isfinite
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from engine.authority_gates import (
    ClaimAuthorityInput,
    ClaimDecision,
    GateReason,
    decision_within_authority,
    evaluate_claim_authority,
)
from engine.calibration.hashing import stable_json_hash

from app.models.lab_science import (
    ANALYTICAL_IDENTITY_STATES,
    ANALYTICAL_METHOD_STATUSES,
    ANALYTICAL_QC_STATUSES,
    ANALYTICAL_RUN_STATUSES,
    ANALYTICAL_TECHNIQUES,
    ASSESSMENT_RESULT_STATES,
    CLAIM_DECISIONS,
    CLAIM_EVIDENCE_ROLES,
    CLAIM_REVIEW_STATES,
    CLAIM_SUBJECT_TYPES,
    REGULATORY_STANDARD_STATES,
    REGULATORY_SUBJECT_TYPES,
    LabAnalyticalAttachment,
    LabAnalyticalMethodVersion,
    LabAnalyticalPeak,
    LabAnalyticalQCRecord,
    LabAnalyticalRun,
    LabClaimAssessmentEvidenceLink,
    LabClaimAssessmentVersion,
    LabGCOEvent,
    LabRegulatoryAssessmentVersion,
    LabRegulatoryFinding,
)

if TYPE_CHECKING:
    from contextlib import AbstractAsyncContextManager

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.repositories.lab import LabRepository


class ScienceAuthorityError(ValueError):
    """Base class for a stable science-authority rejection."""

    code = "SCIENCE_AUTHORITY_ERROR"


class ScienceAuthorityConflictError(ScienceAuthorityError):
    """A valid command shape that conflicts with canonical authority."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _text(value: str, field: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ScienceAuthorityError(f"{field} must not be blank")
    return normalized


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _choice(value: str, field: str, allowed: tuple[str, ...]) -> str:
    normalized = _text(value, field)
    if normalized not in allowed:
        raise ScienceAuthorityError(
            f"{field} must be one of {', '.join(allowed)}"
        )
    return normalized


def _finite_optional(
    value: float | None,
    field: str,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float | None:
    if value is None:
        return None
    normalized = float(value)
    if not isfinite(normalized):
        raise ScienceAuthorityError(f"{field} must be finite")
    if minimum is not None and normalized < minimum:
        raise ScienceAuthorityError(f"{field} must be at least {minimum:g}")
    if maximum is not None and normalized > maximum:
        raise ScienceAuthorityError(f"{field} must be at most {maximum:g}")
    return normalized


def _aware(value: datetime, field: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ScienceAuthorityError(f"{field} must be timezone-aware")
    return value


def _digest(value: str, field: str = "content_sha256") -> str:
    normalized = _text(value, field).casefold()
    if len(normalized) != 64 or any(
        character not in "0123456789abcdef" for character in normalized
    ):
        raise ScienceAuthorityError(
            f"{field} must be a 64-character hexadecimal digest"
        )
    return normalized


def _tuple_text(values: tuple[str, ...], field: str) -> tuple[str, ...]:
    normalized = tuple(_text(value, field) for value in values)
    if len(normalized) != len(set(normalized)):
        raise ScienceAuthorityError(f"{field} must not contain duplicates")
    return normalized


@dataclass(frozen=True, slots=True)
class AnalyticalMethodInput:
    schema_version: str
    technique: str
    intended_use: str
    status: str
    method: dict
    evidence_record_id: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )
        object.__setattr__(
            self,
            "technique",
            _choice(self.technique, "technique", ANALYTICAL_TECHNIQUES),
        )
        object.__setattr__(
            self, "intended_use", _text(self.intended_use, "intended_use")
        )
        object.__setattr__(
            self,
            "status",
            _choice(self.status, "status", ANALYTICAL_METHOD_STATUSES),
        )
        object.__setattr__(self, "method", dict(self.method))
        object.__setattr__(
            self,
            "evidence_record_id",
            _text(self.evidence_record_id, "evidence_record_id"),
        )


@dataclass(frozen=True, slots=True)
class AnalyticalRunInput:
    method_version_id: str
    run_kind: str
    status: str
    instrument_identifier: str
    acquired_at: datetime
    parameters: dict
    deviations: tuple[str, ...]
    processing_version: str
    experiment_id: str | None = None
    sample_id: str | None = None
    bottle_id: str | None = None
    formula_version_id: str | None = None
    build_plan_version_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "method_version_id",
            _text(self.method_version_id, "method_version_id"),
        )
        object.__setattr__(
            self,
            "run_kind",
            _choice(self.run_kind, "run_kind", ANALYTICAL_TECHNIQUES),
        )
        object.__setattr__(
            self,
            "status",
            _choice(self.status, "status", ANALYTICAL_RUN_STATUSES),
        )
        object.__setattr__(
            self,
            "instrument_identifier",
            _text(self.instrument_identifier, "instrument_identifier"),
        )
        object.__setattr__(
            self, "acquired_at", _aware(self.acquired_at, "acquired_at")
        )
        object.__setattr__(self, "parameters", dict(self.parameters))
        object.__setattr__(
            self, "deviations", _tuple_text(self.deviations, "deviations")
        )
        object.__setattr__(
            self,
            "processing_version",
            _text(self.processing_version, "processing_version"),
        )
        for field in (
            "experiment_id",
            "sample_id",
            "bottle_id",
            "formula_version_id",
            "build_plan_version_id",
        ):
            object.__setattr__(self, field, _optional_text(getattr(self, field)))
        if not any(
            (
                self.experiment_id,
                self.sample_id,
                self.bottle_id,
                self.formula_version_id,
                self.build_plan_version_id,
            )
        ):
            raise ScienceAuthorityError(
                "analytical run requires at least one canonical subject"
            )


@dataclass(frozen=True, slots=True)
class AnalyticalPeakInput:
    analytical_run_id: str
    peak_key: str
    retention_time_minutes: float | None = None
    retention_index: float | None = None
    area: float | None = None
    response_factor: float | None = None
    qualifier_ions: tuple[int, ...] = ()
    tentative_identity: str | None = None
    material_id: str | None = None
    identity_state: str = "UNASSIGNED"
    match_score: float | None = None
    quantitation_basis: str | None = None
    quantity: float | None = None
    quantity_unit: str | None = None
    standard_uncertainty: float | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "analytical_run_id",
            _text(self.analytical_run_id, "analytical_run_id"),
        )
        object.__setattr__(self, "peak_key", _text(self.peak_key, "peak_key"))
        for field in (
            "retention_time_minutes",
            "retention_index",
            "area",
            "response_factor",
            "quantity",
            "standard_uncertainty",
        ):
            object.__setattr__(
                self,
                field,
                _finite_optional(getattr(self, field), field, minimum=0),
            )
        object.__setattr__(
            self,
            "match_score",
            _finite_optional(
                self.match_score,
                "match_score",
                minimum=0,
                maximum=1,
            ),
        )
        ions = tuple(int(value) for value in self.qualifier_ions)
        if any(value < 0 for value in ions):
            raise ScienceAuthorityError("qualifier_ions must be nonnegative")
        object.__setattr__(self, "qualifier_ions", ions)
        object.__setattr__(
            self, "tentative_identity", _optional_text(self.tentative_identity)
        )
        object.__setattr__(self, "material_id", _optional_text(self.material_id))
        object.__setattr__(
            self,
            "identity_state",
            _choice(
                self.identity_state,
                "identity_state",
                ANALYTICAL_IDENTITY_STATES,
            ),
        )
        object.__setattr__(
            self, "quantitation_basis", _optional_text(self.quantitation_basis)
        )
        object.__setattr__(self, "quantity_unit", _optional_text(self.quantity_unit))
        object.__setattr__(self, "notes", _optional_text(self.notes))
        if self.identity_state == "CONFIRMED" and self.material_id is None:
            raise ScienceAuthorityError(
                "confirmed analytical identity requires material_id"
            )
        quantity_fields = (
            self.quantity,
            self.quantity_unit,
            self.quantitation_basis,
        )
        if any(value is not None for value in quantity_fields) and not all(
            value is not None for value in quantity_fields
        ):
            raise ScienceAuthorityError(
                "quantity requires quantity_unit and quantitation_basis"
            )


@dataclass(frozen=True, slots=True)
class AnalyticalQCInput:
    analytical_run_id: str
    qc_key: str
    qc_type: str
    status: str
    criteria: dict
    observed: dict
    evidence_record_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "analytical_run_id",
            _text(self.analytical_run_id, "analytical_run_id"),
        )
        object.__setattr__(self, "qc_key", _text(self.qc_key, "qc_key"))
        object.__setattr__(self, "qc_type", _text(self.qc_type, "qc_type"))
        object.__setattr__(
            self,
            "status",
            _choice(self.status, "status", ANALYTICAL_QC_STATUSES),
        )
        object.__setattr__(self, "criteria", dict(self.criteria))
        object.__setattr__(self, "observed", dict(self.observed))
        object.__setattr__(
            self,
            "evidence_record_id",
            _optional_text(self.evidence_record_id),
        )


@dataclass(frozen=True, slots=True)
class AnalyticalAttachmentInput:
    analytical_run_id: str
    attachment_kind: str
    media_type: str
    byte_length: int
    content_sha256: str
    storage_locator: str
    evidence_record_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "analytical_run_id",
            _text(self.analytical_run_id, "analytical_run_id"),
        )
        object.__setattr__(
            self,
            "attachment_kind",
            _text(self.attachment_kind, "attachment_kind"),
        )
        object.__setattr__(
            self, "media_type", _text(self.media_type, "media_type")
        )
        length = int(self.byte_length)
        if length < 0:
            raise ScienceAuthorityError("byte_length must be nonnegative")
        object.__setattr__(self, "byte_length", length)
        object.__setattr__(
            self, "content_sha256", _digest(self.content_sha256)
        )
        object.__setattr__(
            self,
            "storage_locator",
            _text(self.storage_locator, "storage_locator"),
        )
        object.__setattr__(
            self,
            "evidence_record_id",
            _optional_text(self.evidence_record_id),
        )


@dataclass(frozen=True, slots=True)
class GCOEventInput:
    analytical_run_id: str
    event_key: str
    descriptor: str
    assessor_pseudonym: str
    analytical_peak_id: str | None = None
    retention_time_minutes: float | None = None
    retention_index: float | None = None
    intensity: float | None = None
    repeatability: dict | None = None
    evidence_record_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "analytical_run_id",
            _text(self.analytical_run_id, "analytical_run_id"),
        )
        object.__setattr__(self, "event_key", _text(self.event_key, "event_key"))
        object.__setattr__(self, "descriptor", _text(self.descriptor, "descriptor"))
        object.__setattr__(
            self,
            "assessor_pseudonym",
            _text(self.assessor_pseudonym, "assessor_pseudonym"),
        )
        object.__setattr__(
            self, "analytical_peak_id", _optional_text(self.analytical_peak_id)
        )
        object.__setattr__(
            self,
            "retention_time_minutes",
            _finite_optional(
                self.retention_time_minutes,
                "retention_time_minutes",
                minimum=0,
            ),
        )
        object.__setattr__(
            self,
            "retention_index",
            _finite_optional(
                self.retention_index,
                "retention_index",
                minimum=0,
            ),
        )
        object.__setattr__(
            self,
            "intensity",
            _finite_optional(
                self.intensity,
                "intensity",
                minimum=0,
                maximum=1,
            ),
        )
        object.__setattr__(self, "repeatability", dict(self.repeatability or {}))
        object.__setattr__(
            self,
            "evidence_record_id",
            _optional_text(self.evidence_record_id),
        )


@dataclass(frozen=True, slots=True)
class RegulatoryAssessmentInput:
    schema_version: str
    subject_type: str
    subject_id: str
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
    assumptions: tuple[str, ...]
    unresolved: tuple[str, ...]
    permitted_wording: str | None

    def __post_init__(self) -> None:
        for field in (
            "schema_version",
            "subject_id",
            "standard_identifier",
            "jurisdiction",
            "product_category",
            "concentration_basis",
        ):
            object.__setattr__(self, field, _text(getattr(self, field), field))
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
            self, "standard_amendment", _optional_text(self.standard_amendment)
        )
        object.__setattr__(
            self,
            "standard_state",
            _choice(
                self.standard_state,
                "standard_state",
                REGULATORY_STANDARD_STATES,
            ),
        )
        object.__setattr__(
            self,
            "source_evidence_record_id",
            _optional_text(self.source_evidence_record_id),
        )
        object.__setattr__(
            self,
            "finished_product_concentration",
            _finite_optional(
                self.finished_product_concentration,
                "finished_product_concentration",
                minimum=0,
            ),
        )
        object.__setattr__(
            self, "evaluated_at", _aware(self.evaluated_at, "evaluated_at")
        )
        object.__setattr__(
            self,
            "result_state",
            _choice(
                self.result_state,
                "result_state",
                ASSESSMENT_RESULT_STATES,
            ),
        )
        object.__setattr__(
            self, "assumptions", _tuple_text(self.assumptions, "assumptions")
        )
        object.__setattr__(
            self, "unresolved", _tuple_text(self.unresolved, "unresolved")
        )
        object.__setattr__(
            self, "permitted_wording", _optional_text(self.permitted_wording)
        )


@dataclass(frozen=True, slots=True)
class RegulatoryFindingInput:
    regulatory_assessment_version_id: str
    finding_key: str
    restriction_id: str | None
    material_id: str | None
    substance_identity: str
    observed_fraction: float | None
    maximum_fraction: float | None
    concentration_basis: str | None
    result_state: str
    detail: str
    evidence_record_id: str | None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "regulatory_assessment_version_id",
            _text(
                self.regulatory_assessment_version_id,
                "regulatory_assessment_version_id",
            ),
        )
        object.__setattr__(
            self, "finding_key", _text(self.finding_key, "finding_key")
        )
        object.__setattr__(self, "restriction_id", _optional_text(self.restriction_id))
        object.__setattr__(self, "material_id", _optional_text(self.material_id))
        object.__setattr__(
            self,
            "substance_identity",
            _text(self.substance_identity, "substance_identity"),
        )
        object.__setattr__(
            self,
            "observed_fraction",
            _finite_optional(
                self.observed_fraction,
                "observed_fraction",
                minimum=0,
            ),
        )
        object.__setattr__(
            self,
            "maximum_fraction",
            _finite_optional(
                self.maximum_fraction,
                "maximum_fraction",
                minimum=0,
            ),
        )
        object.__setattr__(
            self, "concentration_basis", _optional_text(self.concentration_basis)
        )
        object.__setattr__(
            self,
            "result_state",
            _choice(
                self.result_state,
                "result_state",
                ASSESSMENT_RESULT_STATES,
            ),
        )
        object.__setattr__(self, "detail", _text(self.detail, "detail"))
        object.__setattr__(
            self,
            "evidence_record_id",
            _optional_text(self.evidence_record_id),
        )


@dataclass(frozen=True, slots=True)
class ClaimEvidenceInput:
    evidence_record_id: str
    role: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "evidence_record_id",
            _text(self.evidence_record_id, "evidence_record_id"),
        )
        object.__setattr__(
            self,
            "role",
            _choice(self.role, "role", CLAIM_EVIDENCE_ROLES),
        )


@dataclass(frozen=True, slots=True)
class ClaimAssessmentInput:
    schema_version: str
    claim_type: str
    subject_type: str
    subject_id: str
    policy_version: str
    decision: str
    authority: dict
    missing_evidence: tuple[str, ...]
    conflicts: tuple[str, ...]
    permitted_wording: str | None
    forbidden_wording: str | None
    human_review_state: str
    reviewer_pseudonym: str | None
    reviewed_at: datetime | None
    evidence_links: tuple[ClaimEvidenceInput, ...]

    def __post_init__(self) -> None:
        for field in (
            "schema_version",
            "claim_type",
            "subject_id",
            "policy_version",
        ):
            object.__setattr__(self, field, _text(getattr(self, field), field))
        object.__setattr__(
            self,
            "subject_type",
            _choice(self.subject_type, "subject_type", CLAIM_SUBJECT_TYPES),
        )
        object.__setattr__(
            self,
            "decision",
            _choice(self.decision, "decision", CLAIM_DECISIONS),
        )
        object.__setattr__(self, "authority", dict(self.authority))
        object.__setattr__(
            self,
            "missing_evidence",
            _tuple_text(self.missing_evidence, "missing_evidence"),
        )
        object.__setattr__(
            self,
            "conflicts",
            _tuple_text(self.conflicts, "conflicts"),
        )
        object.__setattr__(
            self, "permitted_wording", _optional_text(self.permitted_wording)
        )
        object.__setattr__(
            self, "forbidden_wording", _optional_text(self.forbidden_wording)
        )
        object.__setattr__(
            self,
            "human_review_state",
            _choice(
                self.human_review_state,
                "human_review_state",
                CLAIM_REVIEW_STATES,
            ),
        )
        object.__setattr__(
            self, "reviewer_pseudonym", _optional_text(self.reviewer_pseudonym)
        )
        if self.reviewed_at is not None:
            object.__setattr__(
                self, "reviewed_at", _aware(self.reviewed_at, "reviewed_at")
            )
        links = tuple(self.evidence_links)
        link_keys = {
            (link.evidence_record_id, link.role)
            for link in links
        }
        if len(link_keys) != len(links):
            raise ScienceAuthorityError("evidence_links must not contain duplicates")
        object.__setattr__(self, "evidence_links", links)


def _dated(value: date | datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


class LabScienceServiceMixin:
    """Science-authority commands using the canonical transaction owner."""

    if TYPE_CHECKING:
        repository: LabRepository
        session: AsyncSession

        def _transaction(self) -> AbstractAsyncContextManager[None]: ...

    async def _require_evidence(self, evidence_id: str | None) -> None:
        if evidence_id is not None and (
            await self.repository.get_evidence_record(evidence_id) is None
        ):
            raise ScienceAuthorityConflictError(
                "EVIDENCE_NOT_FOUND",
                f"Evidence record not found: {evidence_id}.",
            )

    async def _require_run_subjects(self, command: AnalyticalRunInput) -> None:
        checks = (
            (
                command.experiment_id,
                self.repository.get_experiment,
                "EXPERIMENT_NOT_FOUND",
            ),
            (
                command.sample_id,
                self.repository.get_sample,
                "SAMPLE_NOT_FOUND",
            ),
            (
                command.bottle_id,
                self.repository.get_bottle,
                "BOTTLE_NOT_FOUND",
            ),
            (
                command.formula_version_id,
                self.repository.get_formula_version,
                "FORMULA_VERSION_NOT_FOUND",
            ),
            (
                command.build_plan_version_id,
                self.repository.get_build_plan_version,
                "BUILD_PLAN_VERSION_NOT_FOUND",
            ),
        )
        for identity, getter, code in checks:
            if identity is not None and await getter(identity) is None:
                raise ScienceAuthorityConflictError(
                    code,
                    f"Canonical analytical subject not found: {identity}.",
                )

    async def _science_subject_exists(
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

    async def create_analytical_method_version(
        self,
        command: AnalyticalMethodInput,
        *,
        parent_version_id: str | None = None,
    ) -> LabAnalyticalMethodVersion:
        async with self._transaction():
            await self._require_evidence(command.evidence_record_id)
            parent = None
            if parent_version_id is None:
                method_id = str(uuid4())
                version_number = 1
            else:
                parent = await self.repository.get_analytical_method_version(
                    parent_version_id
                )
                if parent is None:
                    raise ScienceAuthorityConflictError(
                        "ANALYTICAL_METHOD_PARENT_NOT_FOUND",
                        f"Analytical method parent not found: {parent_version_id}.",
                    )
                latest = await self.repository.latest_analytical_method_version(
                    parent.method_id
                )
                if latest is None or latest.id != parent.id:
                    raise ScienceAuthorityConflictError(
                        "ANALYTICAL_METHOD_PARENT_NOT_LATEST",
                        "Analytical method revision must use the latest parent.",
                    )
                method_id = parent.method_id
                version_number = parent.version_number + 1
            payload = {
                "schema": "lab-analytical-method-v1",
                "method_id": method_id,
                "version_number": version_number,
                "schema_version": command.schema_version,
                "technique": command.technique,
                "intended_use": command.intended_use,
                "status": command.status,
                "method": command.method,
                "evidence_record_id": command.evidence_record_id,
                "parent_sha256": parent.content_sha256 if parent else None,
            }
            return await self.repository.add(
                LabAnalyticalMethodVersion(
                    method_id=method_id,
                    version_number=version_number,
                    schema_version=command.schema_version,
                    technique=command.technique,
                    intended_use=command.intended_use,
                    status=command.status,
                    method_json=dict(command.method),
                    evidence_record_id=command.evidence_record_id,
                    content_sha256=stable_json_hash(payload),
                    parent_version_id=parent.id if parent else None,
                    parent_sha256=parent.content_sha256 if parent else None,
                )
            )

    async def record_analytical_run(
        self,
        command: AnalyticalRunInput,
    ) -> LabAnalyticalRun:
        async with self._transaction():
            if (
                await self.repository.get_analytical_method_version(
                    command.method_version_id
                )
                is None
            ):
                raise ScienceAuthorityConflictError(
                    "ANALYTICAL_METHOD_NOT_FOUND",
                    f"Analytical method not found: {command.method_version_id}.",
                )
            await self._require_run_subjects(command)
            run_id = str(uuid4())
            payload = {
                "schema": "lab-analytical-run-v1",
                "run_id": run_id,
                "method_version_id": command.method_version_id,
                "run_kind": command.run_kind,
                "status": command.status,
                "instrument_identifier": command.instrument_identifier,
                "acquired_at": _dated(command.acquired_at),
                "parameters": command.parameters,
                "deviations": command.deviations,
                "processing_version": command.processing_version,
                "experiment_id": command.experiment_id,
                "sample_id": command.sample_id,
                "bottle_id": command.bottle_id,
                "formula_version_id": command.formula_version_id,
                "build_plan_version_id": command.build_plan_version_id,
            }
            return await self.repository.add(
                LabAnalyticalRun(
                    run_id=run_id,
                    method_version_id=command.method_version_id,
                    run_kind=command.run_kind,
                    status=command.status,
                    instrument_identifier=command.instrument_identifier,
                    acquired_at=command.acquired_at,
                    parameters_json=dict(command.parameters),
                    deviations_json=list(command.deviations),
                    processing_version=command.processing_version,
                    experiment_id=command.experiment_id,
                    sample_id=command.sample_id,
                    bottle_id=command.bottle_id,
                    formula_version_id=command.formula_version_id,
                    build_plan_version_id=command.build_plan_version_id,
                    content_sha256=stable_json_hash(payload),
                )
            )

    async def record_analytical_peak(
        self,
        command: AnalyticalPeakInput,
    ) -> LabAnalyticalPeak:
        async with self._transaction():
            if (
                await self.repository.get_analytical_run(
                    command.analytical_run_id
                )
                is None
            ):
                raise ScienceAuthorityConflictError(
                    "ANALYTICAL_RUN_NOT_FOUND",
                    f"Analytical run not found: {command.analytical_run_id}.",
                )
            if command.material_id is not None and (
                await self.repository.get_material(command.material_id) is None
            ):
                raise ScienceAuthorityConflictError(
                    "MATERIAL_NOT_FOUND",
                    f"Material not found: {command.material_id}.",
                )
            payload = {
                "schema": "lab-analytical-peak-v1",
                **{
                    field: getattr(command, field)
                    for field in command.__dataclass_fields__
                },
            }
            return await self.repository.add(
                LabAnalyticalPeak(
                    analytical_run_id=command.analytical_run_id,
                    peak_key=command.peak_key,
                    retention_time_minutes=command.retention_time_minutes,
                    retention_index=command.retention_index,
                    area=command.area,
                    response_factor=command.response_factor,
                    qualifier_ions_json=list(command.qualifier_ions),
                    tentative_identity=command.tentative_identity,
                    material_id=command.material_id,
                    identity_state=command.identity_state,
                    match_score=command.match_score,
                    quantitation_basis=command.quantitation_basis,
                    quantity=command.quantity,
                    quantity_unit=command.quantity_unit,
                    standard_uncertainty=command.standard_uncertainty,
                    notes=command.notes,
                    content_sha256=stable_json_hash(payload),
                )
            )

    async def record_analytical_qc(
        self,
        command: AnalyticalQCInput,
    ) -> LabAnalyticalQCRecord:
        async with self._transaction():
            if (
                await self.repository.get_analytical_run(
                    command.analytical_run_id
                )
                is None
            ):
                raise ScienceAuthorityConflictError(
                    "ANALYTICAL_RUN_NOT_FOUND",
                    f"Analytical run not found: {command.analytical_run_id}.",
                )
            await self._require_evidence(command.evidence_record_id)
            payload = {
                "schema": "lab-analytical-qc-v1",
                "analytical_run_id": command.analytical_run_id,
                "qc_key": command.qc_key,
                "qc_type": command.qc_type,
                "status": command.status,
                "criteria": command.criteria,
                "observed": command.observed,
                "evidence_record_id": command.evidence_record_id,
            }
            return await self.repository.add(
                LabAnalyticalQCRecord(
                    analytical_run_id=command.analytical_run_id,
                    qc_key=command.qc_key,
                    qc_type=command.qc_type,
                    status=command.status,
                    criteria_json=dict(command.criteria),
                    observed_json=dict(command.observed),
                    evidence_record_id=command.evidence_record_id,
                    content_sha256=stable_json_hash(payload),
                )
            )

    async def bind_analytical_attachment(
        self,
        command: AnalyticalAttachmentInput,
    ) -> LabAnalyticalAttachment:
        async with self._transaction():
            if (
                await self.repository.get_analytical_run(
                    command.analytical_run_id
                )
                is None
            ):
                raise ScienceAuthorityConflictError(
                    "ANALYTICAL_RUN_NOT_FOUND",
                    f"Analytical run not found: {command.analytical_run_id}.",
                )
            await self._require_evidence(command.evidence_record_id)
            return await self.repository.add(
                LabAnalyticalAttachment(
                    analytical_run_id=command.analytical_run_id,
                    attachment_kind=command.attachment_kind,
                    media_type=command.media_type,
                    byte_length=command.byte_length,
                    content_sha256=command.content_sha256,
                    storage_locator=command.storage_locator,
                    evidence_record_id=command.evidence_record_id,
                )
            )

    async def record_gco_event(
        self,
        command: GCOEventInput,
    ) -> LabGCOEvent:
        async with self._transaction():
            if (
                await self.repository.get_analytical_run(
                    command.analytical_run_id
                )
                is None
            ):
                raise ScienceAuthorityConflictError(
                    "ANALYTICAL_RUN_NOT_FOUND",
                    f"Analytical run not found: {command.analytical_run_id}.",
                )
            if command.analytical_peak_id is not None:
                peak = await self.repository.get_analytical_peak(
                    command.analytical_peak_id
                )
                if peak is None:
                    raise ScienceAuthorityConflictError(
                        "ANALYTICAL_PEAK_NOT_FOUND",
                        f"Analytical peak not found: {command.analytical_peak_id}.",
                    )
                if peak.analytical_run_id != command.analytical_run_id:
                    raise ScienceAuthorityConflictError(
                        "GCO_PEAK_RUN_MISMATCH",
                        "GC-O event peak must belong to the same analytical run.",
                    )
            await self._require_evidence(command.evidence_record_id)
            payload = {
                "schema": "lab-gco-event-v1",
                **{
                    field: getattr(command, field)
                    for field in command.__dataclass_fields__
                },
            }
            return await self.repository.add(
                LabGCOEvent(
                    analytical_run_id=command.analytical_run_id,
                    analytical_peak_id=command.analytical_peak_id,
                    event_key=command.event_key,
                    retention_time_minutes=command.retention_time_minutes,
                    retention_index=command.retention_index,
                    descriptor=command.descriptor,
                    intensity=command.intensity,
                    assessor_pseudonym=command.assessor_pseudonym,
                    repeatability_json=dict(command.repeatability or {}),
                    evidence_record_id=command.evidence_record_id,
                    content_sha256=stable_json_hash(payload),
                )
            )

    async def create_regulatory_assessment_version(
        self,
        command: RegulatoryAssessmentInput,
        *,
        parent_version_id: str | None = None,
    ) -> LabRegulatoryAssessmentVersion:
        async with self._transaction():
            if not await self._science_subject_exists(
                command.subject_type,
                command.subject_id,
            ):
                raise ScienceAuthorityConflictError(
                    "REGULATORY_SUBJECT_NOT_FOUND",
                    f"Regulatory subject not found: {command.subject_id}.",
                )
            await self._require_evidence(command.source_evidence_record_id)
            if command.result_state == "PASS" and (
                command.standard_state != "CURRENT"
                or command.source_evidence_record_id is None
                or command.unresolved
                or command.permitted_wording is None
            ):
                raise ScienceAuthorityConflictError(
                    "REGULATORY_PASS_NOT_SUPPORTED",
                    "Regulatory PASS requires current sourced resolved authority.",
                )
            parent = None
            if parent_version_id is None:
                assessment_id = str(uuid4())
                version_number = 1
            else:
                parent = await self.repository.get_regulatory_assessment_version(
                    parent_version_id
                )
                if parent is None:
                    raise ScienceAuthorityConflictError(
                        "REGULATORY_PARENT_NOT_FOUND",
                        f"Regulatory parent not found: {parent_version_id}.",
                    )
                latest = (
                    await self.repository.latest_regulatory_assessment_version(
                        parent.assessment_id
                    )
                )
                if latest is None or latest.id != parent.id:
                    raise ScienceAuthorityConflictError(
                        "REGULATORY_PARENT_NOT_LATEST",
                        "Regulatory revision must use the latest parent.",
                    )
                assessment_id = parent.assessment_id
                version_number = parent.version_number + 1
            payload = {
                "schema": "lab-regulatory-assessment-v1",
                "assessment_id": assessment_id,
                "version_number": version_number,
                "schema_version": command.schema_version,
                "subject_type": command.subject_type,
                "subject_id": command.subject_id,
                "standard_identifier": command.standard_identifier,
                "standard_amendment": command.standard_amendment,
                "standard_state": command.standard_state,
                "source_evidence_record_id": command.source_evidence_record_id,
                "jurisdiction": command.jurisdiction,
                "product_category": command.product_category,
                "concentration_basis": command.concentration_basis,
                "finished_product_concentration": (
                    command.finished_product_concentration
                ),
                "effective_date": _dated(command.effective_date),
                "evaluated_at": _dated(command.evaluated_at),
                "result_state": command.result_state,
                "assumptions": command.assumptions,
                "unresolved": command.unresolved,
                "permitted_wording": command.permitted_wording,
                "parent_sha256": parent.content_sha256 if parent else None,
            }
            return await self.repository.add(
                LabRegulatoryAssessmentVersion(
                    assessment_id=assessment_id,
                    version_number=version_number,
                    schema_version=command.schema_version,
                    subject_type=command.subject_type,
                    subject_id=command.subject_id,
                    parent_version_id=parent.id if parent else None,
                    standard_identifier=command.standard_identifier,
                    standard_amendment=command.standard_amendment,
                    standard_state=command.standard_state,
                    source_evidence_record_id=(
                        command.source_evidence_record_id
                    ),
                    jurisdiction=command.jurisdiction,
                    product_category=command.product_category,
                    concentration_basis=command.concentration_basis,
                    finished_product_concentration=(
                        command.finished_product_concentration
                    ),
                    effective_date=command.effective_date,
                    evaluated_at=command.evaluated_at,
                    result_state=command.result_state,
                    assumptions_json=list(command.assumptions),
                    unresolved_json=list(command.unresolved),
                    permitted_wording=command.permitted_wording,
                    content_sha256=stable_json_hash(payload),
                    parent_sha256=parent.content_sha256 if parent else None,
                )
            )

    async def record_regulatory_finding(
        self,
        command: RegulatoryFindingInput,
    ) -> LabRegulatoryFinding:
        async with self._transaction():
            if (
                await self.repository.get_regulatory_assessment_version(
                    command.regulatory_assessment_version_id
                )
                is None
            ):
                raise ScienceAuthorityConflictError(
                    "REGULATORY_ASSESSMENT_NOT_FOUND",
                    "Regulatory assessment version not found.",
                )
            if command.restriction_id is not None and (
                await self.repository.get_restriction(command.restriction_id)
                is None
            ):
                raise ScienceAuthorityConflictError(
                    "RESTRICTION_NOT_FOUND",
                    f"Restriction not found: {command.restriction_id}.",
                )
            if command.material_id is not None and (
                await self.repository.get_material(command.material_id) is None
            ):
                raise ScienceAuthorityConflictError(
                    "MATERIAL_NOT_FOUND",
                    f"Material not found: {command.material_id}.",
                )
            await self._require_evidence(command.evidence_record_id)
            if command.result_state == "PASS" and (
                command.observed_fraction is None
                or command.maximum_fraction is None
                or command.concentration_basis is None
                or command.observed_fraction > command.maximum_fraction
            ):
                raise ScienceAuthorityConflictError(
                    "REGULATORY_FINDING_PASS_NOT_SUPPORTED",
                    "A PASS finding requires comparable fractions within the limit.",
                )
            payload = {
                "schema": "lab-regulatory-finding-v1",
                **{
                    field: getattr(command, field)
                    for field in command.__dataclass_fields__
                },
            }
            return await self.repository.add(
                LabRegulatoryFinding(
                    regulatory_assessment_version_id=(
                        command.regulatory_assessment_version_id
                    ),
                    finding_key=command.finding_key,
                    restriction_id=command.restriction_id,
                    material_id=command.material_id,
                    substance_identity=command.substance_identity,
                    observed_fraction=command.observed_fraction,
                    maximum_fraction=command.maximum_fraction,
                    concentration_basis=command.concentration_basis,
                    result_state=command.result_state,
                    detail=command.detail,
                    evidence_record_id=command.evidence_record_id,
                    content_sha256=stable_json_hash(payload),
                )
            )

    async def create_claim_assessment_version(
        self,
        command: ClaimAssessmentInput,
        *,
        parent_version_id: str | None = None,
    ) -> LabClaimAssessmentVersion:
        # Exhaustive dispatch is deliberately performed before any lookup or
        # persistence.  Historical rows remain readable, but new writes may
        # use only the two reviewed contracts.
        if command.schema_version not in {"a2-claim-v1", "a4-claim-v1"}:
            raise ScienceAuthorityConflictError(
                "CLAIM_SCHEMA_UNSUPPORTED",
                f"Unsupported claim schema: {command.schema_version}.",
            )
        if command.schema_version == "a2-claim-v1" and command.decision not in {
            "ADVISORY_ONLY",
            "WITHHOLD_UNKNOWN",
        }:
            raise ScienceAuthorityConflictError(
                "CLAIM_LEGACY_DECISION_EXCEEDS_CEILING",
                "New A2 claim writes are limited to ADVISORY_ONLY or "
                "WITHHOLD_UNKNOWN.",
            )
        if (
            command.schema_version == "a4-claim-v1"
            and command.policy_version != "a4-policy-v1"
        ):
            raise ScienceAuthorityConflictError(
                "CLAIM_POLICY_UNSUPPORTED",
                "A4 claims require the server-owned a4-policy-v1 path.",
            )
        async with self._transaction():
            if not await self._science_subject_exists(
                command.subject_type,
                command.subject_id,
            ):
                raise ScienceAuthorityConflictError(
                    "CLAIM_SUBJECT_NOT_FOUND",
                    f"Claim subject not found: {command.subject_id}.",
                )
            for link in command.evidence_links:
                await self._require_evidence(link.evidence_record_id)
            authority_payload = dict(command.authority)
            permitted_wording = command.permitted_wording
            forbidden_wording = command.forbidden_wording
            if command.schema_version == "a2-claim-v1":
                authority_payload = {
                    "authority_scope": "LEGACY_ADVISORY_ONLY",
                    "release_authority": False,
                    "safety_authority": False,
                    "compounding_authority": False,
                    "caller_authority_discarded": True,
                }
                permitted_wording = (
                    "Advisory evidence only; no release, safety, or "
                    "compounding authority."
                    if command.decision == "ADVISORY_ONLY"
                    else None
                )
                forbidden_wording = (
                    "Do not describe this legacy assessment as validated, "
                    "safe, compliant, executable, or release-authorized."
                )
            if command.schema_version == "a4-claim-v1":
                try:
                    authority_input = ClaimAuthorityInput.from_mapping(
                        command.claim_type,
                        authority_payload,
                    )
                except ValueError as exc:
                    raise ScienceAuthorityConflictError(
                        "CLAIM_AUTHORITY_INPUT_INVALID",
                        str(exc),
                    ) from exc
                authority_input = replace(
                    authority_input,
                    contradiction_present=(
                        authority_input.contradiction_present
                        or bool(command.conflicts)
                    ),
                    human_reviewed=(
                        command.human_review_state == "APPROVED"
                    ),
                    documentary_support=(
                        authority_input.documentary_support
                        or bool(command.evidence_links)
                    ),
                )
                authority_evaluation = evaluate_claim_authority(
                    authority_input
                )
                maximum_decision = authority_evaluation.decision
                reasons = list(authority_evaluation.reasons)
                if command.missing_evidence:
                    maximum_decision = ClaimDecision.WITHHOLD_UNKNOWN
                    if GateReason.EVIDENCE_INCOMPLETE not in reasons:
                        reasons.append(GateReason.EVIDENCE_INCOMPLETE)
                if not isinstance(maximum_decision, ClaimDecision):
                    raise ScienceAuthorityConflictError(
                        "CLAIM_AUTHORITY_INPUT_INVALID",
                        "Claim evaluator returned no claim decision.",
                    )
                if not decision_within_authority(
                    command.decision,
                    maximum_decision,
                ):
                    raise ScienceAuthorityConflictError(
                        "CLAIM_DECISION_EXCEEDS_AUTHORITY",
                        "Requested claim decision exceeds computed "
                        f"authority {maximum_decision.value}: "
                        + ", ".join(reason.value for reason in reasons),
                    )
                authority_payload = {
                    field.name: getattr(authority_input, field.name)
                    for field in dataclass_fields(ClaimAuthorityInput)
                    if field.name != "claim_type"
                }
                authority_payload.update(
                    {
                        "gate_schema": "a4-claim-authority-v1",
                        "computed_maximum_decision": maximum_decision.value,
                        "computed_reasons": [reason.value for reason in reasons],
                        "release_authority": False,
                        "safety_authority": False,
                        "compounding_authority": False,
                    }
                )
            if command.decision == "ALLOW_EXACT":
                direct_evidence_ids = {
                    link.evidence_record_id
                    for link in command.evidence_links
                    if link.role == "DIRECT"
                }
                has_direct = bool(direct_evidence_ids)
                if (
                    not has_direct
                    or command.missing_evidence
                    or command.conflicts
                    or command.permitted_wording is None
                    or command.human_review_state
                    not in {"APPROVED", "NOT_REQUIRED"}
                ):
                    raise ScienceAuthorityConflictError(
                        "CLAIM_EXACT_NOT_SUPPORTED",
                        "Exact authority requires direct, complete, "
                        "conflict-free evidence and satisfied review.",
                    )
                if command.subject_type == "ANALYTICAL_RUN":
                    qc_records = await self.repository.analytical_qc_records(
                        command.subject_id
                    )
                    if not qc_records or any(
                        record.status != "PASS" for record in qc_records
                    ):
                        raise ScienceAuthorityConflictError(
                            "ANALYTICAL_QC_NOT_ACCEPTED",
                            "Exact analytical authority requires passing QC.",
                        )
                    assessment_id = command.authority.get(
                        "analytical_authority_assessment_id"
                    )
                    b5_assessment = (
                        await self.repository.get_analytical_claim_assessment(
                            str(assessment_id)
                        )
                        if assessment_id is not None
                        else None
                    )
                    expected_b5_claim_type = {
                        "ANALYTICAL_IDENTITY": "IDENTITY",
                        "ANALYTICAL_QUANTITY": "QUANTITY",
                    }.get(command.claim_type)
                    # A4 is the server-owned claim policy.  B5 remains the
                    # analytical assessment policy that produced the bound
                    # run-level support; requiring both objects to share one
                    # policy identifier would make the reviewed A4 exact path
                    # impossible by construction.
                    expected_b5_policy_version = (
                        "b5-analytical-claim-v1"
                        if command.schema_version == "a4-claim-v1"
                        else command.policy_version
                    )
                    if (
                        b5_assessment is None
                        or b5_assessment.analytical_run_id != command.subject_id
                        or b5_assessment.decision != "SUPPORTED_FOR_SCOPE"
                        or b5_assessment.claim_type != expected_b5_claim_type
                        or b5_assessment.policy_version
                        != expected_b5_policy_version
                        or b5_assessment.evidence_record_id
                        not in direct_evidence_ids
                    ):
                        raise ScienceAuthorityConflictError(
                            "ANALYTICAL_B5_AUTHORITY_REQUIRED",
                            "Exact analytical authority requires a matching "
                            "supported B5 assessment.",
                        )
                    authority_payload[
                        "analytical_authority_assessment_id"
                    ] = str(assessment_id)
            parent = None
            if parent_version_id is None:
                claim_id = str(uuid4())
                version_number = 1
            else:
                parent = await self.repository.get_claim_assessment_version(
                    parent_version_id
                )
                if parent is None:
                    raise ScienceAuthorityConflictError(
                        "CLAIM_PARENT_NOT_FOUND",
                        f"Claim parent not found: {parent_version_id}.",
                    )
                latest = await self.repository.latest_claim_assessment_version(
                    parent.claim_id
                )
                if latest is None or latest.id != parent.id:
                    raise ScienceAuthorityConflictError(
                        "CLAIM_PARENT_NOT_LATEST",
                        "Claim revision must use the latest parent.",
                    )
                claim_id = parent.claim_id
                version_number = parent.version_number + 1
            evidence_payload = tuple(
                {
                    "evidence_record_id": link.evidence_record_id,
                    "role": link.role,
                }
                for link in sorted(
                    command.evidence_links,
                    key=lambda item: (item.role, item.evidence_record_id),
                )
            )
            payload: dict[str, Any] = {
                "schema": "lab-claim-assessment-v1",
                "claim_id": claim_id,
                "version_number": version_number,
                "schema_version": command.schema_version,
                "claim_type": command.claim_type,
                "subject_type": command.subject_type,
                "subject_id": command.subject_id,
                "policy_version": command.policy_version,
                "decision": command.decision,
                "authority": authority_payload,
                "missing_evidence": command.missing_evidence,
                "conflicts": command.conflicts,
                "permitted_wording": permitted_wording,
                "forbidden_wording": forbidden_wording,
                "human_review_state": command.human_review_state,
                "reviewer_pseudonym": command.reviewer_pseudonym,
                "reviewed_at": _dated(command.reviewed_at),
                "evidence_links": evidence_payload,
                "parent_sha256": parent.content_sha256 if parent else None,
            }
            assessment = await self.repository.add(
                LabClaimAssessmentVersion(
                    claim_id=claim_id,
                    version_number=version_number,
                    schema_version=command.schema_version,
                    claim_type=command.claim_type,
                    subject_type=command.subject_type,
                    subject_id=command.subject_id,
                    parent_version_id=parent.id if parent else None,
                    policy_version=command.policy_version,
                    decision=command.decision,
                    authority_json=authority_payload,
                    missing_evidence_json=list(command.missing_evidence),
                    conflicts_json=list(command.conflicts),
                    permitted_wording=permitted_wording,
                    forbidden_wording=forbidden_wording,
                    human_review_state=command.human_review_state,
                    reviewer_pseudonym=command.reviewer_pseudonym,
                    reviewed_at=command.reviewed_at,
                    content_sha256=stable_json_hash(payload),
                    parent_sha256=parent.content_sha256 if parent else None,
                )
            )
            for link in command.evidence_links:
                await self.repository.add(
                    LabClaimAssessmentEvidenceLink(
                        claim_assessment_version_id=assessment.id,
                        evidence_record_id=link.evidence_record_id,
                        role=link.role,
                    )
                )
            return assessment


__all__ = [
    "AnalyticalAttachmentInput",
    "AnalyticalMethodInput",
    "AnalyticalPeakInput",
    "AnalyticalQCInput",
    "AnalyticalRunInput",
    "ClaimAssessmentInput",
    "ClaimEvidenceInput",
    "GCOEventInput",
    "LabScienceServiceMixin",
    "RegulatoryAssessmentInput",
    "RegulatoryFindingInput",
    "ScienceAuthorityConflictError",
    "ScienceAuthorityError",
]
