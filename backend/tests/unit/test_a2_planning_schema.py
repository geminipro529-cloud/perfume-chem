from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint

import app.models.lab  # noqa: F401
from app.models.base import Base
from app.models.lab import APPEND_ONLY_TABLES

PLANNING_TABLES = {
    "lab_target_hypothesis_versions",
    "lab_target_lines",
    "lab_target_evidence_links",
    "lab_accepted_target_versions",
    "lab_formula_version_edges",
    "lab_inventory_mapping_versions",
    "lab_inventory_mapping_evidence_links",
    "lab_build_plan_versions",
    "lab_build_plan_lines",
    "lab_build_plan_evidence_links",
    "lab_inventory_reservation_events",
}


def _named_constraints(table_name: str, constraint_type: type) -> set[str]:
    return {
        str(constraint.name)
        for constraint in Base.metadata.tables[table_name].constraints
        if isinstance(constraint, constraint_type)
    }


def test_a2_planning_tables_are_canonical_and_append_only():
    assert PLANNING_TABLES <= set(Base.metadata.tables)
    assert PLANNING_TABLES <= APPEND_ONLY_TABLES
    for name in PLANNING_TABLES:
        assert "updated_at" not in Base.metadata.tables[name].columns


def test_a2_planning_tables_declare_named_checks_and_uniqueness():
    expected = {
        "lab_target_hypothesis_versions": {
            "uq_lab_target_version",
            "uq_lab_target_version_content_sha256",
            "ck_lab_target_version_positive",
        },
        "lab_target_lines": {
            "uq_lab_target_line_position",
            "uq_lab_target_line_identity",
            "uq_lab_target_line_id_version",
            "ck_lab_target_line_quantities",
            "ck_lab_target_line_fractions",
        },
        "lab_target_evidence_links": {
            "uq_lab_target_evidence_link",
        },
        "lab_accepted_target_versions": {
            "uq_lab_accepted_target_version",
            "uq_lab_accepted_target_identity",
            "ck_lab_accepted_target_version_positive",
        },
        "lab_formula_version_edges": {
            "uq_lab_formula_version_edge",
            "ck_lab_formula_version_edge_not_self",
        },
        "lab_inventory_mapping_versions": {
            "uq_lab_mapping_version",
            "ck_lab_mapping_version_positive",
            "ck_lab_mapping_confidence",
            "ck_lab_mapping_stock_status",
        },
        "lab_inventory_mapping_evidence_links": {
            "uq_lab_mapping_evidence_link",
        },
        "lab_build_plan_versions": {
            "uq_lab_build_plan_version",
            "uq_lab_build_plan_content_sha256",
            "ck_lab_build_plan_version_positive",
            "ck_lab_build_plan_status",
        },
        "lab_build_plan_lines": {
            "uq_lab_build_plan_line_position",
            "uq_lab_build_plan_line_identity",
            "uq_lab_build_plan_line_id_version",
            "ck_lab_build_plan_line_quantities",
            "ck_lab_build_plan_line_fraction",
        },
        "lab_build_plan_evidence_links": {
            "uq_lab_build_plan_evidence_link",
        },
        "lab_inventory_reservation_events": {
            "uq_lab_reservation_sequence",
            "uq_lab_reservation_idempotency",
            "ck_lab_reservation_sequence",
            "ck_lab_reservation_mass",
            "ck_lab_reservation_state",
        },
    }
    for table_name, required in expected.items():
        named = _named_constraints(table_name, (CheckConstraint, UniqueConstraint))
        assert required <= named


def test_a2_line_evidence_links_use_composite_membership_foreign_keys():
    expected = {
        "lab_target_evidence_links": "fk_lab_target_evidence_line_version",
        "lab_build_plan_evidence_links": "fk_lab_build_evidence_line_version",
        "lab_inventory_reservation_events": "fk_lab_reservation_line_version",
    }
    for table_name, name in expected.items():
        assert name in _named_constraints(table_name, ForeignKeyConstraint)
