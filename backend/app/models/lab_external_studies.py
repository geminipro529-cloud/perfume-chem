"""Append-only, B1-bound published/external study records.

These records preserve source-reported study structure without reusing the
physical Laboratory Beta experiment tables.  They confer no formula, stock,
model-training, sensory-truth, physical-execution, or release authority.
"""

from __future__ import annotations

from sqlalchemy import (
    JSON,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.lab import LabRecord

EXTERNAL_STUDY_DOMAINS = (
    "HUMAN_SENSORY",
    "ANALYTICAL_CHEMISTRY",
    "BIOLOGICAL_ASSAY",
    "PHYSICAL_CHEMISTRY",
    "MIXED_METHODS",
    "OTHER",
)
EXTERNAL_STIMULUS_KINDS = (
    "SINGLE",
    "MIXTURE",
    "CONTROL",
    "RECOMBINATION",
    "OMISSION",
    "ADDITION",
    "PAIR",
    "TRIANGLE_SET",
    "OTHER",
)
EXTERNAL_CONDITION_ROLES = (
    "BASELINE",
    "CONTROL",
    "TEST",
    "OMISSION",
    "ADDITION",
    "RATIO",
    "OTHER",
)
EXTERNAL_UNIT_GRAINS = (
    "PARTICIPANT",
    "GROUP",
    "AGGREGATE",
    "SAMPLE",
)
EXTERNAL_OBSERVATION_GRAINS = (
    "INDIVIDUAL",
    "GROUP_AGGREGATE",
    "STUDY_AGGREGATE",
    "SAMPLE",
)
EXTERNAL_AGGREGATION_STATISTICS = (
    "RAW",
    "COUNT",
    "MEAN",
    "MEDIAN",
    "PROPORTION",
    "SCORE",
    "SIGNIFICANCE",
    "OTHER",
)
EXTERNAL_MISSINGNESS_STATES = (
    "OBSERVED",
    "MISSING",
    "NOT_APPLICABLE",
    "NOT_REPORTED",
)
EXTERNAL_CROSSWALK_STATUSES = (
    "EXACT_PROJECT_MATERIAL",
    "EXACT_EXTERNAL_IDENTITY_ONLY",
    "CANDIDATE",
    "CONFLICT",
    "UNRESOLVED",
    "OPAQUE_PRODUCT",
)
EXTERNAL_CONFLICT_TYPES = (
    "TABLE_PROSE",
    "METHOD_RESULT",
    "ETHICS",
    "RIGHTS",
    "IDENTITY",
    "UNIT",
    "OTHER",
)
EXTERNAL_CONFLICT_STATES = (
    "OPEN",
    "NARROWED",
    "RESOLVED",
)


def _quoted(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


class LabExternalStudyVersion(LabRecord):
    __tablename__ = "lab_external_study_versions"
    __table_args__ = (
        UniqueConstraint(
            "study_id",
            "version_number",
            name="uq_lab_external_study_version",
        ),
        UniqueConstraint(
            "record_sha256",
            name="uq_lab_external_study_record_sha256",
        ),
        CheckConstraint(
            "version_number >= 1",
            name="ck_lab_external_study_version_positive",
        ),
        CheckConstraint(
            f"study_domain IN ({_quoted(EXTERNAL_STUDY_DOMAINS)})",
            name="ck_lab_external_study_domain",
        ),
        CheckConstraint(
            "authority_state = 'SOURCE_REPORTED_ONLY'",
            name="ck_lab_external_study_authority",
        ),
        CheckConstraint(
            "length(source_use_request_sha256) = 64 AND "
            "length(source_use_assessment_sha256) = 64 AND "
            "length(record_sha256) = 64",
            name="ck_lab_external_study_hashes",
        ),
        CheckConstraint(
            "(version_number = 1 AND supersedes_version_id IS NULL "
            "AND parent_record_sha256 IS NULL) OR "
            "(version_number > 1 AND supersedes_version_id IS NOT NULL "
            "AND length(parent_record_sha256) = 64)",
            name="ck_lab_external_study_version_chain",
        ),
    )

    study_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    source_version_id: Mapped[str] = mapped_column(
        ForeignKey("lab_source_document_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    source_extraction_id: Mapped[str] = mapped_column(
        ForeignKey("lab_source_extraction_records.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_family: Mapped[str] = mapped_column(String(255), nullable=False)
    study_key: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    study_domain: Mapped[str] = mapped_column(String(60), nullable=False)
    design_json: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        server_default=text("'{}'"),
        nullable=False,
    )
    protocol_json: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        server_default=text("'{}'"),
        nullable=False,
    )
    source_use_request_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    source_use_assessment_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    source_use_constraint_version_ids_json: Mapped[list] = mapped_column(
        JSON,
        default=list,
        server_default=text("'[]'"),
        nullable=False,
    )
    source_use_constraint_record_sha256s_json: Mapped[list] = mapped_column(
        JSON,
        default=list,
        server_default=text("'[]'"),
        nullable=False,
    )
    adapter_name: Mapped[str] = mapped_column(String(160), nullable=False)
    adapter_version: Mapped[str] = mapped_column(String(100), nullable=False)
    adapter_config_json: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        server_default=text("'{}'"),
        nullable=False,
    )
    authority_state: Mapped[str] = mapped_column(
        String(40),
        default="SOURCE_REPORTED_ONLY",
        server_default=text("'SOURCE_REPORTED_ONLY'"),
        nullable=False,
    )
    supersedes_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_external_study_versions.id", ondelete="RESTRICT")
    )
    parent_record_sha256: Mapped[str | None] = mapped_column(String(64))
    record_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class LabExternalStimulusVersion(LabRecord):
    __tablename__ = "lab_external_stimulus_versions"
    __table_args__ = (
        UniqueConstraint(
            "study_version_id",
            "stimulus_key",
            name="uq_lab_external_stimulus_key",
        ),
        UniqueConstraint(
            "record_sha256",
            name="uq_lab_external_stimulus_record_sha256",
        ),
        CheckConstraint(
            f"stimulus_kind IN ({_quoted(EXTERNAL_STIMULUS_KINDS)})",
            name="ck_lab_external_stimulus_kind",
        ),
        CheckConstraint(
            "length(record_sha256) = 64",
            name="ck_lab_external_stimulus_record_sha256",
        ),
    )

    study_version_id: Mapped[str] = mapped_column(
        ForeignKey("lab_external_study_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    stimulus_key: Mapped[str] = mapped_column(String(255), nullable=False)
    source_extraction_id: Mapped[str] = mapped_column(
        ForeignKey("lab_source_extraction_records.id", ondelete="RESTRICT"),
        nullable=False,
    )
    stimulus_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    matrix_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    preparation_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    context_json: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        server_default=text("'{}'"),
        nullable=False,
    )
    record_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class LabExternalStimulusComponent(LabRecord):
    __tablename__ = "lab_external_stimulus_components"
    __table_args__ = (
        UniqueConstraint(
            "stimulus_version_id",
            "position",
            name="uq_lab_external_component_position",
        ),
        UniqueConstraint(
            "stimulus_version_id",
            "component_key",
            name="uq_lab_external_component_key",
        ),
        UniqueConstraint(
            "record_sha256",
            name="uq_lab_external_component_record_sha256",
        ),
        CheckConstraint(
            "position >= 1",
            name="ck_lab_external_component_position",
        ),
        CheckConstraint(
            "(quantity_value_text IS NULL AND quantity_unit IS NULL "
            "AND quantity_basis IS NULL) OR "
            "(quantity_value_text IS NOT NULL AND quantity_unit IS NOT NULL "
            "AND quantity_basis IS NOT NULL)",
            name="ck_lab_external_component_quantity_shape",
        ),
        CheckConstraint(
            "(concentration_value_text IS NULL "
            "AND concentration_unit IS NULL "
            "AND concentration_basis IS NULL) OR "
            "(concentration_value_text IS NOT NULL "
            "AND concentration_unit IS NOT NULL "
            "AND concentration_basis IS NOT NULL)",
            name="ck_lab_external_component_concentration_shape",
        ),
        CheckConstraint(
            "length(record_sha256) = 64",
            name="ck_lab_external_component_record_sha256",
        ),
    )

    stimulus_version_id: Mapped[str] = mapped_column(
        ForeignKey("lab_external_stimulus_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    component_key: Mapped[str] = mapped_column(String(255), nullable=False)
    source_extraction_id: Mapped[str] = mapped_column(
        ForeignKey("lab_source_extraction_records.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_identity_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    quantity_value_text: Mapped[str | None] = mapped_column(String(128))
    quantity_unit: Mapped[str | None] = mapped_column(String(80))
    quantity_basis: Mapped[str | None] = mapped_column(String(100))
    concentration_value_text: Mapped[str | None] = mapped_column(String(128))
    concentration_unit: Mapped[str | None] = mapped_column(String(80))
    concentration_basis: Mapped[str | None] = mapped_column(String(100))
    carrier_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    purity_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    role: Mapped[str | None] = mapped_column(String(100))
    record_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class LabExternalCondition(LabRecord):
    __tablename__ = "lab_external_conditions"
    __table_args__ = (
        UniqueConstraint(
            "study_version_id",
            "condition_key",
            name="uq_lab_external_condition_key",
        ),
        UniqueConstraint(
            "record_sha256",
            name="uq_lab_external_condition_record_sha256",
        ),
        CheckConstraint(
            f"condition_role IN ({_quoted(EXTERNAL_CONDITION_ROLES)})",
            name="ck_lab_external_condition_role",
        ),
        CheckConstraint(
            "length(record_sha256) = 64",
            name="ck_lab_external_condition_record_sha256",
        ),
    )

    study_version_id: Mapped[str] = mapped_column(
        ForeignKey("lab_external_study_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    condition_key: Mapped[str] = mapped_column(String(255), nullable=False)
    source_extraction_id: Mapped[str] = mapped_column(
        ForeignKey("lab_source_extraction_records.id", ondelete="RESTRICT"),
        nullable=False,
    )
    condition_role: Mapped[str] = mapped_column(String(40), nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    primary_stimulus_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_external_stimulus_versions.id", ondelete="RESTRICT")
    )
    factors_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    context_json: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        server_default=text("'{}'"),
        nullable=False,
    )
    record_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class LabExternalExperimentalUnit(LabRecord):
    __tablename__ = "lab_external_experimental_units"
    __table_args__ = (
        UniqueConstraint(
            "study_version_id",
            "unit_key",
            name="uq_lab_external_unit_key",
        ),
        UniqueConstraint(
            "record_sha256",
            name="uq_lab_external_unit_record_sha256",
        ),
        CheckConstraint(
            f"unit_grain IN ({_quoted(EXTERNAL_UNIT_GRAINS)})",
            name="ck_lab_external_unit_grain",
        ),
        CheckConstraint(
            "reported_n IS NULL OR reported_n >= 1",
            name="ck_lab_external_unit_reported_n",
        ),
        CheckConstraint(
            "parent_unit_id IS NULL OR parent_unit_id <> id",
            name="ck_lab_external_unit_not_self_parent",
        ),
        CheckConstraint(
            "length(record_sha256) = 64",
            name="ck_lab_external_unit_record_sha256",
        ),
    )

    study_version_id: Mapped[str] = mapped_column(
        ForeignKey("lab_external_study_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    unit_key: Mapped[str] = mapped_column(String(255), nullable=False)
    source_extraction_id: Mapped[str] = mapped_column(
        ForeignKey("lab_source_extraction_records.id", ondelete="RESTRICT"),
        nullable=False,
    )
    unit_grain: Mapped[str] = mapped_column(String(40), nullable=False)
    parent_unit_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_external_experimental_units.id", ondelete="RESTRICT")
    )
    pseudonymous_token: Mapped[str | None] = mapped_column(String(255))
    reported_n: Mapped[int | None] = mapped_column(Integer)
    context_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    record_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class LabExternalObservation(LabRecord):
    __tablename__ = "lab_external_observations"
    __table_args__ = (
        UniqueConstraint(
            "study_version_id",
            "observation_key",
            name="uq_lab_external_observation_key",
        ),
        UniqueConstraint(
            "record_sha256",
            name="uq_lab_external_observation_record_sha256",
        ),
        CheckConstraint(
            f"observation_grain IN ({_quoted(EXTERNAL_OBSERVATION_GRAINS)})",
            name="ck_lab_external_observation_grain",
        ),
        CheckConstraint(
            "aggregation_statistic IN "
            f"({_quoted(EXTERNAL_AGGREGATION_STATISTICS)})",
            name="ck_lab_external_observation_statistic",
        ),
        CheckConstraint(
            f"missingness IN ({_quoted(EXTERNAL_MISSINGNESS_STATES)})",
            name="ck_lab_external_observation_missingness",
        ),
        CheckConstraint(
            "(missingness = 'OBSERVED' AND value_json IS NOT NULL) OR "
            "(missingness <> 'OBSERVED' AND value_json IS NULL)",
            name="ck_lab_external_observation_value_shape",
        ),
        CheckConstraint(
            "(repeat_index IS NULL OR repeat_index >= 1) AND "
            "(replicate_index IS NULL OR replicate_index >= 1)",
            name="ck_lab_external_observation_indices",
        ),
        CheckConstraint(
            "length(record_sha256) = 64",
            name="ck_lab_external_observation_record_sha256",
        ),
    )

    study_version_id: Mapped[str] = mapped_column(
        ForeignKey("lab_external_study_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    observation_key: Mapped[str] = mapped_column(String(255), nullable=False)
    source_extraction_id: Mapped[str] = mapped_column(
        ForeignKey("lab_source_extraction_records.id", ondelete="RESTRICT"),
        nullable=False,
    )
    condition_id: Mapped[str] = mapped_column(
        ForeignKey("lab_external_conditions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    experimental_unit_id: Mapped[str] = mapped_column(
        ForeignKey("lab_external_experimental_units.id", ondelete="RESTRICT"),
        nullable=False,
    )
    primary_stimulus_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_external_stimulus_versions.id", ondelete="RESTRICT")
    )
    trial_key: Mapped[str] = mapped_column(String(255), nullable=False)
    session_key: Mapped[str | None] = mapped_column(String(255))
    repeat_index: Mapped[int | None] = mapped_column(Integer)
    presentation_json: Mapped[list] = mapped_column(JSON, nullable=False)
    endpoint_key: Mapped[str] = mapped_column(String(255), nullable=False)
    value_json: Mapped[dict | None] = mapped_column(JSON(none_as_null=True))
    original_unit: Mapped[str] = mapped_column(String(100), nullable=False)
    scale_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    timepoint_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    replicate_index: Mapped[int | None] = mapped_column(Integer)
    observation_grain: Mapped[str] = mapped_column(String(40), nullable=False)
    aggregation_statistic: Mapped[str] = mapped_column(String(40), nullable=False)
    missingness: Mapped[str] = mapped_column(String(40), nullable=False)
    uncertainty_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    limitations_json: Mapped[list] = mapped_column(
        JSON,
        default=list,
        server_default=text("'[]'"),
        nullable=False,
    )
    record_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class LabExternalIdentityCrosswalk(LabRecord):
    __tablename__ = "lab_external_identity_crosswalks"
    __table_args__ = (
        UniqueConstraint(
            "component_id",
            name="uq_lab_external_crosswalk_component",
        ),
        UniqueConstraint(
            "record_sha256",
            name="uq_lab_external_crosswalk_record_sha256",
        ),
        CheckConstraint(
            f"resolution_status IN ({_quoted(EXTERNAL_CROSSWALK_STATUSES)})",
            name="ck_lab_external_crosswalk_status",
        ),
        CheckConstraint(
            "(resolution_status = 'EXACT_PROJECT_MATERIAL' "
            "AND material_id IS NOT NULL) OR "
            "(resolution_status IN "
            "('EXACT_EXTERNAL_IDENTITY_ONLY', 'UNRESOLVED', 'OPAQUE_PRODUCT') "
            "AND material_id IS NULL) OR "
            "resolution_status IN ('CANDIDATE', 'CONFLICT')",
            name="ck_lab_external_crosswalk_material_shape",
        ),
        CheckConstraint(
            "length(record_sha256) = 64",
            name="ck_lab_external_crosswalk_record_sha256",
        ),
    )

    component_id: Mapped[str] = mapped_column(
        ForeignKey("lab_external_stimulus_components.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    source_extraction_id: Mapped[str] = mapped_column(
        ForeignKey("lab_source_extraction_records.id", ondelete="RESTRICT"),
        nullable=False,
    )
    resolution_status: Mapped[str] = mapped_column(String(50), nullable=False)
    material_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_materials.id", ondelete="RESTRICT")
    )
    source_identity_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    resolved_identity_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    evidence_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    record_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class LabExternalStudyConflict(LabRecord):
    __tablename__ = "lab_external_study_conflicts"
    __table_args__ = (
        UniqueConstraint(
            "study_version_id",
            "conflict_key",
            name="uq_lab_external_conflict_key",
        ),
        UniqueConstraint(
            "record_sha256",
            name="uq_lab_external_conflict_record_sha256",
        ),
        CheckConstraint(
            f"conflict_type IN ({_quoted(EXTERNAL_CONFLICT_TYPES)})",
            name="ck_lab_external_conflict_type",
        ),
        CheckConstraint(
            f"conflict_state IN ({_quoted(EXTERNAL_CONFLICT_STATES)})",
            name="ck_lab_external_conflict_state",
        ),
        CheckConstraint(
            "source_extraction_id <> related_extraction_id",
            name="ck_lab_external_conflict_distinct_extractions",
        ),
        CheckConstraint(
            "length(record_sha256) = 64",
            name="ck_lab_external_conflict_record_sha256",
        ),
    )

    study_version_id: Mapped[str] = mapped_column(
        ForeignKey("lab_external_study_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    conflict_key: Mapped[str] = mapped_column(String(255), nullable=False)
    conflict_type: Mapped[str] = mapped_column(String(40), nullable=False)
    conflict_state: Mapped[str] = mapped_column(String(40), nullable=False)
    source_extraction_id: Mapped[str] = mapped_column(
        ForeignKey("lab_source_extraction_records.id", ondelete="RESTRICT"),
        nullable=False,
    )
    related_extraction_id: Mapped[str] = mapped_column(
        ForeignKey("lab_source_extraction_records.id", ondelete="RESTRICT"),
        nullable=False,
    )
    details_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    record_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


EXTERNAL_STUDY_TABLE_NAMES = {
    LabExternalStudyVersion.__tablename__,
    LabExternalStimulusVersion.__tablename__,
    LabExternalStimulusComponent.__tablename__,
    LabExternalCondition.__tablename__,
    LabExternalExperimentalUnit.__tablename__,
    LabExternalObservation.__tablename__,
    LabExternalIdentityCrosswalk.__tablename__,
    LabExternalStudyConflict.__tablename__,
}


__all__ = [name for name in globals() if name.startswith("LabExternal")] + [
    "EXTERNAL_AGGREGATION_STATISTICS",
    "EXTERNAL_CONDITION_ROLES",
    "EXTERNAL_CONFLICT_STATES",
    "EXTERNAL_CONFLICT_TYPES",
    "EXTERNAL_CROSSWALK_STATUSES",
    "EXTERNAL_MISSINGNESS_STATES",
    "EXTERNAL_OBSERVATION_GRAINS",
    "EXTERNAL_STIMULUS_KINDS",
    "EXTERNAL_STUDY_DOMAINS",
    "EXTERNAL_STUDY_TABLE_NAMES",
    "EXTERNAL_UNIT_GRAINS",
]
