from app.models.base import Base
from app.models.lab import APPEND_ONLY_TABLES, LAB_TABLE_NAMES
from app.models.lab_external_studies import EXTERNAL_STUDY_TABLE_NAMES

EXPECTED_TABLES = {
    "lab_external_study_versions",
    "lab_external_stimulus_versions",
    "lab_external_stimulus_components",
    "lab_external_conditions",
    "lab_external_experimental_units",
    "lab_external_observations",
    "lab_external_identity_crosswalks",
    "lab_external_study_conflicts",
}


def test_external_study_tables_are_native_append_only_lab_tables():
    assert EXTERNAL_STUDY_TABLE_NAMES == EXPECTED_TABLES
    assert EXPECTED_TABLES <= LAB_TABLE_NAMES
    assert EXPECTED_TABLES <= APPEND_ONLY_TABLES
    assert EXPECTED_TABLES <= set(Base.metadata.tables)


def test_external_study_schema_preserves_source_grain_and_authority_boundary():
    study = Base.metadata.tables["lab_external_study_versions"]
    assert {
        "study_id",
        "version_number",
        "source_version_id",
        "source_extraction_id",
        "source_family",
        "study_key",
        "study_domain",
        "design_json",
        "protocol_json",
        "source_use_request_sha256",
        "source_use_assessment_sha256",
        "source_use_constraint_version_ids_json",
        "source_use_constraint_record_sha256s_json",
        "authority_state",
        "supersedes_version_id",
        "parent_record_sha256",
        "record_sha256",
    } <= set(study.columns.keys())

    observation = Base.metadata.tables["lab_external_observations"]
    assert {
        "study_version_id",
        "source_extraction_id",
        "condition_id",
        "experimental_unit_id",
        "primary_stimulus_version_id",
        "trial_key",
        "session_key",
        "repeat_index",
        "presentation_json",
        "endpoint_key",
        "value_json",
        "original_unit",
        "scale_json",
        "timepoint_json",
        "replicate_index",
        "observation_grain",
        "aggregation_statistic",
        "missingness",
        "uncertainty_json",
        "limitations_json",
        "record_sha256",
    } <= set(observation.columns.keys())

    unit = Base.metadata.tables["lab_external_experimental_units"]
    assert "unit_grain" in unit.columns.keys()
    assert "parent_unit_id" in unit.columns.keys()
    assert "reported_n" in unit.columns.keys()

    component = Base.metadata.tables["lab_external_stimulus_components"]
    assert {
        "position",
        "source_identity_json",
        "quantity_value_text",
        "quantity_unit",
        "quantity_basis",
        "concentration_value_text",
        "concentration_unit",
        "concentration_basis",
    } <= set(component.columns.keys())


def test_external_study_schema_has_named_checks_hashes_and_foreign_keys():
    expected_checks = {
        "lab_external_study_versions": {
            "ck_lab_external_study_version_positive",
            "ck_lab_external_study_domain",
            "ck_lab_external_study_authority",
            "ck_lab_external_study_hashes",
            "ck_lab_external_study_version_chain",
        },
        "lab_external_stimulus_versions": {
            "ck_lab_external_stimulus_kind",
            "ck_lab_external_stimulus_record_sha256",
        },
        "lab_external_stimulus_components": {
            "ck_lab_external_component_position",
            "ck_lab_external_component_quantity_shape",
            "ck_lab_external_component_concentration_shape",
            "ck_lab_external_component_record_sha256",
        },
        "lab_external_conditions": {
            "ck_lab_external_condition_role",
            "ck_lab_external_condition_record_sha256",
        },
        "lab_external_experimental_units": {
            "ck_lab_external_unit_grain",
            "ck_lab_external_unit_reported_n",
            "ck_lab_external_unit_not_self_parent",
            "ck_lab_external_unit_record_sha256",
        },
        "lab_external_observations": {
            "ck_lab_external_observation_grain",
            "ck_lab_external_observation_statistic",
            "ck_lab_external_observation_missingness",
            "ck_lab_external_observation_value_shape",
            "ck_lab_external_observation_indices",
            "ck_lab_external_observation_record_sha256",
        },
        "lab_external_identity_crosswalks": {
            "ck_lab_external_crosswalk_status",
            "ck_lab_external_crosswalk_material_shape",
            "ck_lab_external_crosswalk_record_sha256",
        },
        "lab_external_study_conflicts": {
            "ck_lab_external_conflict_type",
            "ck_lab_external_conflict_state",
            "ck_lab_external_conflict_distinct_extractions",
            "ck_lab_external_conflict_record_sha256",
        },
    }
    for table_name, names in expected_checks.items():
        table = Base.metadata.tables[table_name]
        actual = {constraint.name for constraint in table.constraints}
        assert names <= actual
        assert any(constraint.__class__.__name__ == "ForeignKeyConstraint" for constraint in table.constraints)
