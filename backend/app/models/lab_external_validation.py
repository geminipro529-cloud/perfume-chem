"""Immutable, authority-safe project-owned external-validation records.

The generic Lab Beta experiment tables remain available for compatibility.
This table is the strict intake boundary for future temporal sensory cells and
pairwise preferences.  Every record snapshots its complete scope and is
permanently non-authoritative until a separate, explicit admission process is
implemented.
"""

from __future__ import annotations

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.lab import LabRecord

EXTERNAL_VALIDATION_RECORD_KINDS = (
    "TEMPORAL_OBSERVATION",
    "PAIRWISE_PREFERENCE",
)
EXTERNAL_VALIDATION_MISSINGNESS_STATES = (
    "OBSERVED",
    "MISSING",
    "NOT_APPLICABLE",
)
EXTERNAL_VALIDATION_PREFERENCE_OUTCOMES = (
    "PRIMARY",
    "SECONDARY",
    "TIE",
)


def _quoted(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


_FALSE_AUTHORITY_CHECK = (
    "processing_allowed = 0 AND scientific_authority = 0 "
    "AND sensory_authority = 0 AND model_calibration_authority = 0 "
    "AND release_authority = 0 AND safety_authority = 0 "
    "AND compounding_authority = 0 AND evidence_admission_authorized = 0"
)


class LabExternalValidationRecord(LabRecord):
    """One immutable observed cell or pairwise outcome with exact scope."""

    __tablename__ = "lab_external_validation_records"
    __table_args__ = (
        UniqueConstraint(
            "requester_scope",
            "idempotency_key_sha256",
            name="uq_lab_external_validation_idempotency",
        ),
        UniqueConstraint(
            "canonical_cell_sha256",
            name="uq_lab_external_validation_cell",
        ),
        UniqueConstraint(
            "record_sha256",
            name="uq_lab_external_validation_record_hash",
        ),
        CheckConstraint(
            f"record_kind IN ({_quoted(EXTERNAL_VALIDATION_RECORD_KINDS)})",
            name="ck_lab_external_validation_kind",
        ),
        CheckConstraint(
            "missingness_state IN "
            f"({_quoted(EXTERNAL_VALIDATION_MISSINGNESS_STATES)})",
            name="ck_lab_external_validation_missingness",
        ),
        CheckConstraint(
            "preference_outcome IS NULL OR preference_outcome IN "
            f"({_quoted(EXTERNAL_VALIDATION_PREFERENCE_OUTCOMES)})",
            name="ck_lab_external_validation_preference_outcome",
        ),
        CheckConstraint(
            "(record_kind = 'TEMPORAL_OBSERVATION' "
            "AND secondary_application_id IS NULL "
            "AND presentation_position IS NOT NULL "
            "AND preference_outcome IS NULL) OR "
            "(record_kind = 'PAIRWISE_PREFERENCE' "
            "AND secondary_application_id IS NOT NULL "
            "AND presentation_position IS NULL "
            "AND value_decimal_text IS NULL)",
            name="ck_lab_external_validation_kind_shape",
        ),
        CheckConstraint(
            "(missingness_state = 'OBSERVED' AND "
            "((record_kind = 'TEMPORAL_OBSERVATION' "
            "AND value_decimal_text IS NOT NULL) OR "
            "(record_kind = 'PAIRWISE_PREFERENCE' "
            "AND preference_outcome IS NOT NULL)) "
            "AND missing_reason IS NULL) OR "
            "(missingness_state != 'OBSERVED' "
            "AND value_decimal_text IS NULL "
            "AND preference_outcome IS NULL "
            "AND missing_reason IS NOT NULL)",
            name="ck_lab_external_validation_value_shape",
        ),
        CheckConstraint(
            "presentation_position IS NULL OR presentation_position >= 1",
            name="ck_lab_external_validation_position",
        ),
        CheckConstraint(
            "length(idempotency_key_sha256) = 64 AND "
            "length(command_sha256) = 64 AND "
            "length(canonical_cell_sha256) = 64 AND "
            "length(protocol_scope_sha256) = 64 AND "
            "length(sample_scope_sha256) = 64 AND "
            "length(condition_scope_sha256) = 64 AND "
            "length(order_scope_sha256) = 64 AND "
            "length(assessor_scope_sha256) = 64 AND "
            "length(provenance_scope_sha256) = 64 AND "
            "length(record_sha256) = 64",
            name="ck_lab_external_validation_hashes",
        ),
        CheckConstraint(
            _FALSE_AUTHORITY_CHECK,
            name="ck_lab_external_validation_no_authority",
        ),
    )

    schema_version: Mapped[str] = mapped_column(String(96), nullable=False)
    record_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    experiment_id: Mapped[str] = mapped_column(
        ForeignKey("lab_experiments.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    primary_application_id: Mapped[str] = mapped_column(
        ForeignKey("lab_applications.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    secondary_application_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_applications.id", ondelete="RESTRICT"),
        index=True,
    )
    requester_scope: Mapped[str] = mapped_column(String(255), nullable=False)
    protocol_id: Mapped[str] = mapped_column(String(255), nullable=False)
    endpoint_id: Mapped[str] = mapped_column(String(255), nullable=False)
    repeat_id: Mapped[str] = mapped_column(String(255), nullable=False)
    time_seconds_decimal_text: Mapped[str] = mapped_column(String(128), nullable=False)
    presentation_sequence_id: Mapped[str] = mapped_column(String(255), nullable=False)
    presentation_position: Mapped[int | None] = mapped_column(Integer)
    missingness_state: Mapped[str] = mapped_column(String(32), nullable=False)
    value_decimal_text: Mapped[str | None] = mapped_column(String(128))
    preference_outcome: Mapped[str | None] = mapped_column(String(32))
    missing_reason: Mapped[str | None] = mapped_column(String(500))

    protocol_snapshot_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    sample_snapshot_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    condition_snapshot_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    order_snapshot_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    assessor_snapshot_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    provenance_snapshot_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    payload_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )

    idempotency_key_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    command_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    canonical_cell_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    protocol_scope_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    sample_scope_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    condition_scope_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    order_scope_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    assessor_scope_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    provenance_scope_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    record_sha256: Mapped[str] = mapped_column(String(64), nullable=False)

    processing_allowed: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("0"), nullable=False
    )
    scientific_authority: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("0"), nullable=False
    )
    sensory_authority: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("0"), nullable=False
    )
    model_calibration_authority: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("0"), nullable=False
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


EXTERNAL_VALIDATION_TABLE_NAMES = {"lab_external_validation_records"}


__all__ = [
    "EXTERNAL_VALIDATION_MISSINGNESS_STATES",
    "EXTERNAL_VALIDATION_PREFERENCE_OUTCOMES",
    "EXTERNAL_VALIDATION_RECORD_KINDS",
    "EXTERNAL_VALIDATION_TABLE_NAMES",
    "LabExternalValidationRecord",
]
