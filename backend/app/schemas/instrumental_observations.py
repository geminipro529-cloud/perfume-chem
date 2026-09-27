"""Strict public contracts for non-authoritative instrumental observations."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_SHA256_PATTERN = r"^[0-9a-f]{64}$"


def _canonical_decimal(value: str, *, positive: bool = False) -> str:
    try:
        parsed = Decimal(value)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("must be canonical finite decimal text") from exc
    if not parsed.is_finite() or parsed < 0 or (positive and parsed <= 0):
        raise ValueError("must be canonical finite non-negative decimal text")
    rendered = "0" if parsed == 0 else format(parsed, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    if value != rendered:
        raise ValueError("must be canonical plain-decimal text")
    return rendered


class InstrumentalObservationIntakeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: Literal["lab-instrumental-observation-request-v1"]
    requester: str = Field(min_length=1, max_length=255)
    idempotency_key: str = Field(min_length=1, max_length=255)
    observation_id: str = Field(min_length=1, max_length=255)
    formula_sha256: str = Field(pattern=_SHA256_PATTERN)
    inventory_sha256: str = Field(pattern=_SHA256_PATTERN)
    stock_lot_bundle_sha256: str = Field(pattern=_SHA256_PATTERN)
    preparation_receipt_sha256: str = Field(pattern=_SHA256_PATTERN)
    release_scenario_sha256: str = Field(pattern=_SHA256_PATTERN)
    deposit_decimal: str = Field(min_length=1, max_length=128)
    deposit_unit: Literal["mg", "g", "uL", "mL"]
    matrix_id: str = Field(min_length=1, max_length=255)
    substrate: Literal["GLASS", "BLOTTER", "SKIN_SURROGATE", "SKIN"]
    temperature_k_decimal: str = Field(min_length=1, max_length=128)
    relative_humidity_decimal: str = Field(min_length=1, max_length=128)
    airflow_m_s_decimal: str = Field(min_length=1, max_length=128)
    surface_area_m2_decimal: str = Field(min_length=1, max_length=128)
    delivery_geometry_id: str = Field(min_length=1, max_length=255)
    sampling_method_id: str = Field(min_length=1, max_length=255)
    instrument_id: str = Field(min_length=1, max_length=255)
    calibration_receipt_sha256: str = Field(pattern=_SHA256_PATTERN)
    blank_receipt_sha256: str = Field(pattern=_SHA256_PATTERN)
    time_seconds_decimal: str = Field(min_length=1, max_length=128)
    replicate_id: str = Field(min_length=1, max_length=255)
    session_id: str = Field(min_length=1, max_length=255)
    raw_data_sha256: str = Field(pattern=_SHA256_PATTERN)
    processed_result_sha256: str = Field(pattern=_SHA256_PATTERN)
    protocol_deviations: list[str] = Field(default_factory=list, max_length=100)

    @field_validator(
        "requester",
        "idempotency_key",
        "observation_id",
        "matrix_id",
        "delivery_geometry_id",
        "sampling_method_id",
        "instrument_id",
        "replicate_id",
        "session_id",
    )
    @classmethod
    def strip_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("must not be blank")
        return normalized

    @field_validator("deposit_decimal", "temperature_k_decimal", "surface_area_m2_decimal")
    @classmethod
    def positive_decimal(cls, value: str) -> str:
        return _canonical_decimal(value, positive=True)

    @field_validator("relative_humidity_decimal", "airflow_m_s_decimal", "time_seconds_decimal")
    @classmethod
    def nonnegative_decimal(cls, value: str) -> str:
        return _canonical_decimal(value)

    @field_validator("protocol_deviations")
    @classmethod
    def normalize_deviations(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if any(not value or len(value) > 500 for value in normalized):
            raise ValueError("protocol deviations must be nonblank and at most 500 characters")
        if len({value.casefold() for value in normalized}) != len(normalized):
            raise ValueError("protocol deviations must be unique")
        return normalized

    @model_validator(mode="after")
    def validate_humidity(self) -> Self:
        if Decimal(self.relative_humidity_decimal) > 1:
            raise ValueError("relative_humidity_decimal must be from zero to one")
        return self


class InstrumentalObservationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["lab-instrumental-observation-response-v1"]
    id: str
    write_state: Literal["CREATED", "REPLAYED", "READ"]
    observation_id: str
    formula_sha256: str
    inventory_sha256: str
    release_scenario_sha256: str
    substrate: Literal["GLASS", "BLOTTER", "SKIN_SURROGATE", "SKIN"]
    time_seconds_decimal: str
    replicate_id: str
    session_id: str
    raw_data_sha256: str
    processed_result_sha256: str
    protocol_deviations: list[str]
    deviation_state: Literal["NONE_DECLARED", "DECLARED"]
    review_state: Literal["UNREVIEWED"]
    command_sha256: str
    record_sha256: str
    created_at: datetime
    processing_allowed: Literal[False] = False
    scientific_authority: Literal[False] = False
    model_calibration_authority: Literal[False] = False
    release_authority: Literal[False] = False
    safety_authority: Literal[False] = False
    compounding_authority: Literal[False] = False
    evidence_admission_authorized: Literal[False] = False


__all__ = [
    "InstrumentalObservationIntakeRequest",
    "InstrumentalObservationResponse",
]
