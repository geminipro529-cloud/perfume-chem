from __future__ import annotations


def _request(*, key: str = "api-key", amount: str = "100") -> dict:
    return {
        "schema_version": "lab-engine-job-request-v1",
        "job_type": "FORMULA_ANALYSIS",
        "idempotency_key": key,
        "requester": "api-fixture",
        "payload": {
            "formula_id": "formula-api",
            "formula_name": "API fixture",
            "rows": [
                {
                    "row_id": "row-1",
                    "material": "Linalool",
                    "amount_decimal": amount,
                    "amount_unit": "uL",
                    "stock_id": "stock-linalool",
                    "concentration_fraction_decimal": "1",
                    "concentration_basis": "NEAT",
                    "basket": "B1",
                    "operation": "DIRECT_ADD",
                }
            ],
            "final_volume_ml_decimal": "30",
        },
    }


async def test_engine_job_api_is_async_idempotent_and_cancellable(client) -> None:
    created = await client.post("/api/v1/lab/v2/engine-jobs", json=_request())
    assert created.status_code == 202
    body = created.json()
    assert body["state"] == "QUEUED"
    assert body["job_type"] == "FORMULA_ANALYSIS"
    assert body["events"][0]["state"] == "QUEUED"
    assert body["event_chain_verified"] is True
    assert body["result_hash_verified"] is None
    for key in (
        "release_authority",
        "safety_authority",
        "compounding_authority",
        "evidence_admission_authorized",
    ):
        assert body[key] is False

    replay = await client.post("/api/v1/lab/v2/engine-jobs", json=_request())
    assert replay.status_code == 202
    assert replay.json()["id"] == body["id"]

    mismatch = await client.post(
        "/api/v1/lab/v2/engine-jobs", json=_request(amount="101")
    )
    assert mismatch.status_code == 409
    assert mismatch.json()["error"]["code"] == "IDEMPOTENCY_COMMAND_MISMATCH"

    cancelled = await client.post(
        f"/api/v1/lab/v2/engine-jobs/{body['id']}/cancel",
        json={"requester": "api-fixture", "reason": "fixture stop"},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["state"] == "CANCELLED"

    fetched = await client.get(f"/api/v1/lab/v2/engine-jobs/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["result"]["terminal_state"] == "CANCELLED"
    assert fetched.json()["event_chain_verified"] is True
    assert fetched.json()["result_hash_verified"] is True


async def test_engine_job_api_rejects_arbitrary_execution_payload(client) -> None:
    request = _request(key="arbitrary")
    request["payload"] = {"module": "os", "function": "system", "shell": "whoami"}

    response = await client.post("/api/v1/lab/v2/engine-jobs", json=request)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_ENGINE_JOB_PAYLOAD"
