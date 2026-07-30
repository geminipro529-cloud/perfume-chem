from dataclasses import replace

import pytest

from app.services.lab_properties import (
    AssertionCandidateInput,
    PropertyObservationInput,
    SelectedAssertionInput,
)
from app.services.lab_service import LabService
from app.services.lab_thresholds import (
    OAV_MISMATCH_CODES,
    OAV_PROHIBITED_CLAIMS,
    OAV_SCREENING_USES,
    LegacyThresholdInput,
    OAVAssessmentInput,
    OAVCompatibilityInput,
    ThresholdAuthorityError,
    ThresholdContextInput,
    evaluate_oav_compatibility,
)
from tests.unit.test_b2_property_service import _source_and_extraction

IDENTITY = {
    "chemical_name": "Linalool",
    "cas": "78-70-6",
    "grade": "analytical",
    "purity": "0.99 mass fraction",
    "stereochemistry": "racemate",
}


def _compatibility(**overrides) -> OAVCompatibilityInput:
    values = {
        "threshold_available": True,
        "concentration_identity_scope": "CHEMICAL_ENTITY",
        "concentration_identity_sha256": "a" * 64,
        "threshold_identity_scope": "CHEMICAL_ENTITY",
        "threshold_identity_sha256": "a" * 64,
        "concentration_value": 10.0,
        "concentration_unit": "ppm",
        "concentration_basis": "MOLE_FRACTION",
        "concentration_medium": "AIR",
        "concentration_matrix_specification_state": "SPECIFIED",
        "concentration_matrix_composition": {"carrier": "air"},
        "concentration_route": "ORTHONASAL",
        "concentration_temperature_k": 298.15,
        "concentration_pressure_pa": 101325.0,
        "concentration_relative_humidity_percent": 50.0,
        "concentration_evidence_class": "MEASURED",
        "concentration_review_state": "ACCEPTED_FOR_SCOPED_USE",
        "concentration_model_context": {"kind": "MEASURED_HEADSPACE"},
        "threshold_value": 2.0,
        "threshold_unit": "ppb",
        "threshold_basis": "MOLE_FRACTION",
        "threshold_medium": "AIR",
        "threshold_matrix_specification_state": "SPECIFIED",
        "threshold_matrix_composition": {"carrier": "air"},
        "threshold_endpoint": "DETECTION",
        "threshold_route": "ORTHONASAL",
        "threshold_temperature_k": 298.15,
        "threshold_pressure_pa": 101325.0,
        "threshold_relative_humidity_percent": 50.0,
        "threshold_evidence_class": "MEASURED",
        "threshold_review_state": "ACCEPTED_FOR_SCOPED_USE",
        "threshold_authority_state": "AUTHORIZED_FOR_SCOPED_PROPERTY",
        "threshold_selection_kind": "OBSERVATION",
        "threshold_interpolation_state": "EXACT",
        "requested_endpoint": "DETECTION",
        "requested_route": "ORTHONASAL",
        "strict_science_mode": True,
    }
    values.update(overrides)
    return OAVCompatibilityInput(**values)


def test_compatible_context_computes_only_a_screening_ratio():
    result = evaluate_oav_compatibility(_compatibility())

    assert result.status == "COMPUTED"
    assert result.oav_value == pytest.approx(5000.0)
    assert result.mismatch_codes == ()
    assert result.permitted_uses == OAV_SCREENING_USES
    assert result.prohibited_claims == OAV_PROHIBITED_CLAIMS
    assert "RELEASE" in result.prohibited_claims
    assert "EXACT_INTENSITY" in result.prohibited_claims


def test_absent_threshold_reports_only_missing_threshold_when_concentration_is_valid():
    result = evaluate_oav_compatibility(
        _compatibility(threshold_available=False)
    )

    assert result.status == "WITHHELD"
    assert result.oav_value is None
    assert result.mismatch_codes == ("MISSING_THRESHOLD",)


@pytest.mark.parametrize(
    ("overrides", "code"),
    [
        ({"threshold_available": False}, "MISSING_THRESHOLD"),
        (
            {"threshold_identity_sha256": "b" * 64},
            "IDENTITY_SCOPE_MISMATCH",
        ),
        ({"threshold_medium": "ETHANOL_SOLUTION"}, "THRESHOLD_MEDIUM_MISMATCH"),
        ({"threshold_endpoint": "RECOGNITION"}, "THRESHOLD_ENDPOINT_MISMATCH"),
        ({"threshold_route": "RETRONASAL"}, "THRESHOLD_ROUTE_MISMATCH"),
        ({"threshold_basis": "MASS_FRACTION"}, "THRESHOLD_UNIT_INCOMPARABLE"),
        (
            {"threshold_matrix_specification_state": "UNSPECIFIED"},
            "THRESHOLD_MATRIX_UNSPECIFIED",
        ),
        (
            {"threshold_evidence_class": "HEURISTIC"},
            "THRESHOLD_AUTHORITY_TOO_LOW",
        ),
        (
            {"concentration_evidence_class": "HEURISTIC"},
            "CONCENTRATION_NOT_COMPARABLE",
        ),
        (
            {"threshold_interpolation_state": "EXTRAPOLATED"},
            "MODEL_OUTSIDE_APPLICABILITY_DOMAIN",
        ),
    ],
)
def test_each_context_failure_withholds_oav(overrides, code):
    result = evaluate_oav_compatibility(_compatibility(**overrides))

    assert result.status == "WITHHELD"
    assert result.oav_value is None
    assert code in result.mismatch_codes


def test_multiple_mismatches_are_unique_and_stably_ordered():
    result = evaluate_oav_compatibility(
        _compatibility(
            threshold_available=False,
            threshold_identity_sha256="b" * 64,
            threshold_medium="ETHANOL_SOLUTION",
            threshold_basis="MASS_FRACTION",
            threshold_matrix_specification_state="UNSPECIFIED",
            threshold_evidence_class="HEURISTIC",
        )
    )

    assert result.mismatch_codes == tuple(
        code for code in OAV_MISMATCH_CODES if code in result.mismatch_codes
    )
    assert len(result.mismatch_codes) == len(set(result.mismatch_codes))
    assert result.oav_value is None


def test_solution_threshold_never_converts_to_air_by_unit_conversion():
    result = evaluate_oav_compatibility(
        _compatibility(
            threshold_medium="ETHANOL_SOLUTION",
            threshold_unit="ppm",
        )
    )

    assert result.status == "WITHHELD"
    assert "THRESHOLD_MEDIUM_MISMATCH" in result.mismatch_codes


def test_cross_basis_conversion_is_withheld_even_with_prerequisites():
    result = evaluate_oav_compatibility(
        replace(
            _compatibility(threshold_basis="MASS_FRACTION"),
            conversion_prerequisites={
                "molecular_weight_g_mol": 154.25,
                "temperature_k": 298.15,
                "pressure_pa": 101325.0,
                "gas_behavior_assumption": "ideal",
                "density_kg_m3": 1.2,
                "concentration_definition": "declared",
                "partition_model": "declared",
            },
        )
    )

    assert result.status == "WITHHELD"
    assert "THRESHOLD_UNIT_INCOMPARABLE" in result.mismatch_codes


def _property_input(
    *,
    observation_id: str,
    source_version_id: str,
    extraction_record_id: str,
    property_type: str,
    numeric_value: float,
    unit: str,
    applicability_domain: dict,
) -> PropertyObservationInput:
    return PropertyObservationInput(
        observation_id=observation_id,
        schema_version="lab-property-observation-v1",
        identity_scope="CHEMICAL_ENTITY",
        subject_identity=dict(IDENTITY),
        property_type=property_type,
        value_kind="NUMERIC",
        numeric_value=numeric_value,
        original_unit=unit,
        canonical_unit=unit,
        temperature_k=298.15,
        pressure_pa=101325.0,
        relative_humidity_percent=50.0,
        matrix="air",
        phase="gas",
        purity_fraction=0.99,
        method="dynamic olfactometry",
        source_version_id=source_version_id,
        extraction_record_id=extraction_record_id,
        source_locator={"page": 12, "table": "2", "row": "Linalool"},
        replicate_count=20,
        statistic="geometric mean",
        evidence_class="MEASURED",
        review_state="ACCEPTED_FOR_SCOPED_USE",
        applicability_domain=applicability_domain,
        required_scope=f"property:{property_type.lower()}",
    )


async def _record_property(
    service: LabService,
    *,
    observation_id: str,
    property_type: str,
    numeric_value: float,
    unit: str,
    applicability_domain: dict,
    digest_character: str,
):
    scope = f"property:{property_type.lower()}"
    source, extraction = await _source_and_extraction(
        service,
        observation_id,
        digest_character=digest_character,
        scope=scope,
    )
    return await service.record_property_observation(
        _property_input(
            observation_id=observation_id,
            source_version_id=source.id,
            extraction_record_id=extraction.id,
            property_type=property_type,
            numeric_value=numeric_value,
            unit=unit,
            applicability_domain=applicability_domain,
        )
    )


@pytest.mark.asyncio
async def test_threshold_context_and_assessment_are_explicit_id_records(
    db_session,
):
    service = LabService(db_session)
    threshold = await _record_property(
        service,
        observation_id="threshold-linalool-air",
        property_type="ODOR_THRESHOLD",
        numeric_value=2.0,
        unit="ppb",
        applicability_domain={"purpose": "threshold"},
        digest_character="7",
    )
    context = await service.record_threshold_context(
        ThresholdContextInput(
            context_id="threshold-context-linalool-air",
            observation_id=threshold.id,
            schema_version="lab-threshold-context-v1",
            endpoint="DETECTION",
            route="ORTHONASAL",
            medium="AIR",
            matrix_specification_state="SPECIFIED",
            matrix_composition={"carrier": "air"},
            concentration_basis="MOLE_FRACTION",
            apparatus={"type": "dynamic_olfactometer"},
            population={"description": "adult panel"},
            training_state="TRAINED",
            sample_size=20,
            psychophysical_procedure="3-AFC ascending limits",
        )
    )
    assertion = await service.record_selected_assertion(
        SelectedAssertionInput(
            assertion_id="threshold-assertion-linalool-air",
            schema_version="lab-selected-assertion-v1",
            requested_identity_scope="CHEMICAL_ENTITY",
            requested_identity=dict(IDENTITY),
            requested_property_type="ODOR_THRESHOLD",
            requested_conditions={"context_id": context.id},
            conflict_set_id=None,
            selection_policy_version="b3-exact-threshold-v1",
            selection_kind="OBSERVATION",
            selected_observation_id=threshold.id,
            selected_model=None,
            interpolation_state="EXACT",
            propagated_uncertainty={},
            applicability={"context_id": context.id},
            authority_state="AUTHORIZED_FOR_SCOPED_PROPERTY",
            permitted_claim_wording="Screening threshold for this exact context.",
            candidates=(
                AssertionCandidateInput(
                    observation_id=threshold.id,
                    decision="INCLUDE",
                    rationale="Exact accepted contextual observation.",
                ),
            ),
        )
    )
    concentration = await _record_property(
        service,
        observation_id="concentration-linalool-air",
        property_type="CONCENTRATION",
        numeric_value=10.0,
        unit="ppm",
        applicability_domain={
            "medium": "AIR",
            "matrix_specification_state": "SPECIFIED",
            "matrix_composition": {"carrier": "air"},
            "concentration_basis": "MOLE_FRACTION",
            "route": "ORTHONASAL",
            "model_context": {"kind": "MEASURED_HEADSPACE"},
        },
        digest_character="8",
    )

    assessment = await service.record_oav_assessment(
        OAVAssessmentInput(
            assessment_id="oav-linalool-air",
            schema_version="lab-oav-assessment-v1",
            concentration_observation_id=concentration.id,
            threshold_assertion_id=assertion.id,
            requested_endpoint="DETECTION",
            requested_route="ORTHONASAL",
            strict_science_mode=True,
            conversion_prerequisites={},
        )
    )
    loaded = await service.repository.get_oav_assessment(assessment.id)

    assert loaded is not None
    assert loaded.id == assessment.id
    assert loaded.status == "COMPUTED"
    assert loaded.oav_value == pytest.approx(5000.0)
    assert loaded.mismatch_codes_json == []
    assert loaded.prohibited_claims_json == list(OAV_PROHIBITED_CLAIMS)
    assert not hasattr(service.repository, "latest_oav_assessment")

    wrong_context_assertion = await service.record_selected_assertion(
        SelectedAssertionInput(
            assertion_id="threshold-assertion-wrong-context",
            schema_version="lab-selected-assertion-v1",
            requested_identity_scope="CHEMICAL_ENTITY",
            requested_identity=dict(IDENTITY),
            requested_property_type="ODOR_THRESHOLD",
            requested_conditions={"context_id": "different-context"},
            conflict_set_id=None,
            selection_policy_version="b3-exact-threshold-v1",
            selection_kind="OBSERVATION",
            selected_observation_id=threshold.id,
            selected_model=None,
            interpolation_state="EXACT",
            propagated_uncertainty={},
            applicability={"context_id": "different-context"},
            authority_state="AUTHORIZED_FOR_SCOPED_PROPERTY",
            permitted_claim_wording="Mismatched context must not authorize OAV.",
            candidates=(
                AssertionCandidateInput(
                    observation_id=threshold.id,
                    decision="INCLUDE",
                    rationale="Deliberately mismatched B3 context.",
                ),
            ),
        )
    )
    wrong_context_assessment = await service.record_oav_assessment(
        OAVAssessmentInput(
            assessment_id="oav-wrong-threshold-assertion-context",
            schema_version="lab-oav-assessment-v1",
            concentration_observation_id=concentration.id,
            threshold_assertion_id=wrong_context_assertion.id,
            requested_endpoint="DETECTION",
            requested_route="ORTHONASAL",
            strict_science_mode=True,
            conversion_prerequisites={},
        )
    )
    assert wrong_context_assessment.status == "WITHHELD"
    assert wrong_context_assessment.oav_value is None
    assert (
        "THRESHOLD_AUTHORITY_TOO_LOW"
        in wrong_context_assessment.mismatch_codes_json
    )

    with pytest.raises(
        ThresholdAuthorityError,
        match="threshold assertion does not exist",
    ):
        await service.record_oav_assessment(
            OAVAssessmentInput(
                assessment_id="oav-unknown-threshold-assertion",
                schema_version="lab-oav-assessment-v1",
                concentration_observation_id=concentration.id,
                threshold_assertion_id="missing-threshold-assertion",
                requested_endpoint="DETECTION",
                requested_route="ORTHONASAL",
                strict_science_mode=True,
                conversion_prerequisites={},
            )
        )


@pytest.mark.asyncio
async def test_threshold_context_requires_b3_identity_dimensions(db_session):
    service = LabService(db_session)
    source, extraction = await _source_and_extraction(
        service,
        "threshold-incomplete-identity",
        digest_character="9",
        scope="property:odor_threshold",
    )
    command = _property_input(
        observation_id="threshold-incomplete-identity",
        source_version_id=source.id,
        extraction_record_id=extraction.id,
        property_type="ODOR_THRESHOLD",
        numeric_value=2.0,
        unit="ppb",
        applicability_domain={"purpose": "threshold"},
    )
    observation = await service.record_property_observation(
        replace(
            command,
            subject_identity={
                "chemical_name": "Linalool",
                "cas": "78-70-6",
            },
        )
    )

    with pytest.raises(ThresholdAuthorityError, match="grade"):
        await service.record_threshold_context(
            ThresholdContextInput(
                context_id="context-incomplete-identity",
                observation_id=observation.id,
                schema_version="lab-threshold-context-v1",
                endpoint="DETECTION",
                route="ORTHONASAL",
                medium="AIR",
                matrix_specification_state="SPECIFIED",
                matrix_composition={"carrier": "air"},
                concentration_basis="MOLE_FRACTION",
                apparatus={"type": "dynamic_olfactometer"},
                population={"description": "adult panel"},
                training_state="TRAINED",
                sample_size=20,
                psychophysical_procedure="3-AFC",
            )
        )


@pytest.mark.asyncio
async def test_legacy_threshold_status_is_preserved_and_never_promoted(
    db_session,
):
    service = LabService(db_session)
    record = await service.record_legacy_threshold(
        LegacyThresholdInput(
            record_id="legacy-linalool-air",
            schema_version="lab-legacy-threshold-v1",
            material_key="linalool",
            medium="AIR",
            numeric_value=0.51,
            original_unit="ppb",
            verification_status="DERIVED",
            source_payload={"sources": ["legacy source"], "note": "legacy"},
        )
    )

    assert record.verification_status == "DERIVED"
    assert record.authority_state == "LEGACY_CONTEXT_INCOMPLETE"
    assert await service.repository.get_property_observation(record.id) is None
    assert await service.repository.get_selected_assertion(record.id) is None
