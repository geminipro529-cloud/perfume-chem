"""Checkpoint 16 immutable instrumental observation API."""

from __future__ import annotations

import pytest


def _payload(**overrides):
    payload = {
        "schema_version": "lab-instrumental-observation-request-v1",
        "requester": "cp16-test",
        "idempotency_key": "obs-key-1",
        "observation_id": "glass-run-1-t300-r1",
        "formula_sha256": "1" * 64,
        "inventory_sha256": "2" * 64,
        "stock_lot_bundle_sha256": "3" * 64,
        "preparation_receipt_sha256": "4" * 64,
        "release_scenario_sha256": "5" * 64,
        "deposit_decimal": "0.1",
        "deposit_unit": "g",
        "matrix_id": "ethanol-water-80-20",
        "substrate": "GLASS",
        "temperature_k_decimal": "298.15",
        "relative_humidity_decimal": "0.5",
        "airflow_m_s_decimal": "0.1",
        "surface_area_m2_decimal": "0.0001",
        "delivery_geometry_id": "sealed-vial-20ml",
        "sampling_method_id": "spme-v1",
        "instrument_id": "gcms-1",
        "calibration_receipt_sha256": "6" * 64,
        "blank_receipt_sha256": "7" * 64,
        "time_seconds_decimal": "300",
        "replicate_id": "replicate-1",
        "session_id": "session-1",
        "raw_data_sha256": "8" * 64,
        "processed_result_sha256": "9" * 64,
        "protocol_deviations": [],
    }
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
async def test_instrumental_observation_is_idempotent_immutable_and_authority_false(client):
    first = await client.post(
        "/api/v1/lab/v2/instrumental-observations", json=_payload()
    )
    assert first.status_code == 201, first.text
    created = first.json()
    assert created["write_state"] == "CREATED"
    assert created["review_state"] == "UNREVIEWED"
    assert created["deviation_state"] == "NONE_DECLARED"
    authority_keys = (
        "processing_allowed",
        "scientific_authority",
        "model_calibration_authority",
        "release_authority",
        "safety_authority",
        "compounding_authority",
        "evidence_admission_authorized",
    )
    assert all(created[key] is False for key in authority_keys)

    replay = await client.post(
        "/api/v1/lab/v2/instrumental-observations", json=_payload()
    )
    assert replay.status_code == 201
    assert replay.json()["write_state"] == "REPLAYED"
    assert replay.json()["id"] == created["id"]
    assert replay.json()["record_sha256"] == created["record_sha256"]

    fetched = await client.get(
        f"/api/v1/lab/v2/instrumental-observations/{created['id']}"
    )
    assert fetched.status_code == 200
    assert fetched.json()["write_state"] == "READ"
    assert fetched.json()["record_sha256"] == created["record_sha256"]

    conflict = await client.post(
        "/api/v1/lab/v2/instrumental-observations",
        json=_payload(raw_data_sha256="a" * 64),
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == (
        "INSTRUMENTAL_OBSERVATION_IDEMPOTENCY_CONFLICT"
    )


@pytest.mark.asyncio
async def test_instrumental_observation_preserves_protocol_deviations(client):
    response = await client.post(
        "/api/v1/lab/v2/instrumental-observations",
        json=_payload(
            idempotency_key="obs-key-deviation",
            observation_id="glass-run-1-t300-r2",
            replicate_id="replicate-2",
            protocol_deviations=["Airflow varied during the final 10 seconds."],
        ),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["deviation_state"] == "DECLARED"
    assert body["protocol_deviations"] == [
        "Airflow varied during the final 10 seconds."
    ]
    assert body["processing_allowed"] is False


@pytest.mark.asyncio
async def test_instrumental_observation_rejects_noncanonical_or_invalid_conditions(client):
    noncanonical = await client.post(
        "/api/v1/lab/v2/instrumental-observations",
        json=_payload(deposit_decimal="0.100"),
    )
    assert noncanonical.status_code == 422

    invalid_humidity = await client.post(
        "/api/v1/lab/v2/instrumental-observations",
        json=_payload(relative_humidity_decimal="1.1"),
    )
    assert invalid_humidity.status_code == 422

    forbidden_authority = _payload()
    forbidden_authority["release_authority"] = True
    authority = await client.post(
        "/api/v1/lab/v2/instrumental-observations",
        json=forbidden_authority,
    )
    assert authority.status_code == 422
