"""One-release adapters from synchronous responses to durable engine jobs.

Legacy response payloads remain available for one release, but every migrated
project-owned endpoint first submits the equivalent closed-registry command.
The compatibility computation remains non-authoritative and cannot pretend a
queued job has executed.
"""

from __future__ import annotations

import asyncio
from decimal import Decimal
from time import monotonic
from typing import Any, Iterable, Mapping

from engine.calibration.hashing import stable_json_hash
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lab_engine_jobs import ENGINE_TERMINAL_STATES
from app.services.engine_jobs import build_engine_job_identity
from app.services.validation_pipeline import PipelineReport

_FALSE_AUTHORITY = {
    "release_authority": False,
    "safety_authority": False,
    "compounding_authority": False,
    "evidence_admission_authorized": False,
}


def _decimal_text(value: object) -> str:
    decimal_value = Decimal(str(value))
    if decimal_value == 0:
        return "0"
    text = format(decimal_value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def _formula_rows(ingredients: Mapping[str, float]) -> list[dict[str, Any]]:
    return [
        {
            "row_id": f"legacy-row-{index}",
            "material": str(material),
            "amount_decimal": _decimal_text(amount),
            "amount_unit": "uL",
            "concentration_basis": "UNKNOWN",
            "operation": "DIRECT_ADD",
        }
        for index, (material, amount) in enumerate(ingredients.items(), start=1)
        if Decimal(str(amount)) > 0
    ]


def _receipt(
    *,
    job_type: str,
    payload: dict[str, Any],
    scope: str,
) -> dict[str, Any]:
    requester = f"synchronous-compatibility:{scope}"
    identity = build_engine_job_identity(
        job_type=job_type,
        payload=payload,
        requester=requester,
        idempotency_key=stable_json_hash(
            {
                "schema": "synchronous-compatibility-command-v1",
                "scope": scope,
                "job_type": job_type,
                "payload": payload,
            }
        ),
    )
    return {
        "schema_version": "lab-engine-job-compatibility-receipt-v1",
        "compatibility_state": "SYNCHRONOUS_COMPATIBILITY_ONE_RELEASE",
        "operation_scope": scope,
        "job_type": job_type,
        "command_sha256": identity["command_sha256"],
        "job_fingerprint_sha256": identity["job_fingerprint_sha256"],
        "normalized_payload_sha256": identity["normalized_payload_sha256"],
        "implementation_fingerprint_sha256": identity[
            "implementation_fingerprint_sha256"
        ],
        "reference_bundle_sha256": identity["reference_bundle_sha256"],
        "inventory_fingerprint_sha256": identity[
            "inventory_fingerprint_sha256"
        ],
        "capability_fingerprint_sha256": identity[
            "capability_fingerprint_sha256"
        ],
        "durable_job_created": False,
        "durable_execution_performed": False,
        "durable_endpoint": "/api/v1/lab/v2/engine-jobs",
        **_FALSE_AUTHORITY,
    }


async def _durable_receipt(
    *,
    session: AsyncSession,
    job_type: str,
    payload: dict[str, Any],
    scope: str,
    wait_timeout_seconds: float = 0.05,
) -> dict[str, Any]:
    """Submit the exact durable command and optionally observe quick completion."""

    from app.services.lab_service import LabService  # noqa: PLC0415

    requester = f"synchronous-compatibility:{scope}"
    idempotency_key = stable_json_hash(
        {
            "schema": "synchronous-compatibility-command-v2",
            "scope": scope,
            "job_type": job_type,
            "payload": payload,
        }
    )
    service = LabService(session)
    job, reused = await service.submit_engine_job(
        job_type=job_type,
        payload=payload,
        requester=requester,
        idempotency_key=idempotency_key,
        request_schema_version="lab-engine-job-request-v1",
    )
    snapshot = await service.engine_job_snapshot(job.id)
    deadline = monotonic() + max(0.0, min(float(wait_timeout_seconds), 0.25))
    while (
        snapshot["state"] not in ENGINE_TERMINAL_STATES
        and monotonic() < deadline
    ):
        await asyncio.sleep(min(0.01, max(0.0, deadline - monotonic())))
        snapshot = await service.engine_job_snapshot(job.id)
    terminal = snapshot["state"] in ENGINE_TERMINAL_STATES
    return {
        "schema_version": "lab-engine-job-compatibility-receipt-v2",
        "compatibility_state": (
            "DURABLE_JOB_TERMINAL" if terminal else "DURABLE_JOB_QUEUED"
        ),
        "operation_scope": scope,
        "job_id": job.id,
        "job_type": job.job_type,
        "job_state": snapshot["state"],
        "job_reused": reused,
        "command_sha256": job.command_sha256,
        "job_fingerprint_sha256": job.job_fingerprint_sha256,
        "normalized_payload_sha256": job.normalized_payload_sha256,
        "implementation_fingerprint_sha256": (
            job.implementation_fingerprint_sha256
        ),
        "reference_bundle_sha256": job.reference_bundle_sha256,
        "inventory_fingerprint_sha256": job.inventory_fingerprint_sha256,
        "capability_fingerprint_sha256": job.capability_fingerprint_sha256,
        "durable_job_created": True,
        "durable_execution_performed": terminal,
        "durable_result_hash_verified": snapshot["result_hash_verified"],
        "durable_endpoint": f"/api/v1/lab/v2/engine-jobs/{job.id}",
        **_FALSE_AUTHORITY,
    }


def bind_formula_analysis_compatibility(
    report: PipelineReport,
    ingredients: Mapping[str, float],
    *,
    scope: str,
    formula_name: str = "Legacy synchronous formula",
) -> PipelineReport:
    rows = _formula_rows(ingredients)
    if not rows:
        report.engine_job_contract = {
            "schema_version": "lab-engine-job-compatibility-receipt-v1",
            "compatibility_state": "WITHHOLD_NO_POSITIVE_DOSE_ROWS",
            "operation_scope": scope,
            "durable_job_created": False,
            "durable_execution_performed": False,
            **_FALSE_AUTHORITY,
        }
        return report
    formula_id = stable_json_hash(
        {"scope": scope, "formula_name": formula_name, "rows": rows}
    )
    report.engine_job_contract = _receipt(
        job_type="FORMULA_ANALYSIS",
        payload={
            "formula_id": formula_id,
            "formula_name": formula_name,
            "rows": rows,
        },
        scope=scope,
    )
    return report


def bind_mixer_sequence_compatibility(
    report: PipelineReport,
    *,
    scope: str,
    formula_name: str,
    ingredients: Mapping[str, float] | None = None,
    rows: Iterable[Mapping[str, Any]] | None = None,
) -> PipelineReport:
    if rows is None:
        normalized_rows = _formula_rows(ingredients or {})
    else:
        normalized_rows = [
            {
                "row_id": str(row["row_id"]),
                "material": str(row["material"]),
                "amount_decimal": _decimal_text(row["raw_ul"]),
                "amount_unit": "uL",
                "concentration_basis": "UNKNOWN",
                "basket": (
                    f"B{int(row['basket'])}"
                    if row.get("basket") is not None
                    else None
                ),
                "operation": str(row.get("operation") or "DIRECT_ADD"),
            }
            for row in rows
        ]
    formula_id = stable_json_hash(
        {"scope": scope, "formula_name": formula_name, "rows": normalized_rows}
    )
    report.engine_job_contract = _receipt(
        job_type="MIXER_SEQUENCE",
        payload={
            "formula_id": formula_id,
            "formula_name": formula_name,
            "rows": normalized_rows,
            "order_policy": "BASKET_THEN_DESCENDING_LIQUIDS_MASS_SEPARATE",
        },
        scope=scope,
    )
    return report


async def enqueue_formula_analysis_compatibility(
    session: AsyncSession,
    report: PipelineReport,
    ingredients: Mapping[str, float],
    *,
    scope: str,
    formula_name: str = "Legacy synchronous formula",
) -> PipelineReport:
    rows = _formula_rows(ingredients)
    if not rows:
        report.engine_job_contract = {
            "schema_version": "lab-engine-job-compatibility-receipt-v2",
            "compatibility_state": "WITHHOLD_NO_POSITIVE_DOSE_ROWS",
            "operation_scope": scope,
            "durable_job_created": False,
            "durable_execution_performed": False,
            **_FALSE_AUTHORITY,
        }
        return report
    formula_id = stable_json_hash(
        {"scope": scope, "formula_name": formula_name, "rows": rows}
    )
    report.engine_job_contract = await _durable_receipt(
        session=session,
        job_type="FORMULA_ANALYSIS",
        payload={
            "formula_id": formula_id,
            "formula_name": formula_name,
            "rows": rows,
        },
        scope=scope,
    )
    return report


async def enqueue_mixer_sequence_compatibility(
    session: AsyncSession,
    report: PipelineReport,
    *,
    scope: str,
    formula_name: str,
    ingredients: Mapping[str, float] | None = None,
    rows: Iterable[Mapping[str, Any]] | None = None,
) -> PipelineReport:
    if rows is None:
        normalized_rows = _formula_rows(ingredients or {})
    else:
        normalized_rows = [
            {
                "row_id": str(row["row_id"]),
                "material": str(row["material"]),
                "amount_decimal": _decimal_text(row["raw_ul"]),
                "amount_unit": "uL",
                "concentration_basis": "UNKNOWN",
                "basket": (
                    f"B{int(row['basket'])}"
                    if row.get("basket") is not None
                    else None
                ),
                "operation": str(row.get("operation") or "DIRECT_ADD"),
            }
            for row in rows
        ]
    if not normalized_rows:
        report.engine_job_contract = {
            "schema_version": "lab-engine-job-compatibility-receipt-v2",
            "compatibility_state": "WITHHOLD_NO_POSITIVE_DOSE_ROWS",
            "operation_scope": scope,
            "durable_job_created": False,
            "durable_execution_performed": False,
            **_FALSE_AUTHORITY,
        }
        return report
    formula_id = stable_json_hash(
        {"scope": scope, "formula_name": formula_name, "rows": normalized_rows}
    )
    report.engine_job_contract = await _durable_receipt(
        session=session,
        job_type="MIXER_SEQUENCE",
        payload={
            "formula_id": formula_id,
            "formula_name": formula_name,
            "rows": normalized_rows,
            "order_policy": "BASKET_THEN_DESCENDING_LIQUIDS_MASS_SEPARATE",
        },
        scope=scope,
    )
    return report


__all__ = [
    "bind_formula_analysis_compatibility",
    "bind_mixer_sequence_compatibility",
    "enqueue_formula_analysis_compatibility",
    "enqueue_mixer_sequence_compatibility",
]
