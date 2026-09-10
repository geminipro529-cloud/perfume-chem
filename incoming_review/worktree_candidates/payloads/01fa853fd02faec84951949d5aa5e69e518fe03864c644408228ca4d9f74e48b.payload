from __future__ import annotations

from dataclasses import replace
from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.models.lab_external_studies import (
    LabExternalObservation,
    LabExternalStudyVersion,
)
from app.services.lab_external_studies import (
    ExternalConditionInput,
    ExternalExperimentalUnitInput,
    ExternalIdentityCrosswalkInput,
    ExternalObservationInput,
    ExternalStimulusComponentInput,
    ExternalStimulusInput,
    ExternalStudyAdmissionError,
    ExternalStudyInput,
)
from app.services.lab_service import LabService
from app.services.lab_sources import (
    ExtractionRecordInput,
    SourceDocumentInput,
    SourceUseConstraintInput,
    SourceUseRequest,
)

SCOPE = "EXTERNAL_STUDY_ADMISSION"


def _uuid() -> str:
    return str(uuid4())


def _source_input() -> SourceDocumentInput:
    return SourceDocumentInput(
        schema_version="lab-source-document-v2",
        source_type="PRIMARY_RESEARCH_DATASET",
        title="External mixture psychophysics dataset",
        artifact_sha256="a" * 64,
        language="en",
        review_state="REVIEWED",
        independence_group="study-family-a",
        authors=("A. Researcher",),
        identifiers={"doi": "10.1000/external-study"},
        retrieval_date=date(2026, 8, 10),
        default_locator={"artifact_id": "dataset-v1"},
        rights={
            "reuse_status": "PERMITTED",
            "license_or_reuse_restriction": "internal analysis permitted",
            "license_url": "https://example.test/terms",
            "redistribution_allowed": False,
            "spdx_identifier": None,
            "notes": "Internal methods analysis only.",
        },
    )


def _use_request(source_version_id: str) -> SourceUseRequest:
    return SourceUseRequest(
        subject_source_version_id=source_version_id,
        artifact_scope="DATASET",
        artifact_locator={"artifact_id": "dataset-v1"},
        channel="official-dataset",
        intended_action="INTERNAL_ANALYSIS",
        purpose_context="external-study-admission",
        as_of_date=date(2026, 8, 10),
        requested_records=7,
        attribution_planned=True,
    )


async def _accept(
    service: LabService,
    subject_type: str,
    subject_id: str,
) -> None:
    for state in (
        "PARSED",
        "IDENTITY_RESOLVED",
        "UNIT_NORMALIZED",
        "CONDITION_NORMALIZED",
        "CONFLICT_CHECKED",
        "HUMAN_REVIEWED",
    ):
        await service.transition_evidence_workflow(
            subject_type=subject_type,
            subject_id=subject_id,
            to_state=state,
            reviewer_pseudonym=("reviewer" if state == "HUMAN_REVIEWED" else None),
            scopes=(),
            reason=f"advance to {state}",
        )
    await service.transition_evidence_workflow(
        subject_type=subject_type,
        subject_id=subject_id,
        to_state="ACCEPTED_FOR_SCOPED_USE",
        reviewer_pseudonym="reviewer",
        scopes=(SCOPE,),
        reason="accepted for source-scoped external-study admission",
    )


async def _prepare_source(service: LabService):
    source = await service.register_source_document(_source_input())
    await _accept(service, "SOURCE_VERSION", source.id)
    await service.register_source_use_constraint(
        SourceUseConstraintInput(
            subject_source_version_id=source.id,
            terms_source_version_id=source.id,
            artifact_scope="DATASET",
            artifact_locator={"artifact_id": "dataset-v1"},
            channel="official-dataset",
            intended_action="INTERNAL_ANALYSIS",
            purpose_context="external-study-admission",
            decision="DECLARED_ALLOWED",
            constraints={
                "max_records": 7,
                "attribution_required": True,
            },
            terms_retrieval_date=date(2026, 8, 10),
            review_state="REVIEWED",
            reviewer_pseudonym="rights-reviewer",
            legal_review_required=False,
        )
    )
    return source


async def _extraction(
    service: LabService,
    source_version_id: str,
    output_id: str,
    ordinal: int,
):
    extraction = await service.record_source_extraction(
        ExtractionRecordInput(
            source_version_id=source_version_id,
            locator={"sheet": "data", "row": ordinal},
            structure_context={"record_kind": "external-study-row"},
            original_wording=f"source row {ordinal}",
            original_value={"row": ordinal},
            parsed_value={"row": ordinal},
            normalization={"state": "SOURCE_PRESERVED"},
            parser_or_model_version="external-study-test-adapter/1",
            reviewer_pseudonym="reviewer",
            uncertainty={"state": "NOT_REPORTED"},
            ambiguity=(),
            output_observation_id=output_id,
            input_sha256=f"{ordinal:064x}",
            output_sha256=f"{ordinal + 100:064x}",
        )
    )
    await _accept(service, "EXTRACTION_RECORD", extraction.id)
    return extraction


async def _valid_command(service: LabService) -> ExternalStudyInput:
    source = await _prepare_source(service)
    ids = {name: _uuid() for name in (
        "study", "stimulus", "component", "condition", "unit", "observation", "crosswalk"
    )}
    extractions = {}
    for ordinal, name in enumerate(ids, start=1):
        extractions[name] = await _extraction(
            service,
            source.id,
            ids[name],
            ordinal,
        )
    return ExternalStudyInput(
        record_id=ids["study"],
        study_id=_uuid(),
        study_key="ma-2021",
        source_version_id=source.id,
        source_extraction_id=extractions["study"].id,
        source_family="study-family-a",
        title="Human binary-mixture ratings",
        study_domain="HUMAN_SENSORY",
        design={"participant_trial_nesting": True},
        protocol={"matrix": "source reported"},
        source_use_request=_use_request(source.id),
        stimuli=(
            ExternalStimulusInput(
                record_id=ids["stimulus"],
                stimulus_key="stimulus-1",
                source_extraction_id=extractions["stimulus"].id,
                stimulus_kind="MIXTURE",
                label="binary mixture 1",
                matrix={"state": "SOURCE_REPORTED", "name": "air"},
                preparation={"state": "SOURCE_REPORTED"},
                context={"source_stimulus_id": "1"},
            ),
        ),
        components=(
            ExternalStimulusComponentInput(
                record_id=ids["component"],
                stimulus_version_id=ids["stimulus"],
                position=1,
                component_key="odorant-a",
                source_extraction_id=extractions["component"].id,
                source_identity={"label": "Odorant A"},
                quantity_value_text=None,
                quantity_unit=None,
                quantity_basis=None,
                concentration_value_text="1.25",
                concentration_unit="ppm",
                concentration_basis="SOURCE_REPORTED",
                carrier={"state": "NOT_REPORTED"},
                purity={"state": "NOT_REPORTED"},
                role="COMPONENT",
            ),
        ),
        conditions=(
            ExternalConditionInput(
                record_id=ids["condition"],
                condition_key="condition-1",
                source_extraction_id=extractions["condition"].id,
                condition_role="TEST",
                label="binary test condition",
                primary_stimulus_version_id=ids["stimulus"],
                factors={"ratio": "SOURCE_REPORTED"},
                context={"experiment": 1},
            ),
        ),
        experimental_units=(
            ExternalExperimentalUnitInput(
                record_id=ids["unit"],
                unit_key="participant-001",
                source_extraction_id=extractions["unit"].id,
                unit_grain="PARTICIPANT",
                parent_unit_id=None,
                pseudonymous_token="participant-001",
                reported_n=1,
                context={"cohort": "trained"},
            ),
        ),
        observations=(
            ExternalObservationInput(
                record_id=ids["observation"],
                observation_key="participant-001-trial-001-intensity",
                source_extraction_id=extractions["observation"].id,
                condition_id=ids["condition"],
                experimental_unit_id=ids["unit"],
                primary_stimulus_version_id=ids["stimulus"],
                trial_key="trial-001",
                session_key="session-1",
                repeat_index=1,
                presentation=(
                    {
                        "position": 1,
                        "stimulus_version_id": ids["stimulus"],
                        "role": "TARGET",
                    },
                ),
                endpoint_key="intensity",
                value={"value": "7"},
                original_unit="score",
                scale={"minimum": 0, "maximum": 10},
                timepoint={"label": "immediate"},
                replicate_index=1,
                observation_grain="INDIVIDUAL",
                aggregation_statistic="RAW",
                missingness="OBSERVED",
                uncertainty={"state": "NOT_REPORTED"},
                limitations=(),
            ),
        ),
        crosswalks=(
            ExternalIdentityCrosswalkInput(
                record_id=ids["crosswalk"],
                component_id=ids["component"],
                source_extraction_id=extractions["crosswalk"].id,
                resolution_status="EXACT_EXTERNAL_IDENTITY_ONLY",
                material_id=None,
                source_identity={"label": "Odorant A"},
                resolved_identity={"source_local_id": "odorant-a"},
                evidence={"route": "SOURCE_LITERAL"},
            ),
        ),
        conflicts=(),
        adapter_name="external-study-test-adapter",
        adapter_version="1",
        adapter_config={"strict": True},
    )


@pytest.mark.asyncio
async def test_external_study_admission_preserves_grain_and_is_source_only(db_session):
    service = LabService(db_session)
    result = await service.register_external_study(await _valid_command(service))

    assert result.study.authority_state == "SOURCE_REPORTED_ONLY"
    assert result.projection["study"]["record_sha256"] == result.study.record_sha256
    assert result.projection["observations"][0]["observation_grain"] == "INDIVIDUAL"
    assert result.projection["observations"][0]["trial_key"] == "trial-001"
    assert result.projection["observations"][0]["presentation"][0]["position"] == 1
    assert result.projection["authority"] == {
        "formula": False,
        "inventory": False,
        "physical_execution": False,
        "model_training": False,
        "sensory_truth": False,
        "release": False,
    }
    assert result.projection_sha256 == result.projection["projection_sha256"]


@pytest.mark.asyncio
async def test_external_study_admission_rejects_nonmatching_rights_without_rows(db_session):
    service = LabService(db_session)
    command = await _valid_command(service)
    blocked = replace(
        command,
        source_use_request=replace(command.source_use_request, channel="wrong-channel"),
    )

    with pytest.raises(ExternalStudyAdmissionError) as error:
        await service.register_external_study(blocked)
    assert error.value.code == "EXTERNAL_STUDY_SOURCE_USE_NOT_ALLOWED"
    count = await db_session.scalar(select(func.count()).select_from(LabExternalStudyVersion))
    assert count == 0


@pytest.mark.asyncio
async def test_external_study_admission_rejects_pseudoreplication_and_cross_study_refs(db_session):
    service = LabService(db_session)
    command = await _valid_command(service)
    aggregate_unit = replace(
        command.experimental_units[0],
        unit_grain="AGGREGATE",
        pseudonymous_token=None,
        reported_n=30,
    )
    pseudo_individual = replace(
        command.observations[0],
        observation_grain="INDIVIDUAL",
    )
    invalid = replace(
        command,
        experimental_units=(aggregate_unit,),
        observations=(pseudo_individual,),
    )
    with pytest.raises(ExternalStudyAdmissionError) as error:
        await service.register_external_study(invalid)
    assert error.value.code == "EXTERNAL_STUDY_GRAIN_MISMATCH"

    foreign_stimulus = replace(
        command.observations[0],
        presentation=(
            {
                "position": 1,
                "stimulus_version_id": _uuid(),
                "role": "TARGET",
            },
        ),
    )
    with pytest.raises(ExternalStudyAdmissionError) as error:
        await service.register_external_study(
            replace(command, observations=(foreign_stimulus,))
        )
    assert error.value.code == "EXTERNAL_STUDY_REFERENCE_OUTSIDE_GRAPH"


@pytest.mark.asyncio
async def test_external_study_admission_preserves_aggregate_and_missing_grain(db_session):
    service = LabService(db_session)
    command = await _valid_command(service)
    aggregate_unit = replace(
        command.experimental_units[0],
        unit_grain="AGGREGATE",
        pseudonymous_token=None,
        reported_n=30,
    )
    missing_aggregate = replace(
        command.observations[0],
        observation_grain="STUDY_AGGREGATE",
        aggregation_statistic="MEAN",
        missingness="NOT_REPORTED",
        value=None,
        original_unit="NOT_REPORTED",
    )
    result = await service.register_external_study(
        replace(
            command,
            experimental_units=(aggregate_unit,),
            observations=(missing_aggregate,),
        )
    )
    observation = result.projection["observations"][0]
    assert observation["observation_grain"] == "STUDY_AGGREGATE"
    assert observation["missingness"] == "NOT_REPORTED"
    assert observation["value"] is None


@pytest.mark.asyncio
async def test_external_study_admission_rejects_source_family_and_identity_leakage(db_session):
    service = LabService(db_session)
    command = await _valid_command(service)
    with pytest.raises(ExternalStudyAdmissionError) as family_error:
        await service.register_external_study(
            replace(command, source_family="another-study-family")
        )
    assert family_error.value.code == "EXTERNAL_STUDY_SOURCE_FAMILY_LEAKAGE"

    bad_crosswalk = replace(
        command.crosswalks[0],
        source_identity={"label": "Another identity"},
    )
    with pytest.raises(ExternalStudyAdmissionError) as identity_error:
        await service.register_external_study(
            replace(command, crosswalks=(bad_crosswalk,))
        )
    assert identity_error.value.code == "EXTERNAL_STUDY_IDENTITY_CROSSWALK_MISMATCH"


@pytest.mark.asyncio
async def test_external_study_projection_is_deterministic_and_tamper_evident(db_session):
    service = LabService(db_session)
    result = await service.register_external_study(await _valid_command(service))
    replay = await service.external_study_projection(result.study.id)
    assert replay == result.projection

    await db_session.execute(
        LabExternalObservation.__table__.update()
        .where(LabExternalObservation.id == result.observations[0].id)
        .values(endpoint_key="tampered")
    )
    with pytest.raises(ExternalStudyAdmissionError) as error:
        await service.external_study_projection(result.study.id)
    assert error.value.code == "EXTERNAL_STUDY_RECORD_HASH_MISMATCH"
