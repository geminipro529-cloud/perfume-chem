"""Persistence-only queries for B1-bound external-study records."""

from __future__ import annotations

from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lab_external_studies import (
    LabExternalCondition,
    LabExternalExperimentalUnit,
    LabExternalIdentityCrosswalk,
    LabExternalObservation,
    LabExternalStimulusComponent,
    LabExternalStimulusVersion,
    LabExternalStudyConflict,
    LabExternalStudyVersion,
)


class LabExternalStudyRepositoryMixin:
    session: AsyncSession

    async def get_external_study_version(
        self,
        version_id: str,
    ) -> LabExternalStudyVersion | None:
        return cast(
            LabExternalStudyVersion | None,
            await self.session.get(LabExternalStudyVersion, version_id),
        )

    async def latest_external_study_version(
        self,
        study_id: str,
    ) -> LabExternalStudyVersion | None:
        return cast(
            LabExternalStudyVersion | None,
            await self.session.scalar(
                select(LabExternalStudyVersion)
                .where(LabExternalStudyVersion.study_id == study_id)
                .order_by(
                    LabExternalStudyVersion.version_number.desc(),
                    LabExternalStudyVersion.id,
                )
                .limit(1)
            ),
        )

    async def external_study_by_hash(
        self,
        record_sha256: str,
    ) -> LabExternalStudyVersion | None:
        return cast(
            LabExternalStudyVersion | None,
            await self.session.scalar(
                select(LabExternalStudyVersion)
                .where(LabExternalStudyVersion.record_sha256 == record_sha256)
                .limit(1)
            ),
        )

    async def external_study_stimuli(
        self,
        study_version_id: str,
    ) -> list[LabExternalStimulusVersion]:
        result = await self.session.scalars(
            select(LabExternalStimulusVersion)
            .where(
                LabExternalStimulusVersion.study_version_id
                == study_version_id
            )
            .order_by(
                LabExternalStimulusVersion.stimulus_key,
                LabExternalStimulusVersion.id,
            )
        )
        return list(result)

    async def external_study_components(
        self,
        study_version_id: str,
    ) -> list[LabExternalStimulusComponent]:
        result = await self.session.scalars(
            select(LabExternalStimulusComponent)
            .join(
                LabExternalStimulusVersion,
                LabExternalStimulusVersion.id
                == LabExternalStimulusComponent.stimulus_version_id,
            )
            .where(
                LabExternalStimulusVersion.study_version_id
                == study_version_id
            )
            .order_by(
                LabExternalStimulusComponent.stimulus_version_id,
                LabExternalStimulusComponent.position,
                LabExternalStimulusComponent.id,
            )
        )
        return list(result)

    async def external_study_conditions(
        self,
        study_version_id: str,
    ) -> list[LabExternalCondition]:
        result = await self.session.scalars(
            select(LabExternalCondition)
            .where(LabExternalCondition.study_version_id == study_version_id)
            .order_by(
                LabExternalCondition.condition_key,
                LabExternalCondition.id,
            )
        )
        return list(result)

    async def external_study_units(
        self,
        study_version_id: str,
    ) -> list[LabExternalExperimentalUnit]:
        result = await self.session.scalars(
            select(LabExternalExperimentalUnit)
            .where(
                LabExternalExperimentalUnit.study_version_id
                == study_version_id
            )
            .order_by(
                LabExternalExperimentalUnit.unit_key,
                LabExternalExperimentalUnit.id,
            )
        )
        return list(result)

    async def external_study_observations(
        self,
        study_version_id: str,
    ) -> list[LabExternalObservation]:
        result = await self.session.scalars(
            select(LabExternalObservation)
            .where(
                LabExternalObservation.study_version_id == study_version_id
            )
            .order_by(
                LabExternalObservation.trial_key,
                LabExternalObservation.session_key,
                LabExternalObservation.repeat_index,
                LabExternalObservation.replicate_index,
                LabExternalObservation.endpoint_key,
                LabExternalObservation.observation_key,
                LabExternalObservation.id,
            )
        )
        return list(result)

    async def external_study_crosswalks(
        self,
        study_version_id: str,
    ) -> list[LabExternalIdentityCrosswalk]:
        result = await self.session.scalars(
            select(LabExternalIdentityCrosswalk)
            .join(
                LabExternalStimulusComponent,
                LabExternalStimulusComponent.id
                == LabExternalIdentityCrosswalk.component_id,
            )
            .join(
                LabExternalStimulusVersion,
                LabExternalStimulusVersion.id
                == LabExternalStimulusComponent.stimulus_version_id,
            )
            .where(
                LabExternalStimulusVersion.study_version_id
                == study_version_id
            )
            .order_by(
                LabExternalIdentityCrosswalk.component_id,
                LabExternalIdentityCrosswalk.id,
            )
        )
        return list(result)

    async def external_study_conflicts(
        self,
        study_version_id: str,
    ) -> list[LabExternalStudyConflict]:
        result = await self.session.scalars(
            select(LabExternalStudyConflict)
            .where(
                LabExternalStudyConflict.study_version_id == study_version_id
            )
            .order_by(
                LabExternalStudyConflict.conflict_key,
                LabExternalStudyConflict.id,
            )
        )
        return list(result)


__all__ = ["LabExternalStudyRepositoryMixin"]
