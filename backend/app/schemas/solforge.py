"""Closed SolForge contexts nested inside existing laboratory JSON fields."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
Criterion = Literal["TARGET_FIDELITY", "DEPTH", "RICHNESS", "LIKING"]


class _ClosedContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    @field_validator("*", mode="before")
    @classmethod
    def _validate_sha_fields(cls, value, info):
        if info.field_name and info.field_name.endswith("sha256"):
            if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
                raise ValueError(f"{info.field_name} must be a lower-case SHA-256 digest")
        return value


class SolForgeProtocolContextV1(_ClosedContext):
    schema_version: Literal["solforge_protocol_context_v1"]
    compiled_experiment_sha256: str
    schedule_sha256: str
    arm_ids: tuple[str, ...] = Field(min_length=1)
    criterion_ids: tuple[Criterion, ...] = Field(min_length=1)
    test_only: bool = False

    @field_validator("arm_ids", "criterion_ids")
    @classmethod
    def _unique(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("values must be unique")
        return value


class SolForgeObservationContextV1(_ClosedContext):
    schema_version: Literal["solforge_observation_context_v1"]
    compiled_experiment_sha256: str
    schedule_sha256: str
    sample_id: str = Field(min_length=1)
    sample_sha256: str
    assessor_id: str = Field(min_length=1)
    repeat_index: int = Field(ge=1)
    timepoint_seconds: float = Field(ge=0)
    endpoint: Criterion
    presentation_sequence: int = Field(ge=1)
    test_only: bool = False


class SolForgeComparisonContextV1(_ClosedContext):
    schema_version: Literal["solforge_comparison_context_v1"]
    compiled_experiment_sha256: str
    schedule_sha256: str
    criterion: Criterion
    assessor_id: str = Field(min_length=1)
    repeat_index: int = Field(ge=1)
    timepoint_seconds: float = Field(ge=0)
    left_sample_id: str = Field(min_length=1)
    right_sample_id: str = Field(min_length=1)
    first_presented_item: str = Field(min_length=1)
    test_only: bool = False

    @model_validator(mode="after")
    def _validate_pair(self):
        if self.left_sample_id == self.right_sample_id:
            raise ValueError("comparison samples must differ")
        if self.first_presented_item not in {
            self.left_sample_id,
            self.right_sample_id,
        }:
            raise ValueError("first_presented_item must be one compared sample")
        return self


__all__ = [
    "SolForgeComparisonContextV1",
    "SolForgeObservationContextV1",
    "SolForgeProtocolContextV1",
]
