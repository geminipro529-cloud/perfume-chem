"""Append-only B4 knowledge-rule authority and compilation history."""

from __future__ import annotations

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.lab import LabRecord

RULE_ENDPOINT_KINDS = (
    "EXACT_IDENTITY",
    "GROUP",
    "GENERIC_PROSE",
    "UNRESOLVED",
)
RULE_RELATIONS = (
    "REINFORCES",
    "MASKS",
    "SUPPRESSES",
    "SYNERGIZES",
    "ADDS",
    "EXTENDS",
    "BRIDGES",
    "BRIGHTENS",
    "ROUNDS",
    "DRIES",
    "WARMS",
    "COOLS",
    "DIFFUSES",
    "TEMPORALLY_HANDS_OFF",
    "FUNCTIONALLY_SUBSTITUTES",
    "NON_EQUIVALENT",
    "MATRIX_DEPENDENT_INTERACTION",
    "SAFETY_CONTRIBUTION",
)
RULE_DIRECTIONALITIES = ("DIRECTED", "BIDIRECTIONAL", "SYMMETRIC")
RULE_STATUSES = (
    "AUTHORITATIVE",
    "SUPPORTED",
    "ADVISORY",
    "SPECULATIVE",
    "INVALID",
    "SUPERSEDED",
)
RULE_REVIEW_STATES = (
    "UNREVIEWED",
    "IN_REVIEW",
    "APPROVED",
    "REJECTED",
    "SUPERSEDED",
)
RULE_RUNTIME_ROLES = ("EXPLANATORY", "ADVISORY", "BLOCKING")
RULE_SUPPORT_KINDS = (
    "PROPERTY_OBSERVATION",
    "LAB_OBSERVATION",
    "LAB_EXPERIMENT",
    "TEST_ARTIFACT",
    "NUMERICAL_MODEL",
)


def _quoted(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


class LabRuleGroup(LabRecord):
    __tablename__ = "lab_rule_groups"
    __table_args__ = (
        Index("ix_lab_rule_groups_group_key", "group_key"),
        UniqueConstraint(
            "group_key",
            "version",
            name="uq_lab_rule_group_key_version",
        ),
        UniqueConstraint(
            "content_sha256",
            name="uq_lab_rule_group_content_sha256",
        ),
        CheckConstraint(
            "version >= 1",
            name="ck_lab_rule_group_version",
        ),
        CheckConstraint(
            f"status IN ({_quoted(RULE_STATUSES)})",
            name="ck_lab_rule_group_status",
        ),
        CheckConstraint(
            f"review_state IN ({_quoted(RULE_REVIEW_STATES)})",
            name="ck_lab_rule_group_review_state",
        ),
        CheckConstraint(
            "status <> 'AUTHORITATIVE' OR ("
            "source_document_version_id IS NOT NULL "
            "AND source_extraction_id IS NOT NULL "
            "AND source_locator IS NOT NULL "
            "AND length(source_locator) > 0 "
            "AND review_state = 'APPROVED'"
            ")",
            name="ck_lab_rule_group_authority",
        ),
        CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_rule_group_content_sha256",
        ),
        ForeignKeyConstraint(
            ["source_document_version_id"],
            ["lab_source_document_versions.id"],
            ondelete="RESTRICT",
            name="fk_lab_rule_group_source_version",
        ),
        ForeignKeyConstraint(
            ["source_extraction_id"],
            ["lab_source_extraction_records.id"],
            ondelete="RESTRICT",
            name="fk_lab_rule_group_extraction",
        ),
        ForeignKeyConstraint(
            ["supersedes_group_id"],
            ["lab_rule_groups.id"],
            ondelete="RESTRICT",
            name="fk_lab_rule_group_supersedes",
        ),
    )

    group_key: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    definition: Mapped[str] = mapped_column(Text, nullable=False)
    source_document_version_id: Mapped[str | None] = mapped_column(String(36))
    source_extraction_id: Mapped[str | None] = mapped_column(String(36))
    source_locator: Mapped[str | None] = mapped_column(Text)
    review_state: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    supersedes_group_id: Mapped[str | None] = mapped_column(String(36))
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class LabRuleGroupMember(LabRecord):
    __tablename__ = "lab_rule_group_members"
    __table_args__ = (
        Index("ix_lab_rule_group_members_group_id", "group_id"),
        UniqueConstraint(
            "group_id",
            "position",
            name="uq_lab_rule_group_member_position",
        ),
        UniqueConstraint(
            "content_sha256",
            name="uq_lab_rule_group_member_content_sha256",
        ),
        CheckConstraint(
            "position >= 1",
            name="ck_lab_rule_group_member_position",
        ),
        CheckConstraint(
            "("
            "(identity_scope_sha256 IS NOT NULL AND nested_group_id IS NULL) OR "
            "(identity_scope_sha256 IS NULL AND nested_group_id IS NOT NULL)"
            ")",
            name="ck_lab_rule_group_member_shape",
        ),
        CheckConstraint(
            "identity_scope_sha256 IS NULL OR length(identity_scope_sha256) = 64",
            name="ck_lab_rule_group_member_identity_sha256",
        ),
        CheckConstraint(
            "nested_group_id IS NULL OR nested_group_id <> group_id",
            name="ck_lab_rule_group_member_not_self",
        ),
        CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_rule_group_member_content_sha256",
        ),
        ForeignKeyConstraint(
            ["group_id"],
            ["lab_rule_groups.id"],
            ondelete="RESTRICT",
            name="fk_lab_rule_group_member_group",
        ),
        ForeignKeyConstraint(
            ["nested_group_id"],
            ["lab_rule_groups.id"],
            ondelete="RESTRICT",
            name="fk_lab_rule_group_member_nested_group",
        ),
    )

    group_id: Mapped[str] = mapped_column(String(36), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    identity_scope_sha256: Mapped[str | None] = mapped_column(String(64))
    nested_group_id: Mapped[str | None] = mapped_column(String(36))
    member_role: Mapped[str | None] = mapped_column(Text)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


def _endpoint_shape(prefix: str) -> str:
    kind = f"{prefix}_kind"
    identity = f"{prefix}_identity_scope_sha256"
    group = f"{prefix}_group_id"
    label = f"{prefix}_raw_label"
    return (
        "("
        f"({kind} = 'EXACT_IDENTITY' AND {identity} IS NOT NULL "
        f"AND length({identity}) = 64 AND {group} IS NULL "
        f"AND length({label}) > 0) OR "
        f"({kind} = 'GROUP' AND {identity} IS NULL AND {group} IS NOT NULL "
        f"AND length({label}) > 0) OR "
        f"({kind} IN ('GENERIC_PROSE', 'UNRESOLVED') AND {identity} IS NULL "
        f"AND {group} IS NULL AND length({label}) > 0)"
        ")"
    )


class LabKnowledgeRule(LabRecord):
    __tablename__ = "lab_knowledge_rules"
    __table_args__ = (
        Index("ix_lab_knowledge_rules_rule_key", "rule_key"),
        Index("ix_lab_knowledge_rules_status", "status"),
        Index(
            "ix_lab_knowledge_rules_subject_identity",
            "subject_identity_scope_sha256",
        ),
        Index(
            "ix_lab_knowledge_rules_object_identity",
            "object_identity_scope_sha256",
        ),
        UniqueConstraint(
            "rule_key",
            "version",
            name="uq_lab_knowledge_rule_key_version",
        ),
        UniqueConstraint(
            "content_sha256",
            name="uq_lab_knowledge_rule_content_sha256",
        ),
        CheckConstraint(
            "version >= 1",
            name="ck_lab_knowledge_rule_version",
        ),
        CheckConstraint(
            f"subject_kind IN ({_quoted(RULE_ENDPOINT_KINDS)})",
            name="ck_lab_knowledge_rule_subject_kind",
        ),
        CheckConstraint(
            f"object_kind IN ({_quoted(RULE_ENDPOINT_KINDS)})",
            name="ck_lab_knowledge_rule_object_kind",
        ),
        CheckConstraint(
            _endpoint_shape("subject"),
            name="ck_lab_knowledge_rule_subject_shape",
        ),
        CheckConstraint(
            _endpoint_shape("object"),
            name="ck_lab_knowledge_rule_object_shape",
        ),
        CheckConstraint(
            f"relation IN ({_quoted(RULE_RELATIONS)})",
            name="ck_lab_knowledge_rule_relation",
        ),
        CheckConstraint(
            f"directionality IN ({_quoted(RULE_DIRECTIONALITIES)})",
            name="ck_lab_knowledge_rule_directionality",
        ),
        CheckConstraint(
            f"status IN ({_quoted(RULE_STATUSES)})",
            name="ck_lab_knowledge_rule_status",
        ),
        CheckConstraint(
            f"review_state IN ({_quoted(RULE_REVIEW_STATES)})",
            name="ck_lab_knowledge_rule_review_state",
        ),
        CheckConstraint(
            "status <> 'AUTHORITATIVE' OR ("
            "source_document_version_id IS NOT NULL "
            "AND source_extraction_id IS NOT NULL "
            "AND length(source_locator) > 0 "
            "AND review_state = 'APPROVED'"
            ")",
            name="ck_lab_knowledge_rule_authority_scope",
        ),
        CheckConstraint(
            f"runtime_role IN ({_quoted(RULE_RUNTIME_ROLES)})",
            name="ck_lab_knowledge_rule_runtime_role",
        ),
        CheckConstraint(
            "runtime_role <> 'BLOCKING' OR status = 'AUTHORITATIVE'",
            name="ck_lab_knowledge_rule_blocking_authority",
        ),
        CheckConstraint(
            "("
            "subject_kind NOT IN ('GENERIC_PROSE', 'UNRESOLVED') "
            "AND object_kind NOT IN ('GENERIC_PROSE', 'UNRESOLVED')"
            ") OR (runtime_role <> 'BLOCKING' AND status <> 'AUTHORITATIVE' "
            "AND numerical_model_ref IS NULL)",
            name="ck_lab_knowledge_rule_generic_nonblocking",
        ),
        CheckConstraint(
            "length(raw_source_path) > 0 AND length(raw_json_pointer) > 0",
            name="ck_lab_knowledge_rule_raw_locator",
        ),
        CheckConstraint(
            "length(raw_payload_sha256) = 64",
            name="ck_lab_knowledge_rule_payload_sha256",
        ),
        CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_knowledge_rule_content_sha256",
        ),
        ForeignKeyConstraint(
            ["subject_group_id"],
            ["lab_rule_groups.id"],
            ondelete="RESTRICT",
            name="fk_lab_knowledge_rule_subject_group",
        ),
        ForeignKeyConstraint(
            ["object_group_id"],
            ["lab_rule_groups.id"],
            ondelete="RESTRICT",
            name="fk_lab_knowledge_rule_object_group",
        ),
        ForeignKeyConstraint(
            ["source_document_version_id"],
            ["lab_source_document_versions.id"],
            ondelete="RESTRICT",
            name="fk_lab_knowledge_rule_source_version",
        ),
        ForeignKeyConstraint(
            ["source_extraction_id"],
            ["lab_source_extraction_records.id"],
            ondelete="RESTRICT",
            name="fk_lab_knowledge_rule_extraction",
        ),
        ForeignKeyConstraint(
            ["supersedes_rule_id"],
            ["lab_knowledge_rules.id"],
            ondelete="RESTRICT",
            name="fk_lab_knowledge_rule_supersedes",
        ),
    )

    rule_key: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    subject_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    subject_raw_label: Mapped[str] = mapped_column(Text, nullable=False)
    subject_identity_scope_sha256: Mapped[str | None] = mapped_column(String(64))
    subject_group_id: Mapped[str | None] = mapped_column(String(36))
    relation: Mapped[str] = mapped_column(String(60), nullable=False)
    object_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    object_raw_label: Mapped[str] = mapped_column(Text, nullable=False)
    object_identity_scope_sha256: Mapped[str | None] = mapped_column(String(64))
    object_group_id: Mapped[str | None] = mapped_column(String(36))
    directionality: Mapped[str] = mapped_column(String(40), nullable=False)
    matrix_context_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    dose_domain_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    temporal_domain_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    expected_effect_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    attribute: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    source_document_version_id: Mapped[str | None] = mapped_column(String(36))
    source_extraction_id: Mapped[str | None] = mapped_column(String(36))
    source_locator: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_class: Mapped[str] = mapped_column(String(80), nullable=False)
    uncertainty_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    review_state: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    runtime_role: Mapped[str] = mapped_column(String(40), nullable=False)
    numerical_model_ref: Mapped[str | None] = mapped_column(Text)
    supersedes_rule_id: Mapped[str | None] = mapped_column(String(36))
    raw_source_path: Mapped[str] = mapped_column(Text, nullable=False)
    raw_json_pointer: Mapped[str] = mapped_column(Text, nullable=False)
    raw_payload_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    compiler_diagnostics_json: Mapped[list] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class LabRuleContradiction(LabRecord):
    __tablename__ = "lab_rule_contradictions"
    __table_args__ = (
        Index("ix_lab_rule_contradictions_rule_id", "rule_id"),
        UniqueConstraint(
            "rule_id",
            "contradictory_rule_id",
            "reason_code",
            name="uq_lab_rule_contradiction_pair_reason",
        ),
        UniqueConstraint(
            "content_sha256",
            name="uq_lab_rule_contradiction_content_sha256",
        ),
        CheckConstraint(
            "rule_id <> contradictory_rule_id",
            name="ck_lab_rule_contradiction_distinct",
        ),
        CheckConstraint(
            "rule_id < contradictory_rule_id",
            name="ck_lab_rule_contradiction_ordered",
        ),
        CheckConstraint(
            "length(reason_code) > 0",
            name="ck_lab_rule_contradiction_reason",
        ),
        CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_rule_contradiction_content_sha256",
        ),
        ForeignKeyConstraint(
            ["rule_id"],
            ["lab_knowledge_rules.id"],
            ondelete="RESTRICT",
            name="fk_lab_rule_contradiction_rule",
        ),
        ForeignKeyConstraint(
            ["contradictory_rule_id"],
            ["lab_knowledge_rules.id"],
            ondelete="RESTRICT",
            name="fk_lab_rule_contradiction_other_rule",
        ),
    )

    rule_id: Mapped[str] = mapped_column(String(36), nullable=False)
    contradictory_rule_id: Mapped[str] = mapped_column(String(36), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(80), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    blocking: Mapped[bool] = mapped_column(Boolean, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class LabRuleSupportEvidence(LabRecord):
    __tablename__ = "lab_rule_support_evidence"
    __table_args__ = (
        Index("ix_lab_rule_support_evidence_rule_id", "rule_id"),
        UniqueConstraint(
            "content_sha256",
            name="uq_lab_rule_support_content_sha256",
        ),
        CheckConstraint(
            f"support_kind IN ({_quoted(RULE_SUPPORT_KINDS)})",
            name="ck_lab_rule_support_kind",
        ),
        CheckConstraint(
            "length(reference_id) > 0",
            name="ck_lab_rule_support_reference",
        ),
        CheckConstraint(
            "("
            "(matrix_context_sha256 IS NULL AND dose_domain_sha256 IS NULL) OR "
            "(length(matrix_context_sha256) = 64 AND length(dose_domain_sha256) = 64)"
            ")",
            name="ck_lab_rule_support_context_hashes",
        ),
        CheckConstraint(
            f"review_state IN ({_quoted(RULE_REVIEW_STATES)})",
            name="ck_lab_rule_support_review_state",
        ),
        CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_rule_support_content_sha256",
        ),
        ForeignKeyConstraint(
            ["rule_id"],
            ["lab_knowledge_rules.id"],
            ondelete="RESTRICT",
            name="fk_lab_rule_support_rule",
        ),
    )

    rule_id: Mapped[str] = mapped_column(String(36), nullable=False)
    support_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    reference_id: Mapped[str] = mapped_column(Text, nullable=False)
    controlled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    matrix_context_sha256: Mapped[str | None] = mapped_column(String(64))
    dose_domain_sha256: Mapped[str | None] = mapped_column(String(64))
    uncertainty_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    review_state: Mapped[str] = mapped_column(String(40), nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class LabRuleCompilationRun(LabRecord):
    __tablename__ = "lab_rule_compilation_runs"
    __table_args__ = (
        Index(
            "ix_lab_rule_compilation_runs_source_corpus_sha256",
            "source_corpus_sha256",
        ),
        UniqueConstraint(
            "content_sha256",
            name="uq_lab_rule_compilation_content_sha256",
        ),
        CheckConstraint(
            "source_record_count >= 0 AND compiled_rule_count >= 0 "
            "AND invalid_exact_count >= 0 AND duplicate_count >= 0 "
            "AND contradiction_count >= 0 AND cycle_count >= 0 "
            "AND orphan_count >= 0 AND generic_count >= 0",
            name="ck_lab_rule_compilation_counts",
        ),
        CheckConstraint(
            "baseline_invalid_exact_count >= 0 AND "
            "(passed = 0 OR invalid_exact_count <= baseline_invalid_exact_count)",
            name="ck_lab_rule_compilation_baseline",
        ),
        CheckConstraint(
            "length(source_corpus_sha256) = 64 "
            "AND length(report_sha256) = 64 "
            "AND length(content_sha256) = 64",
            name="ck_lab_rule_compilation_hashes",
        ),
    )

    compiler_version: Mapped[str] = mapped_column(String(80), nullable=False)
    source_manifest_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    source_corpus_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    source_record_count: Mapped[int] = mapped_column(Integer, nullable=False)
    compiled_rule_count: Mapped[int] = mapped_column(Integer, nullable=False)
    invalid_exact_count: Mapped[int] = mapped_column(Integer, nullable=False)
    duplicate_count: Mapped[int] = mapped_column(Integer, nullable=False)
    contradiction_count: Mapped[int] = mapped_column(Integer, nullable=False)
    cycle_count: Mapped[int] = mapped_column(Integer, nullable=False)
    orphan_count: Mapped[int] = mapped_column(Integer, nullable=False)
    generic_count: Mapped[int] = mapped_column(Integer, nullable=False)
    baseline_invalid_exact_count: Mapped[int] = mapped_column(Integer, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    report_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


RULE_AUTHORITY_TABLE_NAMES: set[str] = {
    LabRuleGroup.__tablename__,
    LabRuleGroupMember.__tablename__,
    LabKnowledgeRule.__tablename__,
    LabRuleContradiction.__tablename__,
    LabRuleSupportEvidence.__tablename__,
    LabRuleCompilationRun.__tablename__,
}


__all__ = [
    "RULE_AUTHORITY_TABLE_NAMES",
    "RULE_DIRECTIONALITIES",
    "RULE_ENDPOINT_KINDS",
    "RULE_RELATIONS",
    "RULE_REVIEW_STATES",
    "RULE_RUNTIME_ROLES",
    "RULE_STATUSES",
    "RULE_SUPPORT_KINDS",
    "LabKnowledgeRule",
    "LabRuleCompilationRun",
    "LabRuleContradiction",
    "LabRuleGroup",
    "LabRuleGroupMember",
    "LabRuleSupportEvidence",
]
