"""Append-only B3 contextual thresholds, OAV assessments, and legacy quarantine."""

from __future__ import annotations

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Float,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.lab import LabRecord

THRESHOLD_ENDPOINTS = (
    "DETECTION",
    "RECOGNITION",
    "DIFFERENCE",
    "REJECTION",
    "OTHER",
)
THRESHOLD_ROUTES = ("ORTHONASAL", "RETRONASAL", "OTHER")
THRESHOLD_MATRIX_STATES = ("SPECIFIED", "UNSPECIFIED")
THRESHOLD_TRAINING_STATES = (
    "TRAINED",
    "UNTRAINED",
    "MIXED",
    "NOT_REPORTED",
)
THRESHOLD_CONCENTRATION_BASES = (
    "MOLE_FRACTION",
    "MASS_FRACTION",
    "VOLUME_FRACTION",
    "MASS_CONCENTRATION",
    "AMOUNT_CONCENTRATION",
    "OTHER_DECLARED",
)
OAV_ASSESSMENT_STATUSES = ("COMPUTED", "WITHHELD")
LEGACY_THRESHOLD_AUTHORITY = "LEGACY_CONTEXT_INCOMPLETE"


def _quoted(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


class LabThresholdObservationContext(LabRecord):
    __tablename__ = "lab_threshold_observation_contexts"
    __table_args__ = (
        Index(
            "ix_lab_threshold_observation_contexts_observation_id",
            "observation_id",
            unique=True,
        ),
        UniqueConstraint(
            "observation_id",
            name="uq_lab_threshold_context_observation",
        ),
        UniqueConstraint(
            "content_sha256",
            name="uq_lab_threshold_context_content_sha256",
        ),
        CheckConstraint(
            f"endpoint IN ({_quoted(THRESHOLD_ENDPOINTS)})",
            name="ck_lab_threshold_context_endpoint",
        ),
        CheckConstraint(
            f"route IN ({_quoted(THRESHOLD_ROUTES)})",
            name="ck_lab_threshold_context_route",
        ),
        CheckConstraint(
            f"matrix_specification_state IN ({_quoted(THRESHOLD_MATRIX_STATES)})",
            name="ck_lab_threshold_context_matrix_state",
        ),
        CheckConstraint(
            f"concentration_basis IN ({_quoted(THRESHOLD_CONCENTRATION_BASES)})",
            name="ck_lab_threshold_context_basis",
        ),
        CheckConstraint(
            f"training_state IN ({_quoted(THRESHOLD_TRAINING_STATES)})",
            name="ck_lab_threshold_context_training",
        ),
        CheckConstraint(
            "sample_size >= 1",
            name="ck_lab_threshold_context_sample_size",
        ),
        CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_threshold_context_content_sha256",
        ),
        ForeignKeyConstraint(
            ["observation_id"],
            ["lab_property_observations.id"],
            ondelete="RESTRICT",
            name="fk_lab_threshold_context_observation",
        ),
    )

    observation_id: Mapped[str] = mapped_column(String(36), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(80), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(40), nullable=False)
    route: Mapped[str] = mapped_column(String(40), nullable=False)
    medium: Mapped[str] = mapped_column(Text, nullable=False)
    matrix_specification_state: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )
    matrix_composition_json: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    concentration_basis: Mapped[str] = mapped_column(
        String(60),
        nullable=False,
    )
    apparatus_json: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    population_json: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    training_state: Mapped[str] = mapped_column(String(40), nullable=False)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    psychophysical_procedure: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class LabOAVAssessment(LabRecord):
    __tablename__ = "lab_oav_assessments"
    __table_args__ = (
        Index(
            "ix_lab_oav_assessments_concentration_observation_id",
            "concentration_observation_id",
        ),
        Index(
            "ix_lab_oav_assessments_threshold_assertion_id",
            "threshold_assertion_id",
        ),
        UniqueConstraint(
            "content_sha256",
            name="uq_lab_oav_assessment_content_sha256",
        ),
        CheckConstraint(
            f"status IN ({_quoted(OAV_ASSESSMENT_STATUSES)})",
            name="ck_lab_oav_assessment_status",
        ),
        CheckConstraint(
            "("
            "(status = 'COMPUTED' AND oav_value IS NOT NULL "
            "AND oav_value >= 0 AND mismatch_count = 0) OR "
            "(status = 'WITHHELD' AND oav_value IS NULL "
            "AND mismatch_count >= 1)"
            ")",
            name="ck_lab_oav_assessment_shape",
        ),
        CheckConstraint(
            "strict_science_mode = 1",
            name="ck_lab_oav_assessment_strict",
        ),
        CheckConstraint(
            f"requested_endpoint IN ({_quoted(THRESHOLD_ENDPOINTS)})",
            name="ck_lab_oav_assessment_endpoint",
        ),
        CheckConstraint(
            f"requested_route IN ({_quoted(THRESHOLD_ROUTES)})",
            name="ck_lab_oav_assessment_route",
        ),
        CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_oav_assessment_content_sha256",
        ),
        ForeignKeyConstraint(
            ["concentration_observation_id"],
            ["lab_property_observations.id"],
            ondelete="RESTRICT",
            name="fk_lab_oav_assessment_concentration",
        ),
        ForeignKeyConstraint(
            ["threshold_assertion_id"],
            ["lab_selected_assertions.id"],
            ondelete="RESTRICT",
            name="fk_lab_oav_assessment_threshold_assertion",
        ),
    )

    schema_version: Mapped[str] = mapped_column(String(80), nullable=False)
    concentration_observation_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
    )
    threshold_assertion_id: Mapped[str | None] = mapped_column(String(36))
    requested_endpoint: Mapped[str] = mapped_column(String(40), nullable=False)
    requested_route: Mapped[str] = mapped_column(String(40), nullable=False)
    strict_science_mode: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    oav_value: Mapped[float | None] = mapped_column(Float)
    mismatch_count: Mapped[int] = mapped_column(Integer, nullable=False)
    mismatch_codes_json: Mapped[list] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    conversion_prerequisites_json: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    input_snapshot_json: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    permitted_uses_json: Mapped[list] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    prohibited_claims_json: Mapped[list] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class LabLegacyThresholdRecord(LabRecord):
    __tablename__ = "lab_legacy_threshold_records"
    __table_args__ = (
        Index(
            "ix_lab_legacy_threshold_records_material_key",
            "material_key",
        ),
        UniqueConstraint(
            "content_sha256",
            name="uq_lab_legacy_threshold_content_sha256",
        ),
        CheckConstraint(
            "length(verification_status) > 0",
            name="ck_lab_legacy_threshold_status",
        ),
        CheckConstraint(
            f"authority_state = '{LEGACY_THRESHOLD_AUTHORITY}'",
            name="ck_lab_legacy_threshold_authority",
        ),
        CheckConstraint(
            "numeric_value > 0",
            name="ck_lab_legacy_threshold_value",
        ),
        CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_legacy_threshold_content_sha256",
        ),
    )

    schema_version: Mapped[str] = mapped_column(String(80), nullable=False)
    material_key: Mapped[str] = mapped_column(Text, nullable=False)
    medium: Mapped[str] = mapped_column(String(60), nullable=False)
    numeric_value: Mapped[float] = mapped_column(Float, nullable=False)
    original_unit: Mapped[str] = mapped_column(Text, nullable=False)
    verification_status: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
    )
    authority_state: Mapped[str] = mapped_column(String(60), nullable=False)
    source_payload_json: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


THRESHOLD_AUTHORITY_TABLE_NAMES = {
    LabThresholdObservationContext.__tablename__,
    LabOAVAssessment.__tablename__,
    LabLegacyThresholdRecord.__tablename__,
}


__all__ = [
    "LEGACY_THRESHOLD_AUTHORITY",
    "OAV_ASSESSMENT_STATUSES",
    "THRESHOLD_AUTHORITY_TABLE_NAMES",
    "THRESHOLD_CONCENTRATION_BASES",
    "THRESHOLD_ENDPOINTS",
    "THRESHOLD_MATRIX_STATES",
    "THRESHOLD_ROUTES",
    "THRESHOLD_TRAINING_STATES",
    "LabLegacyThresholdRecord",
    "LabOAVAssessment",
    "LabThresholdObservationContext",
]
