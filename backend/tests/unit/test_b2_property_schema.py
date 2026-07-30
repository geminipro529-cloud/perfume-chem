from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint

import app.models.lab  # noqa: F401
from app.models.base import Base
from app.models.lab import APPEND_ONLY_TABLES, LAB_TABLE_NAMES
from app.models.lab_properties import (
    ASSERTION_AUTHORITY_STATES,
    ASSERTION_CANDIDATE_DECISIONS,
    ASSERTION_INTERPOLATION_STATES,
    ASSERTION_SELECTION_KINDS,
    PROPERTY_AUTHORITY_TABLE_NAMES,
    PROPERTY_CENSORING_QUALIFIERS,
    PROPERTY_CONFLICT_MATERIALITIES,
    PROPERTY_CONFLICT_STATES,
    PROPERTY_EVIDENCE_CLASSES,
    PROPERTY_IDENTITY_SCOPES,
    PROPERTY_REVIEW_STATES,
    PROPERTY_VALUE_KINDS,
)

B2_TABLES = {
    "lab_property_observations",
    "lab_property_conflict_sets",
    "lab_property_conflict_members",
    "lab_selected_assertions",
    "lab_selected_assertion_candidates",
}


def _named_constraints(table_name: str, constraint_type: type) -> set[str]:
    return {
        str(constraint.name)
        for constraint in Base.metadata.tables[table_name].constraints
        if isinstance(constraint, constraint_type)
    }


def test_b2_constants_preserve_identity_value_conflict_and_selection_scope():
    assert set(PROPERTY_IDENTITY_SCOPES) == {
        "CHEMICAL_ENTITY",
        "STEREOISOMER_OR_ISOMERIC_MIXTURE",
        "TRADE_GRADE",
        "SUPPLIER_PRODUCT",
        "SUPPLIER_LOT",
        "STOCK_SOLUTION",
        "PHYSICAL_DOSE",
        "NATURAL_MATERIAL",
    }
    assert set(PROPERTY_VALUE_KINDS) == {
        "NUMERIC",
        "CATEGORICAL",
        "INTERVAL",
        "DISTRIBUTION",
        "CENSORED",
    }
    assert set(PROPERTY_CENSORING_QUALIFIERS) == {
        "LT_LOD",
        "LT_LOQ",
        "GT_UPPER_RANGE",
        "NOT_DETECTED",
        "TRACE",
    }
    assert set(PROPERTY_CONFLICT_STATES) == {
        "UNRESOLVED",
        "RESOLVED_FOR_SCOPE",
    }
    assert set(PROPERTY_CONFLICT_MATERIALITIES) == {
        "BLOCKING",
        "NON_BLOCKING",
    }
    assert set(ASSERTION_CANDIDATE_DECISIONS) == {"INCLUDE", "EXCLUDE"}
    assert set(ASSERTION_SELECTION_KINDS) == {"OBSERVATION", "MODEL", "NONE"}
    assert set(ASSERTION_INTERPOLATION_STATES) == {
        "EXACT",
        "INTERPOLATED",
        "EXTRAPOLATED",
        "NOT_APPLICABLE",
    }
    assert set(ASSERTION_AUTHORITY_STATES) == {
        "AUTHORIZED_FOR_SCOPED_PROPERTY",
        "ADVISORY_ONLY",
        "WITHHELD_CONFLICT",
        "WITHHELD_UNKNOWN",
    }
    assert {
        "MEASURED",
        "LITERATURE_DERIVED",
        "SUPPLIER_PROVIDED",
        "EMPIRICALLY_CALIBRATED",
        "MODEL_ESTIMATED",
        "HEURISTIC",
        "SPECULATIVE",
        "UNKNOWN",
    } == set(PROPERTY_EVIDENCE_CLASSES)
    assert {"STAGED", "REVIEWED", "ACCEPTED_FOR_SCOPED_USE", "REJECTED"} <= set(
        PROPERTY_REVIEW_STATES
    )


def test_b2_tables_are_canonical_append_only_and_legacy_properties_are_frozen():
    assert PROPERTY_AUTHORITY_TABLE_NAMES == B2_TABLES
    assert B2_TABLES <= LAB_TABLE_NAMES
    assert B2_TABLES <= APPEND_ONLY_TABLES
    assert "lab_material_properties" in APPEND_ONLY_TABLES
    for table_name in B2_TABLES:
        assert "updated_at" not in Base.metadata.tables[table_name].columns

    legacy = Base.metadata.tables["lab_material_properties"]
    assert {"authority_state", "authority_reason"} <= set(legacy.columns.keys())
    assert legacy.c.authority_state.nullable is False
    assert legacy.c.authority_reason.nullable is False


def test_b2_observation_and_assertion_tables_expose_required_fields():
    observation = set(
        Base.metadata.tables["lab_property_observations"].columns.keys()
    )
    assert {
        "schema_version",
        "identity_scope",
        "subject_identity_json",
        "subject_identity_sha256",
        "property_type",
        "value_kind",
        "numeric_value",
        "categorical_value",
        "interval_lower",
        "interval_upper",
        "distribution_json",
        "censoring_qualifier",
        "censoring_limit",
        "original_unit",
        "canonical_unit",
        "temperature_k",
        "pressure_pa",
        "relative_humidity_percent",
        "matrix",
        "phase",
        "purity_fraction",
        "method",
        "source_version_id",
        "extraction_record_id",
        "source_locator_json",
        "replicate_count",
        "statistic",
        "standard_uncertainty",
        "uncertainty_interval_json",
        "evidence_class",
        "review_state",
        "quality_flags_json",
        "applicability_domain_json",
        "provenance_activity_json",
        "supersedes_observation_id",
        "content_sha256",
    } <= observation

    conflict = set(
        Base.metadata.tables["lab_property_conflict_sets"].columns.keys()
    )
    assert {
        "schema_version",
        "requested_identity_json",
        "requested_identity_sha256",
        "property_type",
        "requested_conditions_json",
        "state",
        "materiality",
        "difference_dimensions_json",
        "explanation",
        "content_sha256",
    } <= conflict

    assertion = set(
        Base.metadata.tables["lab_selected_assertions"].columns.keys()
    )
    assert {
        "schema_version",
        "requested_identity_json",
        "requested_identity_sha256",
        "requested_property_type",
        "requested_conditions_json",
        "conflict_set_id",
        "selection_policy_version",
        "selection_kind",
        "selected_observation_id",
        "selected_model_json",
        "interpolation_state",
        "propagated_uncertainty_json",
        "applicability_json",
        "authority_state",
        "permitted_claim_wording",
        "content_sha256",
    } <= assertion

    candidate = set(
        Base.metadata.tables["lab_selected_assertion_candidates"].columns.keys()
    )
    assert {
        "selected_assertion_id",
        "observation_id",
        "decision",
        "rationale",
    } <= candidate


def test_b2_tables_declare_named_database_constraints_and_foreign_keys():
    expected = {
        "lab_property_observations": {
            "uq_lab_property_observation_content_sha256",
            "uq_lab_property_observation_supersedes",
            "ck_lab_property_observation_identity_scope",
            "ck_lab_property_observation_value_kind",
            "ck_lab_property_observation_value_shape",
            "ck_lab_property_observation_censoring",
            "ck_lab_property_observation_conditions",
            "ck_lab_property_observation_replicate_count",
            "ck_lab_property_observation_evidence_class",
            "ck_lab_property_observation_review_state",
            "ck_lab_property_observation_content_sha256",
        },
        "lab_property_conflict_sets": {
            "uq_lab_property_conflict_content_sha256",
            "ck_lab_property_conflict_state",
            "ck_lab_property_conflict_materiality",
            "ck_lab_property_conflict_content_sha256",
        },
        "lab_property_conflict_members": {
            "uq_lab_property_conflict_member",
        },
        "lab_selected_assertions": {
            "uq_lab_selected_assertion_content_sha256",
            "ck_lab_selected_assertion_selection_kind",
            "ck_lab_selected_assertion_selection_shape",
            "ck_lab_selected_assertion_interpolation",
            "ck_lab_selected_assertion_authority",
            "ck_lab_selected_assertion_content_sha256",
        },
        "lab_selected_assertion_candidates": {
            "uq_lab_selected_assertion_candidate",
            "ck_lab_selected_assertion_candidate_decision",
        },
    }
    for table_name, required in expected.items():
        named = _named_constraints(
            table_name,
            (CheckConstraint, UniqueConstraint),
        )
        assert required <= named

    expected_fks = {
        "lab_property_observations": {
            "fk_lab_property_observation_source",
            "fk_lab_property_observation_extraction",
            "fk_lab_property_observation_supersedes",
        },
        "lab_property_conflict_members": {
            "fk_lab_property_conflict_member_set",
            "fk_lab_property_conflict_member_observation",
        },
        "lab_selected_assertions": {
            "fk_lab_selected_assertion_conflict",
            "fk_lab_selected_assertion_observation",
        },
        "lab_selected_assertion_candidates": {
            "fk_lab_selected_assertion_candidate_assertion",
            "fk_lab_selected_assertion_candidate_observation",
        },
    }
    for table_name, required in expected_fks.items():
        named = _named_constraints(table_name, ForeignKeyConstraint)
        assert required <= named
