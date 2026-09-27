from __future__ import annotations


async def test_physical_lineage_api_is_strict_and_fails_closed(client) -> None:
    readiness = await client.get(
        "/api/v1/lab/v2/build-plans/missing-version/readiness"
    )
    assert readiness.status_code == 404
    assert readiness.json()["error"]["code"] == "BUILD_PLAN_NOT_FOUND"

    missing = await client.post(
        "/api/v1/lab/v2/build-plans/missing-version/commands/next",
        json={
            "schema_version": "lab-compounding-next-command-v1",
            "operator": "api-fixture",
            "idempotency_key": "next-missing",
        },
    )
    assert missing.status_code == 200
    hold = missing.json()
    assert hold["outcome"] == "ORDER_DRIFT_HOLD"
    assert hold["reason"] == "EXACT_PHYSICAL_BINDING_MISSING"
    assert hold["release_authority"] is False
    assert hold["safety_authority"] is False
    assert hold["compounding_authority"] is False

    caller_selected = await client.post(
        "/api/v1/lab/v2/build-plans/missing-version/commands/next",
        json={
            "schema_version": "lab-compounding-next-command-v1",
            "operator": "api-fixture",
            "idempotency_key": "caller-selected",
            "stock_id": "caller-must-not-select-this",
            "target_amount": "100",
        },
    )
    assert caller_selected.status_code == 422
