from dataclasses import replace

import pytest
from sqlalchemy import func, select

from app.models.lab_properties import LabPropertyObservation
from app.services.lab_properties import (
    AssertionCandidateInput,
    PropertyAuthorityConflictError,
    PropertyAuthorityError,
    PropertyConflictInput,
    PropertyObservationInput,
    SelectedAssertionInput,
)
from app.services.lab_service import LabService
from tests.unit.test_b1_source_service import (
    _accept_extraction,
    _extraction_input,
    _source_input,
)

PROPERTY_SCOPE = "property:vapor_pressure"


def _observation_input(
    observation_id: str,
    source_version_id: str,
    extraction_record_id: str,
    **overrides,
) -> PropertyObservationInput:
    values = {
        "observation_id": observation_id,
        "schema_version": "lab-property-observation-v1",
        "identity_scope": "CHEMICAL_ENTITY",
        "subject_identity": {
            "chemical_name": "Linalool",
            "cas": "78-70-6",
        },
        "property_type": "vapor_pressure",
        "value_kind": "NUMERIC",
        "numeric_value": 7.0,
        "categorical_value": None,
        "interval_lower": None,
        "interval_upper": None,
        "distribution": None,
        "censoring_qualifier": None,
        "censoring_limit": None,
        "original_unit": "Pa",
        "canonical_unit": "Pa",
        "temperature_k": 298.15,
        "pressure_pa": 101325.0,
        "relative_humidity_percent": 50.0,
        "matrix": "air",
        "phase": "gas",
        "purity_fraction": 0.99,
        "method": "published measurement",
        "source_version_id": source_version_id,
        "extraction_record_id": extraction_record_id,
        "source_locator": {"page": 12, "table": "2", "row": "Linalool"},
        "replicate_count": 3,
        "statistic": "mean",
        "standard_uncertainty": 0.5,
        "uncertainty_interval": {"coverage_factor": 2},
        "evidence_class": "MEASURED",
        "review_state": "REVIEWED",
        "quality_flags": (),
        "applicability_domain": {"matrix": "air"},
        "provenance_activity": {"actor": "reviewer-1"},
        "supersedes_observation_id": None,
        "required_scope": PROPERTY_SCOPE,
    }
    values.update(overrides)
    return PropertyObservationInput(**values)


async def _source_and_extraction(
    service: LabService,
    observation_id: str,
    *,
    digest_character: str = "1",
    scope: str = PROPERTY_SCOPE,
):
    source = await service.register_source_document(
        _source_input(
            title=f"Property source for {observation_id}",
            artifact_sha256=digest_character * 64,
            independence_group=f"lineage-{observation_id}",
        )
    )
    extraction = await service.record_source_extraction(
        _extraction_input(
            source.id,
            output_observation_id=observation_id,
            input_sha256="e" * 64,
            output_sha256=digest_character * 64,
        )
    )
    await _accept_extraction(service, extraction.id, scope=scope)
    return source, extraction


@pytest.mark.asyncio
async def test_property_observation_requires_exact_accepted_b1_linkage(db_session):
    service = LabService(db_session)
    source = await service.register_source_document(_source_input())
    extraction = await service.record_source_extraction(
        _extraction_input(
            source.id,
            output_observation_id="observation-exact",
        )
    )
    command = _observation_input(
        "observation-exact",
        source.id,
        extraction.id,
    )
    extraction_id = extraction.id

    with pytest.raises(PropertyAuthorityConflictError) as staged:
        await service.record_property_observation(command)
    assert staged.value.code == "PROPERTY_EXTRACTION_SCOPE_NOT_ACCEPTED"

    await _accept_extraction(service, extraction_id, scope=PROPERTY_SCOPE)
    created = await service.record_property_observation(command)

    assert created.id == "observation-exact"
    assert created.source_version_id == source.id
    assert created.extraction_record_id == extraction.id
    assert created.content_sha256

    wrong_source = await service.register_source_document(
        _source_input(
            title="Wrong source",
            artifact_sha256="d" * 64,
            independence_group="wrong-source",
        )
    )
    with pytest.raises(PropertyAuthorityConflictError) as mismatch:
        await service.record_property_observation(
            replace(
                command,
                observation_id="observation-source-mismatch",
                source_version_id=wrong_source.id,
            )
        )
    assert mismatch.value.code == "PROPERTY_EXTRACTION_SOURCE_MISMATCH"

    with pytest.raises(PropertyAuthorityConflictError) as reserved:
        await service.record_property_observation(
            replace(command, observation_id="observation-unreserved")
        )
    assert reserved.value.code == "PROPERTY_EXTRACTION_OBSERVATION_MISMATCH"


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        (
            {"identity_scope": "CAS_ONLY"},
            "identity_scope must be one of",
        ),
        (
            {"subject_identity": {"chemical_name": "Linalool"}},
            "subject_identity is missing required dimensions: cas",
        ),
        (
            {
                "value_kind": "NUMERIC",
                "numeric_value": 1.0,
                "categorical_value": "mixed",
            },
            "NUMERIC requires only numeric_value",
        ),
        (
            {
                "value_kind": "INTERVAL",
                "numeric_value": None,
                "interval_lower": 2.0,
                "interval_upper": 1.0,
            },
            "interval_lower must not exceed interval_upper",
        ),
        (
            {
                "value_kind": "CENSORED",
                "numeric_value": None,
                "censoring_qualifier": "LT_LOQ",
                "censoring_limit": None,
            },
            "censoring_limit is required",
        ),
        (
            {
                "value_kind": "CENSORED",
                "numeric_value": 0.0,
                "censoring_qualifier": "NOT_DETECTED",
            },
            "CENSORED must not contain typed values",
        ),
    ],
)
def test_property_observation_input_rejects_invalid_identity_and_value_shapes(
    overrides,
    message,
):
    with pytest.raises(PropertyAuthorityError, match=message):
        _observation_input(
            "observation-invalid",
            "source-version",
            "extraction-record",
            **overrides,
        )


def test_natural_material_identity_requires_every_preserved_dimension():
    complete = {
        "botanical_species": "Jasminum grandiflorum",
        "plant_part": "flowers",
        "chemotype": "explicitly unknown",
        "geographic_origin": "India",
        "harvest_or_production_period": "2025 season",
        "extraction_or_processing": "solvent extraction",
        "supplier_product": "Jasmine absolute",
        "supplier_lot": "LOT-42",
        "analytical_profile": "gcms-profile-1",
        "stock_solution": "stock-solution-1",
    }
    command = _observation_input(
        "observation-natural",
        "source-version",
        "extraction-record",
        identity_scope="NATURAL_MATERIAL",
        subject_identity=complete,
    )
    assert command.subject_identity == complete

    incomplete = dict(complete)
    incomplete.pop("chemotype")
    with pytest.raises(
        PropertyAuthorityError,
        match="subject_identity is missing required dimensions: chemotype",
    ):
        replace(command, subject_identity=incomplete)


@pytest.mark.asyncio
async def test_all_value_kinds_round_trip_and_not_detected_is_not_zero(db_session):
    service = LabService(db_session)
    cases = (
        ("numeric", {"numeric_value": 7.0}),
        (
            "categorical",
            {
                "value_kind": "CATEGORICAL",
                "numeric_value": None,
                "categorical_value": "insoluble",
            },
        ),
        (
            "interval",
            {
                "value_kind": "INTERVAL",
                "numeric_value": None,
                "interval_lower": 1.0,
                "interval_upper": 2.0,
            },
        ),
        (
            "distribution",
            {
                "value_kind": "DISTRIBUTION",
                "numeric_value": None,
                "distribution": {"kind": "normal", "mean": 7.0, "sd": 0.5},
            },
        ),
        (
            "not-detected",
            {
                "value_kind": "CENSORED",
                "numeric_value": None,
                "censoring_qualifier": "NOT_DETECTED",
            },
        ),
    )
    created = []
    for index, (suffix, overrides) in enumerate(cases, start=1):
        observation_id = f"observation-{suffix}"
        source, extraction = await _source_and_extraction(
            service,
            observation_id,
            digest_character=f"{index}",
        )
        created.append(
            await service.record_property_observation(
                _observation_input(
                    observation_id,
                    source.id,
                    extraction.id,
                    **overrides,
                )
            )
        )

    assert [item.value_kind for item in created] == [
        "NUMERIC",
        "CATEGORICAL",
        "INTERVAL",
        "DISTRIBUTION",
        "CENSORED",
    ]
    censored = created[-1]
    assert censored.numeric_value is None
    assert censored.censoring_qualifier == "NOT_DETECTED"
    assert censored.censoring_limit is None


@pytest.mark.asyncio
async def test_identity_hashes_distinguish_equal_cas_grades_and_lots(db_session):
    service = LabService(db_session)
    records = []
    identities = (
        (
            "TRADE_GRADE",
            {
                "chemical_name": "Linalool",
                "cas": "78-70-6",
                "grade": "natural ex bois de rose",
            },
        ),
        (
            "TRADE_GRADE",
            {
                "chemical_name": "Linalool",
                "cas": "78-70-6",
                "grade": "synthetic 97%",
            },
        ),
        (
            "SUPPLIER_LOT",
            {
                "supplier": "Supplier A",
                "supplier_product": "Linalool natural",
                "supplier_lot": "LOT-1",
            },
        ),
        (
            "SUPPLIER_LOT",
            {
                "supplier": "Supplier A",
                "supplier_product": "Linalool natural",
                "supplier_lot": "LOT-2",
            },
        ),
    )
    for index, (scope, identity) in enumerate(identities, start=6):
        observation_id = f"observation-identity-{index}"
        source, extraction = await _source_and_extraction(
            service,
            observation_id,
            digest_character=f"{index}",
        )
        records.append(
            await service.record_property_observation(
                _observation_input(
                    observation_id,
                    source.id,
                    extraction.id,
                    identity_scope=scope,
                    subject_identity=identity,
                )
            )
        )

    assert len({record.subject_identity_sha256 for record in records}) == 4


@pytest.mark.asyncio
async def test_property_observation_hashes_are_stable_and_duplicates_fail_closed(
    db_session,
):
    service = LabService(db_session)
    source, extraction = await _source_and_extraction(
        service,
        "observation-hashed",
        digest_character="a",
    )
    command = _observation_input(
        "observation-hashed",
        source.id,
        extraction.id,
    )
    created = await service.record_property_observation(command)
    content_sha256 = created.content_sha256

    with pytest.raises(PropertyAuthorityConflictError) as duplicate:
        await service.record_property_observation(command)
    assert duplicate.value.code == "PROPERTY_OBSERVATION_ALREADY_EXISTS"

    count = await db_session.scalar(
        select(func.count()).select_from(LabPropertyObservation)
    )
    assert count == 1
    assert len(content_sha256) == 64


async def _record_observation(
    service: LabService,
    observation_id: str,
    digest_character: str,
    *,
    numeric_value: float,
    method: str,
):
    source, extraction = await _source_and_extraction(
        service,
        observation_id,
        digest_character=digest_character,
    )
    return await service.record_property_observation(
        _observation_input(
            observation_id,
            source.id,
            extraction.id,
            numeric_value=numeric_value,
            method=method,
        )
    )


def _conflict_input(**overrides) -> PropertyConflictInput:
    values = {
        "conflict_set_id": "conflict-vapor-pressure",
        "schema_version": "lab-property-conflict-v1",
        "requested_identity_scope": "CHEMICAL_ENTITY",
        "requested_identity": {
            "chemical_name": "Linalool",
            "cas": "78-70-6",
        },
        "property_type": "vapor_pressure",
        "requested_conditions": {
            "temperature_k": 298.15,
            "matrix": "air",
        },
        "state": "UNRESOLVED",
        "materiality": "BLOCKING",
        "explanation": "Independent reviewed measurements disagree.",
    }
    values.update(overrides)
    return PropertyConflictInput(**values)


def _assertion_input(
    observation_a_id: str,
    observation_b_id: str,
    **overrides,
) -> SelectedAssertionInput:
    values = {
        "assertion_id": "assertion-vapor-pressure",
        "schema_version": "lab-selected-assertion-v1",
        "requested_identity_scope": "CHEMICAL_ENTITY",
        "requested_identity": {
            "chemical_name": "Linalool",
            "cas": "78-70-6",
        },
        "requested_property_type": "vapor_pressure",
        "requested_conditions": {
            "temperature_k": 298.15,
            "matrix": "air",
        },
        "conflict_set_id": "conflict-vapor-pressure",
        "selection_policy_version": "b2-reviewed-source-selection-v1",
        "selection_kind": "OBSERVATION",
        "selected_observation_id": observation_a_id,
        "selected_model": None,
        "interpolation_state": "EXACT",
        "propagated_uncertainty": {"standard_uncertainty": 0.5},
        "applicability": {"required_scope": PROPERTY_SCOPE},
        "authority_state": "WITHHELD_CONFLICT",
        "permitted_claim_wording": (
            "One reviewed observation is shown; authority is withheld "
            "because a material conflict remains unresolved."
        ),
        "candidates": (
            AssertionCandidateInput(
                observation_id=observation_a_id,
                decision="INCLUDE",
                rationale="Direct match to the requested conditions.",
            ),
            AssertionCandidateInput(
                observation_id=observation_b_id,
                decision="EXCLUDE",
                rationale="Conflicting value remains visible and unresolved.",
            ),
        ),
    }
    values.update(overrides)
    return SelectedAssertionInput(**values)


@pytest.mark.asyncio
async def test_conflict_sets_preserve_values_methods_and_source_independence(
    db_session,
):
    service = LabService(db_session)
    first = await _record_observation(
        service,
        "observation-conflict-a",
        "b",
        numeric_value=7.0,
        method="dynamic headspace",
    )
    second = await _record_observation(
        service,
        "observation-conflict-b",
        "c",
        numeric_value=11.0,
        method="static headspace",
    )

    conflict = await service.record_property_conflict(
        _conflict_input(),
        observation_ids=(first.id, second.id),
    )
    members = await service.repository.property_conflict_members(conflict.id)

    assert conflict.state == "UNRESOLVED"
    assert conflict.materiality == "BLOCKING"
    assert {
        "value",
        "method",
        "source_independence_group",
    } <= set(conflict.difference_dimensions_json)
    assert len(members) == 2
    assert len(
        {
            member.differences_json["source_independence_group"]
            for member in members
        }
    ) == 2
    assert {
        member.differences_json["numeric_value"] for member in members
    } == {7.0, 11.0}


@pytest.mark.asyncio
async def test_conflict_sets_require_two_unique_existing_observations(db_session):
    service = LabService(db_session)
    observation = await _record_observation(
        service,
        "observation-conflict-single",
        "d",
        numeric_value=7.0,
        method="dynamic headspace",
    )

    with pytest.raises(PropertyAuthorityError, match="at least two"):
        await service.record_property_conflict(
            _conflict_input(),
            observation_ids=(observation.id,),
        )
    with pytest.raises(PropertyAuthorityError, match="must not contain duplicates"):
        await service.record_property_conflict(
            _conflict_input(),
            observation_ids=(observation.id, observation.id),
        )
    with pytest.raises(PropertyAuthorityConflictError) as missing:
        await service.record_property_conflict(
            _conflict_input(),
            observation_ids=(observation.id, "missing-observation"),
        )
    assert missing.value.code == "PROPERTY_CONFLICT_OBSERVATION_NOT_FOUND"


@pytest.mark.asyncio
async def test_unresolved_blocking_conflict_withholds_selected_assertion_authority(
    db_session,
):
    service = LabService(db_session)
    first = await _record_observation(
        service,
        "observation-assertion-a",
        "e",
        numeric_value=7.0,
        method="dynamic headspace",
    )
    second = await _record_observation(
        service,
        "observation-assertion-b",
        "f",
        numeric_value=11.0,
        method="static headspace",
    )
    conflict = await service.record_property_conflict(
        _conflict_input(),
        observation_ids=(first.id, second.id),
    )
    first_id = first.id
    second_id = second.id
    conflict_id = conflict.id

    with pytest.raises(PropertyAuthorityConflictError) as authority:
        await service.record_selected_assertion(
            _assertion_input(
                first_id,
                second_id,
                authority_state="AUTHORIZED_FOR_SCOPED_PROPERTY",
            )
        )
    assert authority.value.code == "PROPERTY_ASSERTION_BLOCKING_CONFLICT"

    assertion = await service.record_selected_assertion(
        _assertion_input(first_id, second_id)
    )
    candidates = await service.repository.selected_assertion_candidates(
        assertion.id
    )

    assert assertion.conflict_set_id == conflict_id
    assert assertion.authority_state == "WITHHELD_CONFLICT"
    assert [(item.observation_id, item.decision) for item in candidates] == [
        (first_id, "INCLUDE"),
        (second_id, "EXCLUDE"),
    ]


@pytest.mark.asyncio
async def test_selected_assertion_requires_complete_consistent_candidates(db_session):
    service = LabService(db_session)
    first = await _record_observation(
        service,
        "observation-candidate-a",
        "1",
        numeric_value=7.0,
        method="dynamic headspace",
    )
    second = await _record_observation(
        service,
        "observation-candidate-b",
        "2",
        numeric_value=11.0,
        method="static headspace",
    )
    await service.record_property_conflict(
        _conflict_input(),
        observation_ids=(first.id, second.id),
    )
    first_id = first.id
    second_id = second.id

    with pytest.raises(
        PropertyAuthorityConflictError,
    ) as incomplete:
        await service.record_selected_assertion(
            _assertion_input(
                first_id,
                second_id,
                candidates=(
                    AssertionCandidateInput(
                        observation_id=first_id,
                        decision="INCLUDE",
                        rationale="Direct match.",
                    ),
                ),
            )
        )
    assert incomplete.value.code == "PROPERTY_ASSERTION_CANDIDATES_INCOMPLETE"

    with pytest.raises(
        PropertyAuthorityConflictError,
    ) as excluded:
        await service.record_selected_assertion(
            _assertion_input(
                first_id,
                second_id,
                candidates=(
                    AssertionCandidateInput(
                        observation_id=first_id,
                        decision="EXCLUDE",
                        rationale="Excluded.",
                    ),
                    AssertionCandidateInput(
                        observation_id=second_id,
                        decision="INCLUDE",
                        rationale="Included.",
                    ),
                ),
            )
        )
    assert excluded.value.code == "PROPERTY_ASSERTION_SELECTION_INCONSISTENT"

    with pytest.raises(PropertyAuthorityError, match="must not contain duplicates"):
        _assertion_input(
            first_id,
            second_id,
            candidates=(
                AssertionCandidateInput(
                    observation_id=first_id,
                    decision="INCLUDE",
                    rationale="First.",
                ),
                AssertionCandidateInput(
                    observation_id=first_id,
                    decision="EXCLUDE",
                    rationale="Duplicate.",
                ),
            ),
        )


@pytest.mark.asyncio
async def test_assertion_reconstruction_uses_explicit_id_and_preserves_lineage(
    db_session,
):
    service = LabService(db_session)
    first = await _record_observation(
        service,
        "observation-reconstruct-a",
        "3",
        numeric_value=7.0,
        method="dynamic headspace",
    )
    second = await _record_observation(
        service,
        "observation-reconstruct-b",
        "4",
        numeric_value=11.0,
        method="static headspace",
    )
    await service.record_property_conflict(
        _conflict_input(),
        observation_ids=(first.id, second.id),
    )
    assertion = await service.record_selected_assertion(
        _assertion_input(first.id, second.id)
    )

    reconstructed = await service.reconstruct_selected_assertion(
        assertion.id,
        required_scope=PROPERTY_SCOPE,
    )

    assert reconstructed["assertion"]["id"] == assertion.id
    assert reconstructed["assertion"]["selected_observation_id"] == first.id
    assert len(reconstructed["candidates"]) == 2
    assert all(
        candidate["derivation"]["complete"]
        for candidate in reconstructed["candidates"]
    )
    assert {
        candidate["observation"]["numeric_value"]
        for candidate in reconstructed["candidates"]
    } == {7.0, 11.0}
    assert reconstructed["conflict"]["state"] == "UNRESOLVED"
    assert not hasattr(service, "latest_selected_assertion")
    assert not hasattr(service.repository, "latest_selected_assertion")
