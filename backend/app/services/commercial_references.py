"""Server-owned validation and persistence for commercial-reference samples."""

from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from hashlib import sha256
from typing import TYPE_CHECKING, Any

from engine.calibration.hashing import stable_json_hash
from engine.research.commercial_references import load_commercial_reference_registry
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lab_commercial_references import LabCommercialReferenceSample
from app.schemas.commercial_references import CommercialReferenceSampleCreate

if TYPE_CHECKING:
    from app.repositories.lab import LabRepository


class CommercialReferenceError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


class CommercialReferenceConflictError(CommercialReferenceError):
    pass


class CommercialReferenceNotFoundError(CommercialReferenceError):
    pass


class LabCommercialReferenceServiceMixin:
    if TYPE_CHECKING:
        session: AsyncSession
        repository: "LabRepository"

        def _transaction(self) -> AbstractAsyncContextManager[None]: ...

    async def link_commercial_reference_sample(
        self, **request_values: Any
    ) -> tuple[LabCommercialReferenceSample, bool]:
        try:
            request = CommercialReferenceSampleCreate.model_validate(request_values)
        except ValueError as exc:
            raise CommercialReferenceError(
                "INVALID_COMMERCIAL_REFERENCE_SAMPLE",
                "The commercial-reference sample request is invalid.",
            ) from exc
        payload = request.model_dump(mode="json")
        acquisition_date = request.acquisition_date
        requester = payload.pop("requester")
        idempotency_key = payload.pop("idempotency_key")
        request_schema = payload.pop("schema_version")
        registry = load_commercial_reference_registry()
        if payload["registry_sha256"] != registry.registry_sha256:
            raise CommercialReferenceConflictError(
                "COMMERCIAL_REFERENCE_REGISTRY_HASH_MISMATCH",
                "The sample link does not bind the current reviewed registry bytes.",
            )
        product = registry.products.get(payload["product_id"])
        if product is None:
            raise CommercialReferenceNotFoundError(
                "COMMERCIAL_REFERENCE_PRODUCT_NOT_FOUND",
                f"Commercial product not found: {payload['product_id']}.",
            )
        if product.concentration != payload["concentration"] or product.edition != payload["edition"]:
            raise CommercialReferenceConflictError(
                "COMMERCIAL_REFERENCE_PRODUCT_VERSION_MISMATCH",
                "Concentration and edition must exactly match the governed product identity.",
            )
        if payload["panel_id"] is not None:
            panel = registry.panels.get(payload["panel_id"])
            if panel is None:
                raise CommercialReferenceNotFoundError(
                    "COMMERCIAL_REFERENCE_PANEL_NOT_FOUND",
                    f"Commercial panel not found: {payload['panel_id']}.",
                )
            if panel.sha256 != payload["panel_sha256"]:
                raise CommercialReferenceConflictError(
                    "COMMERCIAL_REFERENCE_PANEL_HASH_MISMATCH",
                    "The supplied panel hash does not match the governed panel.",
                )
            member_ids = {
                row["product_id"] for row in (*panel.active_members, *panel.reserve_members)
            }
            if product.product_id not in member_ids:
                raise CommercialReferenceConflictError(
                    "COMMERCIAL_REFERENCE_PRODUCT_NOT_IN_PANEL",
                    "The exact commercial product is not a member of the bound panel.",
                )
        if await self.repository.get_sample(payload["sample_id"]) is None:
            raise CommercialReferenceNotFoundError(
                "LAB_SAMPLE_NOT_FOUND",
                f"Lab sample not found: {payload['sample_id']}.",
            )

        command = {
            "schema_version": "commercial-reference-sample-command-v1",
            "requester_scope": requester,
            "sample": payload,
        }
        command_sha256 = stable_json_hash(command)
        idempotency_key_sha256 = sha256(idempotency_key.encode("utf-8")).hexdigest()
        record_payload = {
            "schema_version": "commercial-reference-sample-record-v1",
            "command_sha256": command_sha256,
            "authority": {
                "release_authority": False,
                "safety_authority": False,
                "compounding_authority": False,
                "evidence_admission_authorized": False,
            },
        }
        values = {
            "schema_version": "commercial-reference-sample-record-v1",
            "sample_id": payload["sample_id"],
            "requester_scope": requester,
            "product_id": payload["product_id"],
            "concentration": payload["concentration"],
            "edition": payload["edition"],
            "sample_identifier": payload["sample_identifier"],
            "registry_sha256": payload["registry_sha256"],
            "panel_id": payload["panel_id"],
            "panel_sha256": payload["panel_sha256"],
            "purchase_source": payload["purchase_source"],
            "batch_code": payload["batch_code"],
            "acquisition_date": acquisition_date,
            "authenticity_documentation_state": payload[
                "authenticity_documentation_state"
            ],
            "payload_json": {
                "request_schema_version": request_schema,
                **payload,
            },
            "idempotency_key_sha256": idempotency_key_sha256,
            "command_sha256": command_sha256,
            "record_sha256": stable_json_hash(record_payload),
            "release_authority": False,
            "safety_authority": False,
            "compounding_authority": False,
            "evidence_admission_authorized": False,
        }
        async with self._transaction():
            existing = await self.repository.commercial_reference_for_idempotency(
                requester_scope=requester,
                idempotency_key_sha256=idempotency_key_sha256,
            )
            if existing is not None:
                if existing.command_sha256 != command_sha256:
                    raise CommercialReferenceConflictError(
                        "COMMERCIAL_REFERENCE_IDEMPOTENCY_CONFLICT",
                        "The idempotency key was reused for different sample-link bytes.",
                    )
                return existing, True
            sample_link = await self.repository.commercial_reference_for_sample(
                payload["sample_id"]
            )
            if sample_link is not None:
                if sample_link.command_sha256 != command_sha256:
                    raise CommercialReferenceConflictError(
                        "COMMERCIAL_REFERENCE_SAMPLE_CONFLICT",
                        "The lab sample already has a different immutable commercial identity.",
                    )
                return sample_link, True
            record = LabCommercialReferenceSample(**values)
            try:
                await self.repository.add(record)
            except IntegrityError as exc:
                raise CommercialReferenceConflictError(
                    "COMMERCIAL_REFERENCE_CONCURRENT_CONFLICT",
                    "A concurrent writer claimed this commercial-reference link.",
                ) from exc
            return record, False

    async def require_commercial_reference_sample(
        self, record_id: str
    ) -> LabCommercialReferenceSample:
        record = await self.repository.get_commercial_reference_sample(record_id)
        if record is None:
            raise CommercialReferenceNotFoundError(
                "COMMERCIAL_REFERENCE_SAMPLE_NOT_FOUND",
                f"Commercial-reference sample not found: {record_id}.",
            )
        return record


def commercial_reference_sample_response(
    record: LabCommercialReferenceSample,
    *,
    reused: bool | None,
) -> dict[str, Any]:
    return {
        "schema_version": "commercial-reference-sample-response-v1",
        "id": record.id,
        "write_state": "READ" if reused is None else ("REPLAYED" if reused else "CREATED"),
        "sample_id": record.sample_id,
        "product_id": record.product_id,
        "concentration": record.concentration,
        "edition": record.edition,
        "sample_identifier": record.sample_identifier,
        "registry_sha256": record.registry_sha256,
        "panel_id": record.panel_id,
        "panel_sha256": record.panel_sha256,
        "purchase_source": record.purchase_source,
        "batch_code": record.batch_code,
        "acquisition_date": record.acquisition_date,
        "authenticity_documentation_state": record.authenticity_documentation_state,
        "photograph_required": False,
        "command_sha256": record.command_sha256,
        "record_sha256": record.record_sha256,
        "created_at": record.created_at,
        "release_authority": False,
        "safety_authority": False,
        "compounding_authority": False,
        "evidence_admission_authorized": False,
    }


__all__ = [
    "CommercialReferenceConflictError",
    "CommercialReferenceError",
    "CommercialReferenceNotFoundError",
    "LabCommercialReferenceServiceMixin",
    "commercial_reference_sample_response",
]
