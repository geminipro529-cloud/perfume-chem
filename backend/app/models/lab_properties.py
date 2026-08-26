"""Append-only B2 property observations, conflicts, and selected assertions."""

from __future__ import annotations

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Float,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.lab import LabRecord

PROPERTY_IDENTITY_SCOPES = (
    "CHEMICAL_ENTITY",
    "STEREOISOMER_OR_ISOMERIC_MIXTURE",
    "TRADE_GRADE",
    "SUPPLIER_PRODUCT",
    "SUPPLIER_LOT",
    "STOCK_SOLUTION",
    "PHYSICAL_DOSE",
    "NATURAL_MATERIAL",
)
PROPERTY_VALUE_KINDS = (
    "NUMERIC",
    "CATEGORICAL",
    "INTERVAL",
    "DISTRIBUTION",
    "CENSORED",
)
PROPERTY_CENSORING_QUALIFIERS = (
    "LT_LOD",
    "LT_LOQ",
    "GT_UPPER_RANGE",
    "NOT_DETECTED",
    "TRACE",
)
PROPERTY_EVIDENCE_CLASSES = (
    "MEASURED",
    "LITERATURE_DERIVED",
    "SUPPLIER_PROVIDED",
    "EMPIRICALLY_CALIBRATED",
    "MODEL_ESTIMATED",
    "HEURISTIC",
    "SPECULATIVE",
    "UNKNOWN",
)
PROPERTY_REVIEW_STATES = (
    "STAGED",
    "REVIEWED",
    "ACCEPTED_FOR_SCOPED_USE",
    "REJECTED",
    "SUPERSEDED",
)
PROPERTY_CONFLICT_STATES = ("UNRESOLVED", "RESOLVED_FOR_SCOPE")
PROPERTY_CONFLICT_MATERIALITIES = ("BLOCKING", "NON_BLOCKING")
ASSERTION_CANDIDATE_DECISIONS = ("INCLUDE", "EXCLUDE")
ASSERTION_SELECTION_KINDS = ("OBSERVATION", "MODEL", "NONE")
ASSERTION_INTERPOLATION_STATES = (
    "EXACT",
    "INTERPOLATED",
    "EXTRAPOLATED",
    "NOT_APPLICABLE",
)
ASSERTION_AUTHORITY_STATES = (
    "AUTHORIZED_FOR_SCOPED_PROPERTY",
    "ADVISORY_ONLY",
    "WITHHELD_CONFLICT",
    "WITHHELD_UNKNOWN",
)


def _quoted(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


class LabPropertyObservation(LabRecord):
    __tablename__ = "lab_property_observations"
    __table_args__ = (
        UniqueConstraint(
            "content_sha256",
            name="uq_lab_property_observation_content_sha256",
        ),
        UniqueConstraint(
            "supersedes_observation_id",
            name="uq_lab_property_observation_supersedes",
        ),
        CheckConstraint(
            f"identity_scope IN ({_quoted(PROPERTY_IDENTITY_SCOPES)})",
            name="ck_lab_property_observation_identity_scope",
        ),
        CheckConstraint(
            f"value_kind IN ({_quoted(PROPERTY_VALUE_KINDS)})",
            name="ck_lab_property_observation_value_kind",
        ),
        CheckConstraint(
            "("
            "(value_kind = 'NUMERIC' AND numeric_value IS NOT NULL "
            "AND categorical_value IS NULL AND interval_lower IS NULL "
            "AND interval_upper IS NULL AND distribution_json IS NULL) OR "
            "(value_kind = 'CATEGORICAL' AND numeric_value IS NULL "
            "AND categorical_value IS NOT NULL AND interval_lower IS NULL "
            "AND interval_upper IS NULL AND distribution_json IS NULL) OR "
            "(value_kind = 'INTERVAL' AND numeric_value IS NULL "
            "AND categorical_value IS NULL AND interval_lower IS NOT NULL "
            "AND interval_upper IS NOT NULL "
            "AND interval_lower <= interval_upper "
            "AND distribution_json IS NULL) OR "
            "(value_kind = 'DISTRIBUTION' AND numeric_value IS NULL "
            "AND categorical_value IS NULL AND interval_lower IS NULL "
            "AND interval_upper IS NULL AND distribution_json IS NOT NULL) OR "
            "(value_kind = 'CENSORED' AND numeric_value IS NULL "
            "AND categorical_value IS NULL AND interval_lower IS NULL "
            "AND interval_upper IS NULL AND distribution_json IS NULL)"
            ")",
            name="ck_lab_property_observation_value_shape",
        ),
        CheckConstraint(
            "("
            "(value_kind <> 'CENSORED' AND censoring_qualifier IS NULL "
            "AND censoring_limit IS NULL) OR "
            "(value_kind = 'CENSORED' "
            f"AND censoring_qualifier IN "
            f"({_quoted(PROPERTY_CENSORING_QUALIFIERS)}) "
            "AND ((censoring_qualifier IN "
            "('LT_LOD', 'LT_LOQ', 'GT_UPPER_RANGE') "
            "AND censoring_limit IS NOT NULL) "
            "OR censoring_qualifier IN ('NOT_DETECTED', 'TRACE')))"
            ")",
            name="ck_lab_property_observation_censoring",
        ),
        CheckConstraint(
            "(temperature_k IS NULL OR temperature_k > 0) "
            "AND (pressure_pa IS NULL OR pressure_pa > 0) "
            "AND (relative_humidity_percent IS NULL "
            "OR (relative_humidity_percent >= 0 "
            "AND relative_humidity_percent <= 100)) "
            "AND (purity_fraction IS NULL "
            "OR (purity_fraction >= 0 AND purity_fraction <= 1)) "
            "AND (standard_uncertainty IS NULL "
            "OR standard_uncertainty >= 0)",
            name="ck_lab_property_observation_conditions",
        ),
        CheckConstraint(
            "replicate_count >= 1",
            name="ck_lab_property_observation_replicate_count",
        ),
        CheckConstraint(
            f"evidence_class IN ({_quoted(PROPERTY_EVIDENCE_CLASSES)})",
            name="ck_lab_property_observation_evidence_class",
        ),
        CheckConstraint(
            f"review_state IN ({_quoted(PROPERTY_REVIEW_STATES)})",
            name="ck_lab_property_observation_review_state",
        ),
        CheckConstraint(
            "length(subject_identity_sha256) = 64",
            name="ck_lab_property_observation_identity_sha256",
        ),
        CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_property_observation_content_sha256",
        ),
        ForeignKeyConstraint(
            ["source_version_id"],
            ["lab_source_document_versions.id"],
            ondelete="RESTRICT",
            name="fk_lab_property_observation_source",
        ),
        ForeignKeyConstraint(
            ["extraction_record_id"],
            ["lab_source_extraction_records.id"],
            ondelete="RESTRICT",
            name="fk_lab_property_observation_extraction",
        ),
        ForeignKeyConstraint(
            ["supersedes_observation_id"],
            ["lab_property_observations.id"],
            ondelete="RESTRICT",
            name="fk_lab_property_observation_supersedes",
        ),
    )

    schema_version: Mapped[str] = mapped_column(String(80), nullable=False)
    identity_scope: Mapped[str] = mapped_column(String(60), nullable=False)
    subject_identity_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    subject_identity_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    property_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    value_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    numeric_value: Mapped[float | None] = mapped_column(Float)
    categorical_value: Mapped[str | None] = mapped_column(Text)
    interval_lower: Mapped[float | None] = mapped_column(Float)
    interval_upper: Mapped[float | None] = mapped_column(Float)
    distribution_json: Mapped[dict | None] = mapped_column(
        JSON(none_as_null=True)
    )
    censoring_qualifier: Mapped[str | None] = mapped_column(String(40))
    censoring_limit: Mapped[float | None] = mapped_column(Float)
    original_unit: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_unit: Mapped[str] = mapped_column(Text, nullable=False)
    temperature_k: Mapped[float | None] = mapped_column(Float)
    pressure_pa: Mapped[float | None] = mapped_column(Float)
    relative_humidity_percent: Mapped[float | None] = mapped_column(Float)
    matrix: Mapped[str | None] = mapped_column(Text)
    phase: Mapped[str | None] = mapped_column(String(80))
    purity_fraction: Mapped[float | None] = mapped_column(Float)
    method: Mapped[str] = mapped_column(Text, nullable=False)
    source_version_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )
    extraction_record_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )
    source_locator_json: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        server_default=text("'{}'"),
        nullable=False,
    )
    replicate_count: Mapped[int] = mapped_column(
        Integer,
        default=1,
        server_default=text("1"),
        nullable=False,
    )
    statistic: Mapped[str] = mapped_column(String(100), nullable=False)
    standard_uncertainty: Mapped[float | None] = mapped_column(Float)
    uncertainty_interval_json: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        server_default=text("'{}'"),
        nullable=False,
    )
    evidence_class: Mapped[str] = mapped_column(String(40), nullable=False)
    review_state: Mapped[str] = mapped_column(String(40), nullable=False)
    quality_flags_json: Mapped[list] = mapped_column(
        JSON,
        default=list,
        server_default=text("'[]'"),
        nullable=False,
    )
    applicability_domain_json: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        server_default=text("'{}'"),
        nullable=False,
    )
    provenance_activity_json: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        server_default=text("'{}'"),
        nullable=False,
    )
    supersedes_observation_id: Mapped[str | None] = mapped_column(String(36))
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class LabPropertyConflictSet(LabRecord):
    __tablename__ = "lab_property_conflict_sets"
    __table_args__ = (
        UniqueConstraint(
            "content_sha256",
            name="uq_lab_property_conflict_content_sha256",
        ),
        CheckConstraint(
            f"state IN ({_quoted(PROPERTY_CONFLICT_STATES)})",
            name="ck_lab_property_conflict_state",
        ),
        CheckConstraint(
            f"materiality IN ({_quoted(PROPERTY_CONFLICT_MATERIALITIES)})",
            name="ck_lab_property_conflict_materiality",
        ),
        CheckConstraint(
            "length(requested_identity_sha256) = 64",
            name="ck_lab_property_conflict_identity_sha256",
        ),
        CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_property_conflict_content_sha256",
        ),
    )

    schema_version: Mapped[str] = mapped_column(String(80), nullable=False)
    requested_identity_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    requested_identity_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    property_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    requested_conditions_json: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        server_default=text("'{}'"),
        nullable=False,
    )
    state: Mapped[str] = mapped_column(String(40), nullable=False)
    materiality: Mapped[str] = mapped_column(String(40), nullable=False)
    difference_dimensions_json: Mapped[list] = mapped_column(
        JSON,
        default=list,
        server_default=text("'[]'"),
        nullable=False,
    )
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class LabPropertyConflictMember(LabRecord):
    __tablename__ = "lab_property_conflict_members"
    __table_args__ = (
        UniqueConstraint(
            "conflict_set_id",
            "observation_id",
            name="uq_lab_property_conflict_member",
        ),
        ForeignKeyConstraint(
            ["conflict_set_id"],
            ["lab_property_conflict_sets.id"],
            ondelete="RESTRICT",
            name="fk_lab_property_conflict_member_set",
        ),
        ForeignKeyConstraint(
            ["observation_id"],
            ["lab_property_observations.id"],
            ondelete="RESTRICT",
            name="fk_lab_property_conflict_member_observation",
        ),
    )

    conflict_set_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )
    observation_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )
    differences_json: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        server_default=text("'{}'"),
        nullable=False,
    )


class LabSelectedAssertion(LabRecord):
    __tablename__ = "lab_selected_assertions"
    __table_args__ = (
        UniqueConstraint(
            "content_sha256",
            name="uq_lab_selected_assertion_content_sha256",
        ),
        CheckConstraint(
            f"selection_kind IN ({_quoted(ASSERTION_SELECTION_KINDS)})",
            name="ck_lab_selected_assertion_selection_kind",
        ),
        CheckConstraint(
            "("
            "(selection_kind = 'OBSERVATION' "
            "AND selected_observation_id IS NOT NULL "
            "AND selected_model_json IS NULL) OR "
            "(selection_kind = 'MODEL' "
            "AND selected_observation_id IS NULL "
            "AND selected_model_json IS NOT NULL) OR "
            "(selection_kind = 'NONE' "
            "AND selected_observation_id IS NULL "
            "AND selected_model_json IS NULL)"
            ")",
            name="ck_lab_selected_assertion_selection_shape",
        ),
        CheckConstraint(
            f"interpolation_state IN "
            f"({_quoted(ASSERTION_INTERPOLATION_STATES)})",
            name="ck_lab_selected_assertion_interpolation",
        ),
        CheckConstraint(
            f"authority_state IN ({_quoted(ASSERTION_AUTHORITY_STATES)})",
            name="ck_lab_selected_assertion_authority",
        ),
        CheckConstraint(
            "length(requested_identity_sha256) = 64",
            name="ck_lab_selected_assertion_identity_sha256",
        ),
        CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_selected_assertion_content_sha256",
        ),
        ForeignKeyConstraint(
            ["conflict_set_id"],
            ["lab_property_conflict_sets.id"],
            ondelete="RESTRICT",
            name="fk_lab_selected_assertion_conflict",
        ),
        ForeignKeyConstraint(
            ["selected_observation_id"],
            ["lab_property_observations.id"],
            ondelete="RESTRICT",
            name="fk_lab_selected_assertion_observation",
        ),
    )

    schema_version: Mapped[str] = mapped_column(String(80), nullable=False)
    requested_identity_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    requested_identity_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    requested_property_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    requested_conditions_json: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        server_default=text("'{}'"),
        nullable=False,
    )
    conflict_set_id: Mapped[str | None] = mapped_column(String(36), index=True)
    selection_policy_version: Mapped[str] = mapped_column(Text, nullable=False)
    selection_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    selected_observation_id: Mapped[str | None] = mapped_column(
        String(36),
        index=True,
    )
    selected_model_json: Mapped[dict | None] = mapped_column(
        JSON(none_as_null=True)
    )
    interpolation_state: Mapped[str] = mapped_column(String(40), nullable=False)
    propagated_uncertainty_json: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        server_default=text("'{}'"),
        nullable=False,
    )
    applicability_json: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        server_default=text("'{}'"),
        nullable=False,
    )
    authority_state: Mapped[str] = mapped_column(String(60), nullable=False)
    permitted_claim_wording: Mapped[str] = mapped_column(Text, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class LabSelectedAssertionCandidate(LabRecord):
    __tablename__ = "lab_selected_assertion_candidates"
    __table_args__ = (
        UniqueConstraint(
            "selected_assertion_id",
            "observation_id",
            name="uq_lab_selected_assertion_candidate",
        ),
        CheckConstraint(
            f"decision IN ({_quoted(ASSERTION_CANDIDATE_DECISIONS)})",
            name="ck_lab_selected_assertion_candidate_decision",
        ),
        ForeignKeyConstraint(
            ["selected_assertion_id"],
            ["lab_selected_assertions.id"],
            ondelete="RESTRICT",
            name="fk_lab_selected_assertion_candidate_assertion",
        ),
        ForeignKeyConstraint(
            ["observation_id"],
            ["lab_property_observations.id"],
            ondelete="RESTRICT",
            name="fk_lab_selected_assertion_candidate_observation",
        ),
    )

    selected_assertion_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )
    observation_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)


PROPERTY_AUTHORITY_TABLE_NAMES = {
    "lab_property_observations",
    "lab_property_conflict_sets",
    "lab_property_conflict_members",
    "lab_selected_assertions",
    "lab_selected_assertion_candidates",
}

__all__ = [
    "ASSERTION_AUTHORITY_STATES",
    "ASSERTION_CANDIDATE_DECISIONS",
    "ASSERTION_INTERPOLATION_STATES",
    "ASSERTION_SELECTION_KINDS",
    "PROPERTY_AUTHORITY_TABLE_NAMES",
    "PROPERTY_CENSORING_QUALIFIERS",
    "PROPERTY_CONFLICT_MATERIALITIES",
    "PROPERTY_CONFLICT_STATES",
    "PROPERTY_EVIDENCE_CLASSES",
    "PROPERTY_IDENTITY_SCOPES",
    "PROPERTY_REVIEW_STATES",
    "PROPERTY_VALUE_KINDS",
    "LabPropertyConflictMember",
    "LabPropertyConflictSet",
    "LabPropertyObservation",
    "LabSelectedAssertion",
    "LabSelectedAssertionCandidate",
]
