"""Append-only B7 claim-specific scientific authority."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.lab import LabRecord, UTCDateTime

CLAIM_AUTHORITY_TYPES = (
    "EXACT_CHEMICAL_IDENTITY",
    "GRADE_IDENTITY",
    "PROPERTY_VALUE",
    "THRESHOLD",
    "ABOVE_THRESHOLD_SCREENING",
    "ANALYTICAL_IDENTIFICATION",
    "ANALYTICAL_QUANTITATION",
    "NATURAL_CONSTITUENT_PROFILE",
    "KNOWLEDGE_RULE_RECOMMENDATION",
    "REGULATORY_SCREENING",
    "FORMULA_OR_MODEL_COMPARISON",
)
CLAIM_AUTHORITY_DECISIONS = (
    "ALLOW_EXACT",
    "ALLOW_SCOPED",
    "ADVISORY_ONLY",
    "WITHHOLD_UNKNOWN",
    "BLOCK",
)
CLAIM_AUTHORITY_SUPPORT_ROLES = (
    "SUPPORTING",
    "CONTRADICTING",
    "LIMITATION",
)
CLAIM_AUTHORITY_SUPPORT_KINDS = (
    "PROPERTY_ASSERTION",
    "OAV_ASSESSMENT",
    "KNOWLEDGE_RULE",
    "ANALYTICAL_ASSESSMENT",
    "COMPOSITION_PROFILE",
    "REGULATORY_SNAPSHOT",
)
CLAIM_DIMENSION_STATES = (
    "PASS",
    "FAIL",
    "UNKNOWN",
    "NOT_APPLICABLE",
)


def _quoted(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


class LabClaimAuthorityVersion(LabRecord):
    __tablename__ = "lab_claim_authority_versions"
    __table_args__ = (
        UniqueConstraint(
            "authority_id",
            "version_number",
            name="uq_lab_claim_authority_version",
        ),
        UniqueConstraint(
            "parent_version_id",
            name="uq_lab_claim_authority_parent",
        ),
        UniqueConstraint(
            "content_sha256",
            name="uq_lab_claim_authority_content_sha256",
        ),
        CheckConstraint(
            "version_number >= 1",
            name="ck_lab_claim_authority_version_positive",
        ),
        CheckConstraint(
            "(version_number = 1 AND parent_version_id IS NULL "
            "AND parent_sha256 IS NULL) OR "
            "(version_number > 1 AND parent_version_id IS NOT NULL "
            "AND length(parent_sha256) = 64)",
            name="ck_lab_claim_authority_version_chain",
        ),
        CheckConstraint(
            f"claim_type IN ({_quoted(CLAIM_AUTHORITY_TYPES)})",
            name="ck_lab_claim_authority_type",
        ),
        CheckConstraint(
            f"decision IN ({_quoted(CLAIM_AUTHORITY_DECISIONS)})",
            name="ck_lab_claim_authority_decision",
        ),
        CheckConstraint(
            "blocker_count >= 0 AND conflict_count >= 0 "
            "AND missing_requirement_count >= 0 "
            "AND critical_unknown_count >= 0 AND support_count >= 0 "
            "AND source_reference_count >= 0",
            name="ck_lab_claim_authority_counts",
        ),
        CheckConstraint(
            "decision <> 'ALLOW_EXACT' OR ("
            "blocker_count = 0 AND conflict_count = 0 "
            "AND missing_requirement_count = 0 "
            "AND critical_unknown_count = 0 AND support_count >= 1 "
            "AND source_reference_count >= 1 "
            "AND length(trim(permitted_wording)) > 0)",
            name="ck_lab_claim_authority_exact_shape",
        ),
        CheckConstraint(
            "decision <> 'ALLOW_SCOPED' OR ("
            "blocker_count = 0 AND conflict_count = 0 "
            "AND critical_unknown_count = 0 AND support_count >= 1 "
            "AND length(trim(permitted_wording)) > 0)",
            name="ck_lab_claim_authority_scoped_shape",
        ),
        CheckConstraint(
            "decision <> 'WITHHOLD_UNKNOWN' OR ("
            "missing_requirement_count > 0 OR critical_unknown_count > 0)",
            name="ck_lab_claim_authority_withheld_shape",
        ),
        CheckConstraint(
            "decision <> 'BLOCK' OR blocker_count > 0",
            name="ck_lab_claim_authority_block_shape",
        ),
        CheckConstraint(
            "release_authority = 0",
            name="ck_lab_claim_authority_no_release",
        ),
        CheckConstraint(
            "length(trim(reviewer_pseudonym)) > 0 AND reviewed_at IS NOT NULL",
            name="ck_lab_claim_authority_review",
        ),
        CheckConstraint(
            "length(policy_sha256) = 64",
            name="ck_lab_claim_authority_policy_sha256",
        ),
        CheckConstraint(
            "length(identity_scope_sha256) = 64",
            name="ck_lab_claim_authority_identity_sha256",
        ),
        CheckConstraint(
            "length(condition_scope_sha256) = 64",
            name="ck_lab_claim_authority_condition_sha256",
        ),
        CheckConstraint(
            "length(claim_scope_sha256) = 64",
            name="ck_lab_claim_authority_scope_sha256",
        ),
        CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_claim_authority_content_sha256",
        ),
        CheckConstraint(
            "parent_sha256 IS NULL OR length(parent_sha256) = 64",
            name="ck_lab_claim_authority_parent_sha256",
        ),
        ForeignKeyConstraint(
            ["legacy_claim_assessment_version_id"],
            ["lab_claim_assessment_versions.id"],
            name="fk_lab_claim_authority_legacy_assessment",
            ondelete="RESTRICT",
        ),
        Index(
            "ix_lab_claim_authority_claim_scope",
            "claim_type",
            "claim_scope_sha256",
            "decision",
        ),
        Index(
            "ix_lab_claim_authority_subject",
            "subject_type",
            "subject_id",
        ),
    )

    authority_id: Mapped[str] = mapped_column(String(36), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_version_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "lab_claim_authority_versions.id",
            ondelete="RESTRICT",
        )
    )
    legacy_claim_assessment_version_id: Mapped[str] = mapped_column(
        String(36), nullable=False
    )
    schema_version: Mapped[str] = mapped_column(String(80), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(100), nullable=False)
    policy_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    policy_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    claim_type: Mapped[str] = mapped_column(String(80), nullable=False)
    subject_type: Mapped[str] = mapped_column(String(40), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(36), nullable=False)
    claim_payload_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    identity_scope_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    identity_scope_sha256: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    condition_scope_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    condition_scope_sha256: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    claim_scope_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    decision: Mapped[str] = mapped_column(String(40), nullable=False)
    dimension_results_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    supporting_observations_json: Mapped[list] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    conflicts_json: Mapped[list] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    missing_requirements_json: Mapped[list] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    source_references_json: Mapped[list] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    uncertainty_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    permitted_wording: Mapped[str] = mapped_column(Text, nullable=False)
    forbidden_wording: Mapped[str] = mapped_column(Text, nullable=False)
    blocker_count: Mapped[int] = mapped_column(Integer, nullable=False)
    conflict_count: Mapped[int] = mapped_column(Integer, nullable=False)
    missing_requirement_count: Mapped[int] = mapped_column(
        Integer, nullable=False
    )
    critical_unknown_count: Mapped[int] = mapped_column(
        Integer, nullable=False
    )
    support_count: Mapped[int] = mapped_column(Integer, nullable=False)
    source_reference_count: Mapped[int] = mapped_column(Integer, nullable=False)
    release_authority: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("0"),
        nullable=False,
    )
    upstream_hashes_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    reviewer_pseudonym: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    reviewed_at: Mapped[datetime] = mapped_column(
        UTCDateTime(timezone=True), nullable=False
    )
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    parent_sha256: Mapped[str | None] = mapped_column(String(64))


class LabClaimAuthoritySupportLink(LabRecord):
    __tablename__ = "lab_claim_authority_support_links"
    __table_args__ = (
        UniqueConstraint(
            "content_sha256",
            name="uq_lab_claim_authority_support_content_sha256",
        ),
        CheckConstraint(
            f"support_kind IN ({_quoted(CLAIM_AUTHORITY_SUPPORT_KINDS)})",
            name="ck_lab_claim_authority_support_kind",
        ),
        CheckConstraint(
            f"role IN ({_quoted(CLAIM_AUTHORITY_SUPPORT_ROLES)})",
            name="ck_lab_claim_authority_support_role",
        ),
        CheckConstraint(
            "("
            "(support_kind = 'PROPERTY_ASSERTION' "
            "AND property_assertion_id IS NOT NULL "
            "AND oav_assessment_id IS NULL "
            "AND knowledge_rule_id IS NULL "
            "AND analytical_assessment_id IS NULL "
            "AND composition_profile_id IS NULL "
            "AND regulatory_snapshot_version_id IS NULL) OR "
            "(support_kind = 'OAV_ASSESSMENT' "
            "AND property_assertion_id IS NULL "
            "AND oav_assessment_id IS NOT NULL "
            "AND knowledge_rule_id IS NULL "
            "AND analytical_assessment_id IS NULL "
            "AND composition_profile_id IS NULL "
            "AND regulatory_snapshot_version_id IS NULL) OR "
            "(support_kind = 'KNOWLEDGE_RULE' "
            "AND property_assertion_id IS NULL "
            "AND oav_assessment_id IS NULL "
            "AND knowledge_rule_id IS NOT NULL "
            "AND analytical_assessment_id IS NULL "
            "AND composition_profile_id IS NULL "
            "AND regulatory_snapshot_version_id IS NULL) OR "
            "(support_kind = 'ANALYTICAL_ASSESSMENT' "
            "AND property_assertion_id IS NULL "
            "AND oav_assessment_id IS NULL "
            "AND knowledge_rule_id IS NULL "
            "AND analytical_assessment_id IS NOT NULL "
            "AND composition_profile_id IS NULL "
            "AND regulatory_snapshot_version_id IS NULL) OR "
            "(support_kind = 'COMPOSITION_PROFILE' "
            "AND property_assertion_id IS NULL "
            "AND oav_assessment_id IS NULL "
            "AND knowledge_rule_id IS NULL "
            "AND analytical_assessment_id IS NULL "
            "AND composition_profile_id IS NOT NULL "
            "AND regulatory_snapshot_version_id IS NULL) OR "
            "(support_kind = 'REGULATORY_SNAPSHOT' "
            "AND property_assertion_id IS NULL "
            "AND oav_assessment_id IS NULL "
            "AND knowledge_rule_id IS NULL "
            "AND analytical_assessment_id IS NULL "
            "AND composition_profile_id IS NULL "
            "AND regulatory_snapshot_version_id IS NOT NULL)"
            ")",
            name="ck_lab_claim_authority_support_shape",
        ),
        CheckConstraint(
            "length(upstream_content_sha256) = 64",
            name="ck_lab_claim_authority_support_upstream_sha256",
        ),
        CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_claim_authority_support_content_sha256",
        ),
        Index(
            "ix_lab_claim_authority_support_authority",
            "claim_authority_version_id",
        ),
        Index(
            "ix_lab_claim_authority_support_kind",
            "support_kind",
        ),
    )

    claim_authority_version_id: Mapped[str] = mapped_column(
        ForeignKey("lab_claim_authority_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    support_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    role: Mapped[str] = mapped_column(String(40), nullable=False)
    property_assertion_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_selected_assertions.id", ondelete="RESTRICT")
    )
    oav_assessment_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_oav_assessments.id", ondelete="RESTRICT")
    )
    knowledge_rule_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_knowledge_rules.id", ondelete="RESTRICT")
    )
    analytical_assessment_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "lab_analytical_claim_assessments.id",
            ondelete="RESTRICT",
        )
    )
    composition_profile_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "lab_regulatory_composition_profiles.id",
            ondelete="RESTRICT",
        )
    )
    regulatory_snapshot_version_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "lab_regulatory_snapshot_versions.id",
            ondelete="RESTRICT",
        )
    )
    upstream_content_sha256: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    derived_facts_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    source_references_json: Mapped[list] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


CLAIM_AUTHORITY_TABLE_NAMES = {
    LabClaimAuthorityVersion.__tablename__,
    LabClaimAuthoritySupportLink.__tablename__,
}


__all__ = [
    "CLAIM_AUTHORITY_DECISIONS",
    "CLAIM_AUTHORITY_SUPPORT_KINDS",
    "CLAIM_AUTHORITY_SUPPORT_ROLES",
    "CLAIM_AUTHORITY_TABLE_NAMES",
    "CLAIM_AUTHORITY_TYPES",
    "CLAIM_DIMENSION_STATES",
    "LabClaimAuthoritySupportLink",
    "LabClaimAuthorityVersion",
]
