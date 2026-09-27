from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256

import pytest
from engine.sensory.panel_contract import REQUIRED_BINDING_IDS

from app.models.lab import APPEND_ONLY_TABLES, LAB_TABLE_NAMES
from app.models.lab_external_validation import EXTERNAL_VALIDATION_TABLE_NAMES
from app.services.external_validation import (
    ExternalValidationConflictError,
    ExternalValidationError,
)
from app.services.lab_service import LabService


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


ASSESSOR = _digest("assessor-1")
QUALIFICATION = _digest("qualification-1")
SESSION = _digest("session-1")
PROVENANCE = _digest("provenance-1")


def _protocol(*, authority_escalation: bool = False) -> dict:
    return {
        "schema_version": "lab-external-validation-protocol-v1",
        "protocol_id": "r6-external-validation-v1",
        "protocol_locked": True,
        "bindings": [
            {
                "binding_id": binding_id,
                "state": "bound",
                "sha256": _digest(f"binding:{binding_id}"),
            }
            for binding_id in REQUIRED_BINDING_IDS
        ],
        "endpoint_scales": [
            {
                "endpoint_id": "pleasantness",
                "minimum": "0",
                "maximum": "10",
                "unit": "ordinal_score",
            }
        ],
        "expected_temporal_cells": [
            {
                "blind_code": "A01",
                "assessor_token_sha256": ASSESSOR,
                "qualification_receipt_sha256": QUALIFICATION,
                "session_token_sha256": SESSION,
                "repeat_id": "repeat-1",
                "time_seconds": time_seconds,
                "endpoint_id": "pleasantness",
                "presentation_sequence_id": "sequence-1",
                "presentation_position": 1,
                "provenance_receipt_sha256": PROVENANCE,
            }
            for time_seconds in ("300", "600")
        ],
        "expected_pairwise_cells": [
            {
                "primary_blind_code": "A01",
                "secondary_blind_code": "B02",
                "assessor_token_sha256": ASSESSOR,
                "qualification_receipt_sha256": QUALIFICATION,
                "session_token_sha256": SESSION,
                "repeat_id": "repeat-1",
                "time_seconds": "300",
                "criterion_id": "liking",
                "presentation_sequence_id": "sequence-1",
                "first_presented_blind_code": "B02",
                "provenance_receipt_sha256": PROVENANCE,
            }
        ],
        "authority": {
            "scientific_authority": authority_escalation,
            "sensory_authority": False,
            "model_calibration_authority": False,
            "release_authority": False,
            "safety_authority": False,
            "compounding_authority": False,
            "evidence_admission_authorized": False,
        },
    }


async def _study(db_session, *, protocol: dict | None = None):
    service = LabService(db_session)
    experiment = await service.create_experiment(
        "R6 strict external-validation fixture",
        protocol=protocol or _protocol(),
        status="locked",
    )
    applications = []
    for index, blind_code in enumerate(("A01", "B02"), start=1):
        bottle = await service.create_bottle(f"Blind bottle {blind_code}")
        sample = await service.add_experiment_sample(
            experiment_id=experiment.id,
            bottle_id=bottle.id,
            blind_code=blind_code,
        )
        application = await service.record_application(
            sample_id=sample.id,
            applied_at=datetime(2026, 9, 27, 2, index, tzinfo=timezone.utc),
            dose={
                "mass_g": "0.01",
                "substrate": "standardized_mouillette",
                "preparation_receipt_sha256": _digest(f"preparation:{blind_code}"),
            },
            context={
                "protocol_id": "r6-external-validation-v1",
                "blind_code": blind_code,
                "assessor_token_sha256": ASSESSOR,
                "qualification_receipt_sha256": QUALIFICATION,
                "session_token_sha256": SESSION,
                "repeat_id": "repeat-1",
                "room_receipt_sha256": _digest("room-1"),
            },
        )
        applications.append(application)
    return service, experiment, tuple(applications)


def _temporal_request(application_id: str, **changes) -> dict:
    request = {
        "schema_version": "lab-external-validation-temporal-request-v1",
        "application_id": application_id,
        "requester": "unit-fixture",
        "idempotency_key": "temporal-1",
        "assessor_token_sha256": ASSESSOR,
        "qualification_receipt_sha256": QUALIFICATION,
        "session_token_sha256": SESSION,
        "provenance_receipt_sha256": PROVENANCE,
        "repeat_id": "repeat-1",
        "time_seconds": "300",
        "endpoint_id": "pleasantness",
        "presentation_sequence_id": "sequence-1",
        "presentation_position": 1,
        "missingness_state": "OBSERVED",
        "value": "7.5",
        "missing_reason": None,
    }
    request.update(changes)
    return request


def _pairwise_request(primary_id: str, secondary_id: str, **changes) -> dict:
    request = {
        "schema_version": "lab-external-validation-pairwise-request-v1",
        "primary_application_id": primary_id,
        "secondary_application_id": secondary_id,
        "requester": "unit-fixture",
        "idempotency_key": "pairwise-1",
        "assessor_token_sha256": ASSESSOR,
        "qualification_receipt_sha256": QUALIFICATION,
        "session_token_sha256": SESSION,
        "provenance_receipt_sha256": PROVENANCE,
        "repeat_id": "repeat-1",
        "time_seconds": "300",
        "criterion_id": "liking",
        "presentation_sequence_id": "sequence-1",
        "first_presented_application_id": secondary_id,
        "missingness_state": "OBSERVED",
        "preference_outcome": "TIE",
        "missing_reason": None,
    }
    request.update(changes)
    return request


def test_cp9_table_is_canonical_and_append_only() -> None:
    assert EXTERNAL_VALIDATION_TABLE_NAMES <= LAB_TABLE_NAMES
    assert EXTERNAL_VALIDATION_TABLE_NAMES <= APPEND_ONLY_TABLES


@pytest.mark.asyncio
async def test_temporal_intake_snapshots_every_scope_and_replays_exactly(db_session) -> None:
    service, experiment, applications = await _study(db_session)

    record, reused = await service.record_external_temporal_observation(
        **_temporal_request(applications[0].id)
    )
    replay, replayed = await service.record_external_temporal_observation(
        **_temporal_request(applications[0].id)
    )

    assert reused is False
    assert replayed is True
    assert replay.id == record.id
    assert record.experiment_id == experiment.id
    assert record.record_kind == "TEMPORAL_OBSERVATION"
    assert record.value_decimal_text == "7.5"
    assert record.protocol_snapshot_json["protocol"]["protocol_locked"] is True
    assert record.sample_snapshot_json["primary"]["blind_code"] == "A01"
    assert record.condition_snapshot_json["primary"]["dose"]["mass_g"] == "0.01"
    assert record.order_snapshot_json["presentation_position"] == 1
    assert record.assessor_snapshot_json["assessor_token_sha256"] == ASSESSOR
    assert record.provenance_snapshot_json["provenance_receipt_sha256"] == PROVENANCE
    for field in (
        "command_sha256",
        "canonical_cell_sha256",
        "protocol_scope_sha256",
        "sample_scope_sha256",
        "condition_scope_sha256",
        "order_scope_sha256",
        "assessor_scope_sha256",
        "provenance_scope_sha256",
        "record_sha256",
    ):
        assert len(getattr(record, field)) == 64
    for field in (
        "processing_allowed",
        "scientific_authority",
        "sensory_authority",
        "model_calibration_authority",
        "release_authority",
        "safety_authority",
        "compounding_authority",
        "evidence_admission_authorized",
    ):
        assert getattr(record, field) is False


@pytest.mark.asyncio
async def test_idempotency_and_canonical_cell_conflicts_fail_closed(db_session) -> None:
    service, _experiment, applications = await _study(db_session)
    application_id = applications[0].id
    await service.record_external_temporal_observation(
        **_temporal_request(application_id)
    )

    with pytest.raises(
        ExternalValidationConflictError,
        match="idempotency key",
    ) as idempotency:
        await service.record_external_temporal_observation(
            **_temporal_request(application_id, value="8")
        )
    assert idempotency.value.code == "EXTERNAL_VALIDATION_IDEMPOTENCY_CONFLICT"

    with pytest.raises(
        ExternalValidationConflictError,
        match="canonical observation cell",
    ) as cell:
        await service.record_external_temporal_observation(
            **_temporal_request(
                application_id,
                idempotency_key="temporal-2",
                value="8",
            )
        )
    assert cell.value.code == "EXTERNAL_VALIDATION_CELL_CONFLICT"


@pytest.mark.asyncio
async def test_explicit_missingness_and_pairwise_ties_are_preserved(db_session) -> None:
    service, _experiment, applications = await _study(db_session)

    missing, _ = await service.record_external_temporal_observation(
        **_temporal_request(
            applications[0].id,
            idempotency_key="temporal-missing",
            time_seconds="600",
            missingness_state="MISSING",
            value=None,
            missing_reason="assessor withdrew before this timepoint",
        )
    )
    pairwise, _ = await service.record_external_pairwise_preference(
        **_pairwise_request(applications[0].id, applications[1].id)
    )

    assert missing.value_decimal_text is None
    assert missing.missingness_state == "MISSING"
    assert missing.missing_reason == "assessor withdrew before this timepoint"
    assert pairwise.preference_outcome == "TIE"
    assert pairwise.sample_snapshot_json["primary"]["blind_code"] == "A01"
    assert pairwise.sample_snapshot_json["secondary"]["blind_code"] == "B02"
    assert pairwise.order_snapshot_json["first_presented_blind_code"] == "B02"


@pytest.mark.asyncio
async def test_undeclared_noncanonical_and_out_of_range_values_are_rejected(db_session) -> None:
    service, _experiment, applications = await _study(db_session)
    application_id = applications[0].id

    cases = (
        ("300.0", "7.5", "canonical plain-decimal"),
        ("-0", "7.5", "canonical plain-decimal"),
        ("300", "NaN", "finite"),
        ("300", "11", "outside"),
    )
    for index, (time_seconds, value, message) in enumerate(cases):
        with pytest.raises(ExternalValidationError, match=message):
            await service.record_external_temporal_observation(
                    **_temporal_request(
                        application_id,
                    idempotency_key=f"invalid-{index}",
                    time_seconds=time_seconds,
                    value=value,
                )
            )

    with pytest.raises(ExternalValidationError) as undeclared:
        await service.record_external_temporal_observation(
                **_temporal_request(
                    application_id,
                idempotency_key="undeclared",
                endpoint_id="intensity",
            )
        )
    assert undeclared.value.code in {
        "EXTERNAL_VALIDATION_CELL_NOT_DECLARED",
        "EXTERNAL_VALIDATION_ENDPOINT_NOT_DECLARED",
    }


@pytest.mark.asyncio
async def test_protocol_authority_escalation_is_rejected(
    db_session,
) -> None:
    escalated = deepcopy(_protocol(authority_escalation=True))
    service, _experiment, applications = await _study(
        db_session,
        protocol=escalated,
    )
    with pytest.raises(ExternalValidationError) as authority:
        await service.record_external_temporal_observation(
            **_temporal_request(applications[0].id)
        )
    assert authority.value.code == "EXTERNAL_VALIDATION_AUTHORITY_ESCALATION"


@pytest.mark.asyncio
async def test_request_schema_application_scope_and_raw_identity_fail_closed(
    db_session,
) -> None:
    service, _experiment, applications = await _study(db_session)
    application_id = applications[0].id

    with pytest.raises(ExternalValidationError) as schema:
        await service.record_external_temporal_observation(
            **_temporal_request(application_id, schema_version="future-schema")
        )
    assert schema.value.code == "INVALID_EXTERNAL_VALIDATION_REQUEST_SCHEMA"

    applications[0].context_json = {
        **applications[0].context_json,
        "participant_name": "raw identity must never enter canonical intake",
    }
    await db_session.flush()
    with pytest.raises(ExternalValidationError) as raw_identity:
        await service.record_external_temporal_observation(
            **_temporal_request(application_id, idempotency_key="raw-identity")
        )
    assert raw_identity.value.code == "EXTERNAL_VALIDATION_RAW_IDENTITY_PROHIBITED"


@pytest.mark.asyncio
async def test_unlocked_or_incompletely_bound_protocol_is_rejected(db_session) -> None:
    unlocked = _protocol()
    unlocked["protocol_locked"] = False
    service, _experiment, applications = await _study(db_session, protocol=unlocked)
    with pytest.raises(ExternalValidationError) as lock:
        await service.record_external_temporal_observation(
            **_temporal_request(applications[0].id)
        )
    assert lock.value.code == "EXTERNAL_VALIDATION_PROTOCOL_NOT_LOCKED"

    incomplete = _protocol()
    incomplete["bindings"] = incomplete["bindings"][:-1]
    service, _experiment, applications = await _study(
        db_session,
        protocol=incomplete,
    )
    with pytest.raises(ExternalValidationError) as bindings:
        await service.record_external_temporal_observation(
            **_temporal_request(
                applications[0].id,
                idempotency_key="incomplete-bindings",
            )
        )
    assert bindings.value.code == "EXTERNAL_VALIDATION_BINDINGS_INCOMPLETE"
