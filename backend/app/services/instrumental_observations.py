"""Immutable intake for fully scoped instrumental observation timepoints."""

from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from hashlib import sha256
from typing import TYPE_CHECKING, Any

from engine.calibration.hashing import stable_json_hash
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lab_instrumental_observations import LabInstrumentalObservation
from app.schemas.instrumental_observations import InstrumentalObservationIntakeRequest

if TYPE_CHECKING:
    from app.repositories.lab import LabRepository


class InstrumentalObservationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


class InstrumentalObservationConflictError(InstrumentalObservationError):
    pass


class InstrumentalObservationNotFoundError(InstrumentalObservationError):
    pass


class LabInstrumentalObservationServiceMixin:
    """Commands sharing the canonical LabService transaction owner."""

    if TYPE_CHECKING:
        session: AsyncSession
        repository: "LabRepository"

        def _transaction(self) -> AbstractAsyncContextManager[None]: ...

    async def record_instrumental_observation(
        self, **request_values: Any
    ) -> tuple[LabInstrumentalObservation, bool]:
        try:
            request = InstrumentalObservationIntakeRequest.model_validate(request_values)
        except ValueError as exc:
            raise InstrumentalObservationError(
                "INVALID_INSTRUMENTAL_OBSERVATION",
                "The instrumental observation request is invalid.",
            ) from exc
        payload = request.model_dump(mode="json")
        requester = payload.pop("requester")
        idempotency_key = payload.pop("idempotency_key")
        schema_version = payload.pop("schema_version")
        command = {
            "schema_version": "lab-instrumental-observation-command-v1",
            "requester_scope": requester,
            "observation": payload,
        }
        command_sha256 = stable_json_hash(command)
        idempotency_key_sha256 = sha256(idempotency_key.encode("utf-8")).hexdigest()
        record_payload = {
            "schema_version": "lab-instrumental-observation-record-v1",
            "command_sha256": command_sha256,
            "review_state": "UNREVIEWED",
            "processing_allowed": False,
            "authority": {
                "scientific_authority": False,
                "model_calibration_authority": False,
                "release_authority": False,
                "safety_authority": False,
                "compounding_authority": False,
                "evidence_admission_authorized": False,
            },
        }
        values = {
            "schema_version": "lab-instrumental-observation-record-v1",
            "observation_id": payload["observation_id"],
            "requester_scope": requester,
            "formula_sha256": payload["formula_sha256"],
            "inventory_sha256": payload["inventory_sha256"],
            "stock_lot_bundle_sha256": payload["stock_lot_bundle_sha256"],
            "preparation_receipt_sha256": payload["preparation_receipt_sha256"],
            "release_scenario_sha256": payload["release_scenario_sha256"],
            "deposit_decimal_text": payload["deposit_decimal"],
            "deposit_unit": payload["deposit_unit"],
            "matrix_id": payload["matrix_id"],
            "substrate": payload["substrate"],
            "temperature_k_decimal_text": payload["temperature_k_decimal"],
            "relative_humidity_decimal_text": payload["relative_humidity_decimal"],
            "airflow_m_s_decimal_text": payload["airflow_m_s_decimal"],
            "surface_area_m2_decimal_text": payload["surface_area_m2_decimal"],
            "delivery_geometry_id": payload["delivery_geometry_id"],
            "sampling_method_id": payload["sampling_method_id"],
            "instrument_id": payload["instrument_id"],
            "calibration_receipt_sha256": payload["calibration_receipt_sha256"],
            "blank_receipt_sha256": payload["blank_receipt_sha256"],
            "time_seconds_decimal_text": payload["time_seconds_decimal"],
            "replicate_id": payload["replicate_id"],
            "session_id": payload["session_id"],
            "raw_data_sha256": payload["raw_data_sha256"],
            "processed_result_sha256": payload["processed_result_sha256"],
            "protocol_deviations_json": payload["protocol_deviations"],
            "review_state": "UNREVIEWED",
            "payload_json": {
                "request_schema_version": schema_version,
                **payload,
            },
            "idempotency_key_sha256": idempotency_key_sha256,
            "command_sha256": command_sha256,
            "record_sha256": stable_json_hash(record_payload),
            "review_note": None,
            "processing_allowed": False,
            "scientific_authority": False,
            "model_calibration_authority": False,
            "release_authority": False,
            "safety_authority": False,
            "compounding_authority": False,
            "evidence_admission_authorized": False,
        }
        async with self._transaction():
            existing = await self.repository.instrumental_observation_for_idempotency(
                requester_scope=requester,
                idempotency_key_sha256=idempotency_key_sha256,
            )
            if existing is not None:
                if existing.command_sha256 != command_sha256:
                    raise InstrumentalObservationConflictError(
                        "INSTRUMENTAL_OBSERVATION_IDEMPOTENCY_CONFLICT",
                        "The idempotency key was reused for different observation bytes.",
                    )
                return existing, True
            identity = await self.repository.instrumental_observation_for_identity(
                payload["observation_id"]
            )
            if identity is not None:
                if identity.command_sha256 != command_sha256:
                    raise InstrumentalObservationConflictError(
                        "INSTRUMENTAL_OBSERVATION_IDENTITY_CONFLICT",
                        "The observation identity already has different immutable content.",
                    )
                return identity, True
            record = LabInstrumentalObservation(**values)
            try:
                await self.repository.add(record)
            except IntegrityError as exc:
                raise InstrumentalObservationConflictError(
                    "INSTRUMENTAL_OBSERVATION_CONCURRENT_CONFLICT",
                    "A concurrent writer claimed this observation identity.",
                ) from exc
            return record, False

    async def require_instrumental_observation(
        self, record_id: str
    ) -> LabInstrumentalObservation:
        record = await self.repository.get_instrumental_observation(record_id)
        if record is None:
            raise InstrumentalObservationNotFoundError(
                "INSTRUMENTAL_OBSERVATION_NOT_FOUND",
                f"Instrumental observation not found: {record_id}.",
            )
        return record


def instrumental_observation_response(
    record: LabInstrumentalObservation,
    *,
    reused: bool | None,
) -> dict[str, Any]:
    write_state = "READ" if reused is None else ("REPLAYED" if reused else "CREATED")
    deviations = list(record.protocol_deviations_json)
    return {
        "schema_version": "lab-instrumental-observation-response-v1",
        "id": record.id,
        "write_state": write_state,
        "observation_id": record.observation_id,
        "formula_sha256": record.formula_sha256,
        "inventory_sha256": record.inventory_sha256,
        "release_scenario_sha256": record.release_scenario_sha256,
        "substrate": record.substrate,
        "time_seconds_decimal": record.time_seconds_decimal_text,
        "replicate_id": record.replicate_id,
        "session_id": record.session_id,
        "raw_data_sha256": record.raw_data_sha256,
        "processed_result_sha256": record.processed_result_sha256,
        "protocol_deviations": deviations,
        "deviation_state": "DECLARED" if deviations else "NONE_DECLARED",
        "review_state": record.review_state,
        "command_sha256": record.command_sha256,
        "record_sha256": record.record_sha256,
        "created_at": record.created_at,
        "processing_allowed": False,
        "scientific_authority": False,
        "model_calibration_authority": False,
        "release_authority": False,
        "safety_authority": False,
        "compounding_authority": False,
        "evidence_admission_authorized": False,
    }


__all__ = [
    "InstrumentalObservationConflictError",
    "InstrumentalObservationError",
    "InstrumentalObservationNotFoundError",
    "LabInstrumentalObservationServiceMixin",
    "instrumental_observation_response",
]
