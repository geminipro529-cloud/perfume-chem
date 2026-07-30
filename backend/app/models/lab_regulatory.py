"""Append-only B6 safety and regulatory screening authority."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    Float,
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

REGULATORY_SOURCE_STATUSES = (
    "CURRENT_ENFORCED_OR_FORMALLY_NOTIFIED",
    "FUTURE_EFFECTIVE",
    "DRAFT",
    "CONSULTATION",
    "WATCHLIST",
    "SUPERSEDED",
)
REGULATORY_RESULT_STATES = (
    "PASS_FOR_DECLARED_SCOPE",
    "FAIL",
    "UNKNOWN",
    "NOT_EVALUATED",
)
REGULATORY_AUTHORITY_FAMILIES = (
    "IFRA_STANDARD",
    "JURISDICTIONAL_LEGISLATION",
    "OFFICIAL_GUIDANCE",
)
REGULATORY_RULE_FAMILIES = (
    "IFRA_RESTRICTION",
    "LEGAL_RESTRICTION",
    "ALLERGEN_LABELING",
)
REGULATORY_RULE_KINDS = (
    "MAXIMUM_FINISHED_FRACTION",
    "DECLARATION_THRESHOLD",
)
SUPPLIER_DOCUMENT_SCOPES = ("SUPPLIER_PRODUCT", "SUPPLIER_LOT")
SUPPLIER_REGULATORY_DOCUMENT_TYPES = (
    "SUPPLIER_COA",
    "SUPPLIER_SPECIFICATION",
    "SUPPLIER_SDS",
    "SUPPLIER_IFRA_CERTIFICATE",
    "SUPPLIER_ALLERGEN_DECLARATION",
)
REGULATORY_COMPOSITION_ORIGINS = ("SYNTHETIC", "NATURAL", "TRADE_GRADE")
REGULATORY_COMPOSITION_BASES = (
    "LOT_SPECIFIC",
    "DOCUMENTED_PROXY",
    "UNKNOWN",
)
REGULATORY_COMPOSITION_COMPLETENESS = ("COMPLETE", "PARTIAL", "UNKNOWN")
REGULATORY_SUBJECT_TYPES = ("FORMULA_VERSION", "BUILD_PLAN_VERSION")
REGULATORY_MARKET_ACTIONS = (
    "PLACE_ON_MARKET",
    "MAKE_AVAILABLE",
    "INTERNAL_SCREENING",
)


def _quoted(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


class LabRegulatorySourceVersion(LabRecord):
    __tablename__ = "lab_regulatory_source_versions"
    __table_args__ = (
        UniqueConstraint(
            "authority_id",
            "revision_number",
            name="uq_lab_regulatory_source_version",
        ),
        UniqueConstraint(
            "content_sha256",
            name="uq_lab_regulatory_source_content_sha256",
        ),
        CheckConstraint(
            "revision_number >= 1",
            name="ck_lab_regulatory_source_version_positive",
        ),
        CheckConstraint(
            f"authority_family IN ({_quoted(REGULATORY_AUTHORITY_FAMILIES)})",
            name="ck_lab_regulatory_source_family",
        ),
        CheckConstraint(
            f"status IN ({_quoted(REGULATORY_SOURCE_STATUSES)})",
            name="ck_lab_regulatory_source_status",
        ),
        CheckConstraint(
            "effective_through IS NULL OR effective_from IS NULL "
            "OR effective_through >= effective_from",
            name="ck_lab_regulatory_source_date_range",
        ),
        CheckConstraint(
            "length(official_source_sha256) = 64",
            name="ck_lab_regulatory_source_official_sha256",
        ),
        CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_regulatory_source_content_sha256",
        ),
        CheckConstraint(
            "(revision_number = 1 AND parent_version_id IS NULL) OR "
            "(revision_number > 1 AND parent_version_id IS NOT NULL)",
            name="ck_lab_regulatory_source_version_chain",
        ),
        Index(
            "ix_lab_regulatory_source_authority_status",
            "authority_id",
            "status",
        ),
    )

    authority_id: Mapped[str] = mapped_column(String(36), nullable=False)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_regulatory_source_versions.id", ondelete="RESTRICT")
    )
    schema_version: Mapped[str] = mapped_column(String(80), nullable=False)
    authority_family: Mapped[str] = mapped_column(String(60), nullable=False)
    identifier: Mapped[str] = mapped_column(Text, nullable=False)
    published_version: Mapped[str] = mapped_column(String(100), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(60), nullable=False)
    notified_on: Mapped[date | None] = mapped_column(Date)
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_through: Mapped[date | None] = mapped_column(Date)
    checked_at: Mapped[datetime] = mapped_column(
        UTCDateTime(timezone=True), nullable=False
    )
    supersedes_source_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_regulatory_source_versions.id", ondelete="RESTRICT")
    )
    official_source_document_version_id: Mapped[str] = mapped_column(
        ForeignKey("lab_source_document_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_locator_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    official_source_sha256: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    notes_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class LabRegulatoryRuleVersion(LabRecord):
    __tablename__ = "lab_regulatory_rule_versions"
    __table_args__ = (
        UniqueConstraint(
            "rule_id",
            "revision_number",
            name="uq_lab_regulatory_rule_version",
        ),
        UniqueConstraint(
            "content_sha256",
            name="uq_lab_regulatory_rule_content_sha256",
        ),
        CheckConstraint(
            "revision_number >= 1",
            name="ck_lab_regulatory_rule_version_positive",
        ),
        CheckConstraint(
            "(revision_number = 1 AND parent_version_id IS NULL) OR "
            "(revision_number > 1 AND parent_version_id IS NOT NULL)",
            name="ck_lab_regulatory_rule_version_chain",
        ),
        CheckConstraint(
            f"rule_family IN ({_quoted(REGULATORY_RULE_FAMILIES)})",
            name="ck_lab_regulatory_rule_family",
        ),
        CheckConstraint(
            f"rule_kind IN ({_quoted(REGULATORY_RULE_KINDS)})",
            name="ck_lab_regulatory_rule_kind",
        ),
        CheckConstraint(
            "(rule_kind = 'MAXIMUM_FINISHED_FRACTION' "
            "AND maximum_fraction IS NOT NULL "
            "AND threshold_fraction IS NULL "
            "AND declaration_wording IS NULL) OR "
            "(rule_kind = 'DECLARATION_THRESHOLD' "
            "AND threshold_fraction IS NOT NULL "
            "AND maximum_fraction IS NULL "
            "AND length(trim(declaration_wording)) > 0)",
            name="ck_lab_regulatory_rule_shape",
        ),
        CheckConstraint(
            "(threshold_fraction IS NULL OR "
            "(threshold_fraction >= 0 AND threshold_fraction <= 1)) AND "
            "(maximum_fraction IS NULL OR "
            "(maximum_fraction >= 0 AND maximum_fraction <= 1))",
            name="ck_lab_regulatory_rule_fraction",
        ),
        CheckConstraint(
            "effective_through IS NULL OR effective_from IS NULL "
            "OR effective_through >= effective_from",
            name="ck_lab_regulatory_rule_date_range",
        ),
        CheckConstraint(
            "placement_transition_end IS NULL "
            "OR availability_transition_end IS NULL "
            "OR availability_transition_end >= placement_transition_end",
            name="ck_lab_regulatory_rule_transition_order",
        ),
        CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_regulatory_rule_content_sha256",
        ),
        Index(
            "ix_lab_regulatory_rule_source_family",
            "regulatory_source_version_id",
            "rule_family",
        ),
    )

    rule_id: Mapped[str] = mapped_column(String(36), nullable=False)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_regulatory_rule_versions.id", ondelete="RESTRICT")
    )
    schema_version: Mapped[str] = mapped_column(String(80), nullable=False)
    regulatory_source_version_id: Mapped[str] = mapped_column(
        ForeignKey("lab_regulatory_source_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    rule_family: Mapped[str] = mapped_column(String(50), nullable=False)
    rule_identifier: Mapped[str] = mapped_column(Text, nullable=False)
    material_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_materials.id", ondelete="RESTRICT")
    )
    substance_name: Mapped[str] = mapped_column(Text, nullable=False)
    cas_number: Mapped[str | None] = mapped_column(String(50))
    jurisdiction: Mapped[str] = mapped_column(String(100), nullable=False)
    product_category: Mapped[str] = mapped_column(String(100), nullable=False)
    use_classification: Mapped[str] = mapped_column(String(80), nullable=False)
    concentration_basis: Mapped[str] = mapped_column(
        String(80), nullable=False
    )
    rule_kind: Mapped[str] = mapped_column(String(50), nullable=False)
    threshold_fraction: Mapped[float | None] = mapped_column(Float)
    maximum_fraction: Mapped[float | None] = mapped_column(Float)
    declaration_wording: Mapped[str | None] = mapped_column(Text)
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_through: Mapped[date | None] = mapped_column(Date)
    placement_transition_end: Mapped[date | None] = mapped_column(Date)
    availability_transition_end: Mapped[date | None] = mapped_column(Date)
    transition_conditions_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    assumptions_json: Mapped[list] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class LabSupplierDocumentBinding(LabRecord):
    __tablename__ = "lab_supplier_document_bindings"
    __table_args__ = (
        UniqueConstraint(
            "content_sha256",
            name="uq_lab_supplier_document_binding_content_sha256",
        ),
        CheckConstraint(
            f"scope IN ({_quoted(SUPPLIER_DOCUMENT_SCOPES)})",
            name="ck_lab_supplier_document_scope",
        ),
        CheckConstraint(
            "(scope = 'SUPPLIER_PRODUCT' AND lot_number IS NULL) OR "
            "(scope = 'SUPPLIER_LOT' AND length(trim(lot_number)) > 0)",
            name="ck_lab_supplier_document_scope_shape",
        ),
        CheckConstraint(
            f"document_type IN "
            f"({_quoted(SUPPLIER_REGULATORY_DOCUMENT_TYPES)})",
            name="ck_lab_supplier_document_type",
        ),
        CheckConstraint(
            "expires_on IS NULL OR expires_on >= effective_on",
            name="ck_lab_supplier_document_date_range",
        ),
        CheckConstraint(
            "length(source_artifact_sha256) = 64",
            name="ck_lab_supplier_document_source_sha256",
        ),
        CheckConstraint(
            "length(supplier_identity_sha256) = 64",
            name="ck_lab_supplier_document_identity_sha256",
        ),
        CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_supplier_document_content_sha256",
        ),
        Index(
            "ix_lab_supplier_document_stock_type",
            "stock_solution_id",
            "document_type",
        ),
    )

    stock_solution_id: Mapped[str] = mapped_column(
        ForeignKey("lab_stock_solutions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    scope: Mapped[str] = mapped_column(String(40), nullable=False)
    supplier: Mapped[str] = mapped_column(Text, nullable=False)
    supplier_product: Mapped[str] = mapped_column(Text, nullable=False)
    supplier_product_code: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    grade: Mapped[str] = mapped_column(String(100), nullable=False)
    document_type: Mapped[str] = mapped_column(String(60), nullable=False)
    document_version: Mapped[str] = mapped_column(String(100), nullable=False)
    lot_number: Mapped[str | None] = mapped_column(String(100))
    effective_on: Mapped[date] = mapped_column(Date, nullable=False)
    expires_on: Mapped[date | None] = mapped_column(Date)
    source_document_version_id: Mapped[str] = mapped_column(
        ForeignKey("lab_source_document_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_locator_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    source_artifact_sha256: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    supplier_identity_sha256: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class LabRegulatoryCompositionProfile(LabRecord):
    __tablename__ = "lab_regulatory_composition_profiles"
    __table_args__ = (
        UniqueConstraint(
            "profile_id",
            "version_number",
            name="uq_lab_regulatory_composition_profile_version",
        ),
        UniqueConstraint(
            "content_sha256",
            name="uq_lab_regulatory_composition_profile_content_sha256",
        ),
        CheckConstraint(
            "version_number >= 1",
            name="ck_lab_regulatory_composition_version_positive",
        ),
        CheckConstraint(
            "(version_number = 1 AND parent_version_id IS NULL) OR "
            "(version_number > 1 AND parent_version_id IS NOT NULL)",
            name="ck_lab_regulatory_composition_version_chain",
        ),
        CheckConstraint(
            f"origin IN ({_quoted(REGULATORY_COMPOSITION_ORIGINS)})",
            name="ck_lab_regulatory_composition_origin",
        ),
        CheckConstraint(
            f"composition_basis IN "
            f"({_quoted(REGULATORY_COMPOSITION_BASES)})",
            name="ck_lab_regulatory_composition_basis",
        ),
        CheckConstraint(
            f"completeness IN "
            f"({_quoted(REGULATORY_COMPOSITION_COMPLETENESS)})",
            name="ck_lab_regulatory_composition_completeness",
        ),
        CheckConstraint(
            "(composition_basis = 'UNKNOWN' "
            "AND completeness = 'UNKNOWN' "
            "AND supplier_document_binding_id IS NULL) OR "
            "(composition_basis IN ('LOT_SPECIFIC', 'DOCUMENTED_PROXY') "
            "AND completeness IN ('COMPLETE', 'PARTIAL') "
            "AND supplier_document_binding_id IS NOT NULL)",
            name="ck_lab_regulatory_composition_shape",
        ),
        CheckConstraint(
            "length(trim(reviewer_pseudonym)) > 0 AND reviewed_at IS NOT NULL",
            name="ck_lab_regulatory_composition_review",
        ),
        CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_regulatory_composition_content_sha256",
        ),
        Index(
            "ix_lab_regulatory_composition_stock",
            "stock_solution_id",
            "version_number",
        ),
    )

    profile_id: Mapped[str] = mapped_column(String(36), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_version_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "lab_regulatory_composition_profiles.id",
            ondelete="RESTRICT",
        )
    )
    stock_solution_id: Mapped[str] = mapped_column(
        ForeignKey("lab_stock_solutions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    schema_version: Mapped[str] = mapped_column(String(80), nullable=False)
    origin: Mapped[str] = mapped_column(String(40), nullable=False)
    composition_basis: Mapped[str] = mapped_column(String(40), nullable=False)
    completeness: Mapped[str] = mapped_column(String(40), nullable=False)
    supplier_document_binding_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_supplier_document_bindings.id", ondelete="RESTRICT")
    )
    assumptions_json: Mapped[list] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    limitations_json: Mapped[list] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    reviewer_pseudonym: Mapped[str] = mapped_column(Text, nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(
        UTCDateTime(timezone=True), nullable=False
    )
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class LabRegulatoryCompositionEntry(LabRecord):
    __tablename__ = "lab_regulatory_composition_entries"
    __table_args__ = (
        UniqueConstraint(
            "composition_profile_id",
            "position",
            name="uq_lab_regulatory_composition_entry_position",
        ),
        UniqueConstraint(
            "content_sha256",
            name="uq_lab_regulatory_composition_entry_content_sha256",
        ),
        CheckConstraint(
            "position >= 1",
            name="ck_lab_regulatory_composition_entry_position",
        ),
        CheckConstraint(
            "projection_family = 'REGULATORY'",
            name="ck_lab_regulatory_composition_entry_projection",
        ),
        CheckConstraint(
            "fraction >= 0 AND fraction <= 1",
            name="ck_lab_regulatory_composition_entry_fraction",
        ),
        CheckConstraint(
            "standard_uncertainty IS NULL OR standard_uncertainty >= 0",
            name="ck_lab_regulatory_composition_entry_uncertainty",
        ),
        CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_regulatory_composition_entry_content_sha256",
        ),
    )

    composition_profile_id: Mapped[str] = mapped_column(
        ForeignKey(
            "lab_regulatory_composition_profiles.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    projection_family: Mapped[str] = mapped_column(
        String(40),
        default="REGULATORY",
        server_default=text("'REGULATORY'"),
        nullable=False,
    )
    material_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_materials.id", ondelete="RESTRICT")
    )
    constituent_name: Mapped[str] = mapped_column(Text, nullable=False)
    cas_number: Mapped[str | None] = mapped_column(String(50))
    fraction: Mapped[float] = mapped_column(Float, nullable=False)
    fraction_basis: Mapped[str] = mapped_column(String(80), nullable=False)
    standard_uncertainty: Mapped[float | None] = mapped_column(Float)
    source_locator_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class LabRegulatorySnapshotVersion(LabRecord):
    __tablename__ = "lab_regulatory_snapshot_versions"
    __table_args__ = (
        UniqueConstraint(
            "snapshot_id",
            "version_number",
            name="uq_lab_regulatory_snapshot_version",
        ),
        UniqueConstraint(
            "content_sha256",
            name="uq_lab_regulatory_snapshot_content_sha256",
        ),
        CheckConstraint(
            "version_number >= 1",
            name="ck_lab_regulatory_snapshot_version_positive",
        ),
        CheckConstraint(
            "(version_number = 1 AND parent_version_id IS NULL "
            "AND parent_sha256 IS NULL) OR "
            "(version_number > 1 AND parent_version_id IS NOT NULL "
            "AND length(parent_sha256) = 64)",
            name="ck_lab_regulatory_snapshot_version_chain",
        ),
        CheckConstraint(
            f"subject_type IN ({_quoted(REGULATORY_SUBJECT_TYPES)})",
            name="ck_lab_regulatory_snapshot_subject_type",
        ),
        CheckConstraint(
            f"result_state IN ({_quoted(REGULATORY_RESULT_STATES)})",
            name="ck_lab_regulatory_snapshot_result_state",
        ),
        CheckConstraint(
            f"market_action IN ({_quoted(REGULATORY_MARKET_ACTIONS)})",
            name="ck_lab_regulatory_snapshot_market_action",
        ),
        CheckConstraint(
            "finished_product_concentration >= 0 "
            "AND finished_product_concentration <= 1",
            name="ck_lab_regulatory_snapshot_concentration",
        ),
        CheckConstraint(
            "(result_state = 'PASS_FOR_DECLARED_SCOPE' "
            "AND length(trim(permitted_wording)) > 0) OR "
            "(result_state != 'PASS_FOR_DECLARED_SCOPE' "
            "AND permitted_wording IS NULL)",
            name="ck_lab_regulatory_snapshot_wording",
        ),
        CheckConstraint(
            "length(trim(reviewer_pseudonym)) > 0 AND reviewed_at IS NOT NULL",
            name="ck_lab_regulatory_snapshot_review",
        ),
        CheckConstraint(
            "length(official_source_sha256) = 64",
            name="ck_lab_regulatory_snapshot_official_sha256",
        ),
        CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_regulatory_snapshot_content_sha256",
        ),
        CheckConstraint(
            "parent_sha256 IS NULL OR length(parent_sha256) = 64",
            name="ck_lab_regulatory_snapshot_parent_sha256",
        ),
        ForeignKeyConstraint(
            ["legacy_assessment_version_id"],
            ["lab_regulatory_assessment_versions.id"],
            name="fk_lab_regulatory_snapshot_legacy_assessment",
            ondelete="RESTRICT",
        ),
        Index(
            "ix_lab_regulatory_snapshot_subject",
            "subject_type",
            "subject_id",
        ),
        Index(
            "ix_lab_regulatory_snapshot_result",
            "result_state",
            "evaluated_at",
        ),
    )

    snapshot_id: Mapped[str] = mapped_column(String(36), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_version_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "lab_regulatory_snapshot_versions.id",
            ondelete="RESTRICT",
        )
    )
    schema_version: Mapped[str] = mapped_column(String(80), nullable=False)
    subject_type: Mapped[str] = mapped_column(String(40), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(36), nullable=False)
    legacy_assessment_version_id: Mapped[str | None] = mapped_column(String(36))
    primary_source_version_id: Mapped[str] = mapped_column(
        ForeignKey("lab_regulatory_source_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    standard_identifier: Mapped[str] = mapped_column(Text, nullable=False)
    standard_version: Mapped[str] = mapped_column(String(100), nullable=False)
    official_source_sha256: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    jurisdiction: Mapped[str] = mapped_column(String(100), nullable=False)
    product_category: Mapped[str] = mapped_column(String(100), nullable=False)
    use_classification: Mapped[str] = mapped_column(String(80), nullable=False)
    finished_product_concentration: Mapped[float] = mapped_column(
        Float, nullable=False
    )
    constituent_basis: Mapped[str] = mapped_column(String(80), nullable=False)
    natural_material_assumptions_json: Mapped[list] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    effective_on: Mapped[date] = mapped_column(Date, nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(timezone=True), nullable=False
    )
    evaluator_software_version: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    market_action: Mapped[str] = mapped_column(String(40), nullable=False)
    market_action_on: Mapped[date] = mapped_column(Date, nullable=False)
    current_state_source_ids_json: Mapped[list] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    watch_source_ids_json: Mapped[list] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    rule_version_ids_json: Mapped[list] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    supplier_binding_ids_json: Mapped[list] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    composition_profile_ids_json: Mapped[list] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    upstream_hashes_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    unresolved_items_json: Mapped[list] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    result_reasons_json: Mapped[list] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    result_state: Mapped[str] = mapped_column(String(40), nullable=False)
    permitted_wording: Mapped[str | None] = mapped_column(Text)
    reviewer_pseudonym: Mapped[str] = mapped_column(Text, nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(
        UTCDateTime(timezone=True), nullable=False
    )
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    parent_sha256: Mapped[str | None] = mapped_column(String(64))


class LabRegulatoryAuthorityFinding(LabRecord):
    __tablename__ = "lab_regulatory_authority_findings"
    __table_args__ = (
        UniqueConstraint(
            "snapshot_version_id",
            "rule_version_id",
            name="uq_lab_regulatory_finding_rule",
        ),
        UniqueConstraint(
            "content_sha256",
            name="uq_lab_regulatory_finding_content_sha256",
        ),
        CheckConstraint(
            f"result_state IN ({_quoted(REGULATORY_RESULT_STATES)})",
            name="ck_lab_regulatory_finding_result_state",
        ),
        CheckConstraint(
            f"source_status IN ({_quoted(REGULATORY_SOURCE_STATUSES)})",
            name="ck_lab_regulatory_finding_source_status",
        ),
        CheckConstraint(
            "(observed_fraction IS NULL OR "
            "(observed_fraction >= 0 AND observed_fraction <= 1)) AND "
            "(limit_fraction IS NULL OR "
            "(limit_fraction >= 0 AND limit_fraction <= 1))",
            name="ck_lab_regulatory_finding_fraction",
        ),
        CheckConstraint(
            "(enforced = 0 AND result_state = 'NOT_EVALUATED') OR "
            "(enforced = 1 AND result_state != 'NOT_EVALUATED')",
            name="ck_lab_regulatory_finding_enforcement_shape",
        ),
        CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_regulatory_finding_content_sha256",
        ),
        Index(
            "ix_lab_regulatory_finding_snapshot_result",
            "snapshot_version_id",
            "result_state",
        ),
    )

    snapshot_version_id: Mapped[str] = mapped_column(
        ForeignKey(
            "lab_regulatory_snapshot_versions.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    rule_version_id: Mapped[str] = mapped_column(
        ForeignKey("lab_regulatory_rule_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    substance_name: Mapped[str] = mapped_column(Text, nullable=False)
    cas_number: Mapped[str | None] = mapped_column(String(50))
    observed_fraction: Mapped[float | None] = mapped_column(Float)
    limit_fraction: Mapped[float | None] = mapped_column(Float)
    concentration_basis: Mapped[str] = mapped_column(
        String(80), nullable=False
    )
    source_status: Mapped[str] = mapped_column(String(60), nullable=False)
    enforced: Mapped[bool] = mapped_column(Boolean, nullable=False)
    contribution_lineage_json: Mapped[list] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    reason_codes_json: Mapped[list] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    detail_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    result_state: Mapped[str] = mapped_column(String(40), nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


REGULATORY_AUTHORITY_TABLE_NAMES = {
    "lab_regulatory_source_versions",
    "lab_regulatory_rule_versions",
    "lab_supplier_document_bindings",
    "lab_regulatory_composition_profiles",
    "lab_regulatory_composition_entries",
    "lab_regulatory_snapshot_versions",
    "lab_regulatory_authority_findings",
}


__all__ = [
    "REGULATORY_AUTHORITY_FAMILIES",
    "REGULATORY_AUTHORITY_TABLE_NAMES",
    "REGULATORY_COMPOSITION_BASES",
    "REGULATORY_COMPOSITION_COMPLETENESS",
    "REGULATORY_COMPOSITION_ORIGINS",
    "REGULATORY_MARKET_ACTIONS",
    "REGULATORY_RESULT_STATES",
    "REGULATORY_RULE_FAMILIES",
    "REGULATORY_RULE_KINDS",
    "REGULATORY_SOURCE_STATUSES",
    "REGULATORY_SUBJECT_TYPES",
    "SUPPLIER_DOCUMENT_SCOPES",
    "SUPPLIER_REGULATORY_DOCUMENT_TYPES",
    "LabRegulatoryCompositionEntry",
    "LabRegulatoryCompositionProfile",
    "LabRegulatoryAuthorityFinding",
    "LabRegulatoryRuleVersion",
    "LabRegulatorySnapshotVersion",
    "LabRegulatorySourceVersion",
    "LabSupplierDocumentBinding",
]
