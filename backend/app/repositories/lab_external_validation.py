"""Persistence-only queries for strict external-validation intake records."""

from __future__ import annotations

from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lab_external_validation import LabExternalValidationRecord


class LabExternalValidationRepositoryMixin:
    session: AsyncSession

    async def get_external_validation_record(
        self,
        record_id: str,
    ) -> LabExternalValidationRecord | None:
        return cast(
            LabExternalValidationRecord | None,
            await self.session.get(LabExternalValidationRecord, record_id),
        )

    async def external_validation_record_for_idempotency(
        self,
        *,
        requester_scope: str,
        idempotency_key_sha256: str,
    ) -> LabExternalValidationRecord | None:
        return cast(
            LabExternalValidationRecord | None,
            await self.session.scalar(
                select(LabExternalValidationRecord)
                .where(
                    LabExternalValidationRecord.requester_scope == requester_scope,
                    LabExternalValidationRecord.idempotency_key_sha256
                    == idempotency_key_sha256,
                )
                .limit(1)
            ),
        )

    async def external_validation_record_for_cell(
        self,
        canonical_cell_sha256: str,
    ) -> LabExternalValidationRecord | None:
        return cast(
            LabExternalValidationRecord | None,
            await self.session.scalar(
                select(LabExternalValidationRecord)
                .where(
                    LabExternalValidationRecord.canonical_cell_sha256
                    == canonical_cell_sha256
                )
                .limit(1)
            ),
        )


__all__ = ["LabExternalValidationRepositoryMixin"]
