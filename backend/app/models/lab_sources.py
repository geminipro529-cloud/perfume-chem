"""Append-only source, extraction, workflow, and derivation authority records."""

from __future__ import annotations

from datetime import date

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.lab import LabRecord

SOURCE_TYPES = (
    "AUTHENTICATED_FORMULA_OR_DOSSIER",
    "PRIMARY_PEER_REVIEWED_PAPER",
    "REVIEW_PAPER",
    "STANDARD",
    "REGULATION_OR_OFFICIAL_GUIDANCE",
    "AUTHORITATIVE_DATABASE_RECORD",
    "SUPPLIER_COA",
    "SUPPLIER_SPECIFICATION",
    "SUPPLIER_SDS",
    "SUPPLIER_IFRA_CERTIFICATE",
    "SUPPLIER_ALLERGEN_DECLARATION",
    "PATENT",
    "LOCAL_ANALYTICAL_EXPERIMENT",
    "LOCAL_SENSORY_EXPERIMENT",
    "EXPERT_NOTE",
    "SECONDARY_RECONSTRUCTION",
    "COMMUNITY_OBSERVATION",
    "AI_GENERATED_HYPOTHESIS",
)
EVIDENCE_WORKFLOW_STATES = (
    "STAGED",
    "PARSED",
    "IDENTITY_RESOLVED",
    "UNIT_NORMALIZED",
    "CONDITION_NORMALIZED",
    "CONFLICT_CHECKED",
    "HUMAN_REVIEWED",
    "ACCEPTED_FOR_SCOPED_USE",
    "REJECTED",
    "SUPERSEDED",
)
SOURCE_REVIEW_STATES = ("UNREVIEWED", "REVIEWED", "REJECTED", "SUPERSEDED")
SOURCE_DERIVATION_RELATIONS = (
    "DERIVED_FROM",
    "REPRODUCES",
    "CITES",
    "INCORPORATES",
)
WORKFLOW_SUBJECT_TYPES = ("SOURCE_VERSION", "EXTRACTION_RECORD")


def _quoted(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


class LabSourceDocumentVersion(LabRecord):
    __tablename__ = "lab_source_document_versions"
    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "version_number",
            name="uq_lab_source_document_version",
        ),
        UniqueConstraint(
            "record_sha256",
            name="uq_lab_source_document_record_sha256",
        ),
        CheckConstraint(
            "version_number >= 1",
            name="ck_lab_source_version_positive",
        ),
        CheckConstraint(
            f"source_type IN ({_quoted(SOURCE_TYPES)})",
            name="ck_lab_source_type",
        ),
        CheckConstraint(
            f"review_state IN ({_quoted(SOURCE_REVIEW_STATES)})",
            name="ck_lab_source_review_state",
        ),
        CheckConstraint(
            "length(artifact_sha256) = 64",
            name="ck_lab_source_artifact_sha256",
        ),
        CheckConstraint(
            "length(record_sha256) = 64",
            name="ck_lab_source_record_sha256",
        ),
        CheckConstraint(
            "(version_number = 1 AND supersedes_version_id IS NULL "
            "AND parent_record_sha256 IS NULL) OR "
            "(version_number > 1 AND supersedes_version_id IS NOT NULL "
            "AND length(parent_record_sha256) = 64)",
            name="ck_lab_source_version_chain",
        ),
        ForeignKeyConstraint(
            ["supersedes_version_id"],
            ["lab_source_document_versions.id"],
            ondelete="RESTRICT",
            name="fk_lab_source_document_supersedes",
        ),
    )

    source_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    schema_version: Mapped[str] = mapped_column(String(80), nullable=False)
    source_type: Mapped[str] = mapped_column(String(60), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    authors_json: Mapped[list] = mapped_column(
        JSON,
        default=list,
        server_default=text("'[]'"),
        nullable=False,
    )
    issuing_organization: Mapped[str | None] = mapped_column(Text)
    container_title: Mapped[str | None] = mapped_column(Text)
    publisher_or_authority: Mapped[str | None] = mapped_column(Text)
    identifiers_json: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        server_default=text("'{}'"),
        nullable=False,
    )
    publication_date: Mapped[date | None] = mapped_column(Date)
    revision_date: Mapped[date | None] = mapped_column(Date)
    effective_date: Mapped[date | None] = mapped_column(Date)
    retrieval_date: Mapped[date | None] = mapped_column(Date)
    edition_or_amendment: Mapped[str | None] = mapped_column(Text)
    default_locator_json: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        server_default=text("'{}'"),
        nullable=False,
    )
    artifact_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    license_or_reuse_restriction: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(40), nullable=False)
    original_unit: Mapped[str | None] = mapped_column(Text)
    original_terminology: Mapped[str | None] = mapped_column(Text)
    reviewer_pseudonym: Mapped[str | None] = mapped_column(String(255))
    review_state: Mapped[str] = mapped_column(String(40), nullable=False)
    supersedes_version_id: Mapped[str | None] = mapped_column(String(36))
    independence_group: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    preserved_artifact_path: Mapped[str | None] = mapped_column(Text)
    parent_record_sha256: Mapped[str | None] = mapped_column(String(64))
    record_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class LabSourceDerivationLink(LabRecord):
    __tablename__ = "lab_source_derivation_links"
    __table_args__ = (
        UniqueConstraint(
            "child_source_version_id",
            "parent_source_version_id",
            "relation",
            name="uq_lab_source_derivation_link",
        ),
        UniqueConstraint(
            "record_sha256",
            name="uq_lab_source_derivation_record_sha256",
        ),
        CheckConstraint(
            f"relation IN ({_quoted(SOURCE_DERIVATION_RELATIONS)})",
            name="ck_lab_source_derivation_relation",
        ),
        CheckConstraint(
            "child_source_version_id <> parent_source_version_id",
            name="ck_lab_source_derivation_not_self",
        ),
        CheckConstraint(
            "length(record_sha256) = 64",
            name="ck_lab_source_derivation_record_sha256",
        ),
        ForeignKeyConstraint(
            ["child_source_version_id"],
            ["lab_source_document_versions.id"],
            ondelete="RESTRICT",
            name="fk_lab_source_derivation_child",
        ),
        ForeignKeyConstraint(
            ["parent_source_version_id"],
            ["lab_source_document_versions.id"],
            ondelete="RESTRICT",
            name="fk_lab_source_derivation_parent",
        ),
    )

    child_source_version_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )
    parent_source_version_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )
    relation: Mapped[str] = mapped_column(String(40), nullable=False)
    record_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class LabSourceExtractionRecord(LabRecord):
    __tablename__ = "lab_source_extraction_records"
    __table_args__ = (
        UniqueConstraint(
            "record_sha256",
            name="uq_lab_source_extraction_record_sha256",
        ),
        CheckConstraint(
            "length(input_sha256) = 64",
            name="ck_lab_source_extraction_input_sha256",
        ),
        CheckConstraint(
            "length(output_sha256) = 64",
            name="ck_lab_source_extraction_output_sha256",
        ),
        CheckConstraint(
            "length(record_sha256) = 64",
            name="ck_lab_source_extraction_record_sha256",
        ),
        ForeignKeyConstraint(
            ["source_version_id"],
            ["lab_source_document_versions.id"],
            ondelete="RESTRICT",
            name="fk_lab_source_extraction_source",
        ),
    )

    source_version_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )
    locator_json: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        server_default=text("'{}'"),
        nullable=False,
    )
    structure_context_json: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        server_default=text("'{}'"),
        nullable=False,
    )
    original_wording: Mapped[str | None] = mapped_column(Text)
    original_value_json: Mapped[dict | None] = mapped_column(JSON)
    parsed_value_json: Mapped[dict | None] = mapped_column(JSON)
    normalization_json: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        server_default=text("'{}'"),
        nullable=False,
    )
    parser_or_model_version: Mapped[str] = mapped_column(Text, nullable=False)
    reviewer_pseudonym: Mapped[str | None] = mapped_column(String(255))
    uncertainty_json: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        server_default=text("'{}'"),
        nullable=False,
    )
    ambiguity_json: Mapped[list] = mapped_column(
        JSON,
        default=list,
        server_default=text("'[]'"),
        nullable=False,
    )
    output_observation_id: Mapped[str | None] = mapped_column(
        String(36),
        index=True,
    )
    input_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    output_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    record_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class LabEvidenceWorkflowEvent(LabRecord):
    __tablename__ = "lab_evidence_workflow_events"
    __table_args__ = (
        UniqueConstraint(
            "subject_type",
            "subject_id",
            "sequence_number",
            name="uq_lab_evidence_workflow_sequence",
        ),
        UniqueConstraint(
            "record_sha256",
            name="uq_lab_evidence_workflow_record_sha256",
        ),
        CheckConstraint(
            "sequence_number >= 1",
            name="ck_lab_evidence_workflow_sequence_positive",
        ),
        CheckConstraint(
            f"subject_type IN ({_quoted(WORKFLOW_SUBJECT_TYPES)})",
            name="ck_lab_evidence_workflow_subject_type",
        ),
        CheckConstraint(
            f"from_state IS NULL OR from_state IN "
            f"({_quoted(EVIDENCE_WORKFLOW_STATES)})",
            name="ck_lab_evidence_workflow_from_state",
        ),
        CheckConstraint(
            f"to_state IN ({_quoted(EVIDENCE_WORKFLOW_STATES)})",
            name="ck_lab_evidence_workflow_to_state",
        ),
        CheckConstraint(
            "from_state IS NULL OR from_state <> to_state",
            name="ck_lab_evidence_workflow_transition_changes_state",
        ),
        CheckConstraint(
            "length(record_sha256) = 64",
            name="ck_lab_evidence_workflow_record_sha256",
        ),
        CheckConstraint(
            "(sequence_number = 1 AND from_state IS NULL "
            "AND to_state = 'STAGED') OR "
            "(sequence_number > 1 AND from_state IS NOT NULL)",
            name="ck_lab_evidence_workflow_initial_state",
        ),
    )

    subject_type: Mapped[str] = mapped_column(String(40), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(36), nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    from_state: Mapped[str | None] = mapped_column(String(40))
    to_state: Mapped[str] = mapped_column(String(40), nullable=False)
    reviewer_pseudonym: Mapped[str | None] = mapped_column(String(255))
    scope_json: Mapped[list] = mapped_column(
        JSON,
        default=list,
        server_default=text("'[]'"),
        nullable=False,
    )
    reason: Mapped[str | None] = mapped_column(Text)
    record_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


SOURCE_AUTHORITY_TABLE_NAMES = {
    "lab_source_document_versions",
    "lab_source_derivation_links",
    "lab_source_extraction_records",
    "lab_evidence_workflow_events",
}

__all__ = [
    "EVIDENCE_WORKFLOW_STATES",
    "SOURCE_AUTHORITY_TABLE_NAMES",
    "SOURCE_DERIVATION_RELATIONS",
    "SOURCE_REVIEW_STATES",
    "SOURCE_TYPES",
    "WORKFLOW_SUBJECT_TYPES",
    "LabEvidenceWorkflowEvent",
    "LabSourceDerivationLink",
    "LabSourceDocumentVersion",
    "LabSourceExtractionRecord",
]
