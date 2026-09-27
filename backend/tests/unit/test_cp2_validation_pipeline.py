import json

import pytest
from fastapi import HTTPException

from app.services import validation_pipeline
from app.services.chemistry_validator import (
    ChemistryValidator,
    ReferenceDatasetStatus,
)


def _write_references(tmp_path):
    potency = tmp_path / "potency.json"
    compounds = tmp_path / "compounds.json"
    potency.write_text(
        json.dumps(
            {
                "chemicals": {
                    "Exact Material": {
                        "min_percent": 0,
                        "max_percent": 10,
                        "typical_percent": 5,
                        "potency": "medium",
                        "note": "heart",
                    }
                },
                "potency_categories": {
                    "medium": {"max_allowed": 10, "warning_threshold": 8}
                },
                "note_distribution_guidelines": {},
            }
        ),
        encoding="utf-8",
    )
    compounds.write_text(
        json.dumps(
            {
                "compounds": [
                    {"name": "Exact Material", "ifra_limit": 10.0}
                ]
            }
        ),
        encoding="utf-8",
    )
    return potency, compounds


def test_reference_load_failure_is_explicit_not_a_clean_empty_mapping(tmp_path):
    validator = ChemistryValidator(
        potency_path=tmp_path / "missing-potency.json",
        compounds_path=tmp_path / "missing-compounds.json",
    )
    assert validator.reference_states["potency"].status == (
        ReferenceDatasetStatus.MISSING
    )
    assert validator.reference_states["ifra_compounds"].status == (
        ReferenceDatasetStatus.MISSING
    )
    assert len(validator.reference_bundle_sha256()) == 64


def test_ifra_matching_is_exact_or_explicit_alias_never_substring(tmp_path):
    potency, compounds = _write_references(tmp_path)
    validator = ChemistryValidator(
        potency_path=potency,
        compounds_path=compounds,
        ifra_aliases={"Admitted Exact Alias": "Exact Material"},
    )
    assert validator._get_ifra_record("exact material")[0] == (
        "APPLICABLE_LIMIT"
    )
    assert validator._get_ifra_record("Admitted Exact Alias")[0] == (
        "APPLICABLE_LIMIT"
    )
    assert validator._get_ifra_record("Exact Material Extra")[0] == (
        "NO_MATCHING_RECORD"
    )


def test_unknown_positive_dose_material_withholds_and_errors_keep_severity(
    monkeypatch,
):
    validator = ChemistryValidator()
    monkeypatch.setattr(validation_pipeline, "_validator", validator)
    report = validation_pipeline.validate_formula(
        {"Linalool": 105.0, "Uncovered Material": 1.0}
    )
    assert report.state == "WITHHOLD_UNKNOWN"
    assert report.errors
    assert all(item["severity"] == "error" for item in report.errors)
    assert any(
        requirement.startswith("POSITIVE_DOSE_COVERAGE:")
        for requirement in report.missing_requirements
    )
    envelope = report.to_dict()
    assert envelope["schema_version"] == "backend-advisory-validation-v2"
    assert envelope["processing_allowed"] is True
    assert envelope["authority"] == {
        "release_authority": False,
        "safety_authority": False,
        "compounding_authority": False,
        "regulatory_authority": False,
    }


@pytest.mark.parametrize("bad_value", [True, -1.0, float("nan"), float("inf")])
def test_structural_numeric_invalidity_blocks_with_invalid_input(bad_value):
    with pytest.raises(HTTPException) as error:
        validation_pipeline.validate_formula({"Linalool": bad_value})
    assert error.value.status_code == 400
    detail = error.value.detail
    assert detail["code"] == "INVALID_INPUT"
    assert detail["validation"]["state"] == "INVALID_INPUT"
    assert detail["validation"]["processing_allowed"] is False


def test_validation_envelope_is_always_attached(monkeypatch):
    report = validation_pipeline.PipelineReport()
    payload = validation_pipeline.attach_validation({"result": "ok"}, report)
    assert payload["validation"]["state"] == "ADVISORY_COMPLETE"
    assert payload["_validation"] == payload["validation"]
