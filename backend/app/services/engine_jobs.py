"""Durable, fingerprinted, one-attempt engine-job lifecycle service."""

from __future__ import annotations

import json
import secrets
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from engine.calibration.hashing import (
    PORTABLE_ARTIFACT_HASH_ALGORITHM,
    stable_json_hash,
)
from engine.calibration.hashing import (
    stable_portable_file_hash as stable_file_hash,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lab import LabObservation
from app.models.lab_engine_jobs import (
    ENGINE_TERMINAL_STATES,
    LabEngineJob,
    LabEngineJobEvent,
    LabEngineJobResult,
)
from app.services.engine_job_registry import (
    ENGINE_JOB_CONTRACT_VERSION,
    ENGINE_JOB_CONTRACT_VERSION_V2,
    ENGINE_JOB_REGISTRY,
    REPOSITORY_ROOT,
    implementation_paths,
    validate_engine_payload,
)

if TYPE_CHECKING:
    from app.repositories.lab import LabRepository

ENGINE_JOB_SCHEMA_VERSION = "lab-engine-job-v1"
_CAPABILITY_PATHS = (
    "data/governance/measured_intensity_capabilities_20260923.json",
    "data/governance/wakayama_identity_adjudication_rules_v1.json",
    "data/governance/wakayama_identity_adjudication_summary_20260927.json",
    "data/governance/ifra_policy_status_20260927.json",
    "data/governance/full_potential_cp10_legacy_surface_transitions_20260927.json",
    "data/governance/commercial_reference_registry_v1.json",
    "data/governance/lavande_ambre_profond_r5_design_comparator_20260923.json",
    "data/governance/lavande_ambre_profond_r5_cp3_readiness_protocol_20260924.json",
    "data/governance/lavande_ambre_profond_r5_cp3_readiness_protocol_20260926_v5.json",
    "data/governance/lavande_ambre_profond_r5_standalone_baseline_decision_20260926.json",
    "data/governance/lavande_ambre_profond_r6_aimi_user_decision_20260926.json",
    "data/governance/lavande_ambre_profond_r6_aimi_design_successor_20260926.json",
    "data/governance/lavande_ambre_profond_r6_cp5_execution_input_protocol_20260926.json",
    "data/governance/lavande_ambre_profond_r6_cp6_physical_lineage_intake_20260926.json",
    "data/governance/lavande_ambre_profond_r6_cp7_research_applicability_intake_20260926.json",
    "data/governance/lavande_ambre_profond_r6_cp8_sensory_evidence_intake_20260926.json",
    "data/governance/ma_2021_binary_mixture_baseline_benchmark_20260812.json",
    "data/source_manifests/optimizer_sensory_research_20260909.json",
    "data/governance/inventory_user_authority_overlay_20260924_r5_remaining_stock_forms_v3.json",
    "data/governance/inventory_user_confirmation_20260924_r5_remaining_stock_forms_v3.json",
    "data/governance/inventory_supplier_product_resolution_20260924_aroma_more_lavender_4042.json",
    "engine/experiments/checkpoint5_readiness.py",
    "engine/experiments/checkpoint6_readiness.py",
    "engine/experiments/checkpoint7_readiness.py",
    "engine/experiments/checkpoint8_readiness.py",
    "engine/formulation_intelligence/contracts.py",
    "engine/formulation_intelligence/hedonic_platform.py",
    "engine/sensory/panel_contract.py",
    "engine/hedonic_model.py",
    "engine/research/accounting.py",
    "engine/research/capabilities.py",
    "engine/research/comparison.py",
    "engine/research/commercial_references.py",
    "engine/research/contracts.py",
    "engine/research/perception.py",
    "engine/research/preference.py",
    "engine/research/protocols.py",
    "engine/research/release.py",
    "engine/research/request_interpretation.py",
    "engine/research/safety_policy.py",
    "engine/research/selection.py",
    "engine/research/snapshots.py",
    "engine/optimizer/scoring.py",
    "docs/research/PERFUME_CHEM_C0_SENSORY_PANEL_CONTRACT_2026-08-09.md",
    "engine/dose_response.py",
    "engine/physics/dynamic_release.py",
    "engine/physics/headspace_oav.py",
    "output/optimizer_research_20260909/wakayama_2019/ie9b01225_si_001.pdf",
    "output/optimizer_research_20260909/wakayama_2019/wakayama-intensity.txt",
    "backend/app/services/physical_lineage.py",
    "backend/app/schemas/physical_lineage.py",
    "backend/app/models/lab_cp2_physical.py",
    "backend/alembic/versions/20260923_0017_cp2_physical_lineage.py",
    "backend/alembic/versions/20260927_0020_full_potential_engine_job_v2.py",
    "backend/alembic/versions/20260927_0021_cp18_stock_lot_receipts.py",
    "backend/alembic/versions/20260927_0022_instrumental_observations.py",
    "backend/app/models/lab_instrumental_observations.py",
    "backend/app/services/instrumental_observations.py",
)
_REFERENCE_PATHS = (
    "backend/data/reference/chemicals_potency.json",
    "data/compounds.json",
    "data/formulation_knowledge/literature_v1.json",
    "data/formulation_knowledge/prior_research_corpus_v1.json",
)
_AUTHORITY_CONTEXT = {
    "schema": "engine-job-authority-context-v1",
    "authority_scope": "ADVISORY_EVIDENCE_ONLY",
    "release_authority": False,
    "safety_authority": False,
    "compounding_authority": False,
    "evidence_admission_authorized": False,
}


class EngineJobError(RuntimeError):
    code = "ENGINE_JOB_ERROR"

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class EngineJobConflictError(EngineJobError):
    pass


class EngineJobNotFoundError(EngineJobError):
    pass


@dataclass(frozen=True, slots=True)
class EngineJobLease:
    job: LabEngineJob
    token: str
    owner: str
    epoch: int
    expires_at: datetime


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _hash_secret(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _event_hash_payload(event: LabEngineJobEvent) -> dict[str, Any]:
    return {
        "schema": "lab-engine-job-event-v1",
        "job_id": event.job_id,
        "sequence": event.sequence,
        "state": event.state,
        "lease_owner": event.lease_owner,
        "lease_epoch": event.lease_epoch,
        "lease_token_sha256": event.lease_token_sha256,
        "lease_expires_at": (
            event.lease_expires_at.isoformat()
            if event.lease_expires_at
            else None
        ),
        "attempt": event.attempt,
        "timestamp": event.created_at.isoformat(),
        "sanitized_reason": event.sanitized_reason,
        "detail": dict(event.detail_json),
        "parent_event_sha256": event.parent_event_sha256,
    }


def _result_hash_payload(record: LabEngineJobResult) -> dict[str, Any]:
    return {
        "schema": "lab-engine-job-result-v1",
        "job_id": record.job_id,
        "terminal_state": record.terminal_state,
        "result": dict(record.result_json),
        "validation_state": record.validation_state,
        "diagnostics": dict(record.diagnostics_json),
        "authority_context": _AUTHORITY_CONTEXT,
    }


def _file_manifest(paths: tuple[Path, ...]) -> dict[str, Any]:
    records: list[dict[str, str]] = []
    for path in paths:
        resolved = path.resolve()
        try:
            label = resolved.relative_to(REPOSITORY_ROOT).as_posix()
        except ValueError:
            label = resolved.as_posix()
        records.append(
            {
                "path": label,
                "sha256": (
                    stable_file_hash(resolved) if resolved.is_file() else "MISSING"
                ),
            }
        )
    return {
        "schema": "engine-implementation-manifest-v2",
        "artifact_hash_semantics": PORTABLE_ARTIFACT_HASH_ALGORITHM,
        "files": records,
    }


def _bundle_fingerprint(relative_paths: tuple[str, ...]) -> str:
    manifest = _file_manifest(
        tuple(REPOSITORY_ROOT / path for path in relative_paths)
    )
    return cast(str, stable_json_hash(manifest))


def _research_reference_paths(job_type: str) -> tuple[str, ...]:
    """Bind current research bytes, not just a frozen manifest's old hashes.

    These server-owned paths are read-only references, never execution targets.
    Reject traversal and unregistered roots before fingerprinting anything.
    """
    if job_type not in {"FORMULA_DESIGN", "FORMULA_ANALYSIS"}:
        return _REFERENCE_PATHS
    corpus_path = REPOSITORY_ROOT / "data/formulation_knowledge/prior_research_corpus_v1.json"
    pack_path = REPOSITORY_ROOT / "data/formulation_knowledge/literature_v1.json"
    try:
        corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
        pack = json.loads(pack_path.read_text(encoding="utf-8"))
        paths = [row["path"] for row in corpus["records"]]
        paths.extend(source["local_path"] for source in pack["sources"] if source.get("local_path"))
        if not paths:
            raise ValueError("empty research manifest")
        root = REPOSITORY_ROOT.resolve()
        for label in paths:
            if not isinstance(label, str) or ":" in label or ".." in Path(label).parts:
                raise ValueError("invalid research path")
            resolved = (root / label).resolve()
            if not resolved.is_relative_to(root):
                raise ValueError("research path escapes repository")
            normalized = resolved.relative_to(root).as_posix()
            if not normalized.startswith(("knowledge/", "docs/research/", "data/source_manifests/", "data/governance/")) and normalized != "future_modules/literature_references.py":
                raise ValueError("unregistered research path")
    except (OSError, ValueError, TypeError, KeyError) as error:
        raise EngineJobError("INVALID_RESEARCH_REFERENCE_MANIFEST", "Local research reference manifest is unavailable or invalid.") from error
    return tuple(dict.fromkeys((*_REFERENCE_PATHS, *paths)))


def build_engine_job_identity(
    *,
    job_type: str,
    payload: dict[str, Any],
    requester: str,
    idempotency_key: str,
    request_schema_version: str = "lab-engine-job-request-v1",
    server_bound_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate a closed command and derive every server-owned fingerprint."""

    if job_type not in ENGINE_JOB_REGISTRY:
        raise EngineJobError(
            "UNSUPPORTED_ENGINE_JOB_TYPE",
            f"Unsupported engine job type: {job_type}.",
        )
    try:
        normalized = validate_engine_payload(
            job_type,
            payload,
            request_schema_version=request_schema_version,
        )
    except (TypeError, ValueError) as error:
        raise EngineJobError("INVALID_ENGINE_JOB_PAYLOAD", str(error)) from error

    requester_scope = str(requester).strip()
    key = str(idempotency_key).strip()
    if not requester_scope or not key:
        raise EngineJobError(
            "INVALID_ENGINE_JOB_IDENTITY",
            "requester and idempotency_key must not be blank.",
        )
    spec = ENGINE_JOB_REGISTRY[job_type]
    implementation_manifest = _file_manifest(implementation_paths(job_type))
    implementation_sha256 = stable_json_hash(implementation_manifest)
    reference_sha256 = _bundle_fingerprint(_research_reference_paths(job_type))
    inventory_path = REPOSITORY_ROOT / "inventory.txt"
    inventory_sha256 = (
        stable_file_hash(inventory_path)
        if inventory_path.is_file()
        else stable_json_hash({"inventory": "MISSING"})
    )
    capability_sha256 = _bundle_fingerprint(_CAPABILITY_PATHS)
    authority_sha256 = stable_json_hash(_AUTHORITY_CONTEXT)
    contract_version = (
        ENGINE_JOB_CONTRACT_VERSION_V2
        if request_schema_version == "lab-engine-job-request-v2"
        else ENGINE_JOB_CONTRACT_VERSION
    )
    bound_context = dict(server_bound_context or {})
    bound_context_sha256 = (
        stable_json_hash(bound_context) if bound_context else None
    )
    source_request = {
        "schema_version": request_schema_version,
        "job_type": job_type,
        "payload": normalized,
        "requester": requester_scope,
    }
    if bound_context:
        source_request["server_bound_context"] = bound_context
    source_request_sha256 = stable_json_hash(source_request)
    normalized_sha256 = stable_json_hash(normalized)
    command = {
        "contract_version": contract_version,
        "job_type": job_type,
        "requester_scope": requester_scope,
        "normalized_payload": normalized,
    }
    if bound_context_sha256 is not None:
        command["server_bound_context_sha256"] = bound_context_sha256
    command_sha256 = stable_json_hash(command)
    fingerprint_payload = {
        "schema": (
            "engine-job-fingerprint-v2"
            if contract_version == ENGINE_JOB_CONTRACT_VERSION_V2
            else "engine-job-fingerprint-v1"
        ),
        "command_sha256": command_sha256,
        "formula_and_row_order_sha256": normalized_sha256,
        "implementation_fingerprint_sha256": implementation_sha256,
        "reference_bundle_sha256": reference_sha256,
        "inventory_fingerprint_sha256": inventory_sha256,
        "capability_fingerprint_sha256": capability_sha256,
        "authority_context_sha256": authority_sha256,
        "contract_version": contract_version,
    }
    if bound_context_sha256 is not None:
        fingerprint_payload["server_bound_context_sha256"] = bound_context_sha256
    fingerprint = stable_json_hash(fingerprint_payload)
    return {
        "source_request": source_request,
        "normalized_payload": normalized,
        "source_request_sha256": source_request_sha256,
        "normalized_payload_sha256": normalized_sha256,
        "implementation_manifest": implementation_manifest,
        "implementation_fingerprint_sha256": implementation_sha256,
        "reference_bundle_sha256": reference_sha256,
        "inventory_fingerprint_sha256": inventory_sha256,
        "capability_fingerprint_sha256": capability_sha256,
        "authority_context_sha256": authority_sha256,
        "server_bound_context_sha256": bound_context_sha256,
        "requester_scope": requester_scope,
        "idempotency_key_sha256": _hash_secret(key),
        "command_sha256": command_sha256,
        "job_fingerprint_sha256": fingerprint,
        "execution_class": spec.execution_class,
        "timeout_seconds": spec.timeout_seconds,
        "contract_version": contract_version,
        "job_schema_version": (
            "lab-engine-job-v2"
            if contract_version == ENGINE_JOB_CONTRACT_VERSION_V2
            else ENGINE_JOB_SCHEMA_VERSION
        ),
    }


class LabEngineJobServiceMixin:
    """Engine-job commands sharing the canonical LabService transaction owner."""

    if TYPE_CHECKING:
        session: AsyncSession
        repository: "LabRepository"

        def _transaction(self) -> AbstractAsyncContextManager[None]: ...

    async def _latest_engine_job_event(
        self, job_id: str
    ) -> LabEngineJobEvent | None:
        return cast(
            LabEngineJobEvent | None,
            await self.session.scalar(
                select(LabEngineJobEvent)
                .where(LabEngineJobEvent.job_id == job_id)
                .order_by(LabEngineJobEvent.sequence.desc())
                .limit(1)
            ),
        )

    async def _engine_job_events(self, job_id: str) -> list[LabEngineJobEvent]:
        rows = await self.session.scalars(
            select(LabEngineJobEvent)
            .where(LabEngineJobEvent.job_id == job_id)
            .order_by(LabEngineJobEvent.sequence, LabEngineJobEvent.id)
        )
        return list(rows)

    async def get_engine_job(self, job_id: str) -> LabEngineJob:
        record = await self.session.get(LabEngineJob, str(job_id))
        if record is None:
            raise EngineJobNotFoundError(
                "ENGINE_JOB_NOT_FOUND", f"Engine job not found: {job_id}."
            )
        return record

    async def get_engine_job_result(
        self, job_id: str
    ) -> LabEngineJobResult | None:
        return cast(
            LabEngineJobResult | None,
            await self.session.scalar(
                select(LabEngineJobResult).where(LabEngineJobResult.job_id == job_id)
            ),
        )

    async def _append_engine_job_event(
        self,
        *,
        job_id: str,
        state: str,
        reason: str | None = None,
        detail: dict[str, Any] | None = None,
        lease_owner: str | None = None,
        lease_epoch: int = 0,
        lease_token_sha256: str | None = None,
        lease_expires_at: datetime | None = None,
        attempt: int = 0,
    ) -> LabEngineJobEvent:
        parent = await self._latest_engine_job_event(job_id)
        sequence = 1 if parent is None else parent.sequence + 1
        timestamp = _utcnow()
        event = LabEngineJobEvent(
            job_id=job_id,
            sequence=sequence,
            state=state,
            lease_owner=lease_owner,
            lease_epoch=lease_epoch,
            lease_token_sha256=lease_token_sha256,
            lease_expires_at=lease_expires_at,
            attempt=attempt,
            sanitized_reason=reason,
            detail_json=detail or {},
            parent_event_sha256=parent.event_sha256 if parent else None,
            event_sha256="0" * 64,
            created_at=timestamp,
        )
        event.event_sha256 = stable_json_hash(_event_hash_payload(event))
        self.session.add(event)
        await self.session.flush()
        return event

    async def submit_engine_job(
        self,
        *,
        job_type: str,
        payload: dict[str, Any],
        requester: str,
        idempotency_key: str,
        request_schema_version: str = "lab-engine-job-request-v1",
    ) -> tuple[LabEngineJob, bool]:
        identity = build_engine_job_identity(
            job_type=job_type,
            payload=payload,
            requester=requester,
            idempotency_key=idempotency_key,
            request_schema_version=request_schema_version,
        )
        async with self._transaction():
            observation_ids = tuple(
                identity["normalized_payload"].get("observation_record_ids", [])
                if job_type == "REFERENCE_PANEL_EVALUATION"
                else ()
            )
            if observation_ids:
                rows = (
                    await self.session.execute(
                        select(LabObservation).where(
                            LabObservation.id.in_(observation_ids)
                        )
                    )
                ).scalars()
                by_id = {row.id: row for row in rows}
                missing = [record_id for record_id in observation_ids if record_id not in by_id]
                if missing:
                    raise EngineJobError(
                        "OBSERVATION_RECORD_NOT_FOUND",
                        "Unknown observation record IDs: " + ", ".join(missing),
                    )
                observation_bindings = []
                for record_id in observation_ids:
                    row = by_id[record_id]
                    record_payload = {
                        "id": row.id,
                        "application_id": row.application_id,
                        "elapsed_seconds": row.elapsed_seconds,
                        "observations": dict(row.observations_json),
                        "created_at": row.created_at.isoformat(),
                    }
                    observation_bindings.append(
                        {
                            "record_id": record_id,
                            "record_sha256": stable_json_hash(record_payload),
                        }
                    )
                identity = build_engine_job_identity(
                    job_type=job_type,
                    payload=payload,
                    requester=requester,
                    idempotency_key=idempotency_key,
                    request_schema_version=request_schema_version,
                    server_bound_context={
                        "schema_version": "reference-observation-bindings-v1",
                        "observation_records": observation_bindings,
                    },
                )
            idempotent = await self.session.scalar(
                select(LabEngineJob).where(
                    LabEngineJob.requester_scope
                    == identity["requester_scope"],
                    LabEngineJob.idempotency_key_sha256
                    == identity["idempotency_key_sha256"],
                )
            )
            if idempotent is not None:
                if idempotent.command_sha256 != identity["command_sha256"]:
                    raise EngineJobConflictError(
                        "IDEMPOTENCY_COMMAND_MISMATCH",
                        "The idempotency key was reused for a different command.",
                    )
                return idempotent, True

            coalesced = await self.session.scalar(
                select(LabEngineJob).where(
                    LabEngineJob.job_fingerprint_sha256
                    == identity["job_fingerprint_sha256"]
                )
            )
            if coalesced is not None:
                return coalesced, True

            job = LabEngineJob(
                schema_version=identity["job_schema_version"],
                contract_version=identity["contract_version"],
                job_type=job_type,
                execution_class=identity["execution_class"],
                requester_scope=identity["requester_scope"],
                source_request_json=identity["source_request"],
                normalized_payload_json=identity["normalized_payload"],
                source_request_sha256=identity["source_request_sha256"],
                normalized_payload_sha256=identity[
                    "normalized_payload_sha256"
                ],
                implementation_fingerprint_sha256=identity[
                    "implementation_fingerprint_sha256"
                ],
                implementation_manifest_json=identity[
                    "implementation_manifest"
                ],
                reference_bundle_sha256=identity["reference_bundle_sha256"],
                inventory_fingerprint_sha256=identity[
                    "inventory_fingerprint_sha256"
                ],
                capability_fingerprint_sha256=identity[
                    "capability_fingerprint_sha256"
                ],
                authority_context_sha256=identity[
                    "authority_context_sha256"
                ],
                idempotency_key_sha256=identity["idempotency_key_sha256"],
                command_sha256=identity["command_sha256"],
                job_fingerprint_sha256=identity[
                    "job_fingerprint_sha256"
                ],
                timeout_seconds=identity["timeout_seconds"],
                max_attempts=1,
            )
            self.session.add(job)
            await self.session.flush()
            await self._append_engine_job_event(
                job_id=job.id,
                state="QUEUED",
                reason="JOB_ACCEPTED",
                detail={"reused": False},
            )
            return job, False

    async def claim_next_engine_job(
        self,
        *,
        owner: str,
        lease_seconds: int = 30,
    ) -> EngineJobLease | None:
        owner_text = str(owner).strip()
        if not owner_text or not 5 <= lease_seconds <= 3600:
            raise EngineJobError(
                "INVALID_ENGINE_JOB_LEASE",
                "owner is required and lease_seconds must be from 5 to 3600.",
            )
        async with self._transaction():
            jobs = list(
                await self.session.scalars(
                    select(LabEngineJob).order_by(
                        LabEngineJob.created_at, LabEngineJob.id
                    )
                )
            )
            selected: LabEngineJob | None = None
            latest: LabEngineJobEvent | None = None
            for candidate in jobs:
                event = await self._latest_engine_job_event(candidate.id)
                if event is not None and event.state == "QUEUED":
                    selected, latest = candidate, event
                    break
            if selected is None or latest is None:
                return None
            token = secrets.token_urlsafe(32)
            # A dead worker must fail closed near the job's own hard deadline,
            # not remain leased for an unrelated long global interval.
            effective_lease_seconds = min(
                lease_seconds,
                selected.timeout_seconds + 60,
            )
            expiry = _utcnow() + timedelta(seconds=effective_lease_seconds)
            epoch = latest.lease_epoch + 1
            await self._append_engine_job_event(
                job_id=selected.id,
                state="LEASED",
                reason="WORKER_LEASE_ACQUIRED",
                lease_owner=owner_text,
                lease_epoch=epoch,
                lease_token_sha256=_hash_secret(token),
                lease_expires_at=expiry,
                attempt=1,
            )
            return EngineJobLease(selected, token, owner_text, epoch, expiry)

    async def mark_engine_job_running(
        self, *, job_id: str, owner: str, token: str
    ) -> LabEngineJobEvent:
        expired = False
        running_event: LabEngineJobEvent | None = None
        async with self._transaction():
            await self.get_engine_job(job_id)
            latest = await self._latest_engine_job_event(job_id)
            if latest is None or latest.state != "LEASED":
                raise EngineJobConflictError(
                    "ENGINE_JOB_NOT_LEASED",
                    "Only a currently leased job may enter RUNNING.",
                )
            self._verify_lease(latest, owner, token)
            if latest.lease_expires_at and latest.lease_expires_at <= _utcnow():
                await self._fail_worker_lost(job_id, latest)
                expired = True
            else:
                running_event = await self._append_engine_job_event(
                    job_id=job_id,
                    state="RUNNING",
                    reason="WORKER_EXECUTION_STARTED",
                    lease_owner=latest.lease_owner,
                    lease_epoch=latest.lease_epoch,
                    lease_token_sha256=latest.lease_token_sha256,
                    lease_expires_at=latest.lease_expires_at,
                    attempt=1,
                )
        if expired:
            raise EngineJobConflictError(
                "FAILED_CLOSED_WORKER_LOST", "The worker lease expired."
            )
        if running_event is None:  # Defensive: every non-expired path sets it.
            raise EngineJobConflictError(
                "ENGINE_JOB_STATE_TRANSITION_FAILED",
                "The job could not enter RUNNING.",
            )
        return running_event

    @staticmethod
    def _verify_lease(
        event: LabEngineJobEvent, owner: str, token: str
    ) -> None:
        if (
            event.lease_owner != str(owner).strip()
            or event.lease_token_sha256 != _hash_secret(token)
        ):
            raise EngineJobConflictError(
                "ENGINE_JOB_LEASE_MISMATCH",
                "Worker identity or lease token does not match.",
            )

    async def _store_engine_job_result(
        self,
        *,
        job_id: str,
        terminal_state: str,
        result: dict[str, Any],
        validation_state: str,
        diagnostics: dict[str, Any] | None,
    ) -> LabEngineJobResult:
        record = LabEngineJobResult(
            job_id=job_id,
            terminal_state=terminal_state,
            result_json=result,
            result_sha256="0" * 64,
            validation_state=validation_state,
            diagnostics_json=diagnostics or {},
            release_authority=False,
            safety_authority=False,
            compounding_authority=False,
            evidence_admission_authorized=False,
        )
        record.result_sha256 = stable_json_hash(_result_hash_payload(record))
        self.session.add(record)
        await self.session.flush()
        return record

    async def complete_engine_job(
        self,
        *,
        job_id: str,
        owner: str,
        token: str,
        terminal_state: str,
        result: dict[str, Any],
        validation_state: str,
        diagnostics: dict[str, Any] | None = None,
    ) -> LabEngineJobResult:
        if terminal_state not in {"SUCCEEDED", "WITHHELD", "FAILED"}:
            raise EngineJobError(
                "INVALID_ENGINE_JOB_TERMINAL_STATE",
                "Worker completion must be SUCCEEDED, WITHHELD, or FAILED.",
            )
        expired = False
        completed: LabEngineJobResult | None = None
        async with self._transaction():
            await self.get_engine_job(job_id)
            latest = await self._latest_engine_job_event(job_id)
            if latest is None or latest.state != "RUNNING":
                raise EngineJobConflictError(
                    "ENGINE_JOB_LATE_RESULT_REJECTED",
                    "The job is not RUNNING; late or duplicate results are rejected.",
                )
            self._verify_lease(latest, owner, token)
            if latest.lease_expires_at and latest.lease_expires_at <= _utcnow():
                await self._fail_worker_lost(job_id, latest)
                expired = True
            elif await self.get_engine_job_result(job_id) is not None:
                raise EngineJobConflictError(
                    "ENGINE_JOB_RESULT_ALREADY_EXISTS",
                    "The job already has an immutable terminal result.",
                )
            else:
                completed = await self._store_engine_job_result(
                    job_id=job_id,
                    terminal_state=terminal_state,
                    result=dict(result),
                    validation_state=str(validation_state),
                    diagnostics=diagnostics,
                )
                await self._append_engine_job_event(
                    job_id=job_id,
                    state=terminal_state,
                    reason="WORKER_RESULT_ACCEPTED",
                    detail={"result_sha256": completed.result_sha256},
                    lease_epoch=latest.lease_epoch,
                    attempt=1,
                )
        if expired:
            raise EngineJobConflictError(
                "FAILED_CLOSED_WORKER_LOST", "The worker lease expired."
            )
        if completed is None:
            raise EngineJobConflictError(
                "ENGINE_JOB_RESULT_NOT_STORED",
                "The worker result was not stored.",
            )
        return completed

    async def _fail_worker_lost(
        self, job_id: str, latest: LabEngineJobEvent
    ) -> LabEngineJobResult:
        existing = await self.get_engine_job_result(job_id)
        if existing is not None:
            return existing
        result = await self._store_engine_job_result(
            job_id=job_id,
            terminal_state="FAILED",
            result={
                "status": "FAILED",
                "code": "FAILED_CLOSED_WORKER_LOST",
                "formula_action": "NO_CHANGE",
            },
            validation_state="FAILED_CLOSED_WORKER_LOST",
            diagnostics={"attempt": latest.attempt},
        )
        await self._append_engine_job_event(
            job_id=job_id,
            state="FAILED",
            reason="FAILED_CLOSED_WORKER_LOST",
            detail={"result_sha256": result.result_sha256},
            lease_epoch=latest.lease_epoch,
            attempt=latest.attempt,
        )
        return result

    async def fail_expired_engine_jobs(self) -> int:
        failed = 0
        async with self._transaction():
            jobs = list(await self.session.scalars(select(LabEngineJob)))
            now = _utcnow()
            for job in jobs:
                latest = await self._latest_engine_job_event(job.id)
                if (
                    latest is not None
                    and latest.state in {"LEASED", "RUNNING"}
                    and latest.lease_expires_at is not None
                    and latest.lease_expires_at <= now
                ):
                    await self._fail_worker_lost(job.id, latest)
                    failed += 1
        return failed

    async def cancel_engine_job(
        self, *, job_id: str, requester: str, reason: str
    ) -> LabEngineJob:
        reason_sha256 = _hash_secret(str(reason)[:500])
        async with self._transaction():
            job = await self.get_engine_job(job_id)
            if job.requester_scope != str(requester).strip():
                raise EngineJobConflictError(
                    "ENGINE_JOB_REQUESTER_MISMATCH",
                    "Only the matching requester scope may cancel this job.",
                )
            latest = await self._latest_engine_job_event(job_id)
            if latest is None:
                raise EngineJobConflictError(
                    "ENGINE_JOB_EVENT_CHAIN_MISSING",
                    "The job has no event chain.",
                )
            if latest.state in ENGINE_TERMINAL_STATES:
                return job
            await self._append_engine_job_event(
                job_id=job_id,
                state="CANCEL_REQUESTED",
                reason="CANCEL_REQUESTED",
                detail={"request_reason_sha256": reason_sha256},
                lease_epoch=latest.lease_epoch,
                attempt=latest.attempt,
            )
            result = await self._store_engine_job_result(
                job_id=job_id,
                terminal_state="CANCELLED",
                result={
                    "status": "CANCELLED",
                    "formula_action": "NO_CHANGE",
                },
                validation_state="CANCELLED",
                diagnostics={"request_reason_sha256": reason_sha256},
            )
            await self._append_engine_job_event(
                job_id=job_id,
                state="CANCELLED",
                reason="CANCELLATION_WON",
                detail={"result_sha256": result.result_sha256},
                lease_epoch=latest.lease_epoch,
                attempt=latest.attempt,
            )
            return job

    async def engine_job_snapshot(self, job_id: str) -> dict[str, Any]:
        job = await self.get_engine_job(job_id)
        events = await self._engine_job_events(job.id)
        result = await self.get_engine_job_result(job.id)
        expected_parent: str | None = None
        for event in events:
            if (
                event.parent_event_sha256 != expected_parent
                or event.event_sha256
                != stable_json_hash(_event_hash_payload(event))
            ):
                raise EngineJobConflictError(
                    "ENGINE_JOB_EVENT_CHAIN_INVALID",
                    "The immutable engine-job event chain failed verification.",
                )
            expected_parent = event.event_sha256
        result_hash_verified = (
            result is not None
            and result.result_sha256
            == stable_json_hash(_result_hash_payload(result))
        )
        if result is not None and not result_hash_verified:
            raise EngineJobConflictError(
                "ENGINE_JOB_RESULT_HASH_INVALID",
                "The immutable engine-job result failed verification.",
            )
        latest = events[-1]
        return {
            "schema_version": (
                "lab-engine-job-response-v2"
                if job.contract_version == ENGINE_JOB_CONTRACT_VERSION_V2
                else "lab-engine-job-response-v1"
            ),
            "id": job.id,
            "job_type": job.job_type,
            "execution_class": job.execution_class,
            "requester_scope": job.requester_scope,
            "state": latest.state,
            "job_fingerprint_sha256": job.job_fingerprint_sha256,
            "command_sha256": job.command_sha256,
            "normalized_payload_sha256": job.normalized_payload_sha256,
            "implementation_fingerprint_sha256": (
                job.implementation_fingerprint_sha256
            ),
            "reference_bundle_sha256": job.reference_bundle_sha256,
            "inventory_fingerprint_sha256": job.inventory_fingerprint_sha256,
            "capability_fingerprint_sha256": (
                job.capability_fingerprint_sha256
            ),
            "contract_version": job.contract_version,
            "timeout_seconds": job.timeout_seconds,
            "created_at": job.created_at,
            "event_chain_verified": True,
            "result_hash_verified": result_hash_verified if result else None,
            "events": [
                {
                    "sequence": event.sequence,
                    "state": event.state,
                    "lease_owner": event.lease_owner,
                    "lease_epoch": event.lease_epoch,
                    "lease_expires_at": event.lease_expires_at,
                    "attempt": event.attempt,
                    "reason": event.sanitized_reason,
                    "timestamp": event.created_at,
                    "parent_event_sha256": event.parent_event_sha256,
                    "event_sha256": event.event_sha256,
                }
                for event in events
            ],
            "result": (
                {
                    "terminal_state": result.terminal_state,
                    "result": dict(result.result_json),
                    "result_sha256": result.result_sha256,
                    "validation_state": result.validation_state,
                    "diagnostics": dict(result.diagnostics_json),
                    "release_authority": False,
                    "safety_authority": False,
                    "compounding_authority": False,
                    "evidence_admission_authorized": False,
                }
                if result is not None
                else None
            ),
            **{
                key: False
                for key in (
                    "release_authority",
                    "safety_authority",
                    "compounding_authority",
                    "evidence_admission_authorized",
                )
            },
        }


__all__ = [
    "ENGINE_JOB_SCHEMA_VERSION",
    "EngineJobConflictError",
    "EngineJobError",
    "EngineJobLease",
    "EngineJobNotFoundError",
    "LabEngineJobServiceMixin",
    "build_engine_job_identity",
]
