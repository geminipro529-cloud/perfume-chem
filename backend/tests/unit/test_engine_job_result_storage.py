"""Job results are stored compressed, and read back exactly (Phase 5 finding 5).

A composed formula's result is 250-370 KB of JSON with large repeated sections.
Stored plain, lab.db grew by about 222 KB for every composed perfume.
"""

from __future__ import annotations

import json

import pytest
from sqlalchemy import text

from app.services.lab_service import LabService


def _formula_payload() -> dict:
    return {
        "formula_id": "formula-storage-fixture",
        "formula_name": "Storage fixture",
        "final_volume_ml_decimal": "30.000",
        "rows": [
            {
                "row_id": "row-1",
                "material": "Linalool",
                "amount_decimal": "100",
                "amount_unit": "uL",
                "stock_id": "stock-linalool",
                "concentration_fraction_decimal": "1",
                "concentration_basis": "NEAT",
                "basket": "B1",
                "operation": "DIRECT_ADD",
            },
        ],
    }


def _large_design_result() -> dict:
    """The shape that grew the database: one formula repeated in several sections."""

    rows = [
        {
            "row_id": f"row-{index}",
            "material": f"Material {index} (10% w/w in DPG)",
            "stock_id": f"stock-{index}",
            "amount_ul_decimal": str(10 + index),
            "role": "heart" if index % 2 else "base",
            "why": f"Carries facet {index % 7} beside the named note, per the brief.",
            "descriptors": ["woody", "amber", "dry", f"facet-{index % 7}"],
        }
        for index in range(60)
    ]
    formula = {"rows": rows, "total_ul_decimal": "6000", "issues": []}
    return {
        "formula_design": {
            "optimized_formula": formula,
            "initial_formula": formula,
            "design_variants": [
                {"variant_id": f"v{index}", "formula": formula} for index in range(3)
            ],
            "assistant_message": "Composed from owned stock. " * 40,
        },
        "selection": {"status": "UNORDERED_DESIGN_HYPOTHESES"},
    }


@pytest.mark.asyncio
async def test_a_large_job_result_is_stored_compressed_and_read_back_exactly(
    db_session,
) -> None:
    service = LabService(db_session)
    job, _ = await service.submit_engine_job(
        job_type="FORMULA_ANALYSIS",
        payload=_formula_payload(),
        requester="fixture-requester",
        idempotency_key="storage",
    )
    lease = await service.claim_next_engine_job(owner="worker-fixture", lease_seconds=30)
    assert lease is not None and lease.job.id == job.id
    await service.mark_engine_job_running(job_id=job.id, owner=lease.owner, token=lease.token)
    result = _large_design_result()
    plain_bytes = len(json.dumps(result))
    assert plain_bytes > 50_000

    await service.complete_engine_job(
        job_id=job.id,
        owner=lease.owner,
        token=lease.token,
        terminal_state="SUCCEEDED",
        result=result,
        validation_state="ADVISORY_COMPLETE",
        diagnostics={"executor": "fixture"},
    )

    stored = await db_session.scalar(
        text("SELECT length(result_json) FROM lab_engine_job_results WHERE job_id = :job"),
        {"job": job.id},
    )
    assert stored * 5 < plain_bytes

    snapshot = await service.engine_job_snapshot(job.id)
    assert snapshot["result_hash_verified"] is True
    assert snapshot["result"]["result"] == result


def test_a_small_or_older_plain_result_reads_back_unchanged() -> None:
    from app.models.lab_engine_jobs import CompressedJSON

    column = CompressedJSON()
    small = {"formula_design": None, "selection": {"status": "WITHHELD_NO_FEASIBLE_DESIGN"}}

    assert column.process_bind_param(small, None) == small
    assert column.process_result_value(small, None) == small
    assert column.process_result_value(None, None) is None


def test_the_stored_wrapper_names_its_codec() -> None:
    from app.models.lab_engine_jobs import COMPRESSED_JSON_KEY, CompressedJSON

    column = CompressedJSON()
    stored = column.process_bind_param(_large_design_result(), None)

    assert list(stored) == [COMPRESSED_JSON_KEY]
    assert stored[COMPRESSED_JSON_KEY]["codec"] == "lzma+base64"
    with pytest.raises(ValueError, match="unknown compressed JSON codec"):
        column.process_result_value(
            {COMPRESSED_JSON_KEY: {"codec": "other", "data": ""}}, None
        )
