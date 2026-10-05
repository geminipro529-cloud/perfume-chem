"""Immutable links between lab samples and governed commercial references."""

from __future__ import annotations

from datetime import date

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.lab import LabRecord


class LabCommercialReferenceSample(LabRecord):
    __tablename__ = "lab_commercial_reference_samples"
    __table_args__ = (
        UniqueConstraint("sample_id", name="uq_lab_commercial_reference_sample_link"),
        UniqueConstraint(
            "requester_scope",
            "idempotency_key_sha256",
            name="uq_lab_commercial_reference_sample_idempotency",
        ),
        UniqueConstraint("record_sha256", name="uq_lab_commercial_reference_sample_hash"),
        CheckConstraint(
            "length(registry_sha256) = 64 AND "
            "(panel_sha256 IS NULL OR length(panel_sha256) = 64) AND "
            "length(idempotency_key_sha256) = 64 AND "
            "length(command_sha256) = 64 AND length(record_sha256) = 64",
            name="ck_lab_commercial_reference_sample_hashes",
        ),
        CheckConstraint(
            "release_authority = 0 AND safety_authority = 0 "
            "AND compounding_authority = 0 AND evidence_admission_authorized = 0",
            name="ck_lab_commercial_reference_sample_no_authority",
        ),
    )

    schema_version: Mapped[str] = mapped_column(String(96), nullable=False)
    sample_id: Mapped[str] = mapped_column(
        ForeignKey("lab_samples.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    requester_scope: Mapped[str] = mapped_column(String(255), nullable=False)
    product_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    concentration: Mapped[str] = mapped_column(String(255), nullable=False)
    edition: Mapped[str] = mapped_column(String(255), nullable=False)
    sample_identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    registry_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    panel_id: Mapped[str | None] = mapped_column(String(255))
    panel_sha256: Mapped[str | None] = mapped_column(String(64))
    purchase_source: Mapped[str | None] = mapped_column(String(500))
    batch_code: Mapped[str | None] = mapped_column(String(255))
    acquisition_date: Mapped[date | None] = mapped_column(Date)
    authenticity_documentation_state: Mapped[str] = mapped_column(
        String(80),
        default="NOT_PROVIDED_PERSONAL_MODE",
        server_default="NOT_PROVIDED_PERSONAL_MODE",
        nullable=False,
    )
    payload_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    idempotency_key_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    command_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    record_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
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


COMMERCIAL_REFERENCE_TABLE_NAMES = {"lab_commercial_reference_samples"}


__all__ = [
    "COMMERCIAL_REFERENCE_TABLE_NAMES",
    "LabCommercialReferenceSample",
]
