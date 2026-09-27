from __future__ import annotations


def _assert_receipt(receipt: dict, job_type: str) -> None:
    assert receipt["schema_version"] == (
        "lab-engine-job-compatibility-receipt-v2"
    )
    assert receipt["compatibility_state"] == "DURABLE_JOB_QUEUED"
    assert receipt["job_type"] == job_type
    assert receipt["job_state"] == "QUEUED"
    assert len(receipt["job_id"]) == 36
    assert len(receipt["job_fingerprint_sha256"]) == 64
    assert len(receipt["command_sha256"]) == 64
    assert receipt["durable_job_created"] is True
    assert receipt["durable_execution_performed"] is False
    assert receipt["durable_endpoint"] == (
        f"/api/v1/lab/v2/engine-jobs/{receipt['job_id']}"
    )
    assert receipt["release_authority"] is False
    assert receipt["safety_authority"] is False
    assert receipt["compounding_authority"] is False


async def test_legacy_optimizer_and_mixer_expose_fingerprinted_migration_receipts(
    client,
) -> None:
    optimizer = await client.post(
        "/api/v1/optimizer/score",
        json={
            "body": {
                "ingredients": {"Hedione": 60.0, "Iso E Super": 40.0}
            }
        },
    )
    assert optimizer.status_code == 200
    _assert_receipt(
        optimizer.json()["validation"]["engine_job_contract"],
        "FORMULA_ANALYSIS",
    )
    optimizer_receipt = optimizer.json()["validation"]["engine_job_contract"]
    queued = await client.get(optimizer_receipt["durable_endpoint"])
    assert queued.status_code == 200
    assert queued.json()["id"] == optimizer_receipt["job_id"]
    assert queued.json()["state"] == "QUEUED"

    mixer = await client.post(
        "/api/v1/mixer/sequence",
        json={
            "name": "Compatibility fixture",
            "rows": [
                {
                    "row_id": "b1-large",
                    "material": "Iso E Super",
                    "raw_ul": 100.0,
                    "basket": 1,
                    "operation": "DIRECT_ADD",
                },
                {
                    "row_id": "b1-small",
                    "material": "Hedione",
                    "raw_ul": 50.0,
                    "basket": 1,
                    "operation": "DIRECT_ADD",
                },
            ],
        },
    )
    assert mixer.status_code == 200
    receipt = mixer.json()["validation"]["engine_job_contract"]
    _assert_receipt(receipt, "MIXER_SEQUENCE")
    assert receipt["operation_scope"] == "mixer.sequence"
