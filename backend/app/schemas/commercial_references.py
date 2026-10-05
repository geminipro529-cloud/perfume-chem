"""Strict API contracts for immutable commercial-reference sample links."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_SHA256 = r"^[0-9a-f]{64}$"


class CommercialReferenceSampleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: Literal["commercial-reference-sample-request-v1"]
    requester: str = Field(min_length=1, max_length=255)
    idempotency_key: str = Field(min_length=1, max_length=255)
    sample_id: str = Field(min_length=1, max_length=255)
    product_id: str = Field(min_length=1, max_length=255)
    concentration: str = Field(min_length=1, max_length=255)
    edition: str = Field(min_length=1, max_length=255)
    sample_identifier: str = Field(min_length=1, max_length=255)
    registry_sha256: str = Field(pattern=_SHA256)
    panel_id: str | None = Field(default=None, max_length=255)
    panel_sha256: str | None = Field(default=None, pattern=_SHA256)
    purchase_source: str | None = Field(default=None, max_length=500)
    batch_code: str | None = Field(default=None, max_length=255)
    acquisition_date: date | None = None
    authenticity_documentation_state: Literal[
        "NOT_PROVIDED_PERSONAL_MODE",
        "USER_ASSERTED",
        "DOCUMENTED_NOT_ADJUDICATED",
    ] = "NOT_PROVIDED_PERSONAL_MODE"

    @field_validator(
        "requester",
        "idempotency_key",
        "sample_id",
        "product_id",
        "concentration",
        "edition",
        "sample_identifier",
        "panel_id",
        "purchase_source",
        "batch_code",
    )
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        if not text:
            raise ValueError("optional text must be omitted rather than blank")
        return text

    @model_validator(mode="after")
    def panel_binding_is_complete(self) -> Self:
        if (self.panel_id is None) != (self.panel_sha256 is None):
            raise ValueError("panel_id and panel_sha256 must be supplied together")
        return self


class CommercialReferenceSampleResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["commercial-reference-sample-response-v1"]
    id: str
    write_state: Literal["CREATED", "REPLAYED", "READ"]
    sample_id: str
    product_id: str
    concentration: str
    edition: str
    sample_identifier: str
    registry_sha256: str
    panel_id: str | None
    panel_sha256: str | None
    purchase_source: str | None
    batch_code: str | None
    acquisition_date: date | None
    authenticity_documentation_state: str
    photograph_required: Literal[False] = False
    command_sha256: str
    record_sha256: str
    created_at: datetime
    release_authority: Literal[False] = False
    safety_authority: Literal[False] = False
    compounding_authority: Literal[False] = False
    evidence_admission_authorized: Literal[False] = False


__all__ = [
    "CommercialReferenceSampleCreate",
    "CommercialReferenceSampleResponse",
]
