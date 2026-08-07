"""Fail-closed B5 analytical method, run, QC, and claim authority."""

from __future__ import annotations

import json
from collections.abc import Mapping
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from math import isclose, isfinite
from typing import TYPE_CHECKING, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lab_analytical import (
    ANALYTICAL_CLAIM_TYPES,
    ANALYTICAL_IDENTITY_AUTHORITY_STATES,
    ANALYTICAL_METHOD_AUTHORITY_STATUSES,
    ANALYTICAL_PRIMARY_SUBJECT_TYPES,
    ANALYTICAL_QUANTITATION_STATES,
    ANALYTICAL_RUN_DISPOSITIONS,
    ANALYTICAL_SEQUENCE_ENTRY_ROLES,
    ANALYTICAL_SEQUENCE_STATUSES,
    ANALYTICAL_STANDARD_MATCH_STATES,
    GCO_TRAINING_STATES,
    GCO_WINDOW_BASES,
    METHOD_VALIDATION_RESULTS,
    LabAnalyticalClaimAssessment,
    LabAnalyticalMethodAuthority,
    LabAnalyticalPeakAuthority,
    LabAnalyticalRunAuthority,
    LabAnalyticalSequence,
    LabAnalyticalSequenceEntry,
    LabGCOEventAuthority,
    LabMethodValidationRecord,
)

if TYPE_CHECKING:
    from app.repositories.lab import LabRepository

METHOD_COMPONENT_KEYS = {
    "instrument": frozenset({"identifier", "manufacturer", "model"}),
    "detector": frozenset({"type", "configuration"}),
    "software": frozenset({"name", "version", "processing_version"}),
    "separation": frozenset(
        {
            "column",
            "stationary_phase",
            "temperature_program",
            "carrier_gas",
            "carrier_flow",
        }
    ),
    "acquisition": frozenset(
        {
            "inlet",
            "split",
            "injection",
            "detector_conditions",
            "acquisition_conditions",
        }
    ),
    "sample_preparation": frozenset(
        {"procedure", "dilution_factor", "solvent"}
    ),
    "standards": frozenset({"internal", "external", "retention_index"}),
    "calibration": frozenset(
        {
            "design",
            "working_range",
            "matrix_scope",
            "analyte_scope",
            "method_scope",
        }
    ),
    "response_factors": frozenset({"policy", "values"}),
    "identity_criteria": frozenset(
        {"retention_index", "spectrum", "authentic_standard"}
    ),
    "integration_policy": frozenset({"integration", "deconvolution"}),
    "qc_plan": frozenset({"required_checks", "failure_policy"}),
    "raw_data_policy": frozenset(
        {"vendor_format", "open_format", "preservation"}
    ),
}
HS_SPME_KEYS = frozenset(
    {
        "fiber",
        "conditioning",
        "vial",
        "sample_mass",
        "headspace_volume",
        "incubation",
        "extraction",
        "agitation",
        "desorption",
    }
)
ANALYTICAL_QC_CHECK_TYPES = (
    "BLANK",
    "DRIFT_CHECK",
    "CALIBRATION_VERIFICATION",
    "INTERNAL_STANDARD",
    "RI_STANDARD",
    "DUPLICATE",
    "CONTROL_SAMPLE",
)
ANALYTICAL_MISSING_REQUIREMENT_CODES = (
    "METHOD_AUTHORITY_MISSING",
    "METHOD_STATUS_INSUFFICIENT",
    "METHOD_VALIDATION_MISSING",
    "METHOD_VALIDATION_FAILED",
    "SEQUENCE_NOT_ACQUIRED",
    "RAW_VENDOR_DATA_MISSING",
    "OPEN_EXPORT_MISSING",
    "RUN_DISPOSITION_BLOCKING",
    "QC_REQUIRED_CHECK_MISSING",
    "QC_REQUIRED_CHECK_UNRESOLVED",
    "QC_FAILED_BLOCKING",
    "IDENTITY_EVIDENCE_INSUFFICIENT",
    "CALIBRATION_MISSING",
    "QUANTITATION_BASIS_INVALID",
    "UNCERTAINTY_MISSING",
    "APPLICABILITY_MISMATCH",
    "REVIEW_MISSING",
)
ANALYTICAL_QUALIFICATION_CODES = ("QC_FAILED_QUALIFYING",)
VALIDATION_CHARACTERISTIC_KEYS = (
    "selectivity_specificity",
    "calibration_function",
    "working_range",
    "residual_behavior",
    "weighting",
    "limit_of_detection",
    "limit_of_quantitation",
    "trueness_recovery",
    "repeatability",
    "intermediate_precision",
    "robustness_ruggedness",
    "matrix_effect",
    "carryover",
    "sample_stability",
    "blank_behavior",
    "sampling_preparation_uncertainty",
    "measurement_uncertainty",
)
CALIBRATED_QUANTITATION_KEYS = frozenset(
    {
        "calibration_reference",
        "standard_reference",
        "response_factor",
        "working_range",
        "dilution_factor",
        "blank_correction",
        "qc_types",
        "quantity",
        "quantity_unit",
        "quantity_basis",
        "measurement_uncertainty",
        "matrix_calibration_id",
        "analyte_calibration_id",
        "method_calibration_id",
    }
)


class AnalyticalAuthorityError(ValueError):
    """Raised when analytical input cannot satisfy the B5 contract."""


class AnalyticalAuthorityConflictError(AnalyticalAuthorityError):
    """Raised when referenced canonical state cannot support the command."""

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
        raise AnalyticalAuthorityError(
            "analytical authority values must be finite canonical JSON"
        ) from exc


def canonical_json_sha256(value: Any) -> str:
    return sha256(_canonical(value).encode("utf-8")).hexdigest()


def _text(value: str, field: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise AnalyticalAuthorityError(f"{field} must not be empty")
    return normalized


def _choice(value: str, field: str, choices: tuple[str, ...]) -> str:
    normalized = _text(value, field).upper()
    if normalized not in choices:
        raise AnalyticalAuthorityError(
            f"{field} must be one of: {', '.join(choices)}"
        )
    return normalized


def _aware(value: datetime, field: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise AnalyticalAuthorityError(f"{field} must be timezone-aware")
    return value


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _finite(
    value: float,
    field: str,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    normalized = float(value)
    if not isfinite(normalized):
        raise AnalyticalAuthorityError(f"{field} must be finite")
    if minimum is not None and normalized < minimum:
        raise AnalyticalAuthorityError(
            f"{field} must be at least {minimum}"
        )
    if maximum is not None and normalized > maximum:
        raise AnalyticalAuthorityError(
            f"{field} must be at most {maximum}"
        )
    return normalized


def _tuple_text(values: tuple[str, ...], field: str) -> tuple[str, ...]:
    normalized = tuple(_text(value, field) for value in values)
    if not normalized:
        raise AnalyticalAuthorityError(f"{field} must not be empty")
    if len(normalized) != len(set(normalized)):
        raise AnalyticalAuthorityError(f"{field} must not contain duplicates")
    return normalized


def _mapping(
    value: Mapping[str, Any],
    field: str,
    *,
    required_keys: frozenset[str] | None = None,
    exact_keys: bool = False,
) -> dict[str, Any]:
    normalized = dict(value)
    _canonical(normalized)
    if not normalized:
        raise AnalyticalAuthorityError(f"{field} must not be empty")
    if required_keys is not None:
        missing = required_keys.difference(normalized)
        if missing:
            raise AnalyticalAuthorityError(
                f"{field} is missing required keys: {', '.join(sorted(missing))}"
            )
        unknown = set(normalized).difference(required_keys)
        if exact_keys and unknown:
            raise AnalyticalAuthorityError(
                f"{field} contains unknown keys: {', '.join(sorted(unknown))}"
            )
        empty = [
            key
            for key in required_keys
            if normalized[key] is None
            or isinstance(normalized[key], str)
            and not normalized[key].strip()
        ]
        if empty:
            raise AnalyticalAuthorityError(
                f"{field} contains empty values: {', '.join(sorted(empty))}"
            )
    return normalized


def _json_mapping(
    value: Mapping[str, Any],
    field: str,
) -> dict[str, Any]:
    normalized = dict(value)
    try:
        _canonical(normalized)
    except AnalyticalAuthorityError as exc:
        raise AnalyticalAuthorityError(f"{field} is invalid: {exc}") from exc
    return normalized


def _method_component(
    value: Mapping[str, Any],
    field: str,
) -> dict[str, Any]:
    return _mapping(
        value,
        field,
        required_keys=METHOD_COMPONENT_KEYS[field],
        exact_keys=True,
    )


def _qc_plan(value: Mapping[str, Any]) -> dict[str, Any]:
    normalized = _method_component(value, "qc_plan")
    raw_checks = normalized["required_checks"]
    if not isinstance(raw_checks, (list, tuple)):
        raise AnalyticalAuthorityError(
            "qc_plan.required_checks must be an ordered list"
        )
    checks = tuple(
        _choice(str(item), "qc_plan.required_checks", ANALYTICAL_QC_CHECK_TYPES)
        for item in raw_checks
    )
    if not checks or len(checks) != len(set(checks)):
        raise AnalyticalAuthorityError(
            "qc_plan.required_checks must be nonempty and unique"
        )
    raw_policy = normalized["failure_policy"]
    if not isinstance(raw_policy, Mapping):
        raise AnalyticalAuthorityError(
            "qc_plan.failure_policy must be an object"
        )
    policy = {
        _choice(str(key), "qc_plan.failure_policy key", ANALYTICAL_QC_CHECK_TYPES):
        _choice(
            str(disposition),
            "qc_plan.failure_policy disposition",
            ("BLOCK", "QUALIFY"),
        )
        for key, disposition in raw_policy.items()
    }
    if set(policy) != set(checks):
        raise AnalyticalAuthorityError(
            "qc_plan.failure_policy must define every required check exactly"
        )
    return {
        "required_checks": list(checks),
        "failure_policy": {key: policy[key] for key in sorted(policy)},
    }


@dataclass(frozen=True, slots=True)
class AnalyticalMethodAuthorityInput:
    method_version_id: str
    schema_version: str
    status: str
    analyte_scope: tuple[str, ...]
    instrument: Mapping[str, Any]
    detector: Mapping[str, Any]
    software: Mapping[str, Any]
    separation: Mapping[str, Any]
    acquisition: Mapping[str, Any]
    sample_preparation: Mapping[str, Any]
    hs_spme: Mapping[str, Any] | None
    standards: Mapping[str, Any]
    calibration: Mapping[str, Any]
    response_factors: Mapping[str, Any]
    identity_criteria: Mapping[str, Any]
    integration_policy: Mapping[str, Any]
    qc_plan: Mapping[str, Any]
    raw_data_policy: Mapping[str, Any]
    source_document_version_id: str
    source_locator: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "method_version_id",
            _text(self.method_version_id, "method_version_id"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _text(self.schema_version, "schema_version"),
        )
        object.__setattr__(
            self,
            "status",
            _choice(
                self.status,
                "status",
                ANALYTICAL_METHOD_AUTHORITY_STATUSES,
            ),
        )
        object.__setattr__(
            self,
            "analyte_scope",
            _tuple_text(self.analyte_scope, "analyte_scope"),
        )
        for field in METHOD_COMPONENT_KEYS:
            value = getattr(self, field)
            normalized = (
                _qc_plan(value)
                if field == "qc_plan"
                else _method_component(value, field)
            )
            object.__setattr__(self, field, normalized)
        if self.hs_spme is not None:
            object.__setattr__(
                self,
                "hs_spme",
                _mapping(
                    self.hs_spme,
                    "hs_spme",
                    required_keys=HS_SPME_KEYS,
                    exact_keys=True,
                ),
            )
        object.__setattr__(
            self,
            "source_document_version_id",
            _text(
                self.source_document_version_id,
                "source_document_version_id",
            ),
        )
        object.__setattr__(
            self,
            "source_locator",
            _mapping(self.source_locator, "source_locator"),
        )


@dataclass(frozen=True, slots=True)
class MethodValidationInput:
    method_authority_id: str
    intended_claim: str
    matrix_scope: Mapping[str, Any]
    characteristics: Mapping[str, Any]
    acceptance_criteria: Mapping[str, Any]
    result: str
    limitations: tuple[str, ...]
    measurement_uncertainty: Mapping[str, Any]
    reviewer_pseudonym: str
    reviewed_at: datetime
    source_document_version_id: str
    source_locator: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "method_authority_id",
            _text(self.method_authority_id, "method_authority_id"),
        )
        object.__setattr__(
            self,
            "intended_claim",
            _text(self.intended_claim, "intended_claim"),
        )
        object.__setattr__(
            self,
            "matrix_scope",
            _mapping(self.matrix_scope, "matrix_scope"),
        )
        object.__setattr__(
            self,
            "characteristics",
            _mapping(
                self.characteristics,
                "characteristics",
                required_keys=frozenset(VALIDATION_CHARACTERISTIC_KEYS),
                exact_keys=True,
            ),
        )
        object.__setattr__(
            self,
            "acceptance_criteria",
            _mapping(self.acceptance_criteria, "acceptance_criteria"),
        )
        object.__setattr__(
            self,
            "result",
            _choice(self.result, "result", METHOD_VALIDATION_RESULTS),
        )
        object.__setattr__(
            self,
            "limitations",
            _tuple_text(self.limitations, "limitations"),
        )
        object.__setattr__(
            self,
            "measurement_uncertainty",
            _mapping(
                self.measurement_uncertainty,
                "measurement_uncertainty",
            ),
        )
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
        object.__setattr__(
            self,
            "source_document_version_id",
            _text(
                self.source_document_version_id,
                "source_document_version_id",
            ),
        )
        object.__setattr__(
            self,
            "source_locator",
            _mapping(self.source_locator, "source_locator"),
        )


@dataclass(frozen=True, slots=True)
class AnalyticalSequenceEntryInput:
    injection_order: int
    role: str
    reference: str
    level: Mapping[str, Any]

    def __post_init__(self) -> None:
        order = int(self.injection_order)
        if order < 1:
            raise AnalyticalAuthorityError(
                "injection_order must be at least one"
            )
        object.__setattr__(self, "injection_order", order)
        object.__setattr__(
            self,
            "role",
            _choice(self.role, "role", ANALYTICAL_SEQUENCE_ENTRY_ROLES),
        )
        object.__setattr__(
            self,
            "reference",
            _text(self.reference, "reference"),
        )
        object.__setattr__(
            self,
            "level",
            _mapping(self.level, "level"),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "injection_order": self.injection_order,
            "role": self.role,
            "reference": self.reference,
            "level": dict(self.level),
        }


@dataclass(frozen=True, slots=True)
class AnalyticalSequenceInput:
    sequence_key: str
    method_authority_id: str
    instrument_identifier: str
    status: str
    acquired_at: datetime | None
    entries: tuple[AnalyticalSequenceEntryInput, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "sequence_key",
            _text(self.sequence_key, "sequence_key"),
        )
        object.__setattr__(
            self,
            "method_authority_id",
            _text(self.method_authority_id, "method_authority_id"),
        )
        object.__setattr__(
            self,
            "instrument_identifier",
            _text(self.instrument_identifier, "instrument_identifier"),
        )
        status = _choice(
            self.status,
            "status",
            ANALYTICAL_SEQUENCE_STATUSES,
        )
        object.__setattr__(self, "status", status)
        acquired_at = self.acquired_at
        if acquired_at is not None:
            acquired_at = _aware(acquired_at, "acquired_at")
        if status == "ACQUIRED" and acquired_at is None:
            raise AnalyticalAuthorityError(
                "acquired_at is required for an acquired sequence"
            )
        object.__setattr__(self, "acquired_at", acquired_at)
        entries = tuple(self.entries)
        if not entries:
            raise AnalyticalAuthorityError("entries must not be empty")
        expected = tuple(range(1, len(entries) + 1))
        observed = tuple(entry.injection_order for entry in entries)
        if observed != expected:
            raise AnalyticalAuthorityError(
                "sequence injection_order values must be contiguous from one"
            )
        object.__setattr__(self, "entries", entries)


@dataclass(frozen=True, slots=True)
class AnalyticalRunAuthorityInput:
    analytical_run_id: str
    method_authority_id: str
    sequence_id: str
    sequence_entry_id: str
    subject_type: str
    subject_id: str
    subject_stream_sequence: int | None
    matrix_scope: Mapping[str, Any]
    applicability: Mapping[str, Any]
    instrument_state: Mapping[str, Any]
    processing_details: Mapping[str, Any]
    deviation_assessment: Mapping[str, Any]
    reviewer_pseudonym: str
    reviewed_at: datetime
    disposition: str
    raw_vendor_attachment_id: str
    open_export_attachment_id: str

    def __post_init__(self) -> None:
        for field in (
            "analytical_run_id",
            "method_authority_id",
            "sequence_id",
            "sequence_entry_id",
            "subject_id",
            "raw_vendor_attachment_id",
            "open_export_attachment_id",
        ):
            object.__setattr__(
                self,
                field,
                _text(getattr(self, field), field),
            )
        subject_type = _choice(
            self.subject_type,
            "subject_type",
            ANALYTICAL_PRIMARY_SUBJECT_TYPES,
        )
        object.__setattr__(self, "subject_type", subject_type)
        stream_sequence = (
            int(self.subject_stream_sequence)
            if self.subject_stream_sequence is not None
            else None
        )
        if subject_type == "BOTTLE_STREAM":
            if stream_sequence is None or stream_sequence < 1:
                raise AnalyticalAuthorityError(
                    "BOTTLE_STREAM requires a positive subject_stream_sequence"
                )
        elif stream_sequence is not None:
            raise AnalyticalAuthorityError(
                "subject_stream_sequence is only valid for BOTTLE_STREAM"
            )
        object.__setattr__(
            self,
            "subject_stream_sequence",
            stream_sequence,
        )
        for field in (
            "matrix_scope",
            "applicability",
            "instrument_state",
            "processing_details",
            "deviation_assessment",
        ):
            object.__setattr__(
                self,
                field,
                _mapping(getattr(self, field), field),
            )
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
        object.__setattr__(
            self,
            "disposition",
            _choice(
                self.disposition,
                "disposition",
                ANALYTICAL_RUN_DISPOSITIONS,
            ),
        )
        if self.raw_vendor_attachment_id == self.open_export_attachment_id:
            raise AnalyticalAuthorityError(
                "raw vendor and open export attachments must be distinct"
            )


@dataclass(frozen=True, slots=True)
class AnalyticalPeakAuthorityInput:
    analytical_peak_id: str
    analytical_run_authority_id: str
    identity_state: str
    identity_label: str | None
    stationary_phase: str
    spectrum: Mapping[str, Any]
    deconvolution: Mapping[str, Any]
    library_candidates: tuple[Mapping[str, Any], ...]
    exact_mass: Mapping[str, Any]
    authentic_standard_state: str
    co_injection_state: str
    quantifier_ions: tuple[int, ...]
    coelution: Mapping[str, Any]
    manual_review: Mapping[str, Any]
    identity_decision: Mapping[str, Any]
    quantitation_state: str
    quantitation: Mapping[str, Any]
    applicability: Mapping[str, Any]
    reviewer_pseudonym: str
    reviewed_at: datetime

    def __post_init__(self) -> None:
        for field in ("analytical_peak_id", "analytical_run_authority_id"):
            object.__setattr__(
                self,
                field,
                _text(getattr(self, field), field),
            )
        identity_state = _choice(
            self.identity_state,
            "identity_state",
            ANALYTICAL_IDENTITY_AUTHORITY_STATES,
        )
        object.__setattr__(self, "identity_state", identity_state)
        identity_label = _optional_text(self.identity_label)
        if identity_state in {"UNRESOLVED", "REJECTED"}:
            if identity_label is not None:
                raise AnalyticalAuthorityError(
                    "unresolved or rejected identity cannot expose a label"
                )
        elif identity_label is None:
            raise AnalyticalAuthorityError(
                "resolved identity states require identity_label"
            )
        object.__setattr__(self, "identity_label", identity_label)
        object.__setattr__(
            self,
            "stationary_phase",
            _text(self.stationary_phase, "stationary_phase"),
        )
        for field in (
            "spectrum",
            "deconvolution",
            "exact_mass",
            "coelution",
            "manual_review",
            "identity_decision",
        ):
            object.__setattr__(
                self,
                field,
                _json_mapping(getattr(self, field), field),
            )
        candidates = tuple(dict(candidate) for candidate in self.library_candidates)
        _canonical(candidates)
        object.__setattr__(self, "library_candidates", candidates)
        for field in ("authentic_standard_state", "co_injection_state"):
            object.__setattr__(
                self,
                field,
                _choice(
                    getattr(self, field),
                    field,
                    ANALYTICAL_STANDARD_MATCH_STATES,
                ),
            )
        ions = tuple(int(ion) for ion in self.quantifier_ions)
        if any(ion <= 0 for ion in ions) or len(ions) != len(set(ions)):
            raise AnalyticalAuthorityError(
                "quantifier_ions must be unique positive integers"
            )
        object.__setattr__(self, "quantifier_ions", ions)
        quantitation_state = _choice(
            self.quantitation_state,
            "quantitation_state",
            ANALYTICAL_QUANTITATION_STATES,
        )
        object.__setattr__(self, "quantitation_state", quantitation_state)
        quantitation = self._normalize_quantitation(
            quantitation_state,
            self.quantitation,
        )
        object.__setattr__(self, "quantitation", quantitation)
        object.__setattr__(
            self,
            "applicability",
            _mapping(self.applicability, "applicability"),
        )
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

    @staticmethod
    def _normalize_quantitation(
        state: str,
        value: Mapping[str, Any],
    ) -> dict[str, Any]:
        if state == "CALIBRATED_CONCENTRATION":
            normalized = _mapping(
                value,
                "quantitation",
                required_keys=CALIBRATED_QUANTITATION_KEYS,
                exact_keys=True,
            )
            normalized["response_factor"] = _finite(
                normalized["response_factor"],
                "quantitation.response_factor",
                minimum=0,
            )
            normalized["dilution_factor"] = _finite(
                normalized["dilution_factor"],
                "quantitation.dilution_factor",
                minimum=0,
            )
            normalized["blank_correction"] = _finite(
                normalized["blank_correction"],
                "quantitation.blank_correction",
            )
            normalized["quantity"] = _finite(
                normalized["quantity"],
                "quantitation.quantity",
                minimum=0,
            )
            working_range = _mapping(
                normalized["working_range"],
                "quantitation.working_range",
                required_keys=frozenset({"minimum", "maximum", "unit"}),
                exact_keys=True,
            )
            minimum = _finite(
                working_range["minimum"],
                "quantitation.working_range.minimum",
            )
            maximum = _finite(
                working_range["maximum"],
                "quantitation.working_range.maximum",
            )
            if maximum < minimum:
                raise AnalyticalAuthorityError(
                    "quantitation working-range maximum must not be below minimum"
                )
            working_range["minimum"] = minimum
            working_range["maximum"] = maximum
            normalized["working_range"] = working_range
            normalized["measurement_uncertainty"] = _mapping(
                normalized["measurement_uncertainty"],
                "quantitation.measurement_uncertainty",
            )
            qc_types = tuple(
                _choice(
                    str(item),
                    "quantitation.qc_types",
                    ANALYTICAL_QC_CHECK_TYPES,
                )
                for item in normalized["qc_types"]
            )
            if not qc_types:
                raise AnalyticalAuthorityError(
                    "quantitation.qc_types must not be empty"
                )
            normalized["qc_types"] = list(qc_types)
            for field in (
                "calibration_reference",
                "standard_reference",
                "quantity_unit",
                "quantity_basis",
                "matrix_calibration_id",
                "analyte_calibration_id",
                "method_calibration_id",
            ):
                normalized[field] = _text(
                    str(normalized[field]),
                    f"quantitation.{field}",
                )
            return normalized
        if state == "AREA_PERCENT_ONLY":
            normalized = _mapping(
                value,
                "quantitation",
                required_keys=frozenset({"area_percent", "quantity_basis"}),
                exact_keys=True,
            )
            normalized["area_percent"] = _finite(
                normalized["area_percent"],
                "quantitation.area_percent",
                minimum=0,
                maximum=100,
            )
            if str(normalized["quantity_basis"]).strip().lower() != (
                "peak_area_percent"
            ):
                raise AnalyticalAuthorityError(
                    "area percent cannot claim formula weight percent "
                    "or bulk concentration"
                )
            normalized["quantity_basis"] = "peak_area_percent"
            return normalized
        return _mapping(value, "quantitation")


@dataclass(frozen=True, slots=True)
class GCOEventAuthorityInput:
    gco_event_id: str
    analytical_run_authority_id: str
    assessor_training_state: str
    window_basis: str
    window_start: float
    window_end: float
    detection_method: str
    replicate_index: int
    replicate_count: int
    detection_frequency: float
    repeatability: Mapping[str, Any]
    aligned_peak_ids: tuple[str, ...]
    unknown_event: bool
    exact_identity_claim: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "gco_event_id",
            _text(self.gco_event_id, "gco_event_id"),
        )
        object.__setattr__(
            self,
            "analytical_run_authority_id",
            _text(
                self.analytical_run_authority_id,
                "analytical_run_authority_id",
            ),
        )
        object.__setattr__(
            self,
            "assessor_training_state",
            _choice(
                self.assessor_training_state,
                "assessor_training_state",
                GCO_TRAINING_STATES,
            ),
        )
        object.__setattr__(
            self,
            "window_basis",
            _choice(self.window_basis, "window_basis", GCO_WINDOW_BASES),
        )
        start = _finite(self.window_start, "window_start", minimum=0)
        end = _finite(self.window_end, "window_end", minimum=0)
        if end < start:
            raise AnalyticalAuthorityError(
                "window_end must not be below window_start"
            )
        object.__setattr__(self, "window_start", start)
        object.__setattr__(self, "window_end", end)
        object.__setattr__(
            self,
            "detection_method",
            _text(self.detection_method, "detection_method"),
        )
        replicate_index = int(self.replicate_index)
        replicate_count = int(self.replicate_count)
        if replicate_index < 1 or replicate_count < replicate_index:
            raise AnalyticalAuthorityError(
                "replicate_count must include the positive replicate_index"
            )
        object.__setattr__(self, "replicate_index", replicate_index)
        object.__setattr__(self, "replicate_count", replicate_count)
        object.__setattr__(
            self,
            "detection_frequency",
            _finite(
                self.detection_frequency,
                "detection_frequency",
                minimum=0,
                maximum=1,
            ),
        )
        object.__setattr__(
            self,
            "repeatability",
            _mapping(self.repeatability, "repeatability"),
        )
        aligned_peak_ids = tuple(
            _text(peak_id, "aligned_peak_ids")
            for peak_id in self.aligned_peak_ids
        )
        if len(aligned_peak_ids) != len(set(aligned_peak_ids)):
            raise AnalyticalAuthorityError(
                "aligned_peak_ids must not contain duplicates"
            )
        object.__setattr__(self, "aligned_peak_ids", aligned_peak_ids)
        if self.exact_identity_claim:
            raise AnalyticalAuthorityError(
                "GC-O evidence cannot claim exact chemical identity"
            )


@dataclass(frozen=True, slots=True)
class AnalyticalClaimRequest:
    analytical_run_authority_id: str
    peak_authority_id: str
    claim_type: str
    policy_version: str
    requested_scope: Mapping[str, Any]
    reviewer_pseudonym: str
    reviewed_at: datetime
    evidence_record_id: str

    def __post_init__(self) -> None:
        for field in (
            "analytical_run_authority_id",
            "peak_authority_id",
            "policy_version",
            "reviewer_pseudonym",
            "evidence_record_id",
        ):
            object.__setattr__(
                self,
                field,
                _text(getattr(self, field), field),
            )
        object.__setattr__(
            self,
            "claim_type",
            _choice(self.claim_type, "claim_type", ANALYTICAL_CLAIM_TYPES),
        )
        object.__setattr__(
            self,
            "requested_scope",
            _mapping(self.requested_scope, "requested_scope"),
        )
        object.__setattr__(
            self,
            "reviewed_at",
            _aware(self.reviewed_at, "reviewed_at"),
        )


class LabAnalyticalAuthorityServiceMixin:
    """B5 authority commands using the canonical transaction owner."""

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

    async def register_analytical_method_authority(
        self,
        command: AnalyticalMethodAuthorityInput,
    ) -> LabAnalyticalMethodAuthority:
        async with self._transaction():
            method = await self.repository.get_analytical_method_version(
                command.method_version_id
            )
            if method is None:
                raise AnalyticalAuthorityConflictError(
                    "ANALYTICAL_METHOD_NOT_FOUND",
                    f"Analytical method not found: {command.method_version_id}.",
                )
            expected_a2_status = {
                "EXPLORATORY": "DRAFT",
                "VERIFIED": "VALIDATED",
                "VALIDATED_FOR_SCOPE": "VALIDATED",
                "RETIRED": "RETIRED",
            }[command.status]
            if method.status != expected_a2_status:
                raise AnalyticalAuthorityConflictError(
                    "METHOD_STATUS_INCOMPATIBLE",
                    "B5 method status is incompatible with the A2 method status.",
                )
            if method.technique == "HS_SPME_GCMS" and command.hs_spme is None:
                raise AnalyticalAuthorityConflictError(
                    "HS_SPME_CONDITIONS_REQUIRED",
                    "HS-SPME methods require complete extraction conditions.",
                )
            if method.technique != "HS_SPME_GCMS" and command.hs_spme is not None:
                raise AnalyticalAuthorityConflictError(
                    "HS_SPME_CONDITIONS_NOT_APPLICABLE",
                    "HS-SPME conditions are allowed only for HS-SPME methods.",
                )
            source = await self.repository.get_source_document_version(
                command.source_document_version_id
            )
            if source is None:
                raise AnalyticalAuthorityConflictError(
                    "METHOD_SOURCE_NOT_FOUND",
                    "B5 method source document version was not found.",
                )
            if command.status in {"VERIFIED", "VALIDATED_FOR_SCOPE"} and not (
                await self.is_accepted_for_scoped_use(
                    "SOURCE_VERSION",
                    source.id,
                    required_scope="ANALYTICAL_METHOD_AUTHORITY",
                )
            ):
                raise AnalyticalAuthorityConflictError(
                    "METHOD_SOURCE_SCOPE_NOT_ACCEPTED",
                    "Verified method authority requires an accepted B1 source.",
                )
            existing = (
                await self.repository.analytical_method_authority_for_version(
                    method.id
                )
            )
            if existing is not None:
                raise AnalyticalAuthorityConflictError(
                    "METHOD_AUTHORITY_ALREADY_EXISTS",
                    "The A2 method version already has B5 authority.",
                )
            payload = {
                "schema": "lab-analytical-method-authority-v1",
                "method_version_id": method.id,
                "method_content_sha256": method.content_sha256,
                "schema_version": command.schema_version,
                "status": command.status,
                "analyte_scope": command.analyte_scope,
                "instrument": command.instrument,
                "detector": command.detector,
                "software": command.software,
                "separation": command.separation,
                "acquisition": command.acquisition,
                "sample_preparation": command.sample_preparation,
                "hs_spme": command.hs_spme,
                "standards": command.standards,
                "calibration": command.calibration,
                "response_factors": command.response_factors,
                "identity_criteria": command.identity_criteria,
                "integration_policy": command.integration_policy,
                "qc_plan": command.qc_plan,
                "raw_data_policy": command.raw_data_policy,
                "source_document_version_id": source.id,
                "source_record_sha256": source.record_sha256,
                "source_locator": command.source_locator,
                "source_artifact_sha256": source.artifact_sha256,
            }
            return await self.repository.add(
                LabAnalyticalMethodAuthority(
                    method_version_id=method.id,
                    schema_version=command.schema_version,
                    status=command.status,
                    analyte_scope_json=list(command.analyte_scope),
                    instrument_json=dict(command.instrument),
                    detector_json=dict(command.detector),
                    software_json=dict(command.software),
                    separation_json=dict(command.separation),
                    acquisition_json=dict(command.acquisition),
                    sample_preparation_json=dict(command.sample_preparation),
                    hs_spme_json=(
                        dict(command.hs_spme)
                        if command.hs_spme is not None
                        else None
                    ),
                    standards_json=dict(command.standards),
                    calibration_json=dict(command.calibration),
                    response_factors_json=dict(command.response_factors),
                    identity_criteria_json=dict(command.identity_criteria),
                    integration_policy_json=dict(command.integration_policy),
                    qc_plan_json=dict(command.qc_plan),
                    raw_data_policy_json=dict(command.raw_data_policy),
                    source_document_version_id=source.id,
                    source_locator_json=dict(command.source_locator),
                    source_artifact_sha256=source.artifact_sha256,
                    content_sha256=canonical_json_sha256(payload),
                )
            )

    async def record_method_validation(
        self,
        command: MethodValidationInput,
    ) -> LabMethodValidationRecord:
        async with self._transaction():
            authority = await self.repository.get_analytical_method_authority(
                command.method_authority_id
            )
            if authority is None:
                raise AnalyticalAuthorityConflictError(
                    "METHOD_AUTHORITY_NOT_FOUND",
                    "B5 analytical method authority was not found.",
                )
            source = await self.repository.get_source_document_version(
                command.source_document_version_id
            )
            if source is None:
                raise AnalyticalAuthorityConflictError(
                    "METHOD_VALIDATION_SOURCE_NOT_FOUND",
                    "Method-validation source document version was not found.",
                )
            if not await self.is_accepted_for_scoped_use(
                "SOURCE_VERSION",
                source.id,
                required_scope="ANALYTICAL_METHOD_AUTHORITY",
            ):
                raise AnalyticalAuthorityConflictError(
                    "METHOD_VALIDATION_SOURCE_NOT_ACCEPTED",
                    "Method validation requires an accepted B1 source.",
                )
            scope_payload = {
                "intended_claim": command.intended_claim,
                "matrix_scope": command.matrix_scope,
            }
            scope_sha256 = canonical_json_sha256(scope_payload)
            payload = {
                "schema": "lab-method-validation-record-v1",
                "method_authority_id": authority.id,
                "method_authority_sha256": authority.content_sha256,
                **scope_payload,
                "scope_sha256": scope_sha256,
                "characteristics": command.characteristics,
                "acceptance_criteria": command.acceptance_criteria,
                "result": command.result,
                "limitations": command.limitations,
                "measurement_uncertainty": command.measurement_uncertainty,
                "reviewer_pseudonym": command.reviewer_pseudonym,
                "reviewed_at": command.reviewed_at.isoformat(),
                "source_document_version_id": source.id,
                "source_record_sha256": source.record_sha256,
                "source_locator": command.source_locator,
                "source_artifact_sha256": source.artifact_sha256,
            }
            return await self.repository.add(
                LabMethodValidationRecord(
                    method_authority_id=authority.id,
                    intended_claim=command.intended_claim,
                    matrix_scope_json=dict(command.matrix_scope),
                    scope_sha256=scope_sha256,
                    characteristics_json=dict(command.characteristics),
                    acceptance_criteria_json=dict(
                        command.acceptance_criteria
                    ),
                    result=command.result,
                    limitations_json=list(command.limitations),
                    measurement_uncertainty_json=dict(
                        command.measurement_uncertainty
                    ),
                    reviewer_pseudonym=command.reviewer_pseudonym,
                    reviewed_at=command.reviewed_at,
                    source_document_version_id=source.id,
                    source_locator_json=dict(command.source_locator),
                    source_artifact_sha256=source.artifact_sha256,
                    content_sha256=canonical_json_sha256(payload),
                )
            )

    async def create_analytical_sequence(
        self,
        command: AnalyticalSequenceInput,
    ) -> LabAnalyticalSequence:
        async with self._transaction():
            method_authority = (
                await self.repository.get_analytical_method_authority(
                    command.method_authority_id
                )
            )
            if method_authority is None:
                raise AnalyticalAuthorityConflictError(
                    "METHOD_AUTHORITY_NOT_FOUND",
                    "B5 analytical method authority was not found.",
                )
            roles = {entry.role for entry in command.entries}
            if "SAMPLE" not in roles:
                raise AnalyticalAuthorityConflictError(
                    "SEQUENCE_SAMPLE_MISSING",
                    "An analytical sequence requires at least one sample.",
                )
            required_role_options = {
                "BLANK": {"METHOD_BLANK", "SOLVENT_BLANK"},
                "DRIFT_CHECK": {"QC_SAMPLE"},
                "CALIBRATION_VERIFICATION": {"CALIBRATION_STANDARD"},
                "INTERNAL_STANDARD": {"INTERNAL_STANDARD"},
                "RI_STANDARD": {"RI_STANDARD"},
                "DUPLICATE": {"DUPLICATE", "REPLICATE"},
                "CONTROL_SAMPLE": {"CONTROL"},
            }
            missing_checks = [
                check
                for check in method_authority.qc_plan_json["required_checks"]
                if not roles.intersection(required_role_options[check])
            ]
            if missing_checks:
                raise AnalyticalAuthorityConflictError(
                    "SEQUENCE_REQUIRED_ROLE_MISSING",
                    "Sequence is missing method-required roles: "
                    + ", ".join(sorted(missing_checks)),
                )
            entries_payload = [
                entry.as_dict() for entry in command.entries
            ]
            entries_sha256 = canonical_json_sha256(entries_payload)
            payload = {
                "schema": "lab-analytical-sequence-v1",
                "sequence_key": command.sequence_key,
                "method_authority_id": method_authority.id,
                "method_authority_sha256": (
                    method_authority.content_sha256
                ),
                "instrument_identifier": command.instrument_identifier,
                "status": command.status,
                "acquired_at": (
                    command.acquired_at.isoformat()
                    if command.acquired_at is not None
                    else None
                ),
                "entries": entries_payload,
                "entries_sha256": entries_sha256,
            }
            sequence = await self.repository.add(
                LabAnalyticalSequence(
                    sequence_key=command.sequence_key,
                    method_authority_id=method_authority.id,
                    instrument_identifier=command.instrument_identifier,
                    status=command.status,
                    entry_count=len(command.entries),
                    entries_sha256=entries_sha256,
                    acquired_at=command.acquired_at,
                    content_sha256=canonical_json_sha256(payload),
                )
            )
            for entry, entry_payload in zip(
                command.entries,
                entries_payload,
                strict=True,
            ):
                await self.repository.add(
                    LabAnalyticalSequenceEntry(
                        sequence_id=sequence.id,
                        injection_order=entry.injection_order,
                        role=entry.role,
                        reference=entry.reference,
                        level_json=dict(entry.level),
                        content_sha256=canonical_json_sha256(
                            {
                                "schema": (
                                    "lab-analytical-sequence-entry-v1"
                                ),
                                "sequence_id": sequence.id,
                                **entry_payload,
                            }
                        ),
                    )
                )
            return sequence

    async def bind_analytical_run_authority(
        self,
        command: AnalyticalRunAuthorityInput,
    ) -> LabAnalyticalRunAuthority:
        async with self._transaction():
            run = await self.repository.get_analytical_run(
                command.analytical_run_id
            )
            if run is None:
                raise AnalyticalAuthorityConflictError(
                    "ANALYTICAL_RUN_NOT_FOUND",
                    "A2 analytical run was not found.",
                )
            method_authority = (
                await self.repository.get_analytical_method_authority(
                    command.method_authority_id
                )
            )
            if (
                method_authority is None
                or method_authority.method_version_id
                != run.method_version_id
            ):
                raise AnalyticalAuthorityConflictError(
                    "RUN_METHOD_AUTHORITY_MISMATCH",
                    "Run and method authority do not bind the same method.",
                )
            sequence = await self.repository.get_analytical_sequence(
                command.sequence_id
            )
            if (
                sequence is None
                or sequence.method_authority_id != method_authority.id
                or sequence.status != "ACQUIRED"
            ):
                raise AnalyticalAuthorityConflictError(
                    "RUN_SEQUENCE_INVALID",
                    "Run authority requires an acquired matching sequence.",
                )
            await self._validate_analytical_primary_subject(command, run)
            entry = await self.repository.get_analytical_sequence_entry(
                command.sequence_entry_id
            )
            if (
                entry is None
                or entry.sequence_id != sequence.id
                or entry.role != "SAMPLE"
                or entry.reference != command.subject_id
            ):
                raise AnalyticalAuthorityConflictError(
                    "RUN_SEQUENCE_SAMPLE_INVALID",
                    "Run subject must match a sample entry in the sequence.",
                )
            vendor = await self.repository.get_analytical_attachment(
                command.raw_vendor_attachment_id
            )
            if (
                vendor is None
                or vendor.analytical_run_id != run.id
                or vendor.attachment_kind != "RAW_VENDOR_DATA"
                or len(vendor.content_sha256) != 64
            ):
                raise AnalyticalAuthorityConflictError(
                    "RAW_VENDOR_ATTACHMENT_INVALID",
                    "Run authority requires same-run RAW_VENDOR_DATA.",
                )
            open_export = await self.repository.get_analytical_attachment(
                command.open_export_attachment_id
            )
            if (
                open_export is None
                or open_export.analytical_run_id != run.id
                or open_export.attachment_kind != "OPEN_EXPORT"
                or len(open_export.content_sha256) != 64
            ):
                raise AnalyticalAuthorityConflictError(
                    "OPEN_EXPORT_ATTACHMENT_INVALID",
                    "Run authority requires a same-run OPEN_EXPORT.",
                )
            existing = (
                await self.repository.analytical_run_authority_for_run(run.id)
            )
            if existing is not None:
                raise AnalyticalAuthorityConflictError(
                    "RUN_AUTHORITY_ALREADY_EXISTS",
                    "The A2 run already has B5 authority.",
                )
            payload = {
                "schema": "lab-analytical-run-authority-v1",
                "analytical_run_id": run.id,
                "analytical_run_sha256": run.content_sha256,
                "method_authority_id": method_authority.id,
                "method_authority_sha256": (
                    method_authority.content_sha256
                ),
                "sequence_id": sequence.id,
                "sequence_sha256": sequence.content_sha256,
                "sequence_entry_id": entry.id,
                "sequence_entry_sha256": entry.content_sha256,
                "subject_type": command.subject_type,
                "subject_id": command.subject_id,
                "subject_stream_sequence": (
                    command.subject_stream_sequence
                ),
                "matrix_scope": command.matrix_scope,
                "applicability": command.applicability,
                "instrument_state": command.instrument_state,
                "processing_details": command.processing_details,
                "deviation_assessment": command.deviation_assessment,
                "reviewer_pseudonym": command.reviewer_pseudonym,
                "reviewed_at": command.reviewed_at.isoformat(),
                "disposition": command.disposition,
                "raw_vendor_attachment_id": vendor.id,
                "raw_vendor_sha256": vendor.content_sha256,
                "open_export_attachment_id": open_export.id,
                "open_export_sha256": open_export.content_sha256,
            }
            return await self.repository.add(
                LabAnalyticalRunAuthority(
                    analytical_run_id=run.id,
                    method_authority_id=method_authority.id,
                    sequence_id=sequence.id,
                    sequence_entry_id=entry.id,
                    subject_type=command.subject_type,
                    subject_id=command.subject_id,
                    subject_stream_sequence=(
                        command.subject_stream_sequence
                    ),
                    matrix_scope_json=dict(command.matrix_scope),
                    applicability_json=dict(command.applicability),
                    instrument_state_json=dict(command.instrument_state),
                    processing_details_json=dict(
                        command.processing_details
                    ),
                    deviation_assessment_json=dict(
                        command.deviation_assessment
                    ),
                    reviewer_pseudonym=command.reviewer_pseudonym,
                    reviewed_at=command.reviewed_at,
                    disposition=command.disposition,
                    raw_vendor_attachment_id=vendor.id,
                    open_export_attachment_id=open_export.id,
                    content_sha256=canonical_json_sha256(payload),
                )
            )

    async def _validate_analytical_primary_subject(
        self,
        command: AnalyticalRunAuthorityInput,
        run: Any,
    ) -> None:
        matching_context = {
            "SAMPLE": run.sample_id,
            "FORMULA_VERSION": run.formula_version_id,
            "BUILD_PLAN_VERSION": run.build_plan_version_id,
            "BOTTLE_STREAM": run.bottle_id,
        }
        if command.subject_type in matching_context:
            expected = matching_context[command.subject_type]
            if expected != command.subject_id:
                raise AnalyticalAuthorityConflictError(
                    "RUN_PRIMARY_SUBJECT_MISMATCH",
                    "B5 primary subject conflicts with the A2 run context.",
                )
        subject: Any = None
        if command.subject_type == "SAMPLE":
            subject = await self.repository.get_sample(command.subject_id)
        elif command.subject_type == "FORMULA_VERSION":
            subject = await self.repository.get_formula_version(
                command.subject_id
            )
        elif command.subject_type == "BUILD_PLAN_VERSION":
            subject = await self.repository.get_build_plan_version(
                command.subject_id
            )
        elif command.subject_type == "BOTTLE_STREAM":
            subject = await self.repository.get_bottle(command.subject_id)
            events = (
                await self.repository.events_for_bottle(command.subject_id)
                if subject is not None
                else []
            )
            if not any(
                event.stream_sequence == command.subject_stream_sequence
                for event in events
            ):
                raise AnalyticalAuthorityConflictError(
                    "BOTTLE_STREAM_SEQUENCE_NOT_FOUND",
                    "The exact bottle event-stream sequence was not found.",
                )
        else:
            subject = await self.repository.get_stock(command.subject_id)
            if subject is not None and not str(
                subject.lot_number or ""
            ).strip():
                raise AnalyticalAuthorityConflictError(
                    "STOCK_LOT_NUMBER_REQUIRED",
                    "Stock and natural lot subjects require a lot number.",
                )
            if (
                subject is not None
                and command.subject_type == "NATURAL_LOT"
                and str(
                    subject.source_json.get("material_kind", "")
                ).upper()
                != "NATURAL"
            ):
                raise AnalyticalAuthorityConflictError(
                    "NATURAL_LOT_MARKER_REQUIRED",
                    "Natural lot subjects require an explicit natural marker.",
                )
        if subject is None:
            raise AnalyticalAuthorityConflictError(
                "RUN_PRIMARY_SUBJECT_NOT_FOUND",
                "The B5 primary analytical subject was not found.",
            )

    async def record_analytical_peak_authority(
        self,
        command: AnalyticalPeakAuthorityInput,
    ) -> LabAnalyticalPeakAuthority:
        async with self._transaction():
            peak = await self.repository.get_analytical_peak(
                command.analytical_peak_id
            )
            run_authority = (
                await self.repository.get_analytical_run_authority(
                    command.analytical_run_authority_id
                )
            )
            if peak is None:
                raise AnalyticalAuthorityConflictError(
                    "ANALYTICAL_PEAK_NOT_FOUND",
                    "A2 analytical peak was not found.",
                )
            if (
                run_authority is None
                or peak.analytical_run_id
                != run_authority.analytical_run_id
            ):
                raise AnalyticalAuthorityConflictError(
                    "PEAK_RUN_AUTHORITY_MISMATCH",
                    "Peak and run authority do not bind the same A2 run.",
                )
            if (
                await self.repository.analytical_peak_authority_for_peak(
                    peak.id
                )
                is not None
            ):
                raise AnalyticalAuthorityConflictError(
                    "PEAK_AUTHORITY_ALREADY_EXISTS",
                    "The A2 peak already has B5 authority.",
                )
            self._validate_identity_authority(command, peak)
            await self._validate_quantitation_authority(
                command,
                peak,
                run_authority,
            )
            payload = {
                "schema": "lab-analytical-peak-authority-v1",
                "analytical_peak_id": peak.id,
                "analytical_peak_sha256": peak.content_sha256,
                "analytical_run_authority_id": run_authority.id,
                "analytical_run_authority_sha256": (
                    run_authority.content_sha256
                ),
                "identity_state": command.identity_state,
                "identity_label": command.identity_label,
                "stationary_phase": command.stationary_phase,
                "spectrum": command.spectrum,
                "deconvolution": command.deconvolution,
                "library_candidates": command.library_candidates,
                "exact_mass": command.exact_mass,
                "authentic_standard_state": (
                    command.authentic_standard_state
                ),
                "co_injection_state": command.co_injection_state,
                "quantifier_ions": command.quantifier_ions,
                "coelution": command.coelution,
                "manual_review": command.manual_review,
                "identity_decision": command.identity_decision,
                "quantitation_state": command.quantitation_state,
                "quantitation": command.quantitation,
                "applicability": command.applicability,
                "reviewer_pseudonym": command.reviewer_pseudonym,
                "reviewed_at": command.reviewed_at.isoformat(),
            }
            return await self.repository.add(
                LabAnalyticalPeakAuthority(
                    analytical_peak_id=peak.id,
                    analytical_run_authority_id=run_authority.id,
                    identity_state=command.identity_state,
                    identity_label=command.identity_label,
                    stationary_phase=command.stationary_phase,
                    spectrum_json=dict(command.spectrum),
                    deconvolution_json=dict(command.deconvolution),
                    library_candidates_json=[
                        dict(candidate)
                        for candidate in command.library_candidates
                    ],
                    exact_mass_json=dict(command.exact_mass),
                    authentic_standard_state=(
                        command.authentic_standard_state
                    ),
                    co_injection_state=command.co_injection_state,
                    quantifier_ions_json=list(command.quantifier_ions),
                    coelution_json=dict(command.coelution),
                    manual_review_json=dict(command.manual_review),
                    identity_decision_json=dict(
                        command.identity_decision
                    ),
                    quantitation_state=command.quantitation_state,
                    quantitation_json=dict(command.quantitation),
                    applicability_json=dict(command.applicability),
                    reviewer_pseudonym=command.reviewer_pseudonym,
                    reviewed_at=command.reviewed_at,
                    content_sha256=canonical_json_sha256(payload),
                )
            )

    @staticmethod
    def _validate_identity_authority(
        command: AnalyticalPeakAuthorityInput,
        peak: Any,
    ) -> None:
        reviewed = command.manual_review.get("reviewed") is True
        has_retention = (
            peak.retention_time_minutes is not None
            or peak.retention_index is not None
        )
        has_spectrum = bool(command.spectrum)
        if command.identity_state == "CONFIRMED_AUTHENTIC_STANDARD":
            valid = bool(
                peak.material_id
                and has_retention
                and has_spectrum
                and reviewed
                and (
                    command.authentic_standard_state == "MATCHED"
                    or command.co_injection_state == "MATCHED"
                )
                and command.identity_decision.get("material_id")
                == peak.material_id
            )
        elif command.identity_state == "STRONGLY_SUPPORTED_RI_PLUS_SPECTRUM":
            valid = bool(
                peak.retention_index is not None
                and has_spectrum
                and reviewed
            )
        elif command.identity_state == "PROBABLE":
            valid = bool(
                has_retention
                and reviewed
                and (has_spectrum or command.exact_mass.get("available") is True)
            )
        elif command.identity_state == "TENTATIVE_LIBRARY_MATCH":
            valid = bool(command.library_candidates)
        else:
            valid = True
        if not valid:
            raise AnalyticalAuthorityConflictError(
                "IDENTITY_EVIDENCE_INSUFFICIENT",
                "Identity evidence cannot support the requested B5 tier.",
            )

    async def _validate_quantitation_authority(
        self,
        command: AnalyticalPeakAuthorityInput,
        peak: Any,
        run_authority: LabAnalyticalRunAuthority,
    ) -> None:
        if command.quantitation_state == "NONE":
            return
        if command.quantitation_state == "AREA_PERCENT_ONLY":
            if peak.area is None:
                raise AnalyticalAuthorityConflictError(
                    "AREA_PERCENT_AREA_MISSING",
                    "Area-percent reporting requires an A2 peak area.",
                )
            return
        quantitation = command.quantitation
        validation = await self.repository.get_method_validation_record(
            quantitation["calibration_reference"]
        )
        if (
            validation is None
            or validation.method_authority_id
            != run_authority.method_authority_id
            or validation.result != "PASS"
        ):
            raise AnalyticalAuthorityConflictError(
                "CALIBRATION_REFERENCE_INVALID",
                "Calibrated quantity requires a matching PASS validation.",
            )
        if (
            peak.quantity is None
            or peak.quantity_unit != quantitation["quantity_unit"]
            or peak.quantitation_basis != quantitation["quantity_basis"]
            or peak.response_factor is None
            or not isclose(
                peak.quantity,
                quantitation["quantity"],
                rel_tol=1e-12,
                abs_tol=1e-12,
            )
            or not isclose(
                peak.response_factor,
                quantitation["response_factor"],
                rel_tol=1e-12,
                abs_tol=1e-12,
            )
        ):
            raise AnalyticalAuthorityConflictError(
                "QUANTITATION_A2_MISMATCH",
                "B5 quantity must match the preserved A2 peak quantity.",
            )
        working_range = quantitation["working_range"]
        if not (
            working_range["minimum"]
            <= quantitation["quantity"]
            <= working_range["maximum"]
        ):
            raise AnalyticalAuthorityConflictError(
                "QUANTITATION_OUTSIDE_WORKING_RANGE",
                "Quantity lies outside the declared working range.",
            )
        method_authority = (
            await self.repository.get_analytical_method_authority(
                run_authority.method_authority_id
            )
        )
        if method_authority is None:
            raise AnalyticalAuthorityConflictError(
                "METHOD_AUTHORITY_NOT_FOUND",
                "Run method authority was not found.",
            )
        method = await self.repository.get_analytical_method_version(
            method_authority.method_version_id
        )
        if method is None:
            raise AnalyticalAuthorityConflictError(
                "ANALYTICAL_METHOD_NOT_FOUND",
                "A2 analytical method was not found.",
            )
        if method.technique == "HS_SPME_GCMS":
            expected = {
                "matrix_calibration_id": canonical_json_sha256(
                    run_authority.matrix_scope_json
                ),
                "analyte_calibration_id": peak.material_id,
                "method_calibration_id": method_authority.id,
            }
            if any(
                quantitation[key] != value
                for key, value in expected.items()
            ):
                raise AnalyticalAuthorityConflictError(
                    "HS_SPME_CALIBRATION_SCOPE_MISMATCH",
                    "HS-SPME concentration requires matching matrix, "
                    "analyte, and method calibration.",
                )

    async def record_gco_event_authority(
        self,
        command: GCOEventAuthorityInput,
    ) -> LabGCOEventAuthority:
        async with self._transaction():
            event = await self.repository.get_gco_event(command.gco_event_id)
            run_authority = (
                await self.repository.get_analytical_run_authority(
                    command.analytical_run_authority_id
                )
            )
            if event is None:
                raise AnalyticalAuthorityConflictError(
                    "GCO_EVENT_NOT_FOUND",
                    "A2 GC-O event was not found.",
                )
            if (
                run_authority is None
                or event.analytical_run_id
                != run_authority.analytical_run_id
            ):
                raise AnalyticalAuthorityConflictError(
                    "GCO_RUN_AUTHORITY_MISMATCH",
                    "GC-O event and run authority do not bind the same run.",
                )
            position = (
                event.retention_time_minutes
                if command.window_basis == "RETENTION_TIME"
                else event.retention_index
            )
            if (
                position is None
                or not command.window_start
                <= position
                <= command.window_end
            ):
                raise AnalyticalAuthorityConflictError(
                    "GCO_EVENT_OUTSIDE_WINDOW",
                    "A2 GC-O event lies outside the declared event window.",
                )
            for peak_id in command.aligned_peak_ids:
                peak = await self.repository.get_analytical_peak(peak_id)
                if (
                    peak is None
                    or peak.analytical_run_id
                    != run_authority.analytical_run_id
                ):
                    raise AnalyticalAuthorityConflictError(
                        "GCO_ALIGNED_PEAK_INVALID",
                        "Every aligned peak must belong to the GC-O run.",
                    )
            if (
                event.analytical_peak_id is not None
                and event.analytical_peak_id
                not in command.aligned_peak_ids
            ):
                raise AnalyticalAuthorityConflictError(
                    "GCO_PRIMARY_ALIGNMENT_MISSING",
                    "The A2 GC-O peak must remain in aligned candidates.",
                )
            if (
                await self.repository.gco_event_authority_for_event(event.id)
                is not None
            ):
                raise AnalyticalAuthorityConflictError(
                    "GCO_AUTHORITY_ALREADY_EXISTS",
                    "The A2 GC-O event already has B5 authority.",
                )
            payload = {
                "schema": "lab-gco-event-authority-v1",
                "gco_event_id": event.id,
                "gco_event_sha256": event.content_sha256,
                "analytical_run_authority_id": run_authority.id,
                "analytical_run_authority_sha256": (
                    run_authority.content_sha256
                ),
                "assessor_training_state": (
                    command.assessor_training_state
                ),
                "window_basis": command.window_basis,
                "window_start": command.window_start,
                "window_end": command.window_end,
                "detection_method": command.detection_method,
                "replicate_index": command.replicate_index,
                "replicate_count": command.replicate_count,
                "detection_frequency": command.detection_frequency,
                "repeatability": command.repeatability,
                "aligned_peak_ids": command.aligned_peak_ids,
                "unknown_event": command.unknown_event,
                "exact_identity_claim": False,
            }
            return await self.repository.add(
                LabGCOEventAuthority(
                    gco_event_id=event.id,
                    analytical_run_authority_id=run_authority.id,
                    assessor_training_state=(
                        command.assessor_training_state
                    ),
                    window_basis=command.window_basis,
                    window_start=command.window_start,
                    window_end=command.window_end,
                    detection_method=command.detection_method,
                    replicate_index=command.replicate_index,
                    replicate_count=command.replicate_count,
                    detection_frequency=command.detection_frequency,
                    repeatability_json=dict(command.repeatability),
                    aligned_peak_ids_json=list(command.aligned_peak_ids),
                    unknown_event=command.unknown_event,
                    exact_identity_claim=False,
                    content_sha256=canonical_json_sha256(payload),
                )
            )

    async def assess_analytical_claim(
        self,
        command: AnalyticalClaimRequest,
    ) -> LabAnalyticalClaimAssessment:
        async with self._transaction():
            run_authority = (
                await self.repository.get_analytical_run_authority(
                    command.analytical_run_authority_id
                )
            )
            if run_authority is None:
                raise AnalyticalAuthorityConflictError(
                    "RUN_AUTHORITY_NOT_FOUND",
                    "B5 analytical run authority was not found.",
                )
            peak_authority = (
                await self.repository.get_analytical_peak_authority(
                    command.peak_authority_id
                )
            )
            if peak_authority is None:
                raise AnalyticalAuthorityConflictError(
                    "PEAK_AUTHORITY_NOT_FOUND",
                    "B5 analytical peak authority was not found.",
                )
            evidence = await self.repository.get_evidence_record(
                command.evidence_record_id
            )
            if evidence is None:
                raise AnalyticalAuthorityConflictError(
                    "EVIDENCE_NOT_FOUND",
                    "Analytical claim evidence record was not found.",
                )

            method_authority = (
                await self.repository.get_analytical_method_authority(
                    run_authority.method_authority_id
                )
            )
            sequence = await self.repository.get_analytical_sequence(
                run_authority.sequence_id
            )
            vendor_attachment = (
                await self.repository.get_analytical_attachment(
                    run_authority.raw_vendor_attachment_id
                )
            )
            open_attachment = await self.repository.get_analytical_attachment(
                run_authority.open_export_attachment_id
            )
            peak = await self.repository.get_analytical_peak(
                peak_authority.analytical_peak_id
            )

            validation = None
            if method_authority is not None:
                validations = (
                    await self.repository.method_validation_records(
                        method_authority.id
                    )
                )
                requested_scope_sha256 = command.requested_scope.get(
                    "matrix_scope_sha256"
                )
                validation = next(
                    (
                        record
                        for record in validations
                        if record.scope_sha256 == requested_scope_sha256
                    ),
                    None,
                )

            missing: set[str] = set()
            qualifications: set[str] = set()
            details: dict[str, Any] = {}

            if method_authority is None:
                missing.add("METHOD_AUTHORITY_MISSING")
            else:
                sufficient_statuses = (
                    {"VALIDATED_FOR_SCOPE"}
                    if command.claim_type == "QUANTITY"
                    else {"VERIFIED", "VALIDATED_FOR_SCOPE"}
                )
                if method_authority.status not in sufficient_statuses:
                    missing.add("METHOD_STATUS_INSUFFICIENT")
                if validation is None:
                    missing.add("METHOD_VALIDATION_MISSING")
                elif validation.result != "PASS":
                    missing.add("METHOD_VALIDATION_FAILED")

            if sequence is None or sequence.status != "ACQUIRED":
                missing.add("SEQUENCE_NOT_ACQUIRED")
            if (
                vendor_attachment is None
                or vendor_attachment.analytical_run_id
                != run_authority.analytical_run_id
                or vendor_attachment.attachment_kind != "RAW_VENDOR_DATA"
            ):
                missing.add("RAW_VENDOR_DATA_MISSING")
            if (
                open_attachment is None
                or open_attachment.analytical_run_id
                != run_authority.analytical_run_id
                or open_attachment.attachment_kind != "OPEN_EXPORT"
            ):
                missing.add("OPEN_EXPORT_MISSING")
            if run_authority.disposition != "ACCEPTED":
                missing.add("RUN_DISPOSITION_BLOCKING")

            if method_authority is not None:
                qc_plan = dict(method_authority.qc_plan_json)
                required_checks = tuple(qc_plan.get("required_checks", ()))
                failure_policy = dict(qc_plan.get("failure_policy", {}))
                qc_records = (
                    await self.repository.analytical_qc_records(
                        run_authority.analytical_run_id
                    )
                )
                records_by_type: dict[str, list[Any]] = {}
                for record in qc_records:
                    records_by_type.setdefault(
                        str(record.qc_type).strip().upper(),
                        [],
                    ).append(record)
                missing_qc_types: list[str] = []
                unresolved_qc_types: list[str] = []
                blocking_qc_types: list[str] = []
                qualifying_qc_types: list[str] = []
                for qc_type in required_checks:
                    records = records_by_type.get(qc_type, [])
                    if not records:
                        missing_qc_types.append(qc_type)
                        continue
                    statuses = {record.status for record in records}
                    if "FAIL" in statuses:
                        if failure_policy.get(qc_type) == "QUALIFY":
                            qualifying_qc_types.append(qc_type)
                        else:
                            blocking_qc_types.append(qc_type)
                    elif statuses != {"PASS"}:
                        unresolved_qc_types.append(qc_type)
                if missing_qc_types:
                    missing.add("QC_REQUIRED_CHECK_MISSING")
                if unresolved_qc_types:
                    missing.add("QC_REQUIRED_CHECK_UNRESOLVED")
                if blocking_qc_types:
                    missing.add("QC_FAILED_BLOCKING")
                if qualifying_qc_types:
                    qualifications.add("QC_FAILED_QUALIFYING")
                details.update(
                    {
                        "missing_qc_types": sorted(missing_qc_types),
                        "unresolved_qc_types": sorted(
                            unresolved_qc_types
                        ),
                        "blocking_qc_types": sorted(blocking_qc_types),
                        "qualifying_qc_types": sorted(
                            qualifying_qc_types
                        ),
                    }
                )

            if (
                peak is None
                or peak_authority.analytical_run_authority_id
                != run_authority.id
                or peak.analytical_run_id
                != run_authority.analytical_run_id
                or peak_authority.identity_state
                not in {
                    "CONFIRMED_AUTHENTIC_STANDARD",
                    "STRONGLY_SUPPORTED_RI_PLUS_SPECTRUM",
                }
            ):
                missing.add("IDENTITY_EVIDENCE_INSUFFICIENT")

            if (
                peak_authority.applicability_json
                != command.requested_scope
            ):
                missing.add("APPLICABILITY_MISMATCH")

            quantitation = dict(peak_authority.quantitation_json)
            result: dict[str, Any] | None
            if command.claim_type == "QUANTITY":
                calibration_reference = quantitation.get(
                    "calibration_reference"
                )
                if peak_authority.quantitation_state != (
                    "CALIBRATED_CONCENTRATION"
                ) or (
                    method_authority is not None
                    and validation is not None
                    and calibration_reference != validation.id
                ):
                    missing.add("CALIBRATION_MISSING")
                if (
                    str(quantitation.get("quantity_basis", "")).strip().lower()
                    != "calibrated_concentration"
                ):
                    missing.add("QUANTITATION_BASIS_INVALID")
                uncertainty = quantitation.get("measurement_uncertainty")
                if not isinstance(uncertainty, Mapping) or not uncertainty:
                    missing.add("UNCERTAINTY_MISSING")
                result = {
                    "quantity": quantitation.get("quantity"),
                    "quantity_unit": quantitation.get("quantity_unit"),
                    "quantity_basis": quantitation.get("quantity_basis"),
                    "measurement_uncertainty": uncertainty,
                }
            else:
                result = {
                    "identity_state": peak_authority.identity_state,
                    "identity_label": peak_authority.identity_label,
                }

            if (
                not command.reviewer_pseudonym
                or command.reviewed_at is None
                or not run_authority.reviewer_pseudonym
                or run_authority.reviewed_at is None
                or not peak_authority.reviewer_pseudonym
                or peak_authority.reviewed_at is None
                or validation is not None
                and (
                    not validation.reviewer_pseudonym
                    or validation.reviewed_at is None
                )
            ):
                missing.add("REVIEW_MISSING")

            missing_codes = tuple(sorted(missing))
            qualification_codes = tuple(sorted(qualifications))
            if missing_codes:
                decision = "WITHHELD"
                result = None
            elif qualification_codes:
                decision = "ADVISORY_ONLY"
            else:
                decision = "SUPPORTED_FOR_SCOPE"

            upstream_hashes = {
                "analytical_run_authority": run_authority.content_sha256,
                "analytical_peak_authority": peak_authority.content_sha256,
                "method_authority": (
                    method_authority.content_sha256
                    if method_authority is not None
                    else None
                ),
                "method_validation": (
                    validation.content_sha256
                    if validation is not None
                    else None
                ),
                "sequence": (
                    sequence.content_sha256 if sequence is not None else None
                ),
                "raw_vendor_attachment": (
                    vendor_attachment.content_sha256
                    if vendor_attachment is not None
                    else None
                ),
                "open_export_attachment": (
                    open_attachment.content_sha256
                    if open_attachment is not None
                    else None
                ),
                "evidence": canonical_json_sha256(
                    {
                        "evidence_record_id": evidence.id,
                        "payload_sha256": evidence.payload_sha256,
                    }
                ),
            }
            payload = {
                "schema": "lab-analytical-claim-assessment-v1",
                "analytical_run_id": run_authority.analytical_run_id,
                "run_authority_id": run_authority.id,
                "peak_authority_id": peak_authority.id,
                "claim_type": command.claim_type,
                "policy_version": command.policy_version,
                "decision": decision,
                "scope": command.requested_scope,
                "missing_requirements": missing_codes,
                "qualifications": qualification_codes,
                "details": details,
                "upstream_hashes": upstream_hashes,
                "result": result,
                "reviewer_pseudonym": command.reviewer_pseudonym,
                "reviewed_at": command.reviewed_at.isoformat(),
                "evidence_record_id": evidence.id,
            }
            return await self.repository.add(
                LabAnalyticalClaimAssessment(
                    analytical_run_id=run_authority.analytical_run_id,
                    run_authority_id=run_authority.id,
                    peak_authority_id=peak_authority.id,
                    claim_type=command.claim_type,
                    policy_version=command.policy_version,
                    decision=decision,
                    scope_json=dict(command.requested_scope),
                    missing_requirements_json=list(missing_codes),
                    qualifications_json=list(qualification_codes),
                    details_json=details,
                    upstream_hashes_json=upstream_hashes,
                    result_json=result,
                    reviewer_pseudonym=command.reviewer_pseudonym,
                    reviewed_at=command.reviewed_at,
                    evidence_record_id=evidence.id,
                    content_sha256=canonical_json_sha256(payload),
                )
            )


__all__ = [
    "ANALYTICAL_MISSING_REQUIREMENT_CODES",
    "ANALYTICAL_QUALIFICATION_CODES",
    "ANALYTICAL_QC_CHECK_TYPES",
    "HS_SPME_KEYS",
    "METHOD_COMPONENT_KEYS",
    "VALIDATION_CHARACTERISTIC_KEYS",
    "AnalyticalAuthorityConflictError",
    "AnalyticalAuthorityError",
    "AnalyticalClaimRequest",
    "AnalyticalMethodAuthorityInput",
    "AnalyticalPeakAuthorityInput",
    "AnalyticalRunAuthorityInput",
    "AnalyticalSequenceEntryInput",
    "AnalyticalSequenceInput",
    "GCOEventAuthorityInput",
    "LabAnalyticalAuthorityServiceMixin",
    "MethodValidationInput",
    "canonical_json_sha256",
]
