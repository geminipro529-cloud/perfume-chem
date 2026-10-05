"""Strict public contracts for durable Checkpoint-2 engine jobs."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

EngineJobType = Literal[
    "FORMULA_DESIGN",
    "FORMULA_ANALYSIS",
    "RELEASE_SIMULATION",
    "RELEASE_GATE",
    "MIXER_SEQUENCE",
    "OPTIMIZER_SEARCH",
    "CANDIDATE_EVALUATION",
    "SHORTLIST_EVALUATION",
    "MODEL_BENCHMARK",
    "PREFERENCE_ANALYSIS",
    "REFERENCE_PANEL_EVALUATION",
    "BATCH_GATE",
]


class EngineJobRequest(BaseModel):
    """Caller intent only; all fingerprints and authority are server-owned."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[
        "lab-engine-job-request-v1",
        "lab-engine-job-request-v2",
    ]
    job_type: EngineJobType
    payload: dict[str, Any]
    idempotency_key: str = Field(min_length=1, max_length=255)
    requester: str = Field(min_length=1, max_length=255)

    @field_validator("idempotency_key", "requester")
    @classmethod
    def strip_nonempty(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("must not be blank")
        return text


class EngineJobCancelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1, max_length=500)
    requester: str = Field(min_length=1, max_length=255)

    @field_validator("reason", "requester")
    @classmethod
    def strip_nonempty(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("must not be blank")
        return text


class EngineJobEventResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sequence: int
    state: str
    lease_owner: str | None
    lease_epoch: int
    lease_expires_at: datetime | None
    attempt: int
    reason: str | None
    timestamp: datetime
    parent_event_sha256: str | None
    event_sha256: str


class EngineJobResultResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    terminal_state: str
    result: dict[str, Any]
    result_sha256: str
    validation_state: str
    diagnostics: dict[str, Any]
    release_authority: Literal[False] = False
    safety_authority: Literal[False] = False
    compounding_authority: Literal[False] = False
    evidence_admission_authorized: Literal[False] = False


class EngineJobResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[
        "lab-engine-job-response-v1",
        "lab-engine-job-response-v2",
    ]
    id: str
    job_type: EngineJobType
    execution_class: str
    requester_scope: str
    state: str
    job_fingerprint_sha256: str
    command_sha256: str
    normalized_payload_sha256: str
    implementation_fingerprint_sha256: str
    reference_bundle_sha256: str
    inventory_fingerprint_sha256: str
    capability_fingerprint_sha256: str
    contract_version: str
    timeout_seconds: int
    created_at: datetime
    event_chain_verified: Literal[True]
    result_hash_verified: bool | None
    events: list[EngineJobEventResponse]
    result: EngineJobResultResponse | None
    release_authority: Literal[False] = False
    safety_authority: Literal[False] = False
    compounding_authority: Literal[False] = False
    evidence_admission_authorized: Literal[False] = False


__all__ = [
    "EngineJobCancelRequest",
    "EngineJobRequest",
    "EngineJobResponse",
]
