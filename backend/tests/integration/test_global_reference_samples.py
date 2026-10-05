"""Global-reference sample API stays exact, lightweight, and immutable."""

from __future__ import annotations

import pytest
from engine.research.commercial_references import load_commercial_reference_registry


async def _sample_id(client) -> str:
    bottle = await client.post(
        "/api/v1/lab/bottles",
        json={"label": "Commercial reference bottle", "initial_mass_g": 0.0},
    )
    assert bottle.status_code == 201, bottle.text
    experiment = await client.post(
        "/api/v1/lab/experiments",
        json={"name": "Quick reference", "protocol": {"mode": "QUICK_REFERENCE"}},
    )
    assert experiment.status_code == 201, experiment.text
    sample = await client.post(
        f"/api/v1/lab/experiments/{experiment.json()['id']}/samples",
        json={"bottle_id": bottle.json()["id"], "blind_code": "482"},
    )
    assert sample.status_code == 201, sample.text
    return str(sample.json()["id"])


def _payload(sample_id: str, **overrides):
    registry = load_commercial_reference_registry()
    payload = {
        "schema_version": "commercial-reference-sample-request-v1",
        "requester": "personal-reference-test",
        "idempotency_key": "reference-link-1",
        "sample_id": sample_id,
        "product_id": "prada-luna-rossa-carbon-edt",
        "concentration": "Eau de Toilette",
        "edition": "Eau de Toilette",
        "sample_identifier": "prada-carbon-decant-1",
        "registry_sha256": registry.registry_sha256,
        "authenticity_documentation_state": "NOT_PROVIDED_PERSONAL_MODE",
    }
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
async def test_commercial_reference_sample_link_is_lightweight_exact_and_idempotent(client):
    sample_id = await _sample_id(client)
    first = await client.post(
        "/api/v1/lab/v2/commercial-reference-samples",
        json=_payload(sample_id),
    )
    assert first.status_code == 201, first.text
    created = first.json()
    assert created["write_state"] == "CREATED"
    assert created["photograph_required"] is False
    assert created["purchase_source"] is None
    assert created["batch_code"] is None
    assert created["release_authority"] is False
    assert created["evidence_admission_authorized"] is False

    replay = await client.post(
        "/api/v1/lab/v2/commercial-reference-samples",
        json=_payload(sample_id),
    )
    assert replay.status_code == 201
    assert replay.json()["write_state"] == "REPLAYED"
    assert replay.json()["id"] == created["id"]

    fetched = await client.get(
        f"/api/v1/lab/v2/commercial-reference-samples/{created['id']}"
    )
    assert fetched.status_code == 200
    assert fetched.json()["write_state"] == "READ"

    conflict = await client.post(
        "/api/v1/lab/v2/commercial-reference-samples",
        json=_payload(sample_id, sample_identifier="different-bytes"),
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == (
        "COMMERCIAL_REFERENCE_IDEMPOTENCY_CONFLICT"
    )


@pytest.mark.asyncio
async def test_commercial_reference_sample_requires_exact_edition_not_a_photo(client):
    sample_id = await _sample_id(client)
    wrong = await client.post(
        "/api/v1/lab/v2/commercial-reference-samples",
        json=_payload(
            sample_id,
            idempotency_key="wrong-edition",
            edition="Parfum",
        ),
    )
    assert wrong.status_code == 409
    assert wrong.json()["error"]["code"] == (
        "COMMERCIAL_REFERENCE_PRODUCT_VERSION_MISMATCH"
    )

    unwanted_photo = _payload(sample_id, idempotency_key="photo-field")
    unwanted_photo["photo"] = "not-required"
    invalid = await client.post(
        "/api/v1/lab/v2/commercial-reference-samples",
        json=unwanted_photo,
    )
    assert invalid.status_code == 422
