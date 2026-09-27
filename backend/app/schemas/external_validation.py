"""Strict public schemas for authority-safe external-validation intake."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_SHA256_PATTERN = r"^[0-9a-f]{64}$"


class _ExternalValidationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requester: str = Field(min_length=1, max_length=255)
    idempotency_key: str = Field(min_length=1, max_length=255)
    assessor_token_sha256: str = Field(pattern=_SHA256_PATTERN)
    qualification_receipt_sha256: str = Field(pattern=_SHA256_PATTERN)
    session_token_sha256: str = Field(pattern=_SHA256_PATTERN)
    provenance_receipt_sha256: str = Field(pattern=_SHA256_PATTERN)
    repeat_id: str = Field(min_length=1, max_length=255)
    time_seconds: str = Field(min_length=1, max_length=128)
    presentation_sequence_id: str = Field(min_length=1, max_length=255)
    missingness_state: Literal["OBSERVED", "MISSING", "NOT_APPLICABLE"]
    missing_reason: str | None = Field(default=None, min_length=1, max_length=500)

    @field_validator(
        "requester",
        "idempotency_key",
        "repeat_id",
        "presentation_sequence_id",
    )
    @classmethod
    def strip_nonempty(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("must not be blank")
        return normalized

    @field_validator("missing_reason")
    @classmethod
    def strip_optional_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("must not be blank")
        return normalized


class TemporalObservationIntakeRequest(_ExternalValidationRequest):
    schema_version: Literal["lab-external-validation-temporal-request-v1"]
    application_id: str = Field(min_length=1, max_length=64)
    endpoint_id: str = Field(min_length=1, max_length=255)
    presentation_position: int = Field(ge=1)
    value: str | None = Field(default=None, min_length=1, max_length=128)

    @field_validator("application_id", "endpoint_id")
    @classmethod
    def strip_temporal_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("must not be blank")
        return normalized

    @model_validator(mode="after")
    def validate_value_shape(self) -> Self:
        if self.missingness_state == "OBSERVED":
            if self.value is None or self.missing_reason is not None:
                raise ValueError(
                    "OBSERVED temporal records require value and no missing_reason"
                )
        elif self.value is not None or self.missing_reason is None:
            raise ValueError(
                "non-observed temporal records require missing_reason and no value"
            )
        return self


class PairwisePreferenceIntakeRequest(_ExternalValidationRequest):
    schema_version: Literal["lab-external-validation-pairwise-request-v1"]
    primary_application_id: str = Field(min_length=1, max_length=64)
    secondary_application_id: str = Field(min_length=1, max_length=64)
    criterion_id: str = Field(min_length=1, max_length=255)
    first_presented_application_id: str = Field(min_length=1, max_length=64)
    preference_outcome: Literal["PRIMARY", "SECONDARY", "TIE"] | None = None

    @field_validator(
        "primary_application_id",
        "secondary_application_id",
        "criterion_id",
        "first_presented_application_id",
    )
    @classmethod
    def strip_pairwise_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("must not be blank")
        return normalized

    @model_validator(mode="after")
    def validate_pairwise_shape(self) -> Self:
        if self.primary_application_id == self.secondary_application_id:
            raise ValueError("pairwise intake requires two different applications")
        if self.first_presented_application_id not in {
            self.primary_application_id,
            self.secondary_application_id,
        }:
            raise ValueError(
                "first_presented_application_id must identify one compared application"
            )
        if self.missingness_state == "OBSERVED":
            if self.preference_outcome is None or self.missing_reason is not None:
                raise ValueError(
                    "OBSERVED pairwise records require preference_outcome and no missing_reason"
                )
        elif self.preference_outcome is not None or self.missing_reason is None:
            raise ValueError(
                "non-observed pairwise records require missing_reason and no preference_outcome"
            )
        return self


class ExternalValidationRecordResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["lab-external-validation-record-response-v1"]
    id: str
    write_state: Literal["CREATED", "REPLAYED", "READ"]
    record_kind: Literal["TEMPORAL_OBSERVATION", "PAIRWISE_PREFERENCE"]
    experiment_id: str
    primary_application_id: str
    secondary_application_id: str | None
    protocol_id: str
    endpoint_id: str
    repeat_id: str
    time_seconds: str
    presentation_sequence_id: str
    presentation_position: int | None
    missingness_state: Literal["OBSERVED", "MISSING", "NOT_APPLICABLE"]
    value: str | None
    preference_outcome: Literal["PRIMARY", "SECONDARY", "TIE"] | None
    missing_reason: str | None
    command_sha256: str
    canonical_cell_sha256: str
    protocol_scope_sha256: str
    sample_scope_sha256: str
    condition_scope_sha256: str
    order_scope_sha256: str
    assessor_scope_sha256: str
    provenance_scope_sha256: str
    record_sha256: str
    created_at: datetime
    processing_allowed: Literal[False] = False
    scientific_authority: Literal[False] = False
    sensory_authority: Literal[False] = False
    model_calibration_authority: Literal[False] = False
    release_authority: Literal[False] = False
    safety_authority: Literal[False] = False
    compounding_authority: Literal[False] = False
    evidence_admission_authorized: Literal[False] = False


__all__ = [
    "ExternalValidationRecordResponse",
    "PairwisePreferenceIntakeRequest",
    "TemporalObservationIntakeRequest",
]
