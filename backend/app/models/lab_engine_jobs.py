"""Durable append-only Checkpoint-2 engine job records."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.lab import LabRecord, UTCDateTime

ENGINE_JOB_TYPES = (
    "FORMULA_ANALYSIS",
    "RELEASE_SIMULATION",
    "RELEASE_GATE",
    "MIXER_SEQUENCE",
    "OPTIMIZER_SEARCH",
    "CANDIDATE_EVALUATION",
    "SHORTLIST_EVALUATION",
    "MODEL_BENCHMARK",
    "PREFERENCE_ANALYSIS",
    "BATCH_GATE",
)
ENGINE_EXECUTION_CLASSES = (
    "READ_ONLY_DIAGNOSTIC",
    "READ_ONLY_BATCH",
)
ENGINE_JOB_STATES = (
    "QUEUED",
    "LEASED",
    "RUNNING",
    "SUCCEEDED",
    "WITHHELD",
    "FAILED",
    "CANCEL_REQUESTED",
    "CANCELLED",
)
ENGINE_TERMINAL_STATES = ("SUCCEEDED", "WITHHELD", "FAILED", "CANCELLED")


def _quoted(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


_FALSE_AUTHORITY_CHECK = (
    "release_authority = 0 AND safety_authority = 0 "
    "AND compounding_authority = 0 "
    "AND evidence_admission_authorized = 0"
)


class LabEngineJob(LabRecord):
    __tablename__ = "lab_engine_jobs"
    __table_args__ = (
        UniqueConstraint(
            "requester_scope",
            "idempotency_key_sha256",
            name="uq_lab_engine_job_idempotency",
        ),
        UniqueConstraint(
            "job_fingerprint_sha256",
            name="uq_lab_engine_job_fingerprint",
        ),
        CheckConstraint(
            f"job_type IN ({_quoted(ENGINE_JOB_TYPES)})",
            name="ck_lab_engine_job_type",
        ),
        CheckConstraint(
            f"execution_class IN ({_quoted(ENGINE_EXECUTION_CLASSES)})",
            name="ck_lab_engine_job_execution_class",
        ),
        CheckConstraint(
            "length(source_request_sha256) = 64 AND "
            "length(normalized_payload_sha256) = 64 AND "
            "length(implementation_fingerprint_sha256) = 64 AND "
            "length(reference_bundle_sha256) = 64 AND "
            "length(inventory_fingerprint_sha256) = 64 AND "
            "length(capability_fingerprint_sha256) = 64 AND "
            "length(authority_context_sha256) = 64 AND "
            "length(idempotency_key_sha256) = 64 AND "
            "length(command_sha256) = 64 AND "
            "length(job_fingerprint_sha256) = 64",
            name="ck_lab_engine_job_hashes",
        ),
        CheckConstraint(
            "timeout_seconds > 0 AND max_attempts = 1",
            name="ck_lab_engine_job_execution_policy",
        ),
    )

    schema_version: Mapped[str] = mapped_column(String(80), nullable=False)
    contract_version: Mapped[str] = mapped_column(String(80), nullable=False)
    job_type: Mapped[str] = mapped_column(String(60), nullable=False)
    execution_class: Mapped[str] = mapped_column(String(40), nullable=False)
    requester_scope: Mapped[str] = mapped_column(String(255), nullable=False)
    source_request_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    normalized_payload_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    source_request_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    normalized_payload_sha256: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    implementation_fingerprint_sha256: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    implementation_manifest_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    reference_bundle_sha256: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    inventory_fingerprint_sha256: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    capability_fingerprint_sha256: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    authority_context_sha256: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    idempotency_key_sha256: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    command_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    job_fingerprint_sha256: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    max_attempts: Mapped[int] = mapped_column(
        Integer, default=1, server_default=text("1"), nullable=False
    )


class LabEngineJobEvent(LabRecord):
    __tablename__ = "lab_engine_job_events"
    __table_args__ = (
        UniqueConstraint(
            "job_id", "sequence", name="uq_lab_engine_job_event_sequence"
        ),
        UniqueConstraint(
            "event_sha256", name="uq_lab_engine_job_event_hash"
        ),
        CheckConstraint(
            f"state IN ({_quoted(ENGINE_JOB_STATES)})",
            name="ck_lab_engine_job_event_state",
        ),
        CheckConstraint(
            "sequence >= 1 AND lease_epoch >= 0 AND attempt >= 0",
            name="ck_lab_engine_job_event_sequence_attempt",
        ),
        CheckConstraint(
            "(sequence = 1 AND parent_event_sha256 IS NULL) OR "
            "(sequence > 1 AND length(parent_event_sha256) = 64)",
            name="ck_lab_engine_job_event_chain",
        ),
        CheckConstraint(
            "length(event_sha256) = 64 AND "
            "(lease_token_sha256 IS NULL OR length(lease_token_sha256) = 64)",
            name="ck_lab_engine_job_event_hashes",
        ),
        CheckConstraint(
            "(state IN ('LEASED', 'RUNNING') AND lease_owner IS NOT NULL "
            "AND lease_epoch >= 1 AND lease_expires_at IS NOT NULL "
            "AND lease_token_sha256 IS NOT NULL) OR "
            "(state NOT IN ('LEASED', 'RUNNING') AND lease_owner IS NULL "
            "AND lease_expires_at IS NULL AND lease_token_sha256 IS NULL)",
            name="ck_lab_engine_job_event_lease_shape",
        ),
    )

    job_id: Mapped[str] = mapped_column(
        ForeignKey("lab_engine_jobs.id", ondelete="RESTRICT"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    lease_owner: Mapped[str | None] = mapped_column(String(255))
    lease_epoch: Mapped[int] = mapped_column(
        Integer, default=0, server_default=text("0"), nullable=False
    )
    lease_token_sha256: Mapped[str | None] = mapped_column(String(64))
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime(timezone=True)
    )
    attempt: Mapped[int] = mapped_column(
        Integer, default=0, server_default=text("0"), nullable=False
    )
    sanitized_reason: Mapped[str | None] = mapped_column(Text)
    detail_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    parent_event_sha256: Mapped[str | None] = mapped_column(String(64))
    event_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class LabEngineJobResult(LabRecord):
    __tablename__ = "lab_engine_job_results"
    __table_args__ = (
        UniqueConstraint("job_id", name="uq_lab_engine_job_result_job"),
        CheckConstraint(
            f"terminal_state IN ({_quoted(ENGINE_TERMINAL_STATES)})",
            name="ck_lab_engine_job_result_terminal_state",
        ),
        CheckConstraint(
            "length(result_sha256) = 64",
            name="ck_lab_engine_job_result_hash",
        ),
        CheckConstraint(
            _FALSE_AUTHORITY_CHECK,
            name="ck_lab_engine_job_result_no_authority",
        ),
    )

    job_id: Mapped[str] = mapped_column(
        ForeignKey("lab_engine_jobs.id", ondelete="RESTRICT"), nullable=False
    )
    terminal_state: Mapped[str] = mapped_column(String(32), nullable=False)
    result_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    result_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    validation_state: Mapped[str] = mapped_column(String(80), nullable=False)
    diagnostics_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    release_authority: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("0"), nullable=False
    )
    safety_authority: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("0"), nullable=False
    )
    compounding_authority: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("0"), nullable=False
    )
    evidence_admission_authorized: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("0"), nullable=False
    )


CP2_ENGINE_JOB_TABLE_NAMES = {
    "lab_engine_jobs",
    "lab_engine_job_events",
    "lab_engine_job_results",
}


__all__ = [
    "CP2_ENGINE_JOB_TABLE_NAMES",
    "ENGINE_EXECUTION_CLASSES",
    "ENGINE_JOB_STATES",
    "ENGINE_JOB_TYPES",
    "ENGINE_TERMINAL_STATES",
    "LabEngineJob",
    "LabEngineJobEvent",
    "LabEngineJobResult",
]
