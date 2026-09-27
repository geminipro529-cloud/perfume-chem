from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256

import pytest
from engine.sensory.panel_contract import REQUIRED_BINDING_IDS

from app.services.lab_export import LabExportService
from app.services.lab_service import LabService


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


ASSESSOR = _digest("api-assessor")
QUALIFICATION = _digest("api-qualification")
SESSION = _digest("api-session")
PROVENANCE = _digest("api-provenance")


def _protocol() -> dict:
    return {
        "schema_version": "lab-external-validation-protocol-v1",
        "protocol_id": "api-external-validation-v1",
        "protocol_locked": True,
        "bindings": [
            {
                "binding_id": binding_id,
                "state": "bound",
                "sha256": _digest(f"api-binding:{binding_id}"),
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
                "blind_code": "C03",
                "assessor_token_sha256": ASSESSOR,
                "qualification_receipt_sha256": QUALIFICATION,
                "session_token_sha256": SESSION,
                "repeat_id": "repeat-1",
                "time_seconds": "300",
                "endpoint_id": "pleasantness",
                "presentation_sequence_id": "api-sequence-1",
                "presentation_position": 1,
                "provenance_receipt_sha256": PROVENANCE,
            }
        ],
        "expected_pairwise_cells": [
            {
                "primary_blind_code": "C03",
                "secondary_blind_code": "D04",
                "assessor_token_sha256": ASSESSOR,
                "qualification_receipt_sha256": QUALIFICATION,
                "session_token_sha256": SESSION,
                "repeat_id": "repeat-1",
                "time_seconds": "300",
                "criterion_id": "liking",
                "presentation_sequence_id": "api-sequence-1",
                "first_presented_blind_code": "D04",
                "provenance_receipt_sha256": PROVENANCE,
            }
        ],
        "authority": {
            "scientific_authority": False,
            "sensory_authority": False,
            "model_calibration_authority": False,
            "release_authority": False,
            "safety_authority": False,
            "compounding_authority": False,
            "evidence_admission_authorized": False,
        },
    }


async def _applications(db_session):
    service = LabService(db_session)
    experiment = await service.create_experiment(
        "API strict external-validation fixture",
        protocol=_protocol(),
        status="locked",
    )
    applications = []
    for index, blind_code in enumerate(("C03", "D04"), start=1):
        bottle = await service.create_bottle(f"API bottle {blind_code}")
        sample = await service.add_experiment_sample(
            experiment_id=experiment.id,
            bottle_id=bottle.id,
            blind_code=blind_code,
        )
        applications.append(
            await service.record_application(
                sample_id=sample.id,
                applied_at=datetime(2026, 9, 27, 4, index, tzinfo=timezone.utc),
                dose={"mass_g": "0.01", "substrate": "standardized_mouillette"},
                context={
                    "protocol_id": "api-external-validation-v1",
                    "blind_code": blind_code,
                    "assessor_token_sha256": ASSESSOR,
                    "qualification_receipt_sha256": QUALIFICATION,
                    "session_token_sha256": SESSION,
                    "repeat_id": "repeat-1",
                },
            )
        )
    return tuple(applications)


def _temporal_payload(application_id: str) -> dict:
    return {
        "schema_version": "lab-external-validation-temporal-request-v1",
        "application_id": application_id,
        "requester": "api-fixture",
        "idempotency_key": "api-temporal-1",
        "assessor_token_sha256": ASSESSOR,
        "qualification_receipt_sha256": QUALIFICATION,
        "session_token_sha256": SESSION,
        "provenance_receipt_sha256": PROVENANCE,
        "repeat_id": "repeat-1",
        "time_seconds": "300",
        "endpoint_id": "pleasantness",
        "presentation_sequence_id": "api-sequence-1",
        "presentation_position": 1,
        "missingness_state": "OBSERVED",
        "value": "6.5",
        "missing_reason": None,
    }


@pytest.mark.asyncio
async def test_temporal_api_is_idempotent_private_and_non_authoritative(
    client,
    db_session,
) -> None:
    applications = await _applications(db_session)
    payload = _temporal_payload(applications[0].id)

    response = await client.post(
        "/api/v1/lab/v2/external-validation/temporal-observations",
        json=payload,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["write_state"] == "CREATED"
    assert body["record_kind"] == "TEMPORAL_OBSERVATION"
    assert body["value"] == "6.5"
    assert "assessor_token_sha256" not in body
    assert "protocol_snapshot_json" not in body
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
        assert body[field] is False

    replay = await client.post(
        "/api/v1/lab/v2/external-validation/temporal-observations",
        json=payload,
    )
    assert replay.status_code == 201
    assert replay.json()["id"] == body["id"]
    assert replay.json()["write_state"] == "REPLAYED"

    fetched = await client.get(
        f"/api/v1/lab/v2/external-validation/records/{body['id']}"
    )
    assert fetched.status_code == 200
    assert fetched.json()["write_state"] == "READ"
    assert fetched.json()["record_sha256"] == body["record_sha256"]

    changed = dict(payload)
    changed["value"] = "7"
    conflict = await client.post(
        "/api/v1/lab/v2/external-validation/temporal-observations",
        json=changed,
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == (
        "EXTERNAL_VALIDATION_IDEMPOTENCY_CONFLICT"
    )

    exporter = LabExportService(db_session)
    packet = await exporter.export_external_validation_workspace()
    before = await exporter.canonical_external_validation_bytes()
    imported = await exporter.import_workspace(packet)
    after = await exporter.canonical_external_validation_bytes()
    assert packet["format_revision"] == "lab-export-v5"
    assert len(packet["tables"]["lab_external_validation_records"]) == 1
    assert {
        "lab_build_plan_physical_bindings",
        "lab_engine_jobs",
        "lab_external_validation_records",
    } <= set(packet["tables"])
    assert imported.inserted == 0
    assert imported.skipped == sum(len(rows) for rows in packet["tables"].values())
    assert after == before


@pytest.mark.asyncio
async def test_pairwise_api_preserves_tie_and_rejects_caller_authority(
    client,
    db_session,
) -> None:
    applications = await _applications(db_session)
    payload = {
        "schema_version": "lab-external-validation-pairwise-request-v1",
        "primary_application_id": applications[0].id,
        "secondary_application_id": applications[1].id,
        "requester": "api-fixture",
        "idempotency_key": "api-pairwise-1",
        "assessor_token_sha256": ASSESSOR,
        "qualification_receipt_sha256": QUALIFICATION,
        "session_token_sha256": SESSION,
        "provenance_receipt_sha256": PROVENANCE,
        "repeat_id": "repeat-1",
        "time_seconds": "300",
        "criterion_id": "liking",
        "presentation_sequence_id": "api-sequence-1",
        "first_presented_application_id": applications[1].id,
        "missingness_state": "OBSERVED",
        "preference_outcome": "TIE",
        "missing_reason": None,
    }
    response = await client.post(
        "/api/v1/lab/v2/external-validation/pairwise-preferences",
        json=payload,
    )
    assert response.status_code == 201
    assert response.json()["preference_outcome"] == "TIE"

    payload["release_authority"] = True
    rejected = await client.post(
        "/api/v1/lab/v2/external-validation/pairwise-preferences",
        json=payload,
    )
    assert rejected.status_code == 422
