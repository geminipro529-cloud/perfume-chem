"""Admission and deterministic projection for B1-bound external studies."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

from engine.calibration.hashing import stable_json_hash

from app.models.lab_external_studies import (
    EXTERNAL_AGGREGATION_STATISTICS,
    EXTERNAL_CONDITION_ROLES,
    EXTERNAL_CONFLICT_STATES,
    EXTERNAL_CONFLICT_TYPES,
    EXTERNAL_CROSSWALK_STATUSES,
    EXTERNAL_MISSINGNESS_STATES,
    EXTERNAL_OBSERVATION_GRAINS,
    EXTERNAL_STIMULUS_KINDS,
    EXTERNAL_STUDY_DOMAINS,
    EXTERNAL_UNIT_GRAINS,
    LabExternalCondition,
    LabExternalExperimentalUnit,
    LabExternalIdentityCrosswalk,
    LabExternalObservation,
    LabExternalStimulusComponent,
    LabExternalStimulusVersion,
    LabExternalStudyConflict,
    LabExternalStudyVersion,
)
from app.services.lab_sources import SourceUseRequest

if TYPE_CHECKING:
    from contextlib import AbstractAsyncContextManager

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.lab_sources import LabSourceExtractionRecord
    from app.repositories.lab import LabRepository

EXTERNAL_STUDY_SCOPE = "EXTERNAL_STUDY_ADMISSION"
EXTERNAL_PRESENTATION_ROLES = (
    "TARGET",
    "COMPARATOR",
    "ODD",
    "REFERENCE",
    "CONTROL",
    "OTHER",
)


class ExternalStudyAdmissionError(ValueError):
    """Stable fail-closed external-study admission error."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


def _text(value: str, field: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{field} must not be blank")
    return normalized


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _uuid(value: str, field: str) -> str:
    normalized = _text(value, field)
    try:
        return str(UUID(normalized))
    except ValueError as exc:
        raise ValueError(f"{field} must be a UUID") from exc


def _choice(
    value: str,
    field: str,
    allowed: tuple[str, ...],
) -> str:
    normalized = _text(value, field).upper()
    if normalized not in allowed:
        raise ValueError(f"{field} must be one of {', '.join(allowed)}")
    return normalized


def _mapping(
    value: object,
    field: str,
    *,
    required: bool = True,
) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be an object")
    normalized: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise ValueError(f"{field} keys must be strings")
        normalized[key] = item
    if required and not normalized:
        raise ValueError(f"{field} must not be empty")
    stable_json_hash(normalized)
    return normalized


def _decimal_text(value: str | None, field: str) -> str | None:
    normalized = _optional_text(value)
    if normalized is None:
        return None
    try:
        number = Decimal(normalized)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field} must be an exact decimal string") from exc
    if not number.is_finite() or number < 0:
        raise ValueError(f"{field} must be finite and non-negative")
    canonical = format(number, "f")
    if "." in canonical:
        canonical = canonical.rstrip("0").rstrip(".")
    canonical = canonical or "0"
    if normalized != canonical:
        raise ValueError(f"{field} must use canonical plain-decimal text")
    if len(canonical) > 128:
        raise ValueError(f"{field} exceeds the persistence limit")
    return canonical


def _optional_positive_int(value: int | None, field: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{field} must be a positive integer")
    return value


@dataclass(frozen=True, slots=True)
class ExternalStimulusInput:
    record_id: str
    stimulus_key: str
    source_extraction_id: str
    stimulus_kind: str
    label: str
    matrix: Mapping[str, object]
    preparation: Mapping[str, object]
    context: Mapping[str, object]

    def __post_init__(self) -> None:
        object.__setattr__(self, "record_id", _uuid(self.record_id, "record_id"))
        object.__setattr__(self, "stimulus_key", _text(self.stimulus_key, "stimulus_key"))
        object.__setattr__(
            self,
            "source_extraction_id",
            _uuid(self.source_extraction_id, "source_extraction_id"),
        )
        object.__setattr__(
            self,
            "stimulus_kind",
            _choice(self.stimulus_kind, "stimulus_kind", EXTERNAL_STIMULUS_KINDS),
        )
        object.__setattr__(self, "label", _text(self.label, "label"))
        object.__setattr__(self, "matrix", _mapping(self.matrix, "matrix"))
        object.__setattr__(
            self,
            "preparation",
            _mapping(self.preparation, "preparation"),
        )
        object.__setattr__(
            self,
            "context",
            _mapping(self.context, "context", required=False),
        )


@dataclass(frozen=True, slots=True)
class ExternalStimulusComponentInput:
    record_id: str
    stimulus_version_id: str
    position: int
    component_key: str
    source_extraction_id: str
    source_identity: Mapping[str, object]
    quantity_value_text: str | None
    quantity_unit: str | None
    quantity_basis: str | None
    concentration_value_text: str | None
    concentration_unit: str | None
    concentration_basis: str | None
    carrier: Mapping[str, object]
    purity: Mapping[str, object]
    role: str | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "record_id", _uuid(self.record_id, "record_id"))
        object.__setattr__(
            self,
            "stimulus_version_id",
            _uuid(self.stimulus_version_id, "stimulus_version_id"),
        )
        if isinstance(self.position, bool) or self.position < 1:
            raise ValueError("position must be a positive integer")
        object.__setattr__(self, "component_key", _text(self.component_key, "component_key"))
        object.__setattr__(
            self,
            "source_extraction_id",
            _uuid(self.source_extraction_id, "source_extraction_id"),
        )
        object.__setattr__(
            self,
            "source_identity",
            _mapping(self.source_identity, "source_identity"),
        )
        quantity = _decimal_text(self.quantity_value_text, "quantity_value_text")
        quantity_unit = _optional_text(self.quantity_unit)
        quantity_basis = _optional_text(self.quantity_basis)
        if (quantity is None) != (quantity_unit is None) or (
            quantity is None
        ) != (quantity_basis is None):
            raise ValueError("quantity value, unit, and basis must be supplied together")
        concentration = _decimal_text(
            self.concentration_value_text,
            "concentration_value_text",
        )
        concentration_unit = _optional_text(self.concentration_unit)
        concentration_basis = _optional_text(self.concentration_basis)
        if (concentration is None) != (concentration_unit is None) or (
            concentration is None
        ) != (concentration_basis is None):
            raise ValueError(
                "concentration value, unit, and basis must be supplied together"
            )
        object.__setattr__(self, "quantity_value_text", quantity)
        object.__setattr__(self, "quantity_unit", quantity_unit)
        object.__setattr__(self, "quantity_basis", quantity_basis)
        object.__setattr__(self, "concentration_value_text", concentration)
        object.__setattr__(self, "concentration_unit", concentration_unit)
        object.__setattr__(self, "concentration_basis", concentration_basis)
        object.__setattr__(self, "carrier", _mapping(self.carrier, "carrier"))
        object.__setattr__(self, "purity", _mapping(self.purity, "purity"))
        object.__setattr__(self, "role", _optional_text(self.role))


@dataclass(frozen=True, slots=True)
class ExternalConditionInput:
    record_id: str
    condition_key: str
    source_extraction_id: str
    condition_role: str
    label: str
    primary_stimulus_version_id: str | None
    factors: Mapping[str, object]
    context: Mapping[str, object]

    def __post_init__(self) -> None:
        object.__setattr__(self, "record_id", _uuid(self.record_id, "record_id"))
        object.__setattr__(self, "condition_key", _text(self.condition_key, "condition_key"))
        object.__setattr__(
            self,
            "source_extraction_id",
            _uuid(self.source_extraction_id, "source_extraction_id"),
        )
        object.__setattr__(
            self,
            "condition_role",
            _choice(self.condition_role, "condition_role", EXTERNAL_CONDITION_ROLES),
        )
        object.__setattr__(self, "label", _text(self.label, "label"))
        object.__setattr__(
            self,
            "primary_stimulus_version_id",
            (
                _uuid(
                    self.primary_stimulus_version_id,
                    "primary_stimulus_version_id",
                )
                if self.primary_stimulus_version_id is not None
                else None
            ),
        )
        object.__setattr__(self, "factors", _mapping(self.factors, "factors"))
        object.__setattr__(
            self,
            "context",
            _mapping(self.context, "context", required=False),
        )


@dataclass(frozen=True, slots=True)
class ExternalExperimentalUnitInput:
    record_id: str
    unit_key: str
    source_extraction_id: str
    unit_grain: str
    parent_unit_id: str | None
    pseudonymous_token: str | None
    reported_n: int | None
    context: Mapping[str, object]

    def __post_init__(self) -> None:
        object.__setattr__(self, "record_id", _uuid(self.record_id, "record_id"))
        object.__setattr__(self, "unit_key", _text(self.unit_key, "unit_key"))
        object.__setattr__(
            self,
            "source_extraction_id",
            _uuid(self.source_extraction_id, "source_extraction_id"),
        )
        grain = _choice(self.unit_grain, "unit_grain", EXTERNAL_UNIT_GRAINS)
        object.__setattr__(self, "unit_grain", grain)
        parent = (
            _uuid(self.parent_unit_id, "parent_unit_id")
            if self.parent_unit_id is not None
            else None
        )
        if parent == self.record_id:
            raise ValueError("external experimental units cannot parent themselves")
        object.__setattr__(self, "parent_unit_id", parent)
        token = _optional_text(self.pseudonymous_token)
        n = _optional_positive_int(self.reported_n, "reported_n")
        if grain in {"PARTICIPANT", "SAMPLE"} and n != 1:
            raise ValueError(f"{grain} units require reported_n=1")
        if grain == "PARTICIPANT" and token is None:
            raise ValueError("PARTICIPANT units require a pseudonymous token")
        if grain != "PARTICIPANT" and token is not None:
            raise ValueError("only PARTICIPANT units may carry pseudonymous tokens")
        object.__setattr__(self, "pseudonymous_token", token)
        object.__setattr__(self, "reported_n", n)
        object.__setattr__(self, "context", _mapping(self.context, "context"))


def _presentation(
    rows: tuple[Mapping[str, object], ...],
) -> tuple[dict[str, object], ...]:
    if not rows:
        raise ValueError("presentation must not be empty")
    normalized: list[dict[str, object]] = []
    allowed = {"position", "stimulus_version_id", "role", "blind_label", "context"}
    for index, row in enumerate(rows, start=1):
        unexpected = set(row) - allowed
        if unexpected:
            raise ValueError("presentation contains unsupported fields")
        position = row.get("position")
        if isinstance(position, bool) or not isinstance(position, int) or position < 1:
            raise ValueError("presentation position must be a positive integer")
        normalized.append(
            {
                "position": position,
                "stimulus_version_id": _uuid(
                    str(row.get("stimulus_version_id") or ""),
                    f"presentation[{index}].stimulus_version_id",
                ),
                "role": _choice(
                    str(row.get("role") or ""),
                    f"presentation[{index}].role",
                    EXTERNAL_PRESENTATION_ROLES,
                ),
                "blind_label": _optional_text(
                    str(row["blind_label"])
                    if row.get("blind_label") is not None
                    else None
                ),
                "context": _mapping(
                    row.get("context", {}),
                    f"presentation[{index}].context",
                    required=False,
                ),
            }
        )
    ordered = tuple(
        sorted(normalized, key=lambda item: cast(int, item["position"]))
    )
    if tuple(cast(int, item["position"]) for item in ordered) != tuple(
        range(1, len(ordered) + 1)
    ):
        raise ValueError("presentation positions must be unique and contiguous")
    return ordered


@dataclass(frozen=True, slots=True)
class ExternalObservationInput:
    record_id: str
    observation_key: str
    source_extraction_id: str
    condition_id: str
    experimental_unit_id: str
    primary_stimulus_version_id: str | None
    trial_key: str
    session_key: str | None
    repeat_index: int | None
    presentation: tuple[Mapping[str, object], ...]
    endpoint_key: str
    value: Mapping[str, object] | None
    original_unit: str
    scale: Mapping[str, object]
    timepoint: Mapping[str, object]
    replicate_index: int | None
    observation_grain: str
    aggregation_statistic: str
    missingness: str
    uncertainty: Mapping[str, object]
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "record_id", _uuid(self.record_id, "record_id"))
        object.__setattr__(self, "observation_key", _text(self.observation_key, "observation_key"))
        for field in (
            "source_extraction_id",
            "condition_id",
            "experimental_unit_id",
        ):
            object.__setattr__(self, field, _uuid(getattr(self, field), field))
        object.__setattr__(
            self,
            "primary_stimulus_version_id",
            (
                _uuid(
                    self.primary_stimulus_version_id,
                    "primary_stimulus_version_id",
                )
                if self.primary_stimulus_version_id is not None
                else None
            ),
        )
        object.__setattr__(self, "trial_key", _text(self.trial_key, "trial_key"))
        object.__setattr__(self, "session_key", _optional_text(self.session_key))
        object.__setattr__(
            self,
            "repeat_index",
            _optional_positive_int(self.repeat_index, "repeat_index"),
        )
        object.__setattr__(self, "presentation", _presentation(self.presentation))
        object.__setattr__(self, "endpoint_key", _text(self.endpoint_key, "endpoint_key"))
        missingness = _choice(
            self.missingness,
            "missingness",
            EXTERNAL_MISSINGNESS_STATES,
        )
        value = dict(self.value) if self.value is not None else None
        if value is not None:
            stable_json_hash(value)
        if (missingness == "OBSERVED") != (value is not None):
            raise ValueError("only OBSERVED rows may carry a value")
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "missingness", missingness)
        object.__setattr__(self, "original_unit", _text(self.original_unit, "original_unit"))
        object.__setattr__(self, "scale", _mapping(self.scale, "scale"))
        object.__setattr__(self, "timepoint", _mapping(self.timepoint, "timepoint"))
        object.__setattr__(
            self,
            "replicate_index",
            _optional_positive_int(self.replicate_index, "replicate_index"),
        )
        object.__setattr__(
            self,
            "observation_grain",
            _choice(
                self.observation_grain,
                "observation_grain",
                EXTERNAL_OBSERVATION_GRAINS,
            ),
        )
        object.__setattr__(
            self,
            "aggregation_statistic",
            _choice(
                self.aggregation_statistic,
                "aggregation_statistic",
                EXTERNAL_AGGREGATION_STATISTICS,
            ),
        )
        object.__setattr__(
            self,
            "uncertainty",
            _mapping(self.uncertainty, "uncertainty"),
        )
        limitations = tuple(_text(value, "limitations") for value in self.limitations)
        if len(limitations) != len(set(limitations)):
            raise ValueError("limitations must not contain duplicates")
        object.__setattr__(self, "limitations", limitations)


@dataclass(frozen=True, slots=True)
class ExternalIdentityCrosswalkInput:
    record_id: str
    component_id: str
    source_extraction_id: str
    resolution_status: str
    material_id: str | None
    source_identity: Mapping[str, object]
    resolved_identity: Mapping[str, object]
    evidence: Mapping[str, object]

    def __post_init__(self) -> None:
        object.__setattr__(self, "record_id", _uuid(self.record_id, "record_id"))
        object.__setattr__(self, "component_id", _uuid(self.component_id, "component_id"))
        object.__setattr__(
            self,
            "source_extraction_id",
            _uuid(self.source_extraction_id, "source_extraction_id"),
        )
        status = _choice(
            self.resolution_status,
            "resolution_status",
            EXTERNAL_CROSSWALK_STATUSES,
        )
        material = _uuid(self.material_id, "material_id") if self.material_id else None
        if status == "EXACT_PROJECT_MATERIAL" and material is None:
            raise ValueError("EXACT_PROJECT_MATERIAL requires material_id")
        if status in {
            "EXACT_EXTERNAL_IDENTITY_ONLY",
            "UNRESOLVED",
            "OPAQUE_PRODUCT",
        } and material is not None:
            raise ValueError(f"{status} cannot bind a project material")
        object.__setattr__(self, "resolution_status", status)
        object.__setattr__(self, "material_id", material)
        object.__setattr__(
            self,
            "source_identity",
            _mapping(self.source_identity, "source_identity"),
        )
        object.__setattr__(
            self,
            "resolved_identity",
            _mapping(self.resolved_identity, "resolved_identity"),
        )
        object.__setattr__(self, "evidence", _mapping(self.evidence, "evidence"))


@dataclass(frozen=True, slots=True)
class ExternalStudyConflictInput:
    record_id: str
    conflict_key: str
    conflict_type: str
    conflict_state: str
    source_extraction_id: str
    related_extraction_id: str
    details: Mapping[str, object]

    def __post_init__(self) -> None:
        object.__setattr__(self, "record_id", _uuid(self.record_id, "record_id"))
        object.__setattr__(self, "conflict_key", _text(self.conflict_key, "conflict_key"))
        object.__setattr__(
            self,
            "conflict_type",
            _choice(self.conflict_type, "conflict_type", EXTERNAL_CONFLICT_TYPES),
        )
        object.__setattr__(
            self,
            "conflict_state",
            _choice(self.conflict_state, "conflict_state", EXTERNAL_CONFLICT_STATES),
        )
        source = _uuid(self.source_extraction_id, "source_extraction_id")
        related = _uuid(self.related_extraction_id, "related_extraction_id")
        if source == related:
            raise ValueError("conflict extraction records must be distinct")
        object.__setattr__(self, "source_extraction_id", source)
        object.__setattr__(self, "related_extraction_id", related)
        object.__setattr__(self, "details", _mapping(self.details, "details"))


@dataclass(frozen=True, slots=True)
class ExternalStudyInput:
    record_id: str
    study_id: str
    study_key: str
    source_version_id: str
    source_extraction_id: str
    source_family: str
    title: str
    study_domain: str
    design: Mapping[str, object]
    protocol: Mapping[str, object]
    source_use_request: SourceUseRequest
    stimuli: tuple[ExternalStimulusInput, ...]
    components: tuple[ExternalStimulusComponentInput, ...]
    conditions: tuple[ExternalConditionInput, ...]
    experimental_units: tuple[ExternalExperimentalUnitInput, ...]
    observations: tuple[ExternalObservationInput, ...]
    crosswalks: tuple[ExternalIdentityCrosswalkInput, ...]
    conflicts: tuple[ExternalStudyConflictInput, ...]
    adapter_name: str
    adapter_version: str
    adapter_config: Mapping[str, object]
    parent_version_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "record_id", _uuid(self.record_id, "record_id"))
        object.__setattr__(self, "study_id", _uuid(self.study_id, "study_id"))
        object.__setattr__(self, "study_key", _text(self.study_key, "study_key"))
        object.__setattr__(
            self,
            "source_version_id",
            _uuid(self.source_version_id, "source_version_id"),
        )
        object.__setattr__(
            self,
            "source_extraction_id",
            _uuid(self.source_extraction_id, "source_extraction_id"),
        )
        object.__setattr__(self, "source_family", _text(self.source_family, "source_family"))
        object.__setattr__(self, "title", _text(self.title, "title"))
        object.__setattr__(
            self,
            "study_domain",
            _choice(self.study_domain, "study_domain", EXTERNAL_STUDY_DOMAINS),
        )
        object.__setattr__(self, "design", _mapping(self.design, "design"))
        object.__setattr__(self, "protocol", _mapping(self.protocol, "protocol"))
        if not isinstance(self.source_use_request, SourceUseRequest):
            raise ValueError("source_use_request must be a SourceUseRequest")
        for field in (
            "stimuli",
            "components",
            "conditions",
            "experimental_units",
            "observations",
            "crosswalks",
            "conflicts",
        ):
            object.__setattr__(self, field, tuple(getattr(self, field)))
        if not self.stimuli or not self.conditions or not self.experimental_units:
            raise ValueError("external studies require stimuli, conditions, and units")
        object.__setattr__(self, "adapter_name", _text(self.adapter_name, "adapter_name"))
        object.__setattr__(self, "adapter_version", _text(self.adapter_version, "adapter_version"))
        object.__setattr__(
            self,
            "adapter_config",
            _mapping(self.adapter_config, "adapter_config"),
        )
        object.__setattr__(
            self,
            "parent_version_id",
            (
                _uuid(self.parent_version_id, "parent_version_id")
                if self.parent_version_id is not None
                else None
            ),
        )


@dataclass(frozen=True, slots=True)
class ExternalStudyAdmissionResult:
    study: LabExternalStudyVersion
    stimuli: tuple[LabExternalStimulusVersion, ...]
    components: tuple[LabExternalStimulusComponent, ...]
    conditions: tuple[LabExternalCondition, ...]
    experimental_units: tuple[LabExternalExperimentalUnit, ...]
    observations: tuple[LabExternalObservation, ...]
    crosswalks: tuple[LabExternalIdentityCrosswalk, ...]
    conflicts: tuple[LabExternalStudyConflict, ...]
    projection: dict[str, Any]
    projection_sha256: str


def _study_payload(
    row: LabExternalStudyVersion,
    *,
    source_record_sha256: str,
) -> dict[str, Any]:
    return {
        "schema": "lab-external-study-v1",
        "record_id": row.id,
        "study_id": row.study_id,
        "version_number": row.version_number,
        "study_key": row.study_key,
        "source_version_id": row.source_version_id,
        "source_record_sha256": source_record_sha256,
        "source_extraction_id": row.source_extraction_id,
        "source_family": row.source_family,
        "title": row.title,
        "study_domain": row.study_domain,
        "design": row.design_json,
        "protocol": row.protocol_json,
        "source_use_request_sha256": row.source_use_request_sha256,
        "source_use_assessment_sha256": row.source_use_assessment_sha256,
        "source_use_constraint_version_ids": (
            row.source_use_constraint_version_ids_json
        ),
        "source_use_constraint_record_sha256s": (
            row.source_use_constraint_record_sha256s_json
        ),
        "adapter_name": row.adapter_name,
        "adapter_version": row.adapter_version,
        "adapter_config": row.adapter_config_json,
        "authority_state": row.authority_state,
        "parent_record_sha256": row.parent_record_sha256,
    }


def _child_payload(
    schema: str,
    row: object,
    *,
    study_record_sha256: str,
    source_extraction_record_sha256: str,
    fields: Mapping[str, object],
) -> dict[str, Any]:
    return {
        "schema": schema,
        "record_id": getattr(row, "id"),
        "study_record_sha256": study_record_sha256,
        "source_extraction_id": getattr(row, "source_extraction_id"),
        "source_extraction_record_sha256": source_extraction_record_sha256,
        **dict(fields),
    }


def _stimulus_payload(
    row: LabExternalStimulusVersion,
    study_hash: str,
    extraction_hash: str,
) -> dict[str, Any]:
    return _child_payload(
        "lab-external-stimulus-v1",
        row,
        study_record_sha256=study_hash,
        source_extraction_record_sha256=extraction_hash,
        fields={
            "stimulus_key": row.stimulus_key,
            "stimulus_kind": row.stimulus_kind,
            "label": row.label,
            "matrix": row.matrix_json,
            "preparation": row.preparation_json,
            "context": row.context_json,
        },
    )


def _component_payload(
    row: LabExternalStimulusComponent,
    study_hash: str,
    extraction_hash: str,
) -> dict[str, Any]:
    return _child_payload(
        "lab-external-stimulus-component-v1",
        row,
        study_record_sha256=study_hash,
        source_extraction_record_sha256=extraction_hash,
        fields={
            "stimulus_version_id": row.stimulus_version_id,
            "position": row.position,
            "component_key": row.component_key,
            "source_identity": row.source_identity_json,
            "quantity_value_text": row.quantity_value_text,
            "quantity_unit": row.quantity_unit,
            "quantity_basis": row.quantity_basis,
            "concentration_value_text": row.concentration_value_text,
            "concentration_unit": row.concentration_unit,
            "concentration_basis": row.concentration_basis,
            "carrier": row.carrier_json,
            "purity": row.purity_json,
            "role": row.role,
        },
    )


def _condition_payload(
    row: LabExternalCondition,
    study_hash: str,
    extraction_hash: str,
) -> dict[str, Any]:
    return _child_payload(
        "lab-external-condition-v1",
        row,
        study_record_sha256=study_hash,
        source_extraction_record_sha256=extraction_hash,
        fields={
            "condition_key": row.condition_key,
            "condition_role": row.condition_role,
            "label": row.label,
            "primary_stimulus_version_id": row.primary_stimulus_version_id,
            "factors": row.factors_json,
            "context": row.context_json,
        },
    )


def _unit_payload(
    row: LabExternalExperimentalUnit,
    study_hash: str,
    extraction_hash: str,
) -> dict[str, Any]:
    return _child_payload(
        "lab-external-experimental-unit-v1",
        row,
        study_record_sha256=study_hash,
        source_extraction_record_sha256=extraction_hash,
        fields={
            "unit_key": row.unit_key,
            "unit_grain": row.unit_grain,
            "parent_unit_id": row.parent_unit_id,
            "pseudonymous_token": row.pseudonymous_token,
            "reported_n": row.reported_n,
            "context": row.context_json,
        },
    )


def _observation_payload(
    row: LabExternalObservation,
    study_hash: str,
    extraction_hash: str,
) -> dict[str, Any]:
    return _child_payload(
        "lab-external-observation-v1",
        row,
        study_record_sha256=study_hash,
        source_extraction_record_sha256=extraction_hash,
        fields={
            "observation_key": row.observation_key,
            "condition_id": row.condition_id,
            "experimental_unit_id": row.experimental_unit_id,
            "primary_stimulus_version_id": row.primary_stimulus_version_id,
            "trial_key": row.trial_key,
            "session_key": row.session_key,
            "repeat_index": row.repeat_index,
            "presentation": row.presentation_json,
            "endpoint_key": row.endpoint_key,
            "value": row.value_json,
            "original_unit": row.original_unit,
            "scale": row.scale_json,
            "timepoint": row.timepoint_json,
            "replicate_index": row.replicate_index,
            "observation_grain": row.observation_grain,
            "aggregation_statistic": row.aggregation_statistic,
            "missingness": row.missingness,
            "uncertainty": row.uncertainty_json,
            "limitations": row.limitations_json,
        },
    )


def _crosswalk_payload(
    row: LabExternalIdentityCrosswalk,
    study_hash: str,
    extraction_hash: str,
) -> dict[str, Any]:
    return _child_payload(
        "lab-external-identity-crosswalk-v1",
        row,
        study_record_sha256=study_hash,
        source_extraction_record_sha256=extraction_hash,
        fields={
            "component_id": row.component_id,
            "resolution_status": row.resolution_status,
            "material_id": row.material_id,
            "source_identity": row.source_identity_json,
            "resolved_identity": row.resolved_identity_json,
            "evidence": row.evidence_json,
        },
    )


def _conflict_payload(
    row: LabExternalStudyConflict,
    study_hash: str,
    extraction_hash: str,
    related_extraction_hash: str,
) -> dict[str, Any]:
    return _child_payload(
        "lab-external-study-conflict-v1",
        row,
        study_record_sha256=study_hash,
        source_extraction_record_sha256=extraction_hash,
        fields={
            "conflict_key": row.conflict_key,
            "conflict_type": row.conflict_type,
            "conflict_state": row.conflict_state,
            "related_extraction_id": row.related_extraction_id,
            "related_extraction_record_sha256": related_extraction_hash,
            "details": row.details_json,
        },
    )


class LabExternalStudyServiceMixin:
    """Own admission rules while Laboratory Beta remains persistence authority."""

    if TYPE_CHECKING:
        repository: LabRepository
        session: AsyncSession

        def _transaction(self) -> AbstractAsyncContextManager[None]: ...

        async def assess_source_use(self, request: SourceUseRequest): ...

        async def is_accepted_for_scoped_use(
            self,
            subject_type: str,
            subject_id: str,
            *,
            required_scope: str,
        ) -> bool: ...

    async def _accepted_external_extraction(
        self,
        extraction_id: str,
        *,
        source_version_id: str,
        output_record_id: str | None,
    ) -> LabSourceExtractionRecord:
        extraction = await self.repository.get_source_extraction(extraction_id)
        if extraction is None:
            raise ExternalStudyAdmissionError(
                "EXTERNAL_STUDY_EXTRACTION_NOT_FOUND",
                f"B1 extraction not found: {extraction_id}",
            )
        if extraction.source_version_id != source_version_id:
            raise ExternalStudyAdmissionError(
                "EXTERNAL_STUDY_SOURCE_FAMILY_LEAKAGE",
                "External-study extraction belongs to a different source version.",
            )
        if output_record_id is not None and (
            extraction.output_observation_id != output_record_id
        ):
            raise ExternalStudyAdmissionError(
                "EXTERNAL_STUDY_EXTRACTION_OUTPUT_MISMATCH",
                "B1 extraction output identity does not match the external record.",
            )
        accepted = await self.is_accepted_for_scoped_use(
            "EXTRACTION_RECORD",
            extraction.id,
            required_scope=EXTERNAL_STUDY_SCOPE,
        )
        if not accepted:
            raise ExternalStudyAdmissionError(
                "EXTERNAL_STUDY_EXTRACTION_NOT_ACCEPTED",
                "B1 extraction is not accepted for external-study admission.",
            )
        return extraction

    @staticmethod
    def _validate_external_graph(command: ExternalStudyInput) -> None:
        groups = (
            command.stimuli,
            command.components,
            command.conditions,
            command.experimental_units,
            command.observations,
            command.crosswalks,
            command.conflicts,
        )
        record_ids = [command.record_id]
        for group in groups:
            record_ids.extend(item.record_id for item in group)
        if len(record_ids) != len(set(record_ids)):
            raise ExternalStudyAdmissionError(
                "EXTERNAL_STUDY_DUPLICATE_RECORD_ID",
                "External-study graph record IDs must be unique.",
            )
        for rows, key_name in (
            (command.stimuli, "stimulus_key"),
            (command.conditions, "condition_key"),
            (command.experimental_units, "unit_key"),
            (command.observations, "observation_key"),
            (command.conflicts, "conflict_key"),
        ):
            keys = [getattr(row, key_name) for row in rows]
            if len(keys) != len(set(keys)):
                raise ExternalStudyAdmissionError(
                    "EXTERNAL_STUDY_DUPLICATE_SOURCE_KEY",
                    f"External-study {key_name} values must be unique.",
                )

        stimulus_ids = {row.record_id for row in command.stimuli}
        component_ids = {row.record_id for row in command.components}
        condition_ids = {row.record_id for row in command.conditions}
        unit_ids = {row.record_id for row in command.experimental_units}
        for component in command.components:
            if component.stimulus_version_id not in stimulus_ids:
                raise ExternalStudyAdmissionError(
                    "EXTERNAL_STUDY_REFERENCE_OUTSIDE_GRAPH",
                    "Stimulus component references another study graph.",
                )
        component_positions = [
            (row.stimulus_version_id, row.position)
            for row in command.components
        ]
        component_keys = [
            (row.stimulus_version_id, row.component_key)
            for row in command.components
        ]
        if len(component_positions) != len(set(component_positions)) or (
            len(component_keys) != len(set(component_keys))
        ):
            raise ExternalStudyAdmissionError(
                "EXTERNAL_STUDY_DUPLICATE_SOURCE_KEY",
                "Component positions and keys must be unique within a stimulus.",
            )
        for condition in command.conditions:
            if (
                condition.primary_stimulus_version_id is not None
                and condition.primary_stimulus_version_id not in stimulus_ids
            ):
                raise ExternalStudyAdmissionError(
                    "EXTERNAL_STUDY_REFERENCE_OUTSIDE_GRAPH",
                    "Condition references another study graph.",
                )
        parents = {
            row.record_id: row.parent_unit_id
            for row in command.experimental_units
            if row.parent_unit_id is not None
        }
        for child, parent in parents.items():
            if parent not in unit_ids:
                raise ExternalStudyAdmissionError(
                    "EXTERNAL_STUDY_REFERENCE_OUTSIDE_GRAPH",
                    "Experimental-unit parent belongs to another study graph.",
                )
            seen = {child}
            current: str | None = parent
            while current is not None:
                if current in seen:
                    raise ExternalStudyAdmissionError(
                        "EXTERNAL_STUDY_UNIT_CYCLE",
                        "Experimental-unit nesting must be acyclic.",
                    )
                seen.add(current)
                current = parents.get(current)
        unit_by_id = {row.record_id: row for row in command.experimental_units}
        expected_grain = {
            "PARTICIPANT": "INDIVIDUAL",
            "GROUP": "GROUP_AGGREGATE",
            "AGGREGATE": "STUDY_AGGREGATE",
            "SAMPLE": "SAMPLE",
        }
        for observation in command.observations:
            if observation.condition_id not in condition_ids or (
                observation.experimental_unit_id not in unit_ids
            ):
                raise ExternalStudyAdmissionError(
                    "EXTERNAL_STUDY_REFERENCE_OUTSIDE_GRAPH",
                    "Observation references another study graph.",
                )
            if (
                observation.primary_stimulus_version_id is not None
                and observation.primary_stimulus_version_id not in stimulus_ids
            ):
                raise ExternalStudyAdmissionError(
                    "EXTERNAL_STUDY_REFERENCE_OUTSIDE_GRAPH",
                    "Observation references another study stimulus.",
                )
            if any(
                row["stimulus_version_id"] not in stimulus_ids
                for row in observation.presentation
            ):
                raise ExternalStudyAdmissionError(
                    "EXTERNAL_STUDY_REFERENCE_OUTSIDE_GRAPH",
                    "Observation presentation references another study graph.",
                )
            unit = unit_by_id[observation.experimental_unit_id]
            if expected_grain[unit.unit_grain] != observation.observation_grain:
                raise ExternalStudyAdmissionError(
                    "EXTERNAL_STUDY_GRAIN_MISMATCH",
                    "Aggregate source rows cannot become pseudo-participant observations.",
                )
        for crosswalk in command.crosswalks:
            if crosswalk.component_id not in component_ids:
                raise ExternalStudyAdmissionError(
                    "EXTERNAL_STUDY_REFERENCE_OUTSIDE_GRAPH",
                    "Identity crosswalk references another study graph.",
                )
        if len({row.component_id for row in command.crosswalks}) != len(
            command.crosswalks
        ):
            raise ExternalStudyAdmissionError(
                "EXTERNAL_STUDY_DUPLICATE_SOURCE_KEY",
                "Each stimulus component may have at most one identity crosswalk.",
            )
        component_by_id = {row.record_id: row for row in command.components}
        for crosswalk in command.crosswalks:
            if (
                crosswalk.source_identity
                != component_by_id[crosswalk.component_id].source_identity
            ):
                raise ExternalStudyAdmissionError(
                    "EXTERNAL_STUDY_IDENTITY_CROSSWALK_MISMATCH",
                    "Identity crosswalk must preserve the component source identity.",
                )

    async def register_external_study(
        self,
        command: ExternalStudyInput,
    ) -> ExternalStudyAdmissionResult:
        self._validate_external_graph(command)
        if (
            command.source_use_request.subject_source_version_id
            != command.source_version_id
            or command.source_use_request.intended_action != "INTERNAL_ANALYSIS"
        ):
            raise ExternalStudyAdmissionError(
                "EXTERNAL_STUDY_SOURCE_USE_REQUEST_MISMATCH",
                "External-study admission requires exact INTERNAL_ANALYSIS source scope.",
            )
        assessment = await self.assess_source_use(command.source_use_request)
        if assessment.assessment_state != "DECLARED_ALLOWED":
            raise ExternalStudyAdmissionError(
                "EXTERNAL_STUDY_SOURCE_USE_NOT_ALLOWED",
                "Operation-scoped B1 source use did not return DECLARED_ALLOWED.",
            )
        if not await self.is_accepted_for_scoped_use(
            "SOURCE_VERSION",
            command.source_version_id,
            required_scope=EXTERNAL_STUDY_SCOPE,
        ):
            raise ExternalStudyAdmissionError(
                "EXTERNAL_STUDY_SOURCE_NOT_ACCEPTED",
                "B1 source version is not accepted for external-study admission.",
            )

        async with self._transaction():
            source = await self.repository.get_source_document_version(
                command.source_version_id
            )
            if source is None:
                raise ExternalStudyAdmissionError(
                    "EXTERNAL_STUDY_SOURCE_NOT_FOUND",
                    "B1 source version was not found.",
                )
            if command.source_family != source.independence_group:
                raise ExternalStudyAdmissionError(
                    "EXTERNAL_STUDY_SOURCE_FAMILY_LEAKAGE",
                    "External study source family must equal the B1 independence group.",
                )
            if command.parent_version_id is None:
                if await self.repository.latest_external_study_version(
                    command.study_id
                ) is not None:
                    raise ExternalStudyAdmissionError(
                        "EXTERNAL_STUDY_ID_ALREADY_EXISTS",
                        "External study already has an immutable version.",
                    )
                parent = None
                version_number = 1
            else:
                parent = await self.repository.get_external_study_version(
                    command.parent_version_id
                )
                latest = await self.repository.latest_external_study_version(
                    command.study_id
                )
                if (
                    parent is None
                    or parent.study_id != command.study_id
                    or latest is None
                    or latest.id != parent.id
                ):
                    raise ExternalStudyAdmissionError(
                        "EXTERNAL_STUDY_PARENT_NOT_LATEST",
                        "External study revisions must extend the latest version.",
                    )
                version_number = parent.version_number + 1

            extraction_specs: list[tuple[str, str | None]] = [
                (command.source_extraction_id, command.record_id)
            ]
            for group in (
                command.stimuli,
                command.components,
                command.conditions,
                command.experimental_units,
                command.observations,
                command.crosswalks,
            ):
                extraction_specs.extend(
                    (row.source_extraction_id, row.record_id) for row in group
                )
            for conflict in command.conflicts:
                extraction_specs.extend(
                    (
                        (conflict.source_extraction_id, conflict.record_id),
                        (conflict.related_extraction_id, None),
                    )
                )
            extractions: dict[str, LabSourceExtractionRecord] = {}
            for extraction_id, output_id in extraction_specs:
                if extraction_id in extractions:
                    extraction = extractions[extraction_id]
                    if output_id is not None and (
                        extraction.output_observation_id != output_id
                    ):
                        raise ExternalStudyAdmissionError(
                            "EXTERNAL_STUDY_EXTRACTION_REUSED",
                            "One B1 extraction cannot own multiple external records.",
                        )
                    continue
                extractions[extraction_id] = await self._accepted_external_extraction(
                    extraction_id,
                    source_version_id=source.id,
                    output_record_id=output_id,
                )

            for crosswalk in command.crosswalks:
                if crosswalk.material_id is not None and (
                    await self.repository.get_material(crosswalk.material_id)
                    is None
                ):
                    raise ExternalStudyAdmissionError(
                        "EXTERNAL_STUDY_MATERIAL_NOT_FOUND",
                        "Identity crosswalk references an unknown project material.",
                    )

            parent_hash = parent.record_sha256 if parent is not None else None
            study = LabExternalStudyVersion(
                id=command.record_id,
                study_id=command.study_id,
                version_number=version_number,
                source_version_id=source.id,
                source_extraction_id=command.source_extraction_id,
                source_family=command.source_family,
                study_key=command.study_key,
                title=command.title,
                study_domain=command.study_domain,
                design_json=dict(command.design),
                protocol_json=dict(command.protocol),
                source_use_request_sha256=assessment.request_sha256,
                source_use_assessment_sha256=assessment.assessment_sha256,
                source_use_constraint_version_ids_json=list(
                    assessment.constraint_version_ids
                ),
                source_use_constraint_record_sha256s_json=list(
                    assessment.constraint_record_sha256s
                ),
                adapter_name=command.adapter_name,
                adapter_version=command.adapter_version,
                adapter_config_json=dict(command.adapter_config),
                authority_state="SOURCE_REPORTED_ONLY",
                supersedes_version_id=parent.id if parent is not None else None,
                parent_record_sha256=parent_hash,
                record_sha256="0" * 64,
            )
            study.record_sha256 = stable_json_hash(
                _study_payload(study, source_record_sha256=source.record_sha256)
            )
            if await self.repository.external_study_by_hash(study.record_sha256):
                raise ExternalStudyAdmissionError(
                    "EXTERNAL_STUDY_RECORD_ALREADY_EXISTS",
                    "An identical external-study version already exists.",
                )
            study = await self.repository.add(study)

            stimuli: list[LabExternalStimulusVersion] = []
            for stimulus_input in command.stimuli:
                stimulus_row = LabExternalStimulusVersion(
                    id=stimulus_input.record_id,
                    study_version_id=study.id,
                    stimulus_key=stimulus_input.stimulus_key,
                    source_extraction_id=stimulus_input.source_extraction_id,
                    stimulus_kind=stimulus_input.stimulus_kind,
                    label=stimulus_input.label,
                    matrix_json=dict(stimulus_input.matrix),
                    preparation_json=dict(stimulus_input.preparation),
                    context_json=dict(stimulus_input.context),
                    record_sha256="0" * 64,
                )
                stimulus_row.record_sha256 = stable_json_hash(
                    _stimulus_payload(
                        stimulus_row,
                        study.record_sha256,
                        extractions[
                            stimulus_input.source_extraction_id
                        ].record_sha256,
                    )
                )
                stimuli.append(await self.repository.add(stimulus_row))

            components: list[LabExternalStimulusComponent] = []
            for component_input in command.components:
                component_row = LabExternalStimulusComponent(
                    id=component_input.record_id,
                    stimulus_version_id=component_input.stimulus_version_id,
                    position=component_input.position,
                    component_key=component_input.component_key,
                    source_extraction_id=component_input.source_extraction_id,
                    source_identity_json=dict(component_input.source_identity),
                    quantity_value_text=component_input.quantity_value_text,
                    quantity_unit=component_input.quantity_unit,
                    quantity_basis=component_input.quantity_basis,
                    concentration_value_text=(
                        component_input.concentration_value_text
                    ),
                    concentration_unit=component_input.concentration_unit,
                    concentration_basis=component_input.concentration_basis,
                    carrier_json=dict(component_input.carrier),
                    purity_json=dict(component_input.purity),
                    role=component_input.role,
                    record_sha256="0" * 64,
                )
                component_row.record_sha256 = stable_json_hash(
                    _component_payload(
                        component_row,
                        study.record_sha256,
                        extractions[
                            component_input.source_extraction_id
                        ].record_sha256,
                    )
                )
                components.append(await self.repository.add(component_row))

            conditions: list[LabExternalCondition] = []
            for condition_input in command.conditions:
                condition_row = LabExternalCondition(
                    id=condition_input.record_id,
                    study_version_id=study.id,
                    condition_key=condition_input.condition_key,
                    source_extraction_id=condition_input.source_extraction_id,
                    condition_role=condition_input.condition_role,
                    label=condition_input.label,
                    primary_stimulus_version_id=(
                        condition_input.primary_stimulus_version_id
                    ),
                    factors_json=dict(condition_input.factors),
                    context_json=dict(condition_input.context),
                    record_sha256="0" * 64,
                )
                condition_row.record_sha256 = stable_json_hash(
                    _condition_payload(
                        condition_row,
                        study.record_sha256,
                        extractions[
                            condition_input.source_extraction_id
                        ].record_sha256,
                    )
                )
                conditions.append(await self.repository.add(condition_row))

            units: list[LabExternalExperimentalUnit] = []
            pending_units = {row.record_id: row for row in command.experimental_units}
            while pending_units:
                ready = [
                    item
                    for item in pending_units.values()
                    if item.parent_unit_id is None
                    or item.parent_unit_id not in pending_units
                ]
                if not ready:
                    raise ExternalStudyAdmissionError(
                        "EXTERNAL_STUDY_UNIT_CYCLE",
                        "Experimental-unit nesting must be acyclic.",
                    )
                for unit_input in sorted(ready, key=lambda value: value.unit_key):
                    unit_row = LabExternalExperimentalUnit(
                        id=unit_input.record_id,
                        study_version_id=study.id,
                        unit_key=unit_input.unit_key,
                        source_extraction_id=unit_input.source_extraction_id,
                        unit_grain=unit_input.unit_grain,
                        parent_unit_id=unit_input.parent_unit_id,
                        pseudonymous_token=unit_input.pseudonymous_token,
                        reported_n=unit_input.reported_n,
                        context_json=dict(unit_input.context),
                        record_sha256="0" * 64,
                    )
                    unit_row.record_sha256 = stable_json_hash(
                        _unit_payload(
                            unit_row,
                            study.record_sha256,
                            extractions[
                                unit_input.source_extraction_id
                            ].record_sha256,
                        )
                    )
                    units.append(await self.repository.add(unit_row))
                    pending_units.pop(unit_input.record_id)

            observations: list[LabExternalObservation] = []
            for observation_input in command.observations:
                observation_row = LabExternalObservation(
                    id=observation_input.record_id,
                    study_version_id=study.id,
                    observation_key=observation_input.observation_key,
                    source_extraction_id=observation_input.source_extraction_id,
                    condition_id=observation_input.condition_id,
                    experimental_unit_id=(
                        observation_input.experimental_unit_id
                    ),
                    primary_stimulus_version_id=(
                        observation_input.primary_stimulus_version_id
                    ),
                    trial_key=observation_input.trial_key,
                    session_key=observation_input.session_key,
                    repeat_index=observation_input.repeat_index,
                    presentation_json=[
                        dict(value) for value in observation_input.presentation
                    ],
                    endpoint_key=observation_input.endpoint_key,
                    value_json=(
                        dict(observation_input.value)
                        if observation_input.value is not None
                        else None
                    ),
                    original_unit=observation_input.original_unit,
                    scale_json=dict(observation_input.scale),
                    timepoint_json=dict(observation_input.timepoint),
                    replicate_index=observation_input.replicate_index,
                    observation_grain=observation_input.observation_grain,
                    aggregation_statistic=(
                        observation_input.aggregation_statistic
                    ),
                    missingness=observation_input.missingness,
                    uncertainty_json=dict(observation_input.uncertainty),
                    limitations_json=list(observation_input.limitations),
                    record_sha256="0" * 64,
                )
                observation_row.record_sha256 = stable_json_hash(
                    _observation_payload(
                        observation_row,
                        study.record_sha256,
                        extractions[
                            observation_input.source_extraction_id
                        ].record_sha256,
                    )
                )
                observations.append(await self.repository.add(observation_row))

            crosswalks: list[LabExternalIdentityCrosswalk] = []
            for crosswalk_input in command.crosswalks:
                crosswalk_row = LabExternalIdentityCrosswalk(
                    id=crosswalk_input.record_id,
                    component_id=crosswalk_input.component_id,
                    source_extraction_id=crosswalk_input.source_extraction_id,
                    resolution_status=crosswalk_input.resolution_status,
                    material_id=crosswalk_input.material_id,
                    source_identity_json=dict(crosswalk_input.source_identity),
                    resolved_identity_json=dict(
                        crosswalk_input.resolved_identity
                    ),
                    evidence_json=dict(crosswalk_input.evidence),
                    record_sha256="0" * 64,
                )
                crosswalk_row.record_sha256 = stable_json_hash(
                    _crosswalk_payload(
                        crosswalk_row,
                        study.record_sha256,
                        extractions[
                            crosswalk_input.source_extraction_id
                        ].record_sha256,
                    )
                )
                crosswalks.append(await self.repository.add(crosswalk_row))

            conflicts: list[LabExternalStudyConflict] = []
            for conflict_input in command.conflicts:
                conflict_row = LabExternalStudyConflict(
                    id=conflict_input.record_id,
                    study_version_id=study.id,
                    conflict_key=conflict_input.conflict_key,
                    conflict_type=conflict_input.conflict_type,
                    conflict_state=conflict_input.conflict_state,
                    source_extraction_id=conflict_input.source_extraction_id,
                    related_extraction_id=conflict_input.related_extraction_id,
                    details_json=dict(conflict_input.details),
                    record_sha256="0" * 64,
                )
                conflict_row.record_sha256 = stable_json_hash(
                    _conflict_payload(
                        conflict_row,
                        study.record_sha256,
                        extractions[
                            conflict_input.source_extraction_id
                        ].record_sha256,
                        extractions[
                            conflict_input.related_extraction_id
                        ].record_sha256,
                    )
                )
                conflicts.append(await self.repository.add(conflict_row))

        projection = await self.external_study_projection(study.id)
        return ExternalStudyAdmissionResult(
            study=study,
            stimuli=tuple(stimuli),
            components=tuple(components),
            conditions=tuple(conditions),
            experimental_units=tuple(units),
            observations=tuple(observations),
            crosswalks=tuple(crosswalks),
            conflicts=tuple(conflicts),
            projection=projection,
            projection_sha256=str(projection["projection_sha256"]),
        )

    async def external_study_projection(
        self,
        study_version_id: str,
    ) -> dict[str, Any]:
        identifier = _uuid(study_version_id, "study_version_id")
        self.session.expire_all()
        study = await self.repository.get_external_study_version(identifier)
        if study is None:
            raise ExternalStudyAdmissionError(
                "EXTERNAL_STUDY_NOT_FOUND",
                "External study version was not found.",
            )
        source = await self.repository.get_source_document_version(
            study.source_version_id
        )
        if source is None:
            raise ExternalStudyAdmissionError(
                "EXTERNAL_STUDY_SOURCE_NOT_FOUND",
                "B1 source version was not found.",
            )
        if stable_json_hash(
            _study_payload(study, source_record_sha256=source.record_sha256)
        ) != study.record_sha256:
            raise ExternalStudyAdmissionError(
                "EXTERNAL_STUDY_RECORD_HASH_MISMATCH",
                "External study record hash does not replay.",
            )
        stimuli = await self.repository.external_study_stimuli(study.id)
        components = await self.repository.external_study_components(study.id)
        conditions = await self.repository.external_study_conditions(study.id)
        units = await self.repository.external_study_units(study.id)
        observations = await self.repository.external_study_observations(study.id)
        crosswalks = await self.repository.external_study_crosswalks(study.id)
        conflicts = await self.repository.external_study_conflicts(study.id)

        extraction_ids = {
            row.source_extraction_id
            for group in (
                stimuli,
                components,
                conditions,
                units,
                observations,
                crosswalks,
                conflicts,
            )
            for row in group
        } | {row.related_extraction_id for row in conflicts}
        extraction_hashes: dict[str, str] = {}
        for extraction_id in extraction_ids:
            extraction = await self.repository.get_source_extraction(extraction_id)
            if extraction is None:
                raise ExternalStudyAdmissionError(
                    "EXTERNAL_STUDY_EXTRACTION_NOT_FOUND",
                    "Referenced B1 extraction was not found.",
                )
            extraction_hashes[extraction.id] = extraction.record_sha256

        payloads: list[tuple[object, dict[str, Any]]] = []
        payloads.extend(
            (
                row,
                _stimulus_payload(
                    row,
                    study.record_sha256,
                    extraction_hashes[row.source_extraction_id],
                ),
            )
            for row in stimuli
        )
        payloads.extend(
            (
                row,
                _component_payload(
                    row,
                    study.record_sha256,
                    extraction_hashes[row.source_extraction_id],
                ),
            )
            for row in components
        )
        payloads.extend(
            (
                row,
                _condition_payload(
                    row,
                    study.record_sha256,
                    extraction_hashes[row.source_extraction_id],
                ),
            )
            for row in conditions
        )
        payloads.extend(
            (
                row,
                _unit_payload(
                    row,
                    study.record_sha256,
                    extraction_hashes[row.source_extraction_id],
                ),
            )
            for row in units
        )
        payloads.extend(
            (
                row,
                _observation_payload(
                    row,
                    study.record_sha256,
                    extraction_hashes[row.source_extraction_id],
                ),
            )
            for row in observations
        )
        payloads.extend(
            (
                row,
                _crosswalk_payload(
                    row,
                    study.record_sha256,
                    extraction_hashes[row.source_extraction_id],
                ),
            )
            for row in crosswalks
        )
        payloads.extend(
            (
                row,
                _conflict_payload(
                    row,
                    study.record_sha256,
                    extraction_hashes[row.source_extraction_id],
                    extraction_hashes[row.related_extraction_id],
                ),
            )
            for row in conflicts
        )
        for row, payload in payloads:
            if stable_json_hash(payload) != getattr(row, "record_sha256"):
                raise ExternalStudyAdmissionError(
                    "EXTERNAL_STUDY_RECORD_HASH_MISMATCH",
                    "An external-study child record hash does not replay.",
                )

        projection: dict[str, Any] = {
            "schema": "lab-external-study-projection-v1",
            "study": {
                **_study_payload(study, source_record_sha256=source.record_sha256),
                "record_sha256": study.record_sha256,
            },
            "stimuli": [
                {**payload, "record_sha256": row.record_sha256}
                for row, payload in payloads
                if isinstance(row, LabExternalStimulusVersion)
            ],
            "components": [
                {**payload, "record_sha256": row.record_sha256}
                for row, payload in payloads
                if isinstance(row, LabExternalStimulusComponent)
            ],
            "conditions": [
                {**payload, "record_sha256": row.record_sha256}
                for row, payload in payloads
                if isinstance(row, LabExternalCondition)
            ],
            "experimental_units": [
                {**payload, "record_sha256": row.record_sha256}
                for row, payload in payloads
                if isinstance(row, LabExternalExperimentalUnit)
            ],
            "observations": [
                {**payload, "record_sha256": row.record_sha256}
                for row, payload in payloads
                if isinstance(row, LabExternalObservation)
            ],
            "crosswalks": [
                {**payload, "record_sha256": row.record_sha256}
                for row, payload in payloads
                if isinstance(row, LabExternalIdentityCrosswalk)
            ],
            "conflicts": [
                {**payload, "record_sha256": row.record_sha256}
                for row, payload in payloads
                if isinstance(row, LabExternalStudyConflict)
            ],
            "authority": {
                "formula": False,
                "inventory": False,
                "physical_execution": False,
                "model_training": False,
                "sensory_truth": False,
                "release": False,
            },
        }
        projection_hash = stable_json_hash(projection)
        projection["projection_sha256"] = projection_hash
        return projection


__all__ = [
    "EXTERNAL_STUDY_SCOPE",
    "ExternalConditionInput",
    "ExternalExperimentalUnitInput",
    "ExternalIdentityCrosswalkInput",
    "ExternalObservationInput",
    "ExternalStimulusComponentInput",
    "ExternalStimulusInput",
    "ExternalStudyAdmissionError",
    "ExternalStudyAdmissionResult",
    "ExternalStudyConflictInput",
    "ExternalStudyInput",
    "LabExternalStudyServiceMixin",
]
