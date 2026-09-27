from datetime import datetime, timezone

import pytest

from tests.unit.test_b7_claim_authority_service import _property_case


@pytest.mark.asyncio
async def test_claim_authority_api_computes_decision_and_false_authority_flags(
    client,
    db_session,
):
    _service, legacy, assertion, identity, conditions = await _property_case(
        db_session
    )
    response = await client.post(
        "/api/v1/lab/v2/claim-authority-reviews",
        json={
            "schema_version": "lab-claim-authority-request-v1",
            "legacy_claim_assessment_version_id": legacy.id,
            "claim_payload": {
                "property_type": "DENSITY",
                "value": 0.85,
                "unit": "g/mL",
            },
            "identity_scope": identity,
            "condition_scope": conditions,
            "supports": [
                {
                    "support_kind": "PROPERTY_ASSERTION",
                    "record_id": assertion.id,
                    "role": "SUPPORTING",
                }
            ],
            "reviewer_pseudonym": "cp2-api-reviewer",
            "reviewed_at": datetime(
                2026, 9, 23, 0, 0, tzinfo=timezone.utc
            ).isoformat(),
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["schema_version"] == "lab-claim-authority-v1"
    assert payload["decision"] == "ALLOW_EXACT"
    assert payload["authority_scope"] == "SCIENTIFIC_CLAIM_ONLY"
    assert payload["release_authority"] is False
    assert payload["safety_authority"] is False
    assert payload["compounding_authority"] is False
    assert len(payload["policy_sha256"]) == 64
    assert len(payload["content_sha256"]) == 64


@pytest.mark.asyncio
async def test_claim_authority_api_forbids_caller_authority_fields(
    client,
    db_session,
):
    _service, legacy, assertion, identity, conditions = await _property_case(
        db_session
    )
    response = await client.post(
        "/api/v1/lab/v2/claim-authority-reviews",
        json={
            "schema_version": "lab-claim-authority-request-v1",
            "legacy_claim_assessment_version_id": legacy.id,
            "claim_payload": {"property_type": "DENSITY"},
            "identity_scope": identity,
            "condition_scope": conditions,
            "supports": [
                {
                    "support_kind": "PROPERTY_ASSERTION",
                    "record_id": assertion.id,
                    "role": "SUPPORTING",
                }
            ],
            "reviewer_pseudonym": "cp2-api-reviewer",
            "reviewed_at": "2026-09-23T00:00:00Z",
            "decision": "ALLOW_EXACT",
            "release_authority": True,
        },
    )

    assert response.status_code == 422
