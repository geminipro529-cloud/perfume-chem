"""Strict, append-only intake for project-owned external-validation records.

This service records evidence-shaped bytes only.  It never admits them as
scientific evidence, runs a sensory analysis, fits a model, ranks a formula,
or grants physical, safety, compounding, or release authority.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from contextlib import AbstractAsyncContextManager
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from typing import TYPE_CHECKING, Any, cast

from engine.calibration.hashing import stable_json_hash
from engine.sensory.panel_contract import REQUIRED_BINDING_IDS
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lab import LabApplication, LabExperiment, LabSample
from app.models.lab_external_validation import LabExternalValidationRecord

if TYPE_CHECKING:
    from app.repositories.lab import LabRepository

EXTERNAL_VALIDATION_PROTOCOL_SCHEMA = "lab-external-validation-protocol-v1"
EXTERNAL_VALIDATION_RECORD_SCHEMA = "lab-external-validation-record-v1"

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,95}$")
_AUTHORITY_KEYS = (
    "scientific_authority",
    "sensory_authority",
    "model_calibration_authority",
    "release_authority",
    "safety_authority",
    "compounding_authority",
    "evidence_admission_authorized",
)
_PROTOCOL_FIELDS = {
    "schema_version",
    "protocol_id",
    "protocol_locked",
    "bindings",
    "endpoint_scales",
    "expected_temporal_cells",
    "expected_pairwise_cells",
    "authority",
}
_TEMPORAL_MANIFEST_FIELDS = {
    "blind_code",
    "assessor_token_sha256",
    "qualification_receipt_sha256",
    "session_token_sha256",
    "repeat_id",
    "time_seconds",
    "endpoint_id",
    "presentation_sequence_id",
    "presentation_position",
    "provenance_receipt_sha256",
}
_PAIRWISE_MANIFEST_FIELDS = {
    "primary_blind_code",
    "secondary_blind_code",
    "assessor_token_sha256",
    "qualification_receipt_sha256",
    "session_token_sha256",
    "repeat_id",
    "time_seconds",
    "criterion_id",
    "presentation_sequence_id",
    "first_presented_blind_code",
    "provenance_receipt_sha256",
}
_FORBIDDEN_RAW_IDENTITY_FIELDS = {
    "assessor_id",
    "assessor_name",
    "participant_id",
    "participant_name",
    "email",
    "phone",
    "address",
    "raw_identity",
}


class ExternalValidationError(ValueError):
    """Stable fail-closed error for strict validation intake."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


class ExternalValidationConflictError(ExternalValidationError):
    """A replay key or canonical cell conflicts with immutable history."""


class ExternalValidationNotFoundError(ExternalValidationError):
    """A required persisted record was not found."""


def _invalid(code: str, message: str) -> ExternalValidationError:
    return ExternalValidationError(code, message)


def _text(value: object, field: str, *, maximum: int = 255) -> str:
    if not isinstance(value, str):
        raise _invalid("INVALID_EXTERNAL_VALIDATION_REQUEST", f"{field} must be text.")
    normalized = value.strip()
    if not normalized or len(normalized) > maximum:
        raise _invalid(
            "INVALID_EXTERNAL_VALIDATION_REQUEST",
            f"{field} must be nonblank and at most {maximum} characters.",
        )
    return normalized


def _sha256(value: object, field: str) -> str:
    normalized = _text(value, field, maximum=64)
    if not _SHA256_RE.fullmatch(normalized):
        raise _invalid(
            "INVALID_EXTERNAL_VALIDATION_REQUEST",
            f"{field} must be a lowercase SHA-256 digest.",
        )
    return normalized


def _decimal_text(
    value: object,
    field: str,
    *,
    nonnegative: bool,
) -> tuple[Decimal, str]:
    if isinstance(value, bool) or not isinstance(value, str):
        raise _invalid(
            "INVALID_EXTERNAL_VALIDATION_REQUEST",
            f"{field} must be a canonical decimal string.",
        )
    try:
        decimal_value = Decimal(value)
    except InvalidOperation as exc:
        raise _invalid(
            "INVALID_EXTERNAL_VALIDATION_REQUEST",
            f"{field} must be a finite canonical decimal string.",
        ) from exc
    if not decimal_value.is_finite() or (nonnegative and decimal_value < 0):
        qualifier = "finite and nonnegative" if nonnegative else "finite"
        raise _invalid(
            "INVALID_EXTERNAL_VALIDATION_REQUEST",
            f"{field} must be {qualifier}.",
        )
    if decimal_value == 0:
        canonical = "0"
    else:
        canonical = format(decimal_value, "f")
        if "." in canonical:
            canonical = canonical.rstrip("0").rstrip(".")
    if value != canonical or len(canonical) > 128:
        raise _invalid(
            "INVALID_EXTERNAL_VALIDATION_REQUEST",
            f"{field} must use canonical plain-decimal text.",
        )
    return decimal_value, canonical


def _mapping(value: object, field: str) -> dict[str, Any]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise _invalid("INVALID_EXTERNAL_VALIDATION_PROTOCOL", f"{field} must be an object.")
    normalized = {str(key): item for key, item in value.items()}
    try:
        stable_json_hash(normalized)
    except (TypeError, ValueError) as exc:
        raise _invalid(
            "INVALID_EXTERNAL_VALIDATION_PROTOCOL",
            f"{field} must contain canonical finite JSON values.",
        ) from exc
    return normalized


def _sequence(value: object, field: str) -> list[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise _invalid("INVALID_EXTERNAL_VALIDATION_PROTOCOL", f"{field} must be an array.")
    return list(value)


def _reject_raw_identity_fields(value: object, path: str) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key).strip().lower() in _FORBIDDEN_RAW_IDENTITY_FIELDS:
                raise _invalid(
                    "EXTERNAL_VALIDATION_RAW_IDENTITY_PROHIBITED",
                    f"Raw assessor identity is prohibited at {path}.{key}.",
                )
            _reject_raw_identity_fields(item, f"{path}.{key}")
    elif isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray)
    ):
        for index, item in enumerate(value):
            _reject_raw_identity_fields(item, f"{path}[{index}]")


def _normalize_manifest_decimal(value: object, field: str) -> str:
    _number, canonical = _decimal_text(value, field, nonnegative=True)
    return canonical


def _validate_protocol(protocol_value: object) -> dict[str, Any]:
    protocol = _mapping(protocol_value, "experiment protocol")
    if set(protocol) != _PROTOCOL_FIELDS:
        raise _invalid(
            "INVALID_EXTERNAL_VALIDATION_PROTOCOL",
            "The protocol must use the exact v1 external-validation field set.",
        )
    if protocol.get("schema_version") != EXTERNAL_VALIDATION_PROTOCOL_SCHEMA:
        raise _invalid(
            "INVALID_EXTERNAL_VALIDATION_PROTOCOL",
            "The experiment is not bound to the strict external-validation protocol.",
        )
    protocol_id = _text(protocol.get("protocol_id"), "protocol_id", maximum=96)
    if not _IDENTIFIER_RE.fullmatch(protocol_id):
        raise _invalid(
            "INVALID_EXTERNAL_VALIDATION_PROTOCOL",
            "protocol_id must be a lowercase stable identifier.",
        )
    if protocol.get("protocol_locked") is not True:
        raise _invalid(
            "EXTERNAL_VALIDATION_PROTOCOL_NOT_LOCKED",
            "The external-validation protocol must be locked before intake.",
        )

    bindings = _sequence(protocol.get("bindings"), "bindings")
    normalized_bindings: dict[str, str] = {}
    for index, value in enumerate(bindings):
        binding = _mapping(value, f"bindings[{index}]")
        if set(binding) != {"binding_id", "state", "sha256"}:
            raise _invalid(
                "EXTERNAL_VALIDATION_BINDINGS_INCOMPLETE",
                "Every protocol binding must contain only binding_id, state, and sha256.",
            )
        binding_id = _text(binding.get("binding_id"), "binding_id", maximum=96)
        if binding_id in normalized_bindings or binding.get("state") != "bound":
            raise _invalid(
                "EXTERNAL_VALIDATION_BINDINGS_INCOMPLETE",
                "Protocol bindings must be unique and bound.",
            )
        normalized_bindings[binding_id] = _sha256(binding.get("sha256"), "binding sha256")
    if tuple(normalized_bindings) != REQUIRED_BINDING_IDS:
        raise _invalid(
            "EXTERNAL_VALIDATION_BINDINGS_INCOMPLETE",
            "The nine required protocol bindings must be present in canonical order.",
        )

    authority = _mapping(protocol.get("authority"), "authority")
    if set(authority) != set(_AUTHORITY_KEYS) or any(
        authority.get(key) is not False for key in _AUTHORITY_KEYS
    ):
        raise _invalid(
            "EXTERNAL_VALIDATION_AUTHORITY_ESCALATION",
            "The intake protocol may not grant scientific or action authority.",
        )

    scales = _sequence(protocol.get("endpoint_scales"), "endpoint_scales")
    scale_ids: set[str] = set()
    for index, value in enumerate(scales):
        scale = _mapping(value, f"endpoint_scales[{index}]")
        if set(scale) != {"endpoint_id", "minimum", "maximum", "unit"}:
            raise _invalid(
                "INVALID_EXTERNAL_VALIDATION_PROTOCOL",
                "Every endpoint scale must contain endpoint_id, minimum, maximum, and unit.",
            )
        endpoint_id = _text(scale.get("endpoint_id"), "endpoint_id", maximum=96)
        if endpoint_id in scale_ids or not _IDENTIFIER_RE.fullmatch(endpoint_id):
            raise _invalid(
                "INVALID_EXTERNAL_VALIDATION_PROTOCOL",
                "Endpoint scale identifiers must be unique stable identifiers.",
            )
        minimum, _ = _decimal_text(scale.get("minimum"), "scale minimum", nonnegative=False)
        maximum, _ = _decimal_text(scale.get("maximum"), "scale maximum", nonnegative=False)
        if maximum <= minimum:
            raise _invalid(
                "INVALID_EXTERNAL_VALIDATION_PROTOCOL",
                "Endpoint scale maximum must exceed its minimum.",
            )
        _text(scale.get("unit"), "scale unit", maximum=80)
        scale_ids.add(endpoint_id)

    temporal_cells = _sequence(
        protocol.get("expected_temporal_cells"), "expected_temporal_cells"
    )
    temporal_keys: set[tuple[object, ...]] = set()
    for index, value in enumerate(temporal_cells):
        cell = _mapping(value, f"expected_temporal_cells[{index}]")
        if set(cell) != _TEMPORAL_MANIFEST_FIELDS:
            raise _invalid(
                "INVALID_EXTERNAL_VALIDATION_PROTOCOL",
                "Temporal manifest cells must use the exact v1 field set.",
            )
        endpoint_id = _text(cell.get("endpoint_id"), "endpoint_id", maximum=96)
        if endpoint_id not in scale_ids:
            raise _invalid(
                "INVALID_EXTERNAL_VALIDATION_PROTOCOL",
                "Every temporal endpoint must have a declared scale.",
            )
        position = cell.get("presentation_position")
        if isinstance(position, bool) or not isinstance(position, int) or position < 1:
            raise _invalid(
                "INVALID_EXTERNAL_VALIDATION_PROTOCOL",
                "presentation_position must be a positive integer.",
            )
        temporal_key = (
            _text(cell.get("blind_code"), "blind_code", maximum=100),
            _sha256(cell.get("assessor_token_sha256"), "assessor_token_sha256"),
            _sha256(
                cell.get("qualification_receipt_sha256"),
                "qualification_receipt_sha256",
            ),
            _sha256(cell.get("session_token_sha256"), "session_token_sha256"),
            _text(cell.get("repeat_id"), "repeat_id"),
            _normalize_manifest_decimal(cell.get("time_seconds"), "time_seconds"),
            endpoint_id,
            _text(
                cell.get("presentation_sequence_id"),
                "presentation_sequence_id",
            ),
            position,
            _sha256(
                cell.get("provenance_receipt_sha256"),
                "provenance_receipt_sha256",
            ),
        )
        if temporal_key in temporal_keys:
            raise _invalid(
                "INVALID_EXTERNAL_VALIDATION_PROTOCOL",
                "The temporal manifest contains a duplicate canonical cell.",
            )
        temporal_keys.add(temporal_key)

    pairwise_cells = _sequence(
        protocol.get("expected_pairwise_cells"), "expected_pairwise_cells"
    )
    pairwise_keys: set[tuple[object, ...]] = set()
    for index, value in enumerate(pairwise_cells):
        cell = _mapping(value, f"expected_pairwise_cells[{index}]")
        if set(cell) != _PAIRWISE_MANIFEST_FIELDS:
            raise _invalid(
                "INVALID_EXTERNAL_VALIDATION_PROTOCOL",
                "Pairwise manifest cells must use the exact v1 field set.",
            )
        primary = _text(cell.get("primary_blind_code"), "primary_blind_code", maximum=100)
        secondary = _text(
            cell.get("secondary_blind_code"), "secondary_blind_code", maximum=100
        )
        first = _text(
            cell.get("first_presented_blind_code"),
            "first_presented_blind_code",
            maximum=100,
        )
        if primary == secondary or first not in {primary, secondary}:
            raise _invalid(
                "INVALID_EXTERNAL_VALIDATION_PROTOCOL",
                "Pairwise cells require distinct blind codes and a valid first presentation.",
            )
        criterion = _text(cell.get("criterion_id"), "criterion_id", maximum=96)
        if not _IDENTIFIER_RE.fullmatch(criterion):
            raise _invalid(
                "INVALID_EXTERNAL_VALIDATION_PROTOCOL",
                "criterion_id must be a stable identifier.",
            )
        pairwise_key = (
            primary,
            secondary,
            _sha256(cell.get("assessor_token_sha256"), "assessor_token_sha256"),
            _sha256(
                cell.get("qualification_receipt_sha256"),
                "qualification_receipt_sha256",
            ),
            _sha256(cell.get("session_token_sha256"), "session_token_sha256"),
            _text(cell.get("repeat_id"), "repeat_id"),
            _normalize_manifest_decimal(cell.get("time_seconds"), "time_seconds"),
            criterion,
            _text(
                cell.get("presentation_sequence_id"),
                "presentation_sequence_id",
            ),
            first,
            _sha256(
                cell.get("provenance_receipt_sha256"),
                "provenance_receipt_sha256",
            ),
        )
        if pairwise_key in pairwise_keys:
            raise _invalid(
                "INVALID_EXTERNAL_VALIDATION_PROTOCOL",
                "The pairwise manifest contains a duplicate canonical cell.",
            )
        pairwise_keys.add(pairwise_key)

    return protocol


def _application_snapshot(application: LabApplication) -> dict[str, Any]:
    return {
        "application_id": application.id,
        "sample_id": application.sample_id,
        "applied_at": application.applied_at.isoformat(),
        "dose": dict(application.dose_json),
        "context": dict(application.context_json),
    }


def _sample_snapshot(sample: LabSample) -> dict[str, str]:
    return {
        "sample_id": sample.id,
        "bottle_id": sample.bottle_id,
        "blind_code": sample.blind_code,
    }


def _validate_application_context(
    application: LabApplication,
    sample: LabSample,
    *,
    protocol_id: str,
    assessor_token_sha256: str,
    qualification_receipt_sha256: str,
    session_token_sha256: str,
    repeat_id: str,
) -> None:
    context = _mapping(application.context_json, "application context")
    dose = _mapping(application.dose_json, "application dose")
    _reject_raw_identity_fields(context, "application.context")
    _reject_raw_identity_fields(dose, "application.dose")
    if not context or not dose:
        raise _invalid(
            "EXTERNAL_VALIDATION_APPLICATION_SCOPE_INCOMPLETE",
            "Application context and dose must both be nonempty.",
        )
    expected = {
        "protocol_id": protocol_id,
        "blind_code": sample.blind_code,
        "assessor_token_sha256": assessor_token_sha256,
        "qualification_receipt_sha256": qualification_receipt_sha256,
        "session_token_sha256": session_token_sha256,
        "repeat_id": repeat_id,
    }
    if any(context.get(key) != value for key, value in expected.items()):
        raise _invalid(
            "EXTERNAL_VALIDATION_APPLICATION_SCOPE_MISMATCH",
            "The application does not match the protocol, blind sample, assessor, or session.",
        )


def _temporal_scale(
    protocol: Mapping[str, Any], endpoint_id: str
) -> tuple[Decimal, Decimal]:
    matches = [
        item
        for item in cast(list[dict[str, Any]], protocol["endpoint_scales"])
        if item.get("endpoint_id") == endpoint_id
    ]
    if len(matches) != 1:
        raise _invalid(
            "EXTERNAL_VALIDATION_ENDPOINT_NOT_DECLARED",
            "The temporal endpoint is not declared exactly once.",
        )
    minimum, _ = _decimal_text(matches[0]["minimum"], "scale minimum", nonnegative=False)
    maximum, _ = _decimal_text(matches[0]["maximum"], "scale maximum", nonnegative=False)
    return minimum, maximum


class LabExternalValidationServiceMixin:
    """Commands sharing the canonical :class:`LabService` transaction owner."""

    if TYPE_CHECKING:
        session: AsyncSession
        repository: "LabRepository"

        def _transaction(self) -> AbstractAsyncContextManager[None]: ...

    async def _resolve_application_scope(
        self,
        application_id: str,
    ) -> tuple[LabApplication, LabSample, LabExperiment]:
        application = await self.repository.get_application(application_id)
        if application is None:
            raise ExternalValidationNotFoundError(
                "EXTERNAL_VALIDATION_APPLICATION_NOT_FOUND",
                f"Application not found: {application_id}.",
            )
        sample = await self.repository.get_sample(application.sample_id)
        if sample is None:
            raise ExternalValidationNotFoundError(
                "EXTERNAL_VALIDATION_SAMPLE_NOT_FOUND",
                f"Sample not found for application: {application_id}.",
            )
        experiment = await self.repository.get_experiment(sample.experiment_id)
        if experiment is None:
            raise ExternalValidationNotFoundError(
                "EXTERNAL_VALIDATION_EXPERIMENT_NOT_FOUND",
                f"Experiment not found for application: {application_id}.",
            )
        return application, sample, experiment

    async def _persist_external_validation_record(
        self,
        *,
        values: dict[str, Any],
    ) -> tuple[LabExternalValidationRecord, bool]:
        requester_scope = values["requester_scope"]
        idempotency_hash = values["idempotency_key_sha256"]
        command_hash = values["command_sha256"]
        cell_hash = values["canonical_cell_sha256"]

        existing = await self.repository.external_validation_record_for_idempotency(
            requester_scope=requester_scope,
            idempotency_key_sha256=idempotency_hash,
        )
        if existing is not None:
            if existing.command_sha256 != command_hash:
                raise ExternalValidationConflictError(
                    "EXTERNAL_VALIDATION_IDEMPOTENCY_CONFLICT",
                    "The idempotency key was reused for a different command or scope.",
                )
            return existing, True

        existing = await self.repository.external_validation_record_for_cell(cell_hash)
        if existing is not None:
            if existing.command_sha256 != command_hash:
                raise ExternalValidationConflictError(
                    "EXTERNAL_VALIDATION_CELL_CONFLICT",
                    "The canonical observation cell already has different immutable content.",
                )
            return existing, True

        record = LabExternalValidationRecord(**values)
        try:
            await self.repository.add(record)
        except IntegrityError as exc:
            raise ExternalValidationConflictError(
                "EXTERNAL_VALIDATION_CONCURRENT_CONFLICT",
                "A concurrent writer claimed this idempotency key or canonical cell.",
            ) from exc
        return record, False

    async def record_external_temporal_observation(
        self,
        *,
        application_id: str,
        requester: str,
        idempotency_key: str,
        assessor_token_sha256: str,
        qualification_receipt_sha256: str,
        session_token_sha256: str,
        provenance_receipt_sha256: str,
        repeat_id: str,
        time_seconds: str,
        endpoint_id: str,
        presentation_sequence_id: str,
        presentation_position: int,
        missingness_state: str,
        value: str | None,
        missing_reason: str | None,
        schema_version: str,
    ) -> tuple[LabExternalValidationRecord, bool]:
        if schema_version != "lab-external-validation-temporal-request-v1":
            raise _invalid(
                "INVALID_EXTERNAL_VALIDATION_REQUEST_SCHEMA",
                "Unsupported temporal intake request schema.",
            )
        requester_scope = _text(requester, "requester")
        key = _text(idempotency_key, "idempotency_key")
        application_id = _text(application_id, "application_id", maximum=64)
        assessor = _sha256(assessor_token_sha256, "assessor_token_sha256")
        qualification = _sha256(
            qualification_receipt_sha256, "qualification_receipt_sha256"
        )
        session = _sha256(session_token_sha256, "session_token_sha256")
        provenance = _sha256(provenance_receipt_sha256, "provenance_receipt_sha256")
        repeat = _text(repeat_id, "repeat_id")
        _time, time_text = _decimal_text(time_seconds, "time_seconds", nonnegative=True)
        endpoint = _text(endpoint_id, "endpoint_id", maximum=96)
        sequence = _text(presentation_sequence_id, "presentation_sequence_id")
        if (
            isinstance(presentation_position, bool)
            or not isinstance(presentation_position, int)
            or presentation_position < 1
        ):
            raise _invalid(
                "INVALID_EXTERNAL_VALIDATION_REQUEST",
                "presentation_position must be a positive integer.",
            )
        if missingness_state not in {"OBSERVED", "MISSING", "NOT_APPLICABLE"}:
            raise _invalid(
                "INVALID_EXTERNAL_VALIDATION_REQUEST",
                "missingness_state is not supported.",
            )
        reason = _text(missing_reason, "missing_reason", maximum=500) if missing_reason else None
        value_text: str | None = None
        observed_value: Decimal | None = None
        if missingness_state == "OBSERVED":
            if value is None or reason is not None:
                raise _invalid(
                    "INVALID_EXTERNAL_VALIDATION_REQUEST",
                    "Observed temporal records require value and no missing reason.",
                )
            observed_value, value_text = _decimal_text(value, "value", nonnegative=False)
        elif value is not None or reason is None:
            raise _invalid(
                "INVALID_EXTERNAL_VALIDATION_REQUEST",
                "Missing temporal records require a reason and no value.",
            )

        async with self._transaction():
            application, sample, experiment = await self._resolve_application_scope(
                application_id
            )
            protocol = _validate_protocol(experiment.protocol_json)
            protocol_id = cast(str, protocol["protocol_id"])
            _validate_application_context(
                application,
                sample,
                protocol_id=protocol_id,
                assessor_token_sha256=assessor,
                qualification_receipt_sha256=qualification,
                session_token_sha256=session,
                repeat_id=repeat,
            )
            expected_key = (
                sample.blind_code,
                assessor,
                qualification,
                session,
                repeat,
                time_text,
                endpoint,
                sequence,
                presentation_position,
                provenance,
            )
            manifest_keys = {
                (
                    item["blind_code"],
                    item["assessor_token_sha256"],
                    item["qualification_receipt_sha256"],
                    item["session_token_sha256"],
                    item["repeat_id"],
                    item["time_seconds"],
                    item["endpoint_id"],
                    item["presentation_sequence_id"],
                    item["presentation_position"],
                    item["provenance_receipt_sha256"],
                )
                for item in cast(list[dict[str, Any]], protocol["expected_temporal_cells"])
            }
            if expected_key not in manifest_keys:
                raise _invalid(
                    "EXTERNAL_VALIDATION_CELL_NOT_DECLARED",
                    "The temporal observation cell is not in the locked protocol manifest.",
                )
            minimum, maximum = _temporal_scale(protocol, endpoint)
            if observed_value is not None and not minimum <= observed_value <= maximum:
                raise _invalid(
                    "EXTERNAL_VALIDATION_VALUE_OUT_OF_RANGE",
                    "The observed value is outside the locked endpoint scale.",
                )

            protocol_snapshot = {
                "schema_version": "lab-external-validation-protocol-snapshot-v1",
                "experiment_id": experiment.id,
                "protocol": protocol,
            }
            sample_snapshot = {
                "schema_version": "lab-external-validation-sample-snapshot-v1",
                "experiment_id": experiment.id,
                "primary": _sample_snapshot(sample),
                "secondary": None,
            }
            condition_snapshot = {
                "schema_version": "lab-external-validation-condition-snapshot-v1",
                "primary": _application_snapshot(application),
                "secondary": None,
            }
            order_snapshot = {
                "schema_version": "lab-external-validation-order-snapshot-v1",
                "presentation_sequence_id": sequence,
                "blind_code": sample.blind_code,
                "presentation_position": presentation_position,
            }
            assessor_snapshot = {
                "schema_version": "lab-external-validation-assessor-snapshot-v1",
                "assessor_token_sha256": assessor,
                "qualification_receipt_sha256": qualification,
                "session_token_sha256": session,
            }
            provenance_snapshot = {
                "schema_version": "lab-external-validation-provenance-snapshot-v1",
                "provenance_receipt_sha256": provenance,
                "protocol_binding_sha256s": [
                    item["sha256"] for item in cast(list[dict[str, Any]], protocol["bindings"])
                ],
                "requester_scope": requester_scope,
            }
            payload = {
                "schema_version": "lab-external-validation-temporal-payload-v1",
                "missingness_state": missingness_state,
                "value": value_text,
                "missing_reason": reason,
            }
            hashes = {
                "protocol_scope_sha256": stable_json_hash(protocol_snapshot),
                "sample_scope_sha256": stable_json_hash(sample_snapshot),
                "condition_scope_sha256": stable_json_hash(condition_snapshot),
                "order_scope_sha256": stable_json_hash(order_snapshot),
                "assessor_scope_sha256": stable_json_hash(assessor_snapshot),
                "provenance_scope_sha256": stable_json_hash(provenance_snapshot),
            }
            canonical_cell = {
                "schema_version": "lab-external-validation-cell-v1",
                "record_kind": "TEMPORAL_OBSERVATION",
                "protocol_scope_sha256": hashes["protocol_scope_sha256"],
                "primary_application_id": application.id,
                "assessor_token_sha256": assessor,
                "session_token_sha256": session,
                "repeat_id": repeat,
                "time_seconds": time_text,
                "endpoint_id": endpoint,
            }
            canonical_cell_sha256 = stable_json_hash(canonical_cell)
            command = {
                "schema_version": "lab-external-validation-command-v1",
                "record_kind": "TEMPORAL_OBSERVATION",
                "requester_scope": requester_scope,
                "canonical_cell_sha256": canonical_cell_sha256,
                "scope_hashes": hashes,
                "order": order_snapshot,
                "payload": payload,
            }
            command_sha256 = stable_json_hash(command)
            record_hash_payload = {
                "schema_version": EXTERNAL_VALIDATION_RECORD_SCHEMA,
                "command_sha256": command_sha256,
                "canonical_cell_sha256": canonical_cell_sha256,
                "scope_hashes": hashes,
                "payload": payload,
                "authority": {key: False for key in _AUTHORITY_KEYS},
                "processing_allowed": False,
            }
            values = {
                "schema_version": EXTERNAL_VALIDATION_RECORD_SCHEMA,
                "record_kind": "TEMPORAL_OBSERVATION",
                "experiment_id": experiment.id,
                "primary_application_id": application.id,
                "secondary_application_id": None,
                "requester_scope": requester_scope,
                "protocol_id": protocol_id,
                "endpoint_id": endpoint,
                "repeat_id": repeat,
                "time_seconds_decimal_text": time_text,
                "presentation_sequence_id": sequence,
                "presentation_position": presentation_position,
                "missingness_state": missingness_state,
                "value_decimal_text": value_text,
                "preference_outcome": None,
                "missing_reason": reason,
                "protocol_snapshot_json": protocol_snapshot,
                "sample_snapshot_json": sample_snapshot,
                "condition_snapshot_json": condition_snapshot,
                "order_snapshot_json": order_snapshot,
                "assessor_snapshot_json": assessor_snapshot,
                "provenance_snapshot_json": provenance_snapshot,
                "payload_json": payload,
                "idempotency_key_sha256": sha256(key.encode("utf-8")).hexdigest(),
                "command_sha256": command_sha256,
                "canonical_cell_sha256": canonical_cell_sha256,
                **hashes,
                "record_sha256": stable_json_hash(record_hash_payload),
                "processing_allowed": False,
                **{key: False for key in _AUTHORITY_KEYS},
            }
            return await self._persist_external_validation_record(values=values)

    async def record_external_pairwise_preference(
        self,
        *,
        primary_application_id: str,
        secondary_application_id: str,
        requester: str,
        idempotency_key: str,
        assessor_token_sha256: str,
        qualification_receipt_sha256: str,
        session_token_sha256: str,
        provenance_receipt_sha256: str,
        repeat_id: str,
        time_seconds: str,
        criterion_id: str,
        presentation_sequence_id: str,
        first_presented_application_id: str,
        missingness_state: str,
        preference_outcome: str | None,
        missing_reason: str | None,
        schema_version: str,
    ) -> tuple[LabExternalValidationRecord, bool]:
        if schema_version != "lab-external-validation-pairwise-request-v1":
            raise _invalid(
                "INVALID_EXTERNAL_VALIDATION_REQUEST_SCHEMA",
                "Unsupported pairwise intake request schema.",
            )
        requester_scope = _text(requester, "requester")
        key = _text(idempotency_key, "idempotency_key")
        primary_id = _text(primary_application_id, "primary_application_id", maximum=64)
        secondary_id = _text(
            secondary_application_id, "secondary_application_id", maximum=64
        )
        first_id = _text(
            first_presented_application_id,
            "first_presented_application_id",
            maximum=64,
        )
        if primary_id == secondary_id or first_id not in {primary_id, secondary_id}:
            raise _invalid(
                "INVALID_EXTERNAL_VALIDATION_REQUEST",
                "Pairwise intake requires distinct applications and a valid first presentation.",
            )
        assessor = _sha256(assessor_token_sha256, "assessor_token_sha256")
        qualification = _sha256(
            qualification_receipt_sha256, "qualification_receipt_sha256"
        )
        session = _sha256(session_token_sha256, "session_token_sha256")
        provenance = _sha256(provenance_receipt_sha256, "provenance_receipt_sha256")
        repeat = _text(repeat_id, "repeat_id")
        _time, time_text = _decimal_text(time_seconds, "time_seconds", nonnegative=True)
        criterion = _text(criterion_id, "criterion_id", maximum=96)
        sequence = _text(presentation_sequence_id, "presentation_sequence_id")
        if missingness_state not in {"OBSERVED", "MISSING", "NOT_APPLICABLE"}:
            raise _invalid(
                "INVALID_EXTERNAL_VALIDATION_REQUEST",
                "missingness_state is not supported.",
            )
        reason = _text(missing_reason, "missing_reason", maximum=500) if missing_reason else None
        preference = preference_outcome
        if missingness_state == "OBSERVED":
            if preference not in {"PRIMARY", "SECONDARY", "TIE"} or reason is not None:
                raise _invalid(
                    "INVALID_EXTERNAL_VALIDATION_REQUEST",
                    "Observed pairwise records require a supported outcome and no missing reason.",
                )
        elif preference is not None or reason is None:
            raise _invalid(
                "INVALID_EXTERNAL_VALIDATION_REQUEST",
                "Missing pairwise records require a reason and no preference outcome.",
            )

        async with self._transaction():
            primary_app, primary_sample, experiment = await self._resolve_application_scope(
                primary_id
            )
            secondary_app, secondary_sample, secondary_experiment = (
                await self._resolve_application_scope(secondary_id)
            )
            if experiment.id != secondary_experiment.id:
                raise _invalid(
                    "EXTERNAL_VALIDATION_EXPERIMENT_MISMATCH",
                    "Compared applications must belong to the same experiment.",
                )
            protocol = _validate_protocol(experiment.protocol_json)
            protocol_id = cast(str, protocol["protocol_id"])
            for application, sample in (
                (primary_app, primary_sample),
                (secondary_app, secondary_sample),
            ):
                _validate_application_context(
                    application,
                    sample,
                    protocol_id=protocol_id,
                    assessor_token_sha256=assessor,
                    qualification_receipt_sha256=qualification,
                    session_token_sha256=session,
                    repeat_id=repeat,
                )
            first_code = (
                primary_sample.blind_code if first_id == primary_id else secondary_sample.blind_code
            )
            expected_key = (
                primary_sample.blind_code,
                secondary_sample.blind_code,
                assessor,
                qualification,
                session,
                repeat,
                time_text,
                criterion,
                sequence,
                first_code,
                provenance,
            )
            manifest_keys = {
                (
                    item["primary_blind_code"],
                    item["secondary_blind_code"],
                    item["assessor_token_sha256"],
                    item["qualification_receipt_sha256"],
                    item["session_token_sha256"],
                    item["repeat_id"],
                    item["time_seconds"],
                    item["criterion_id"],
                    item["presentation_sequence_id"],
                    item["first_presented_blind_code"],
                    item["provenance_receipt_sha256"],
                )
                for item in cast(list[dict[str, Any]], protocol["expected_pairwise_cells"])
            }
            if expected_key not in manifest_keys:
                raise _invalid(
                    "EXTERNAL_VALIDATION_CELL_NOT_DECLARED",
                    "The pairwise cell is not in the locked protocol manifest.",
                )

            protocol_snapshot = {
                "schema_version": "lab-external-validation-protocol-snapshot-v1",
                "experiment_id": experiment.id,
                "protocol": protocol,
            }
            sample_snapshot = {
                "schema_version": "lab-external-validation-sample-snapshot-v1",
                "experiment_id": experiment.id,
                "primary": _sample_snapshot(primary_sample),
                "secondary": _sample_snapshot(secondary_sample),
            }
            condition_snapshot = {
                "schema_version": "lab-external-validation-condition-snapshot-v1",
                "primary": _application_snapshot(primary_app),
                "secondary": _application_snapshot(secondary_app),
            }
            order_snapshot = {
                "schema_version": "lab-external-validation-order-snapshot-v1",
                "presentation_sequence_id": sequence,
                "primary_blind_code": primary_sample.blind_code,
                "secondary_blind_code": secondary_sample.blind_code,
                "first_presented_blind_code": first_code,
            }
            assessor_snapshot = {
                "schema_version": "lab-external-validation-assessor-snapshot-v1",
                "assessor_token_sha256": assessor,
                "qualification_receipt_sha256": qualification,
                "session_token_sha256": session,
            }
            provenance_snapshot = {
                "schema_version": "lab-external-validation-provenance-snapshot-v1",
                "provenance_receipt_sha256": provenance,
                "protocol_binding_sha256s": [
                    item["sha256"] for item in cast(list[dict[str, Any]], protocol["bindings"])
                ],
                "requester_scope": requester_scope,
            }
            payload = {
                "schema_version": "lab-external-validation-pairwise-payload-v1",
                "missingness_state": missingness_state,
                "preference_outcome": preference,
                "missing_reason": reason,
            }
            hashes = {
                "protocol_scope_sha256": stable_json_hash(protocol_snapshot),
                "sample_scope_sha256": stable_json_hash(sample_snapshot),
                "condition_scope_sha256": stable_json_hash(condition_snapshot),
                "order_scope_sha256": stable_json_hash(order_snapshot),
                "assessor_scope_sha256": stable_json_hash(assessor_snapshot),
                "provenance_scope_sha256": stable_json_hash(provenance_snapshot),
            }
            canonical_cell = {
                "schema_version": "lab-external-validation-cell-v1",
                "record_kind": "PAIRWISE_PREFERENCE",
                "protocol_scope_sha256": hashes["protocol_scope_sha256"],
                "application_ids": sorted((primary_app.id, secondary_app.id)),
                "assessor_token_sha256": assessor,
                "session_token_sha256": session,
                "repeat_id": repeat,
                "time_seconds": time_text,
                "criterion_id": criterion,
            }
            canonical_cell_sha256 = stable_json_hash(canonical_cell)
            command = {
                "schema_version": "lab-external-validation-command-v1",
                "record_kind": "PAIRWISE_PREFERENCE",
                "requester_scope": requester_scope,
                "canonical_cell_sha256": canonical_cell_sha256,
                "scope_hashes": hashes,
                "order": order_snapshot,
                "payload": payload,
            }
            command_sha256 = stable_json_hash(command)
            record_hash_payload = {
                "schema_version": EXTERNAL_VALIDATION_RECORD_SCHEMA,
                "command_sha256": command_sha256,
                "canonical_cell_sha256": canonical_cell_sha256,
                "scope_hashes": hashes,
                "payload": payload,
                "authority": {key: False for key in _AUTHORITY_KEYS},
                "processing_allowed": False,
            }
            values = {
                "schema_version": EXTERNAL_VALIDATION_RECORD_SCHEMA,
                "record_kind": "PAIRWISE_PREFERENCE",
                "experiment_id": experiment.id,
                "primary_application_id": primary_app.id,
                "secondary_application_id": secondary_app.id,
                "requester_scope": requester_scope,
                "protocol_id": protocol_id,
                "endpoint_id": criterion,
                "repeat_id": repeat,
                "time_seconds_decimal_text": time_text,
                "presentation_sequence_id": sequence,
                "presentation_position": None,
                "missingness_state": missingness_state,
                "value_decimal_text": None,
                "preference_outcome": preference,
                "missing_reason": reason,
                "protocol_snapshot_json": protocol_snapshot,
                "sample_snapshot_json": sample_snapshot,
                "condition_snapshot_json": condition_snapshot,
                "order_snapshot_json": order_snapshot,
                "assessor_snapshot_json": assessor_snapshot,
                "provenance_snapshot_json": provenance_snapshot,
                "payload_json": payload,
                "idempotency_key_sha256": sha256(key.encode("utf-8")).hexdigest(),
                "command_sha256": command_sha256,
                "canonical_cell_sha256": canonical_cell_sha256,
                **hashes,
                "record_sha256": stable_json_hash(record_hash_payload),
                "processing_allowed": False,
                **{key: False for key in _AUTHORITY_KEYS},
            }
            return await self._persist_external_validation_record(values=values)

    async def get_external_validation_record(
        self,
        record_id: str,
    ) -> LabExternalValidationRecord:
        record = await self.repository.get_external_validation_record(
            _text(record_id, "record_id", maximum=64)
        )
        if record is None:
            raise ExternalValidationNotFoundError(
                "EXTERNAL_VALIDATION_RECORD_NOT_FOUND",
                f"External-validation record not found: {record_id}.",
            )
        return record


def external_validation_record_response(
    record: LabExternalValidationRecord,
    *,
    reused: bool | None,
) -> dict[str, Any]:
    """Return the narrow public receipt without assessor or protocol bytes."""

    return {
        "schema_version": "lab-external-validation-record-response-v1",
        "id": record.id,
        "write_state": (
            "READ" if reused is None else "REPLAYED" if reused else "CREATED"
        ),
        "record_kind": record.record_kind,
        "experiment_id": record.experiment_id,
        "primary_application_id": record.primary_application_id,
        "secondary_application_id": record.secondary_application_id,
        "protocol_id": record.protocol_id,
        "endpoint_id": record.endpoint_id,
        "repeat_id": record.repeat_id,
        "time_seconds": record.time_seconds_decimal_text,
        "presentation_sequence_id": record.presentation_sequence_id,
        "presentation_position": record.presentation_position,
        "missingness_state": record.missingness_state,
        "value": record.value_decimal_text,
        "preference_outcome": record.preference_outcome,
        "missing_reason": record.missing_reason,
        "command_sha256": record.command_sha256,
        "canonical_cell_sha256": record.canonical_cell_sha256,
        "protocol_scope_sha256": record.protocol_scope_sha256,
        "sample_scope_sha256": record.sample_scope_sha256,
        "condition_scope_sha256": record.condition_scope_sha256,
        "order_scope_sha256": record.order_scope_sha256,
        "assessor_scope_sha256": record.assessor_scope_sha256,
        "provenance_scope_sha256": record.provenance_scope_sha256,
        "record_sha256": record.record_sha256,
        "created_at": record.created_at,
        "processing_allowed": False,
        "scientific_authority": False,
        "sensory_authority": False,
        "model_calibration_authority": False,
        "release_authority": False,
        "safety_authority": False,
        "compounding_authority": False,
        "evidence_admission_authorized": False,
    }


__all__ = [
    "EXTERNAL_VALIDATION_PROTOCOL_SCHEMA",
    "EXTERNAL_VALIDATION_RECORD_SCHEMA",
    "ExternalValidationConflictError",
    "ExternalValidationError",
    "ExternalValidationNotFoundError",
    "LabExternalValidationServiceMixin",
    "external_validation_record_response",
]
