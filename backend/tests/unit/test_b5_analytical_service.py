from dataclasses import replace
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import func, select

from app.models.lab_analytical import LabAnalyticalSequence
from app.services.lab_analytical import (
    ANALYTICAL_MISSING_REQUIREMENT_CODES,
    ANALYTICAL_QUALIFICATION_CODES,
    VALIDATION_CHARACTERISTIC_KEYS,
    AnalyticalAuthorityConflictError,
    AnalyticalAuthorityError,
    AnalyticalClaimRequest,
    AnalyticalMethodAuthorityInput,
    AnalyticalPeakAuthorityInput,
    AnalyticalRunAuthorityInput,
    AnalyticalSequenceEntryInput,
    AnalyticalSequenceInput,
    GCOEventAuthorityInput,
    MethodValidationInput,
)
from app.services.lab_science import (
    AnalyticalAttachmentInput,
    AnalyticalMethodInput,
    AnalyticalPeakInput,
    AnalyticalQCInput,
    AnalyticalRunInput,
    ClaimAssessmentInput,
    ClaimEvidenceInput,
    GCOEventInput,
    ScienceAuthorityConflictError,
)
from app.services.lab_service import LabService
from app.services.lab_sources import SourceDocumentInput
from tests.a2_planning_fixtures import _approved_plan


def _method_configuration() -> dict:
    return {
        "instrument": {
            "identifier": "instrument:pseudonymous",
            "manufacturer": "test-manufacturer",
            "model": "test-model",
        },
        "detector": {
            "type": "MS",
            "configuration": "EI 70 eV",
        },
        "software": {
            "name": "test-software",
            "version": "1.0",
            "processing_version": "processor-v1",
        },
        "separation": {
            "column": "30 m x 0.25 mm x 0.25 um",
            "stationary_phase": "5 percent phenyl",
            "temperature_program": "40 C to 280 C",
            "carrier_gas": "helium",
            "carrier_flow": "1.0 mL/min",
        },
        "acquisition": {
            "inlet": "250 C",
            "split": "10:1",
            "injection": "1 uL",
            "detector_conditions": "source 230 C",
            "acquisition_conditions": "scan 35-350 m/z",
        },
        "sample_preparation": {
            "procedure": "gravimetric dilution",
            "dilution_factor": 100.0,
            "solvent": "ethanol",
        },
        "standards": {
            "internal": ["internal-standard-1"],
            "external": ["external-standard-1"],
            "retention_index": ["c8-c20-alkanes"],
        },
        "calibration": {
            "design": "five-point weighted linear",
            "working_range": {"minimum": 0.01, "maximum": 1.0, "unit": "mg/mL"},
            "matrix_scope": "ethanol perfume extract",
            "analyte_scope": ["linalool"],
            "method_scope": "method-version-bound",
        },
        "response_factors": {
            "policy": "analyte-specific",
            "values": {"linalool": 1.0},
        },
        "identity_criteria": {
            "retention_index": "within validated tolerance",
            "spectrum": "qualified ions and spectrum",
            "authentic_standard": "co-injection for highest tier",
        },
        "integration_policy": {
            "integration": "reviewed bounded baseline",
            "deconvolution": "versioned deterministic settings",
        },
        "qc_plan": {
            "required_checks": [
                "BLANK",
                "CALIBRATION_VERIFICATION",
                "INTERNAL_STANDARD",
                "RI_STANDARD",
            ],
            "failure_policy": {
                "BLANK": "BLOCK",
                "CALIBRATION_VERIFICATION": "BLOCK",
                "INTERNAL_STANDARD": "BLOCK",
                "RI_STANDARD": "BLOCK",
            },
        },
        "raw_data_policy": {
            "vendor_format": "vendor-native",
            "open_format": "ANDI-MS",
            "preservation": "content-addressed immutable artifact store",
        },
    }


def _hs_spme_conditions() -> dict:
    return {
        "fiber": "DVB/CAR/PDMS",
        "conditioning": "conditioned per manufacturer",
        "vial": "20 mL",
        "sample_mass": "1.0 g",
        "headspace_volume": "19 mL",
        "incubation": "10 min at 40 C",
        "extraction": "20 min at 40 C",
        "agitation": "500 rpm",
        "desorption": "5 min at 250 C",
    }


def _method_authority_input(
    method_version_id: str = "method-version-1",
    source_version_id: str = "source-version-1",
    **overrides,
) -> AnalyticalMethodAuthorityInput:
    configuration = _method_configuration()
    values = {
        "method_version_id": method_version_id,
        "schema_version": "b5-analytical-method-v1",
        "status": "VALIDATED_FOR_SCOPE",
        "analyte_scope": ("linalool",),
        "instrument": configuration["instrument"],
        "detector": configuration["detector"],
        "software": configuration["software"],
        "separation": configuration["separation"],
        "acquisition": configuration["acquisition"],
        "sample_preparation": configuration["sample_preparation"],
        "hs_spme": None,
        "standards": configuration["standards"],
        "calibration": configuration["calibration"],
        "response_factors": configuration["response_factors"],
        "identity_criteria": configuration["identity_criteria"],
        "integration_policy": configuration["integration_policy"],
        "qc_plan": configuration["qc_plan"],
        "raw_data_policy": configuration["raw_data_policy"],
        "source_document_version_id": source_version_id,
        "source_locator": {"section": "validated method 1"},
    }
    values.update(overrides)
    return AnalyticalMethodAuthorityInput(**values)


@pytest.mark.parametrize(
    "field",
    [
        "instrument",
        "detector",
        "software",
        "separation",
        "acquisition",
        "sample_preparation",
        "standards",
        "calibration",
        "response_factors",
        "identity_criteria",
        "integration_policy",
        "qc_plan",
        "raw_data_policy",
    ],
)
def test_method_authority_input_requires_every_named_component(field):
    with pytest.raises(AnalyticalAuthorityError, match=field):
        _method_authority_input(**{field: {}})


def test_method_authority_input_rejects_unknown_authority_fields():
    instrument = dict(_method_configuration()["instrument"])
    instrument["accreditation_claim"] = "unverified"

    with pytest.raises(AnalyticalAuthorityError, match="unknown keys"):
        _method_authority_input(instrument=instrument)


@pytest.mark.parametrize(
    ("field", "key", "empty_value"),
    [
        ("instrument", "identifier", {}),
        ("standards", "internal", []),
    ],
)
def test_method_authority_input_rejects_empty_placeholder_values(
    field,
    key,
    empty_value,
):
    component = dict(_method_configuration()[field])
    component[key] = empty_value

    with pytest.raises(AnalyticalAuthorityError, match="empty values"):
        _method_authority_input(**{field: component})


def test_hs_spme_input_requires_every_extraction_condition():
    hs_spme = {
        "fiber": "DVB/CAR/PDMS",
        "conditioning": "conditioned per manufacturer",
        "vial": "20 mL",
        "sample_mass": "1.0 g",
        "headspace_volume": "19 mL",
        "incubation": "10 min at 40 C",
        "extraction": "20 min at 40 C",
        "agitation": "500 rpm",
    }

    with pytest.raises(AnalyticalAuthorityError, match="desorption"):
        _method_authority_input(hs_spme=hs_spme)


def _validation_characteristics() -> dict:
    return {
        key: {"assessment": f"bounded {key}", "result": "acceptable"}
        for key in VALIDATION_CHARACTERISTIC_KEYS
    }


def _validation_input(
    method_authority_id: str = "method-authority-1",
    source_version_id: str = "source-version-1",
    **overrides,
) -> MethodValidationInput:
    values = {
        "method_authority_id": method_authority_id,
        "intended_claim": "linalool identity and concentration",
        "matrix_scope": {
            "matrix": "ethanol perfume extract",
            "analytes": ["linalool"],
            "method_scope": "method-version-bound",
        },
        "characteristics": _validation_characteristics(),
        "acceptance_criteria": {
            "identity": "all qualified ions and RI within tolerance",
            "quantity": "bias and precision within declared limits",
        },
        "result": "PASS",
        "limitations": ("validated only for the declared matrix and range",),
        "measurement_uncertainty": {
            "expanded_uncertainty": 0.08,
            "coverage_factor": 2.0,
            "unit": "relative",
        },
        "reviewer_pseudonym": "reviewer-1",
        "reviewed_at": datetime(2026, 7, 31, 2, 0, tzinfo=timezone.utc),
        "source_document_version_id": source_version_id,
        "source_locator": {"section": "validation summary"},
    }
    values.update(overrides)
    return MethodValidationInput(**values)


def test_validation_input_requires_every_characteristic():
    characteristics = _validation_characteristics()
    characteristics.pop("measurement_uncertainty")

    with pytest.raises(
        AnalyticalAuthorityError,
        match="measurement_uncertainty",
    ):
        _validation_input(characteristics=characteristics)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"acceptance_criteria": {}}, "acceptance_criteria"),
        ({"measurement_uncertainty": {}}, "measurement_uncertainty"),
        ({"reviewer_pseudonym": " "}, "reviewer_pseudonym"),
        ({"reviewed_at": datetime(2026, 7, 31, 2, 0)}, "timezone-aware"),
    ],
)
def test_passing_validation_requires_criteria_uncertainty_and_review(
    overrides,
    message,
):
    with pytest.raises(AnalyticalAuthorityError, match=message):
        _validation_input(**overrides)


def _source_input() -> SourceDocumentInput:
    return SourceDocumentInput(
        schema_version="lab-source-document-v1",
        source_type="LOCAL_ANALYTICAL_EXPERIMENT",
        title="B5 bounded analytical method and validation record",
        artifact_sha256="a" * 64,
        language="en",
        review_state="UNREVIEWED",
        independence_group="b5-method-record-1",
        authors=(),
        issuing_organization="test laboratory",
        container_title=None,
        publisher_or_authority="test laboratory",
        identifiers={"sop": "B5-TEST-1"},
        publication_date=date(2026, 7, 31),
        revision_date=None,
        effective_date=date(2026, 7, 31),
        retrieval_date=date(2026, 7, 31),
        edition_or_amendment="1",
        default_locator={"section": "validated method 1"},
        license_or_reuse_restriction="internal test fixture",
        original_unit=None,
        original_terminology="validated method",
        reviewer_pseudonym=None,
        preserved_artifact_path="evidence/methods/b5-test-1.json",
    )


async def _accept_method_source(service: LabService, source_id: str) -> None:
    for state in (
        "PARSED",
        "IDENTITY_RESOLVED",
        "UNIT_NORMALIZED",
        "CONDITION_NORMALIZED",
        "CONFLICT_CHECKED",
        "HUMAN_REVIEWED",
    ):
        await service.transition_evidence_workflow(
            subject_type="SOURCE_VERSION",
            subject_id=source_id,
            to_state=state,
            reviewer_pseudonym=(
                "reviewer-1" if state == "HUMAN_REVIEWED" else None
            ),
            scopes=(),
            reason=f"advance to {state}",
        )
    await service.transition_evidence_workflow(
        subject_type="SOURCE_VERSION",
        subject_id=source_id,
        to_state="ACCEPTED_FOR_SCOPED_USE",
        reviewer_pseudonym="reviewer-1",
        scopes=("ANALYTICAL_METHOD_AUTHORITY",),
        reason="accepted for B5 method authority",
    )


async def _a2_method(
    service: LabService,
    *,
    technique: str = "GCMS",
    status: str = "VALIDATED",
):
    evidence = await service.record_evidence(
        claim_key=f"b5:method:{technique}:{status}",
        classification="EXACT",
        source_locator="test://b5-method",
        source_version="1",
        method="bounded fixture",
        assumptions=(),
        limitations=(),
        payload_sha256=None,
    )
    return await service.create_analytical_method_version(
        AnalyticalMethodInput(
            schema_version="a2-analytical-v1",
            technique=technique,
            intended_use="linalool identity and concentration",
            status=status,
            method={"legacy_acquisition_spine": True},
            evidence_record_id=evidence.id,
        )
    )


@pytest.mark.asyncio
async def test_verified_method_requires_accepted_source_and_status_match(
    db_session,
):
    service = LabService(db_session)
    source = await service.register_source_document(_source_input())
    method = await _a2_method(service)
    source_id = source.id
    source_artifact_sha256 = source.artifact_sha256
    method_id = method.id
    command = _method_authority_input(method_id, source_id)

    with pytest.raises(AnalyticalAuthorityConflictError) as unaccepted:
        await service.register_analytical_method_authority(command)
    assert unaccepted.value.code == "METHOD_SOURCE_SCOPE_NOT_ACCEPTED"

    await _accept_method_source(service, source_id)
    authority = await service.register_analytical_method_authority(command)

    assert authority.method_version_id == method_id
    assert authority.source_artifact_sha256 == source_artifact_sha256
    assert len(authority.content_sha256) == 64

    draft_method = await _a2_method(service, status="DRAFT")
    with pytest.raises(AnalyticalAuthorityConflictError) as mismatch:
        await service.register_analytical_method_authority(
            _method_authority_input(draft_method.id, source_id)
        )
    assert mismatch.value.code == "METHOD_STATUS_INCOMPATIBLE"


@pytest.mark.asyncio
async def test_hs_spme_method_requires_complete_hs_spme_conditions(db_session):
    service = LabService(db_session)
    source = await service.register_source_document(_source_input())
    await _accept_method_source(service, source.id)
    method = await _a2_method(service, technique="HS_SPME_GCMS")

    with pytest.raises(AnalyticalAuthorityConflictError) as missing:
        await service.register_analytical_method_authority(
            _method_authority_input(method.id, source.id)
        )
    assert missing.value.code == "HS_SPME_CONDITIONS_REQUIRED"


@pytest.mark.asyncio
async def test_method_validation_is_complete_hashed_and_explicitly_retrievable(
    db_session,
):
    service = LabService(db_session)
    source = await service.register_source_document(_source_input())
    await _accept_method_source(service, source.id)
    method = await _a2_method(service)
    authority = await service.register_analytical_method_authority(
        _method_authority_input(method.id, source.id)
    )

    validation = await service.record_method_validation(
        _validation_input(authority.id, source.id)
    )
    records = await service.repository.method_validation_records(authority.id)

    assert records == [validation]
    assert validation.result == "PASS"
    assert validation.source_artifact_sha256 == source.artifact_sha256
    assert len(validation.scope_sha256) == 64
    assert len(validation.content_sha256) == 64
    assert "accreditation" not in validation.__table__.columns


async def _method_authority_graph(
    service: LabService,
    *,
    technique: str = "GCMS",
    **authority_overrides,
):
    source = await service.register_source_document(_source_input())
    await _accept_method_source(service, source.id)
    method = await _a2_method(service, technique=technique)
    authority = await service.register_analytical_method_authority(
        _method_authority_input(method.id, source.id, **authority_overrides)
    )
    return source, method, authority


async def _formula_version(service: LabService):
    formula = await service.create_formula("B5 analytical fixture")
    return await service.add_formula_version(
        formula.id,
        brief={"purpose": "B5 analytical authority"},
        constraints={},
        source={"kind": "bounded-test"},
    )


def _sequence_input(
    method_authority_id: str,
    sample_reference: str,
    *,
    sequence_key: str = "sequence:b5:1",
    entries: tuple[AnalyticalSequenceEntryInput, ...] | None = None,
) -> AnalyticalSequenceInput:
    return AnalyticalSequenceInput(
        sequence_key=sequence_key,
        method_authority_id=method_authority_id,
        instrument_identifier="instrument:pseudonymous",
        status="ACQUIRED",
        acquired_at=datetime(2026, 7, 31, 2, 30, tzinfo=timezone.utc),
        entries=entries
        or (
            AnalyticalSequenceEntryInput(
                injection_order=1,
                role="METHOD_BLANK",
                reference="blank:method",
                level={"matrix": "ethanol"},
            ),
            AnalyticalSequenceEntryInput(
                injection_order=2,
                role="CALIBRATION_STANDARD",
                reference="standard:linalool:mid",
                level={"value": 0.1, "unit": "mg/mL"},
            ),
            AnalyticalSequenceEntryInput(
                injection_order=3,
                role="INTERNAL_STANDARD",
                reference="standard:internal:1",
                level={"value": 0.05, "unit": "mg/mL"},
            ),
            AnalyticalSequenceEntryInput(
                injection_order=4,
                role="RI_STANDARD",
                reference="standard:c8-c20",
                level={"series": "c8-c20"},
            ),
            AnalyticalSequenceEntryInput(
                injection_order=5,
                role="SAMPLE",
                reference=sample_reference,
                level={"matrix": "ethanol perfume extract"},
            ),
        ),
    )


def test_sequence_input_rejects_noncontiguous_injection_order():
    entries = (
        AnalyticalSequenceEntryInput(
            injection_order=1,
            role="METHOD_BLANK",
            reference="blank:method",
            level={"matrix": "ethanol"},
        ),
        AnalyticalSequenceEntryInput(
            injection_order=3,
            role="SAMPLE",
            reference="formula-version-1",
            level={"matrix": "ethanol perfume extract"},
        ),
    )

    with pytest.raises(AnalyticalAuthorityError, match="contiguous"):
        _sequence_input("method-authority-1", "formula-version-1", entries=entries)


@pytest.mark.asyncio
async def test_sequence_is_atomic_ordered_and_method_policy_complete(db_session):
    service = LabService(db_session)
    _, _, authority = await _method_authority_graph(service)
    formula_version = await _formula_version(service)
    valid = _sequence_input(authority.id, formula_version.id)
    entries_without_ri = tuple(
        replace(entry, injection_order=index)
        for index, entry in enumerate(
            (
                entry
                for entry in valid.entries
                if entry.role != "RI_STANDARD"
            ),
            start=1,
        )
    )
    missing_ri = replace(
        valid,
        sequence_key="sequence:b5:missing-ri",
        entries=entries_without_ri,
    )

    with pytest.raises(AnalyticalAuthorityConflictError) as missing:
        await service.create_analytical_sequence(missing_ri)
    assert missing.value.code == "SEQUENCE_REQUIRED_ROLE_MISSING"
    assert (
        await db_session.scalar(
            select(func.count()).select_from(LabAnalyticalSequence)
        )
        == 0
    )

    sequence = await service.create_analytical_sequence(valid)
    entries = await service.repository.analytical_sequence_entries(sequence.id)

    assert sequence.entry_count == 5
    assert [entry.injection_order for entry in entries] == [1, 2, 3, 4, 5]
    assert [entry.role for entry in entries][-1] == "SAMPLE"
    assert len(sequence.entries_sha256) == 64
    assert len(sequence.content_sha256) == 64


def _a2_run_input(
    method_id: str,
    formula_version_id: str | None = None,
    *,
    run_kind: str = "GCMS",
    sample_id: str | None = None,
    bottle_id: str | None = None,
    build_plan_version_id: str | None = None,
):
    return AnalyticalRunInput(
        method_version_id=method_id,
        run_kind=run_kind,
        status="PROCESSED",
        instrument_identifier="instrument:pseudonymous",
        acquired_at=datetime(2026, 7, 31, 2, 35, tzinfo=timezone.utc),
        parameters={"injection": "split"},
        deviations=(),
        processing_version="processor-v1",
        sample_id=sample_id,
        bottle_id=bottle_id,
        formula_version_id=formula_version_id,
        build_plan_version_id=build_plan_version_id,
    )


async def _run_with_raw_files(
    service: LabService,
    method_id: str,
    formula_version_id: str | None = None,
    *,
    run_kind: str = "GCMS",
    sample_id: str | None = None,
    bottle_id: str | None = None,
    build_plan_version_id: str | None = None,
):
    run = await service.record_analytical_run(
        _a2_run_input(
            method_id,
            formula_version_id,
            run_kind=run_kind,
            sample_id=sample_id,
            bottle_id=bottle_id,
            build_plan_version_id=build_plan_version_id,
        )
    )
    vendor = await service.bind_analytical_attachment(
        AnalyticalAttachmentInput(
            analytical_run_id=run.id,
            attachment_kind="RAW_VENDOR_DATA",
            media_type="application/octet-stream",
            byte_length=100,
            content_sha256="b" * 64,
            storage_locator="artifact://b5/run/vendor",
        )
    )
    open_export = await service.bind_analytical_attachment(
        AnalyticalAttachmentInput(
            analytical_run_id=run.id,
            attachment_kind="OPEN_EXPORT",
            media_type="application/netcdf",
            byte_length=120,
            content_sha256="c" * 64,
            storage_locator="artifact://b5/run/open",
        )
    )
    return run, vendor, open_export


def _run_authority_input(
    run_id: str,
    method_authority_id: str,
    sequence_id: str,
    sequence_entry_id: str,
    subject_id: str,
    vendor_attachment_id: str,
    open_export_attachment_id: str,
    **overrides,
) -> AnalyticalRunAuthorityInput:
    values = {
        "analytical_run_id": run_id,
        "method_authority_id": method_authority_id,
        "sequence_id": sequence_id,
        "sequence_entry_id": sequence_entry_id,
        "subject_type": "FORMULA_VERSION",
        "subject_id": subject_id,
        "subject_stream_sequence": None,
        "matrix_scope": {"matrix": "ethanol perfume extract"},
        "applicability": {
            "analytes": ["linalool"],
            "method_scope": "method-version-bound",
        },
        "instrument_state": {
            "tune": "pass",
            "maintenance_state": "in-service",
        },
        "processing_details": {
            "software": "test-software",
            "version": "1.0",
            "processing_version": "processor-v1",
        },
        "deviation_assessment": {
            "deviations": [],
            "impact": "none",
        },
        "reviewer_pseudonym": "reviewer-1",
        "reviewed_at": datetime(2026, 7, 31, 2, 40, tzinfo=timezone.utc),
        "disposition": "ACCEPTED",
        "raw_vendor_attachment_id": vendor_attachment_id,
        "open_export_attachment_id": open_export_attachment_id,
    }
    values.update(overrides)
    return AnalyticalRunAuthorityInput(**values)


@pytest.mark.asyncio
async def test_run_authority_binds_primary_subject_sequence_and_raw_files(
    db_session,
):
    service = LabService(db_session)
    _, method, authority = await _method_authority_graph(service)
    formula_version = await _formula_version(service)
    sequence = await service.create_analytical_sequence(
        _sequence_input(authority.id, formula_version.id)
    )
    entries = await service.repository.analytical_sequence_entries(sequence.id)
    sample_entry = next(entry for entry in entries if entry.role == "SAMPLE")
    run, vendor, open_export = await _run_with_raw_files(
        service,
        method.id,
        formula_version.id,
    )

    run_authority = await service.bind_analytical_run_authority(
        _run_authority_input(
            run.id,
            authority.id,
            sequence.id,
            sample_entry.id,
            formula_version.id,
            vendor.id,
            open_export.id,
        )
    )

    assert run_authority.analytical_run_id == run.id
    assert run_authority.subject_type == "FORMULA_VERSION"
    assert run_authority.subject_id == formula_version.id
    assert run_authority.raw_vendor_attachment_id == vendor.id
    assert run_authority.open_export_attachment_id == open_export.id
    assert len(run_authority.content_sha256) == 64


async def _primary_subject_fixture(
    service: LabService,
    db_session,
    subject_type: str,
) -> tuple[object, dict, int | None]:
    if subject_type == "SAMPLE":
        bottle = await service.create_bottle("B5 sample subject")
        experiment = await service.create_experiment(
            "B5 analytical subject experiment",
            protocol={"purpose": "primary-subject coverage"},
        )
        subject = await service.add_experiment_sample(
            experiment_id=experiment.id,
            bottle_id=bottle.id,
            blind_code="B5-SAMPLE",
        )
        return subject, {"sample_id": subject.id}, None
    if subject_type in {"STOCK_LOT", "NATURAL_LOT"}:
        material = await service.create_material(
            f"B5 {subject_type.lower()} material"
        )
        subject = await service.create_stock_solution(
            material_id=material.id,
            active_fraction=1.0,
            fraction_basis="mass_fraction",
            initial_mass_g=5.0,
            supplier="bounded supplier",
            lot_number=f"LOT-{subject_type}",
        )
        if subject_type == "NATURAL_LOT":
            subject.source_json = {"material_kind": "NATURAL"}
            await db_session.flush()
        context = await _formula_version(service)
        return subject, {"formula_version_id": context.id}, None
    if subject_type == "FORMULA_VERSION":
        subject = await _formula_version(service)
        return subject, {"formula_version_id": subject.id}, None
    if subject_type == "BUILD_PLAN_VERSION":
        _, subject, _, _ = await _approved_plan(db_session)
        return subject, {"build_plan_version_id": subject.id}, None
    if subject_type == "BOTTLE_STREAM":
        subject = await service.create_bottle("B5 bottle-stream subject")
        return subject, {"bottle_id": subject.id}, 1
    raise AssertionError(f"unsupported fixture subject type: {subject_type}")


@pytest.mark.parametrize(
    "subject_type",
    [
        "SAMPLE",
        "STOCK_LOT",
        "NATURAL_LOT",
        "FORMULA_VERSION",
        "BUILD_PLAN_VERSION",
        "BOTTLE_STREAM",
    ],
)
@pytest.mark.asyncio
async def test_run_authority_accepts_each_exact_primary_subject(
    db_session,
    subject_type,
):
    service = LabService(db_session)
    subject, run_context, stream_sequence = await _primary_subject_fixture(
        service,
        db_session,
        subject_type,
    )
    _, method, method_authority = await _method_authority_graph(service)
    sequence = await service.create_analytical_sequence(
        _sequence_input(method_authority.id, subject.id)
    )
    entries = await service.repository.analytical_sequence_entries(sequence.id)
    sample_entry = next(entry for entry in entries if entry.role == "SAMPLE")
    run, vendor, open_export = await _run_with_raw_files(
        service,
        method.id,
        **run_context,
    )

    authority = await service.bind_analytical_run_authority(
        _run_authority_input(
            run.id,
            method_authority.id,
            sequence.id,
            sample_entry.id,
            subject.id,
            vendor.id,
            open_export.id,
            subject_type=subject_type,
            subject_stream_sequence=stream_sequence,
        )
    )

    assert authority.subject_type == subject_type
    assert authority.subject_id == subject.id
    assert authority.subject_stream_sequence == stream_sequence


@pytest.mark.asyncio
async def test_run_authority_rejects_context_mismatch_and_wrong_raw_kind(
    db_session,
):
    service = LabService(db_session)
    _, method, authority = await _method_authority_graph(service)
    formula_version = await _formula_version(service)
    other_formula_version = await _formula_version(service)
    sequence = await service.create_analytical_sequence(
        _sequence_input(authority.id, formula_version.id)
    )
    entries = await service.repository.analytical_sequence_entries(sequence.id)
    sample_entry = next(entry for entry in entries if entry.role == "SAMPLE")
    run, vendor, open_export = await _run_with_raw_files(
        service,
        method.id,
        formula_version.id,
    )
    wrong_kind = await service.bind_analytical_attachment(
        AnalyticalAttachmentInput(
            analytical_run_id=run.id,
            attachment_kind="RAW_DATA",
            media_type="application/octet-stream",
            byte_length=10,
            content_sha256="d" * 64,
            storage_locator="artifact://b5/run/legacy-raw",
        )
    )
    ids = {
        "run": run.id,
        "method_authority": authority.id,
        "sequence": sequence.id,
        "entry": sample_entry.id,
        "formula": formula_version.id,
        "other_formula": other_formula_version.id,
        "vendor": vendor.id,
        "open": open_export.id,
        "wrong_kind": wrong_kind.id,
    }

    with pytest.raises(AnalyticalAuthorityConflictError) as mismatch:
        await service.bind_analytical_run_authority(
            _run_authority_input(
                ids["run"],
                ids["method_authority"],
                ids["sequence"],
                ids["entry"],
                ids["other_formula"],
                ids["vendor"],
                ids["open"],
            )
        )
    assert mismatch.value.code == "RUN_PRIMARY_SUBJECT_MISMATCH"

    with pytest.raises(AnalyticalAuthorityConflictError) as raw_kind:
        await service.bind_analytical_run_authority(
            _run_authority_input(
                ids["run"],
                ids["method_authority"],
                ids["sequence"],
                ids["entry"],
                ids["formula"],
                ids["wrong_kind"],
                ids["open"],
            )
        )
    assert raw_kind.value.code == "RAW_VENDOR_ATTACHMENT_INVALID"


async def _complete_run_authority_graph(
    service: LabService,
    *,
    qc_plan: dict | None = None,
    include_duplicate: bool = False,
    technique: str = "GCMS",
    hs_spme: dict | None = None,
):
    overrides = {"qc_plan": qc_plan} if qc_plan is not None else {}
    if hs_spme is not None:
        overrides["hs_spme"] = hs_spme
    source, method, method_authority = await _method_authority_graph(
        service,
        technique=technique,
        **overrides,
    )
    validation = await service.record_method_validation(
        _validation_input(method_authority.id, source.id)
    )
    formula_version = await _formula_version(service)
    sequence_command = _sequence_input(method_authority.id, formula_version.id)
    if include_duplicate:
        sequence_command = replace(
            sequence_command,
            entries=(
                *sequence_command.entries[:-1],
                AnalyticalSequenceEntryInput(
                    injection_order=5,
                    role="DUPLICATE",
                    reference=formula_version.id,
                    level={"replicate_of": formula_version.id},
                ),
                replace(sequence_command.entries[-1], injection_order=6),
            ),
        )
    sequence = await service.create_analytical_sequence(sequence_command)
    entries = await service.repository.analytical_sequence_entries(sequence.id)
    sample_entry = next(entry for entry in entries if entry.role == "SAMPLE")
    run, vendor, open_export = await _run_with_raw_files(
        service,
        method.id,
        formula_version.id,
        run_kind=technique,
    )
    run_authority = await service.bind_analytical_run_authority(
        _run_authority_input(
            run.id,
            method_authority.id,
            sequence.id,
            sample_entry.id,
            formula_version.id,
            vendor.id,
            open_export.id,
        )
    )
    return {
        "source": source,
        "method": method,
        "method_authority": method_authority,
        "validation": validation,
        "formula_version": formula_version,
        "sequence": sequence,
        "run": run,
        "run_authority": run_authority,
    }


async def _a2_confirmed_peak(service: LabService, run_id: str):
    material = await service.create_material("B5 analytical linalool")
    peak = await service.record_analytical_peak(
        AnalyticalPeakInput(
            analytical_run_id=run_id,
            peak_key="peak:linalool",
            retention_time_minutes=8.5,
            retention_index=1098.0,
            area=12000.0,
            response_factor=1.0,
            qualifier_ions=(71, 93, 121),
            tentative_identity="linalool",
            material_id=material.id,
            identity_state="CONFIRMED",
            match_score=0.98,
            quantitation_basis="calibrated_concentration",
            quantity=0.2,
            quantity_unit="mg/mL",
            standard_uncertainty=0.01,
            notes="B5 bounded fixture",
        )
    )
    return material, peak


def _peak_authority_input(
    peak_id: str,
    run_authority_id: str,
    material_id: str,
    method_authority_id: str,
    validation_id: str,
    matrix_scope_sha256: str,
    **overrides,
) -> AnalyticalPeakAuthorityInput:
    values = {
        "analytical_peak_id": peak_id,
        "analytical_run_authority_id": run_authority_id,
        "identity_state": "CONFIRMED_AUTHENTIC_STANDARD",
        "identity_label": "linalool",
        "stationary_phase": "5 percent phenyl",
        "spectrum": {
            "artifact_sha256": "e" * 64,
            "qualified_ions": [71, 93, 121],
        },
        "deconvolution": {
            "software": "test-software",
            "version": "1.0",
            "settings_sha256": "f" * 64,
        },
        "library_candidates": (
            {"name": "linalool", "score": 0.98, "library": "test-library"},
        ),
        "exact_mass": {"available": False, "reason": "unit-mass instrument"},
        "authentic_standard_state": "MATCHED",
        "co_injection_state": "MATCHED",
        "quantifier_ions": (71,),
        "coelution": {"state": "NOT_OBSERVED", "reviewed": True},
        "manual_review": {
            "reviewed": True,
            "reviewer_pseudonym": "reviewer-1",
        },
        "identity_decision": {
            "material_id": material_id,
            "basis": "authentic standard plus RI and spectrum",
        },
        "quantitation_state": "CALIBRATED_CONCENTRATION",
        "quantitation": {
            "calibration_reference": validation_id,
            "standard_reference": "external-standard-1",
            "response_factor": 1.0,
            "working_range": {
                "minimum": 0.01,
                "maximum": 1.0,
                "unit": "mg/mL",
            },
            "dilution_factor": 100.0,
            "blank_correction": 0.0,
            "qc_types": [
                "BLANK",
                "CALIBRATION_VERIFICATION",
                "INTERNAL_STANDARD",
                "RI_STANDARD",
            ],
            "quantity": 0.2,
            "quantity_unit": "mg/mL",
            "quantity_basis": "calibrated_concentration",
            "measurement_uncertainty": {
                "standard_uncertainty": 0.01,
                "unit": "mg/mL",
            },
            "matrix_calibration_id": matrix_scope_sha256,
            "analyte_calibration_id": material_id,
            "method_calibration_id": method_authority_id,
        },
        "applicability": {
            "matrix_scope_sha256": matrix_scope_sha256,
            "analyte_material_id": material_id,
            "method_authority_id": method_authority_id,
        },
        "reviewer_pseudonym": "reviewer-1",
        "reviewed_at": datetime(2026, 7, 31, 3, 0, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return AnalyticalPeakAuthorityInput(**values)


@pytest.mark.parametrize(
    "identity_state",
    [
        "CONFIRMED_AUTHENTIC_STANDARD",
        "STRONGLY_SUPPORTED_RI_PLUS_SPECTRUM",
        "PROBABLE",
        "TENTATIVE_LIBRARY_MATCH",
        "UNRESOLVED",
        "REJECTED",
    ],
)
def test_peak_authority_input_accepts_only_the_six_identity_states(
    identity_state,
):
    command = _peak_authority_input(
        "peak-1",
        "run-authority-1",
        "material-1",
        "method-authority-1",
        "validation-1",
        "a" * 64,
        identity_state=identity_state,
        identity_label=(
            None if identity_state in {"UNRESOLVED", "REJECTED"} else "linalool"
        ),
        quantitation_state="NONE",
        quantitation={"reason": "identity-state test"},
    )

    assert command.identity_state == identity_state


def test_calibrated_quantity_requires_every_authority_field():
    quantitation = dict(
        _peak_authority_input(
            "peak-1",
            "run-authority-1",
            "material-1",
            "method-authority-1",
            "validation-1",
            "a" * 64,
        ).quantitation
    )
    quantitation.pop("measurement_uncertainty")

    with pytest.raises(
        AnalyticalAuthorityError,
        match="measurement_uncertainty",
    ):
        _peak_authority_input(
            "peak-1",
            "run-authority-1",
            "material-1",
            "method-authority-1",
            "validation-1",
            "a" * 64,
            quantitation=quantitation,
        )


def test_area_percent_cannot_claim_formula_weight_percent():
    with pytest.raises(AnalyticalAuthorityError, match="area percent"):
        _peak_authority_input(
            "peak-1",
            "run-authority-1",
            "material-1",
            "method-authority-1",
            "validation-1",
            "a" * 64,
            quantitation_state="AREA_PERCENT_ONLY",
            quantitation={
                "area_percent": 12.0,
                "quantity_basis": "formula_weight_percent",
            },
        )


@pytest.mark.asyncio
async def test_confirmed_peak_requires_authentic_standard_and_persists_quantity(
    db_session,
):
    service = LabService(db_session)
    graph = await _complete_run_authority_graph(service)
    material, peak = await _a2_confirmed_peak(service, graph["run"].id)
    matrix_hash = graph["validation"].scope_sha256
    command = _peak_authority_input(
        peak.id,
        graph["run_authority"].id,
        material.id,
        graph["method_authority"].id,
        graph["validation"].id,
        matrix_hash,
    )

    peak_authority = await service.record_analytical_peak_authority(command)

    assert peak_authority.identity_state == "CONFIRMED_AUTHENTIC_STANDARD"
    assert peak_authority.quantitation_state == "CALIBRATED_CONCENTRATION"
    assert peak_authority.quantitation_json["quantity"] == 0.2
    assert len(peak_authority.content_sha256) == 64


@pytest.mark.asyncio
async def test_calibrated_peak_rejects_self_declared_wrong_applicability(
    db_session,
):
    service = LabService(db_session)
    graph = await _complete_run_authority_graph(service)
    material, peak = await _a2_confirmed_peak(service, graph["run"].id)
    command = _peak_authority_input(
        peak.id,
        graph["run_authority"].id,
        material.id,
        graph["method_authority"].id,
        graph["validation"].id,
        graph["validation"].scope_sha256,
    )
    wrong_scope = {
        **command.applicability,
        "analyte_material_id": "wrong-material",
    }

    with pytest.raises(AnalyticalAuthorityConflictError) as error:
        await service.record_analytical_peak_authority(
            replace(command, applicability=wrong_scope)
        )

    assert error.value.code == "PEAK_APPLICABILITY_MISMATCH"


@pytest.mark.asyncio
async def test_hs_spme_calibrated_peak_accepts_matching_validation_scope(
    db_session,
):
    service = LabService(db_session)
    graph = await _complete_run_authority_graph(
        service,
        technique="HS_SPME_GCMS",
        hs_spme=_hs_spme_conditions(),
    )
    material, peak = await _a2_confirmed_peak(service, graph["run"].id)

    authority = await service.record_analytical_peak_authority(
        _peak_authority_input(
            peak.id,
            graph["run_authority"].id,
            material.id,
            graph["method_authority"].id,
            graph["validation"].id,
            graph["validation"].scope_sha256,
        )
    )

    assert authority.quantitation_state == "CALIBRATED_CONCENTRATION"


@pytest.mark.asyncio
async def test_hs_spme_quantity_requires_matching_matrix_analyte_and_method(
    db_session,
):
    service = LabService(db_session)
    graph = await _complete_run_authority_graph(
        service,
        technique="HS_SPME_GCMS",
        hs_spme=_hs_spme_conditions(),
    )
    material, peak = await _a2_confirmed_peak(service, graph["run"].id)
    command = _peak_authority_input(
        peak.id,
        graph["run_authority"].id,
        material.id,
        graph["method_authority"].id,
        graph["validation"].id,
        graph["validation"].scope_sha256,
    )
    quantitation = dict(command.quantitation)
    quantitation["matrix_calibration_id"] = "wrong-matrix-calibration"

    with pytest.raises(AnalyticalAuthorityConflictError) as error:
        await service.record_analytical_peak_authority(
            replace(command, quantitation=quantitation)
        )

    assert error.value.code == "HS_SPME_CALIBRATION_SCOPE_MISMATCH"


@pytest.mark.asyncio
async def test_calibrated_quantity_requires_matching_calibration_scope(
    db_session,
):
    service = LabService(db_session)
    graph = await _complete_run_authority_graph(service)
    material, peak = await _a2_confirmed_peak(service, graph["run"].id)
    command = _peak_authority_input(
        peak.id,
        graph["run_authority"].id,
        material.id,
        graph["method_authority"].id,
        graph["validation"].id,
        graph["validation"].scope_sha256,
    )
    quantitation = dict(command.quantitation)
    quantitation["method_calibration_id"] = "wrong-method-authority"

    with pytest.raises(AnalyticalAuthorityConflictError) as error:
        await service.record_analytical_peak_authority(
            replace(command, quantitation=quantitation)
        )

    assert error.value.code == "CALIBRATION_SCOPE_MISMATCH"


@pytest.mark.asyncio
async def test_library_match_alone_cannot_be_promoted_to_probable(db_session):
    service = LabService(db_session)
    graph = await _complete_run_authority_graph(service)
    material, peak = await _a2_confirmed_peak(service, graph["run"].id)
    command = _peak_authority_input(
        peak.id,
        graph["run_authority"].id,
        material.id,
        graph["method_authority"].id,
        graph["validation"].id,
        graph["validation"].scope_sha256,
        identity_state="PROBABLE",
        spectrum={},
        exact_mass={},
        authentic_standard_state="NOT_RUN",
        co_injection_state="NOT_RUN",
        manual_review={"reviewed": True, "reviewer_pseudonym": "reviewer-1"},
        quantitation_state="NONE",
        quantitation={"reason": "identity-only test"},
    )

    with pytest.raises(AnalyticalAuthorityConflictError) as error:
        await service.record_analytical_peak_authority(command)
    assert error.value.code == "IDENTITY_EVIDENCE_INSUFFICIENT"


def _gco_authority_input(
    gco_event_id: str,
    run_authority_id: str,
    aligned_peak_id: str,
    **overrides,
) -> GCOEventAuthorityInput:
    values = {
        "gco_event_id": gco_event_id,
        "analytical_run_authority_id": run_authority_id,
        "assessor_training_state": "QUALIFIED",
        "window_basis": "RETENTION_TIME",
        "window_start": 8.4,
        "window_end": 8.6,
        "detection_method": "time-intensity",
        "replicate_index": 2,
        "replicate_count": 3,
        "detection_frequency": 2 / 3,
        "repeatability": {
            "window_tolerance_minutes": 0.1,
            "descriptor_consistent": True,
        },
        "aligned_peak_ids": (aligned_peak_id,),
        "unknown_event": False,
        "exact_identity_claim": False,
    }
    values.update(overrides)
    return GCOEventAuthorityInput(**values)


def test_gco_authority_forbids_exact_identity_claim():
    with pytest.raises(AnalyticalAuthorityError, match="cannot claim exact"):
        _gco_authority_input(
            "gco-event-1",
            "run-authority-1",
            "peak-1",
            exact_identity_claim=True,
        )


@pytest.mark.asyncio
async def test_gco_authority_preserves_window_training_and_alignment(db_session):
    service = LabService(db_session)
    graph = await _complete_run_authority_graph(service)
    _, peak = await _a2_confirmed_peak(service, graph["run"].id)
    event = await service.record_gco_event(
        GCOEventInput(
            analytical_run_id=graph["run"].id,
            analytical_peak_id=peak.id,
            event_key="gco:linalool",
            retention_time_minutes=8.5,
            retention_index=1098.0,
            descriptor="floral citrus",
            intensity=0.7,
            assessor_pseudonym="assessor-1",
            repeatability={"replicates": 3},
        )
    )

    authority = await service.record_gco_event_authority(
        _gco_authority_input(
            event.id,
            graph["run_authority"].id,
            peak.id,
        )
    )

    assert authority.assessor_training_state == "QUALIFIED"
    assert authority.window_start == 8.4
    assert authority.window_end == 8.6
    assert authority.detection_frequency == pytest.approx(2 / 3)
    assert authority.exact_identity_claim is False


async def _complete_peak_authority_graph(
    service: LabService,
    *,
    qc_plan: dict | None = None,
    include_duplicate: bool = False,
):
    graph = await _complete_run_authority_graph(
        service,
        qc_plan=qc_plan,
        include_duplicate=include_duplicate,
    )
    material, peak = await _a2_confirmed_peak(service, graph["run"].id)
    peak_authority = await service.record_analytical_peak_authority(
        _peak_authority_input(
            peak.id,
            graph["run_authority"].id,
            material.id,
            graph["method_authority"].id,
            graph["validation"].id,
            graph["validation"].scope_sha256,
        )
    )
    graph.update(
        {
            "material": material,
            "peak": peak,
            "peak_authority": peak_authority,
        }
    )
    return graph


async def _record_required_qc(
    service: LabService,
    run_id: str,
    evidence_id: str,
    *,
    status_by_type: dict[str, str] | None = None,
) -> None:
    statuses = status_by_type or {}
    for qc_type in (
        "BLANK",
        "CALIBRATION_VERIFICATION",
        "INTERNAL_STANDARD",
        "RI_STANDARD",
    ):
        status = statuses.get(qc_type, "PASS")
        await service.record_analytical_qc(
            AnalyticalQCInput(
                analytical_run_id=run_id,
                qc_key=f"qc:{qc_type.lower()}",
                qc_type=qc_type,
                status=status,
                criteria={"acceptance": "bounded method criterion"},
                observed={"result": status.lower()},
                evidence_record_id=evidence_id,
            )
        )


def _claim_request(graph: dict, **overrides) -> AnalyticalClaimRequest:
    values = {
        "analytical_run_authority_id": graph["run_authority"].id,
        "peak_authority_id": graph["peak_authority"].id,
        "claim_type": "QUANTITY",
        "policy_version": "b5-analytical-claim-v1",
        "requested_scope": {
            "matrix_scope_sha256": graph["validation"].scope_sha256,
            "analyte_material_id": graph["material"].id,
            "method_authority_id": graph["method_authority"].id,
        },
        "reviewer_pseudonym": "reviewer-1",
        "reviewed_at": datetime(2026, 7, 31, 3, 15, tzinfo=timezone.utc),
        "evidence_record_id": graph["method"].evidence_record_id,
    }
    values.update(overrides)
    return AnalyticalClaimRequest(**values)


@pytest.mark.parametrize(
    "requested_scope",
    [
        {
            "matrix_scope_sha256": "a" * 64,
            "analyte_material_id": "material-1",
        },
        {
            "matrix_scope_sha256": "a" * 64,
            "analyte_material_id": "material-1",
            "method_authority_id": "method-authority-1",
            "unbounded_context": "not-authoritative",
        },
    ],
)
def test_claim_request_requires_exact_applicability_scope_keys(
    requested_scope,
):
    with pytest.raises(AnalyticalAuthorityError):
        AnalyticalClaimRequest(
            analytical_run_authority_id="run-authority-1",
            peak_authority_id="peak-authority-1",
            claim_type="QUANTITY",
            policy_version="b5-analytical-claim-v1",
            requested_scope=requested_scope,
            reviewer_pseudonym="reviewer-1",
            reviewed_at=datetime(2026, 7, 31, 3, 15, tzinfo=timezone.utc),
            evidence_record_id="evidence-1",
        )


def test_claim_gate_code_vocabularies_are_closed_and_stable():
    assert ANALYTICAL_MISSING_REQUIREMENT_CODES == (
        "METHOD_AUTHORITY_MISSING",
        "METHOD_STATUS_INSUFFICIENT",
        "METHOD_VALIDATION_MISSING",
        "METHOD_VALIDATION_FAILED",
        "SEQUENCE_NOT_ACQUIRED",
        "RAW_VENDOR_DATA_MISSING",
        "OPEN_EXPORT_MISSING",
        "RUN_DISPOSITION_BLOCKING",
        "QC_REQUIRED_CHECK_MISSING",
        "QC_REQUIRED_CHECK_UNRESOLVED",
        "QC_FAILED_BLOCKING",
        "IDENTITY_EVIDENCE_INSUFFICIENT",
        "CALIBRATION_MISSING",
        "QUANTITATION_BASIS_INVALID",
        "UNCERTAINTY_MISSING",
        "APPLICABILITY_MISMATCH",
        "REVIEW_MISSING",
    )
    assert ANALYTICAL_QUALIFICATION_CODES == ("QC_FAILED_QUALIFYING",)


@pytest.mark.asyncio
async def test_quantity_claim_is_supported_only_for_the_complete_chain(
    db_session,
):
    service = LabService(db_session)
    graph = await _complete_peak_authority_graph(service)
    await _record_required_qc(
        service,
        graph["run"].id,
        graph["method"].evidence_record_id,
    )

    assessment = await service.assess_analytical_claim(_claim_request(graph))

    assert assessment.decision == "SUPPORTED_FOR_SCOPE"
    assert assessment.missing_requirements_json == []
    assert assessment.qualifications_json == []
    assert assessment.result_json["quantity"] == 0.2
    assert assessment.result_json["quantity_unit"] == "mg/mL"
    assert len(assessment.content_sha256) == 64


@pytest.mark.asyncio
async def test_quantity_claim_requires_quantity_specific_validation_criteria(
    db_session,
):
    service = LabService(db_session)
    graph = await _complete_peak_authority_graph(service)
    await _record_required_qc(
        service,
        graph["run"].id,
        graph["method"].evidence_record_id,
    )
    graph["validation"].acceptance_criteria_json = {
        "identity": "all qualified ions and RI within tolerance",
    }
    await db_session.flush()

    assessment = await service.assess_analytical_claim(_claim_request(graph))

    assert assessment.decision == "WITHHELD"
    assert assessment.missing_requirements_json == [
        "METHOD_VALIDATION_MISSING"
    ]
    assert assessment.result_json is None


@pytest.mark.asyncio
async def test_claim_gate_rejects_self_consistent_false_applicability(
    db_session,
):
    service = LabService(db_session)
    graph = await _complete_peak_authority_graph(service)
    await _record_required_qc(
        service,
        graph["run"].id,
        graph["method"].evidence_record_id,
    )
    wrong_scope = {
        **graph["peak_authority"].applicability_json,
        "method_authority_id": "wrong-method-authority",
    }
    graph["peak_authority"].applicability_json = wrong_scope
    await db_session.flush()

    assessment = await service.assess_analytical_claim(
        _claim_request(graph, requested_scope=wrong_scope)
    )

    assert assessment.decision == "WITHHELD"
    assert assessment.missing_requirements_json == ["APPLICABILITY_MISMATCH"]
    assert assessment.result_json is None


@pytest.mark.parametrize(
    ("scenario", "expected_code"),
    [
        ("method_authority_missing", "METHOD_AUTHORITY_MISSING"),
        ("method_status", "METHOD_STATUS_INSUFFICIENT"),
        ("validation_missing", "METHOD_VALIDATION_MISSING"),
        ("validation_failed", "METHOD_VALIDATION_FAILED"),
        ("sequence", "SEQUENCE_NOT_ACQUIRED"),
        ("raw_vendor", "RAW_VENDOR_DATA_MISSING"),
        ("open_export", "OPEN_EXPORT_MISSING"),
        ("run_disposition", "RUN_DISPOSITION_BLOCKING"),
        ("qc_unresolved", "QC_REQUIRED_CHECK_UNRESOLVED"),
        ("identity", "IDENTITY_EVIDENCE_INSUFFICIENT"),
        ("calibration", "CALIBRATION_MISSING"),
        ("quantitation_basis", "QUANTITATION_BASIS_INVALID"),
        ("uncertainty", "UNCERTAINTY_MISSING"),
        ("applicability", "APPLICABILITY_MISMATCH"),
        ("review", "REVIEW_MISSING"),
    ],
)
@pytest.mark.asyncio
async def test_claim_gate_reports_each_missing_dimension_exactly(
    db_session,
    monkeypatch,
    scenario,
    expected_code,
):
    service = LabService(db_session)
    graph = await _complete_peak_authority_graph(service)
    await _record_required_qc(
        service,
        graph["run"].id,
        graph["method"].evidence_record_id,
    )
    request = _claim_request(graph)

    if scenario == "method_authority_missing":
        async def missing_method_authority(_record_id):
            return None

        monkeypatch.setattr(
            service.repository,
            "get_analytical_method_authority",
            missing_method_authority,
        )
    elif scenario == "method_status":
        graph["method_authority"].status = "VERIFIED"
    elif scenario == "validation_missing":
        async def no_validation_records(_method_authority_id):
            return []

        monkeypatch.setattr(
            service.repository,
            "method_validation_records",
            no_validation_records,
        )
    elif scenario == "validation_failed":
        graph["validation"].result = "FAIL"
    elif scenario == "sequence":
        graph["sequence"].status = "PLANNED"
    elif scenario == "raw_vendor":
        attachment = await service.repository.get_analytical_attachment(
            graph["run_authority"].raw_vendor_attachment_id
        )
        attachment.attachment_kind = "OTHER"
    elif scenario == "open_export":
        attachment = await service.repository.get_analytical_attachment(
            graph["run_authority"].open_export_attachment_id
        )
        attachment.attachment_kind = "OTHER"
    elif scenario == "run_disposition":
        graph["run_authority"].disposition = "PENDING"
    elif scenario == "qc_unresolved":
        qc_records = await service.repository.analytical_qc_records(
            graph["run"].id
        )
        next(record for record in qc_records if record.qc_type == "BLANK").status = (
            "UNKNOWN"
        )
    elif scenario == "identity":
        graph["peak_authority"].identity_state = "PROBABLE"
    elif scenario == "calibration":
        quantitation = dict(graph["peak_authority"].quantitation_json)
        quantitation["calibration_reference"] = "missing-calibration"
        graph["peak_authority"].quantitation_json = quantitation
    elif scenario == "quantitation_basis":
        quantitation = dict(graph["peak_authority"].quantitation_json)
        quantitation["quantity_basis"] = "peak_area_percent"
        graph["peak_authority"].quantitation_json = quantitation
    elif scenario == "uncertainty":
        quantitation = dict(graph["peak_authority"].quantitation_json)
        quantitation["measurement_uncertainty"] = {}
        graph["peak_authority"].quantitation_json = quantitation
    elif scenario == "applicability":
        request = replace(
            request,
            requested_scope={
                **request.requested_scope,
                "method_authority_id": "wrong-method-authority",
            },
        )
    elif scenario == "review":
        graph["peak_authority"].reviewer_pseudonym = ""
    else:
        raise AssertionError(f"unhandled scenario: {scenario}")

    await db_session.flush()
    assessment = await service.assess_analytical_claim(request)

    assert assessment.decision == "WITHHELD"
    assert assessment.missing_requirements_json == [expected_code]
    assert assessment.result_json is None


@pytest.mark.asyncio
async def test_missing_required_qc_withholds_with_exact_requirement(db_session):
    service = LabService(db_session)
    graph = await _complete_peak_authority_graph(service)

    assessment = await service.assess_analytical_claim(_claim_request(graph))

    assert assessment.decision == "WITHHELD"
    assert assessment.missing_requirements_json == [
        "QC_REQUIRED_CHECK_MISSING"
    ]
    assert assessment.details_json["missing_qc_types"] == [
        "BLANK",
        "CALIBRATION_VERIFICATION",
        "INTERNAL_STANDARD",
        "RI_STANDARD",
    ]
    assert assessment.result_json is None


@pytest.mark.asyncio
async def test_blocking_failed_qc_withholds_numerical_result(db_session):
    service = LabService(db_session)
    graph = await _complete_peak_authority_graph(service)
    await _record_required_qc(
        service,
        graph["run"].id,
        graph["method"].evidence_record_id,
        status_by_type={"BLANK": "FAIL"},
    )

    assessment = await service.assess_analytical_claim(_claim_request(graph))

    assert assessment.decision == "WITHHELD"
    assert assessment.missing_requirements_json == ["QC_FAILED_BLOCKING"]
    assert assessment.details_json["blocking_qc_types"] == ["BLANK"]
    assert assessment.result_json is None


@pytest.mark.asyncio
async def test_qualifying_failed_qc_caps_claim_at_advisory(db_session):
    service = LabService(db_session)
    configuration = _method_configuration()
    qc_plan = {
        "required_checks": [
            *configuration["qc_plan"]["required_checks"],
            "DUPLICATE",
        ],
        "failure_policy": {
            **configuration["qc_plan"]["failure_policy"],
            "DUPLICATE": "QUALIFY",
        },
    }
    graph = await _complete_peak_authority_graph(
        service,
        qc_plan=qc_plan,
        include_duplicate=True,
    )
    evidence_id = graph["method"].evidence_record_id
    await _record_required_qc(service, graph["run"].id, evidence_id)
    await service.record_analytical_qc(
        AnalyticalQCInput(
            analytical_run_id=graph["run"].id,
            qc_key="qc:duplicate",
            qc_type="DUPLICATE",
            status="FAIL",
            criteria={"acceptance": "bounded duplicate precision"},
            observed={"result": "outside criterion"},
            evidence_record_id=evidence_id,
        )
    )

    assessment = await service.assess_analytical_claim(_claim_request(graph))

    assert assessment.decision == "ADVISORY_ONLY"
    assert assessment.missing_requirements_json == []
    assert assessment.qualifications_json == ["QC_FAILED_QUALIFYING"]
    assert assessment.details_json["qualifying_qc_types"] == ["DUPLICATE"]


def _a2_exact_analytical_claim(
    run_id: str,
    evidence_id: str,
    *,
    assessment_id: str | None,
    claim_type: str = "ANALYTICAL_QUANTITY",
    policy_version: str = "b5-analytical-claim-v1",
    direct_evidence_id: str | None = None,
) -> ClaimAssessmentInput:
    authority = (
        {"analytical_authority_assessment_id": assessment_id}
        if assessment_id is not None
        else {}
    )
    return ClaimAssessmentInput(
        schema_version="a2-claim-v1",
        claim_type=claim_type,
        subject_type="ANALYTICAL_RUN",
        subject_id=run_id,
        policy_version=policy_version,
        decision="ALLOW_EXACT",
        authority=authority,
        missing_evidence=(),
        conflicts=(),
        permitted_wording="Quantity supported for the exact run and scope",
        forbidden_wording="Formula weight percent equivalence",
        human_review_state="APPROVED",
        reviewer_pseudonym="reviewer-1",
        reviewed_at=datetime(2026, 7, 31, 3, 20, tzinfo=timezone.utc),
        evidence_links=(
            ClaimEvidenceInput(
                evidence_record_id=direct_evidence_id or evidence_id,
                role="DIRECT",
            ),
        ),
    )


@pytest.mark.asyncio
async def test_legacy_all_pass_qc_cannot_bypass_b5_assessment(db_session):
    service = LabService(db_session)
    graph = await _complete_peak_authority_graph(service)
    run_id = graph["run"].id
    evidence_id = graph["method"].evidence_record_id
    await _record_required_qc(service, run_id, evidence_id)
    supported = await service.assess_analytical_claim(_claim_request(graph))
    supported_id = supported.id

    with pytest.raises(ScienceAuthorityConflictError) as missing:
        await service.create_claim_assessment_version(
            _a2_exact_analytical_claim(
                run_id,
                evidence_id,
                assessment_id=None,
            )
        )
    assert missing.value.code == "ANALYTICAL_B5_AUTHORITY_REQUIRED"

    claim = await service.create_claim_assessment_version(
        _a2_exact_analytical_claim(
            run_id,
            evidence_id,
            assessment_id=supported_id,
        )
    )
    assert claim.decision == "ALLOW_EXACT"


@pytest.mark.parametrize(
    "mismatch",
    ["claim_type", "policy_version", "direct_evidence"],
)
@pytest.mark.asyncio
async def test_a2_exact_claim_requires_the_exact_matching_b5_assessment(
    db_session,
    mismatch,
):
    service = LabService(db_session)
    graph = await _complete_peak_authority_graph(service)
    run_id = graph["run"].id
    evidence_id = graph["method"].evidence_record_id
    await _record_required_qc(service, run_id, evidence_id)
    supported = await service.assess_analytical_claim(_claim_request(graph))
    overrides = {}
    if mismatch == "claim_type":
        overrides["claim_type"] = "ANALYTICAL_IDENTITY"
    elif mismatch == "policy_version":
        overrides["policy_version"] = "b5-analytical-claim-v2"
    else:
        other_evidence = await service.record_evidence(
            claim_key="b5:unrelated-direct-evidence",
            classification="EXACT",
            source_locator="test://b5-unrelated",
            source_version="1",
            method="bounded fixture",
            assumptions=(),
            limitations=(),
            payload_sha256=None,
        )
        overrides["direct_evidence_id"] = other_evidence.id

    with pytest.raises(ScienceAuthorityConflictError) as error:
        await service.create_claim_assessment_version(
            _a2_exact_analytical_claim(
                run_id,
                evidence_id,
                assessment_id=supported.id,
                **overrides,
            )
        )

    assert error.value.code == "ANALYTICAL_B5_AUTHORITY_REQUIRED"
