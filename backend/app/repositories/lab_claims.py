"""Persistence-only queries for B7 claim authority."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lab_claims import (
    LabClaimAuthoritySupportLink,
    LabClaimAuthorityVersion,
)


class LabClaimAuthorityRepositoryMixin:
    session: AsyncSession

    async def get_claim_authority_version(
        self,
        version_id: str,
    ) -> LabClaimAuthorityVersion | None:
        return await self.session.get(LabClaimAuthorityVersion, version_id)

    async def latest_claim_authority_version(
        self,
        authority_id: str,
    ) -> LabClaimAuthorityVersion | None:
        return await self.session.scalar(
            select(LabClaimAuthorityVersion)
            .where(LabClaimAuthorityVersion.authority_id == authority_id)
            .order_by(
                LabClaimAuthorityVersion.version_number.desc(),
                LabClaimAuthorityVersion.id,
            )
            .limit(1)
        )

    async def claim_authority_by_hash(
        self,
        content_sha256: str,
    ) -> LabClaimAuthorityVersion | None:
        return await self.session.scalar(
            select(LabClaimAuthorityVersion).where(
                LabClaimAuthorityVersion.content_sha256 == content_sha256
            )
        )

    async def claim_authority_support_links(
        self,
        authority_version_id: str,
    ) -> list[LabClaimAuthoritySupportLink]:
        result = await self.session.scalars(
            select(LabClaimAuthoritySupportLink)
            .where(
                LabClaimAuthoritySupportLink.claim_authority_version_id
                == authority_version_id
            )
            .order_by(
                LabClaimAuthoritySupportLink.support_kind,
                LabClaimAuthoritySupportLink.role,
                LabClaimAuthoritySupportLink.id,
            )
        )
        return list(result)


__all__ = ["LabClaimAuthorityRepositoryMixin"]
