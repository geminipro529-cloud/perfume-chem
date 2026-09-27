"""Append-only, non-authoritative instrumental research observations."""

from __future__ import annotations

from sqlalchemy import JSON, Boolean, CheckConstraint, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.lab import LabRecord


class LabInstrumentalObservation(LabRecord):
    """One immutable timepoint from a fully identified instrumental run."""

    __tablename__ = "lab_instrumental_observations"
    __table_args__ = (
        UniqueConstraint(
            "requester_scope",
            "idempotency_key_sha256",
            name="uq_lab_instrumental_observation_idempotency",
        ),
        UniqueConstraint(
            "observation_id",
            name="uq_lab_instrumental_observation_identity",
        ),
        UniqueConstraint(
            "record_sha256",
            name="uq_lab_instrumental_observation_record_hash",
        ),
        CheckConstraint(
            "substrate IN ('GLASS', 'BLOTTER', 'SKIN_SURROGATE', 'SKIN')",
            name="ck_lab_instrumental_observation_substrate",
        ),
        CheckConstraint(
            "deposit_unit IN ('mg', 'g', 'uL', 'mL')",
            name="ck_lab_instrumental_observation_deposit_unit",
        ),
        CheckConstraint(
            "review_state = 'UNREVIEWED'",
            name="ck_lab_instrumental_observation_review_state",
        ),
        CheckConstraint(
            "length(formula_sha256) = 64 AND length(inventory_sha256) = 64 "
            "AND length(stock_lot_bundle_sha256) = 64 "
            "AND length(preparation_receipt_sha256) = 64 "
            "AND length(release_scenario_sha256) = 64 "
            "AND length(calibration_receipt_sha256) = 64 "
            "AND length(blank_receipt_sha256) = 64 "
            "AND length(raw_data_sha256) = 64 "
            "AND length(processed_result_sha256) = 64 "
            "AND length(idempotency_key_sha256) = 64 "
            "AND length(command_sha256) = 64 AND length(record_sha256) = 64",
            name="ck_lab_instrumental_observation_hashes",
        ),
        CheckConstraint(
            "processing_allowed = 0 AND scientific_authority = 0 "
            "AND model_calibration_authority = 0 AND release_authority = 0 "
            "AND safety_authority = 0 AND compounding_authority = 0 "
            "AND evidence_admission_authorized = 0",
            name="ck_lab_instrumental_observation_no_authority",
        ),
    )

    schema_version: Mapped[str] = mapped_column(String(96), nullable=False)
    observation_id: Mapped[str] = mapped_column(String(255), nullable=False)
    requester_scope: Mapped[str] = mapped_column(String(255), nullable=False)
    formula_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    inventory_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    stock_lot_bundle_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    preparation_receipt_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    release_scenario_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    deposit_decimal_text: Mapped[str] = mapped_column(String(128), nullable=False)
    deposit_unit: Mapped[str] = mapped_column(String(8), nullable=False)
    matrix_id: Mapped[str] = mapped_column(String(255), nullable=False)
    substrate: Mapped[str] = mapped_column(String(32), nullable=False)
    temperature_k_decimal_text: Mapped[str] = mapped_column(String(128), nullable=False)
    relative_humidity_decimal_text: Mapped[str] = mapped_column(String(128), nullable=False)
    airflow_m_s_decimal_text: Mapped[str] = mapped_column(String(128), nullable=False)
    surface_area_m2_decimal_text: Mapped[str] = mapped_column(String(128), nullable=False)
    delivery_geometry_id: Mapped[str] = mapped_column(String(255), nullable=False)
    sampling_method_id: Mapped[str] = mapped_column(String(255), nullable=False)
    instrument_id: Mapped[str] = mapped_column(String(255), nullable=False)
    calibration_receipt_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    blank_receipt_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    time_seconds_decimal_text: Mapped[str] = mapped_column(String(128), nullable=False)
    replicate_id: Mapped[str] = mapped_column(String(255), nullable=False)
    session_id: Mapped[str] = mapped_column(String(255), nullable=False)
    raw_data_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    processed_result_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    protocol_deviations_json: Mapped[list] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    review_state: Mapped[str] = mapped_column(
        String(32), default="UNREVIEWED", server_default="UNREVIEWED", nullable=False
    )
    payload_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    idempotency_key_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    command_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    record_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    review_note: Mapped[str | None] = mapped_column(Text)

    processing_allowed: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("0"), nullable=False
    )
    scientific_authority: Mapped[bool] = mapped_column(
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


INSTRUMENTAL_OBSERVATION_TABLE_NAMES = {"lab_instrumental_observations"}


__all__ = [
    "INSTRUMENTAL_OBSERVATION_TABLE_NAMES",
    "LabInstrumentalObservation",
]
