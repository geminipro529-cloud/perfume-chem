"""Bounded process and artifact boundary for the local SolForge Workbench."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from app.schemas.solforge_workbench import (
    AUTHORITY_FLAGS_FALSE,
    ArmSummaryV1,
    ArtifactRecordSummaryV1,
    SolForgeWorkbenchDesignRequestV1,
    SolForgeWorkbenchDesignResponseV1,
    SolForgeWorkbenchStatusV1,
)

if TYPE_CHECKING:
    from app.core.config import Settings

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_RUN_ID_RE = re.compile(r"^sf-[0-9a-f]{32}$")
_ADMITTED_MODULES = ("architectural-delta-engine",)
_MAX_MANIFEST_BYTES = 2_097_152


class WorkbenchFailure(RuntimeError):  # noqa: N818 - closed protocol term
    """A closed, user-safe failure at the Workbench process boundary."""

    def __init__(self, code: str, status_code: int, detail: str) -> None:
        self.code = code
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


@dataclass(frozen=True, slots=True)
class WorkbenchRuntimeConfig:
    engine_python: Path
    project_root: Path
    script_path: Path
    inventory_path: Path
    artifact_root: Path
    timeout_seconds: int
    max_runs: int
    max_artifact_bytes: int
    max_record_bytes: int
    max_concurrent_runs: int


def canonical_json_bytes(value: object) -> bytes:
    """Match the root engine's deterministic JSON transport encoding."""

    try:
        payload = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"value is not valid canonical JSON: {exc}") from exc
    return payload.encode("utf-8")


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _contained(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _require_regular_file(path: Path, label: str) -> None:
    if path.is_symlink() or not path.is_file():
        raise WorkbenchFailure(
            "WORKBENCH_NOT_CONFIGURED",
            503,
            f"{label} must be a regular non-symlink file",
        )


def resolve_runtime_config(settings: Settings) -> WorkbenchRuntimeConfig:
    """Resolve only operator-controlled paths; request data cannot alter them."""

    project_root = Path(settings.SOLFORGE_PROJECT_ROOT).resolve()
    engine_python = Path(settings.SOLFORGE_ENGINE_PYTHON).resolve()
    script_path = (project_root / "scripts" / "intervention_recommend.py").resolve()
    inventory_path = Path(settings.SOLFORGE_INVENTORY_PATH).resolve()
    artifact_root = Path(settings.SOLFORGE_ARTIFACT_ROOT).resolve()

    if project_root.is_symlink() or not project_root.is_dir():
        raise WorkbenchFailure(
            "WORKBENCH_NOT_CONFIGURED", 503, "project root is unavailable"
        )
    _require_regular_file(engine_python, "engine interpreter")
    _require_regular_file(script_path, "SolForge CLI")
    _require_regular_file(inventory_path, "authoritative inventory")
    if not _contained(script_path, project_root):
        raise WorkbenchFailure(
            "WORKBENCH_NOT_CONFIGURED", 503, "SolForge CLI escapes project root"
        )
    if not _contained(artifact_root, project_root) or artifact_root == project_root:
        raise WorkbenchFailure(
            "WORKBENCH_NOT_CONFIGURED", 503, "artifact root escapes project root"
        )
    artifact_root.mkdir(parents=True, exist_ok=True)
    if artifact_root.is_symlink() or not artifact_root.is_dir():
        raise WorkbenchFailure(
            "WORKBENCH_NOT_CONFIGURED", 503, "artifact root is not a regular directory"
        )

    positive_values = {
        "timeout": settings.SOLFORGE_TIMEOUT_SECONDS,
        "max runs": settings.SOLFORGE_MAX_RUNS,
        "max artifact bytes": settings.SOLFORGE_MAX_ARTIFACT_BYTES,
        "max record bytes": settings.SOLFORGE_MAX_RECORD_BYTES,
        "max concurrent runs": settings.SOLFORGE_MAX_CONCURRENT_RUNS,
    }
    if any(isinstance(value, bool) or int(value) < 1 for value in positive_values.values()):
        raise WorkbenchFailure(
            "WORKBENCH_NOT_CONFIGURED", 503, "Workbench limits must be positive integers"
        )

    return WorkbenchRuntimeConfig(
        engine_python=engine_python,
        project_root=project_root,
        script_path=script_path,
        inventory_path=inventory_path,
        artifact_root=artifact_root,
        timeout_seconds=int(settings.SOLFORGE_TIMEOUT_SECONDS),
        max_runs=int(settings.SOLFORGE_MAX_RUNS),
        max_artifact_bytes=int(settings.SOLFORGE_MAX_ARTIFACT_BYTES),
        max_record_bytes=int(settings.SOLFORGE_MAX_RECORD_BYTES),
        max_concurrent_runs=int(settings.SOLFORGE_MAX_CONCURRENT_RUNS),
    )


def validate_packet_binding(
    request: SolForgeWorkbenchDesignRequestV1,
    config: WorkbenchRuntimeConfig,
) -> tuple[bytes, bytes]:
    """Verify server inventory and case/hypothesis binding before CLI execution."""

    case_bytes = canonical_json_bytes(request.case)
    hypotheses_bytes = canonical_json_bytes(request.hypotheses)
    try:
        requested_inventory = Path(str(request.case["inventory_path"])).resolve()
        declared_inventory_sha256 = str(request.case["inventory_sha256"])
        declared_case_sha256 = str(request.hypotheses["case_sha256"])
    except (KeyError, TypeError, ValueError) as exc:
        raise WorkbenchFailure(
            "PACKET_INVALID", 422, "required packet binding fields are missing"
        ) from exc

    if requested_inventory != config.inventory_path:
        raise WorkbenchFailure(
            "INVENTORY_BINDING_MISMATCH",
            409,
            "case inventory path does not match the configured authority",
        )
    _require_regular_file(config.inventory_path, "authoritative inventory")
    if not _SHA256_RE.fullmatch(declared_inventory_sha256):
        raise WorkbenchFailure(
            "PACKET_INVALID", 422, "inventory_sha256 is not a valid digest"
        )
    observed_inventory_sha256 = _file_sha256(config.inventory_path)
    if declared_inventory_sha256 != observed_inventory_sha256:
        raise WorkbenchFailure(
            "INVENTORY_BINDING_MISMATCH",
            409,
            "case inventory hash does not match the configured authority",
        )

    observed_case_sha256 = hashlib.sha256(case_bytes).hexdigest()
    if declared_case_sha256 != observed_case_sha256:
        raise WorkbenchFailure(
            "PACKET_INVALID",
            422,
            "hypothesis set is not bound to the supplied canonical case",
        )
    return case_bytes, hypotheses_bytes


def inspect_artifact_quota(config: WorkbenchRuntimeConfig) -> tuple[int, int]:
    """Count exact completed run directories without deleting any artifact."""

    if config.artifact_root.is_symlink() or not config.artifact_root.is_dir():
        raise WorkbenchFailure(
            "WORKBENCH_NOT_CONFIGURED", 503, "artifact root is unavailable"
        )
    completed = 0
    total_bytes = 0
    for candidate in config.artifact_root.iterdir():
        if not _RUN_ID_RE.fullmatch(candidate.name):
            continue
        if candidate.is_symlink() or not candidate.is_dir():
            raise WorkbenchFailure(
                "ARTIFACT_VALIDATION_FAILED",
                502,
                "completed run entry is not a regular directory",
            )
        completed += 1
        for record in candidate.iterdir():
            if record.is_symlink():
                raise WorkbenchFailure(
                    "ARTIFACT_VALIDATION_FAILED",
                    502,
                    "artifact run contains a symlink",
                )
            if record.is_file():
                total_bytes += record.stat().st_size
            elif record.is_dir():
                raise WorkbenchFailure(
                    "ARTIFACT_VALIDATION_FAILED",
                    502,
                    "artifact run contains a nested directory",
                )
    return completed, total_bytes


def _load_json_object(path: Path, *, maximum_bytes: int) -> tuple[bytes, dict[str, Any]]:
    if path.is_symlink() or not path.is_file():
        raise WorkbenchFailure(
            "ARTIFACT_VALIDATION_FAILED", 502, "artifact is not a regular file"
        )
    if path.stat().st_size > maximum_bytes:
        raise WorkbenchFailure(
            "ARTIFACT_VALIDATION_FAILED", 502, "artifact exceeds its size limit"
        )
    exact = path.read_bytes()
    try:
        payload = json.loads(exact.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WorkbenchFailure(
            "ARTIFACT_VALIDATION_FAILED", 502, "artifact is not valid UTF-8 JSON"
        ) from exc
    if not isinstance(payload, dict):
        raise WorkbenchFailure(
            "ARTIFACT_VALIDATION_FAILED", 502, "artifact JSON must be an object"
        )
    return exact, payload


def _record_summary(
    entry: dict[str, Any],
    payload: dict[str, Any],
) -> ArtifactRecordSummaryV1:
    return ArtifactRecordSummaryV1(
        filename=str(entry["filename"]),
        schema_version=str(payload["schema_version"]),
        record_sha256=str(entry["record_sha256"]),
        file_sha256=str(entry["file_sha256"]),
    )


def verify_artifact_run(
    run_dir: Path,
    config: WorkbenchRuntimeConfig,
) -> SolForgeWorkbenchDesignResponseV1:
    """Verify every emitted byte before converting a CLI run into an API response."""

    artifact_root = config.artifact_root.resolve()
    run_dir = run_dir.resolve()
    if (
        run_dir.parent != artifact_root
        or not _RUN_ID_RE.fullmatch(run_dir.name)
        or run_dir.is_symlink()
        or not run_dir.is_dir()
    ):
        raise WorkbenchFailure(
            "ARTIFACT_VALIDATION_FAILED", 502, "run directory escapes artifact root"
        )

    manifest_path = run_dir / "MANIFEST.json"
    manifest_exact, manifest = _load_json_object(
        manifest_path, maximum_bytes=_MAX_MANIFEST_BYTES
    )
    if manifest.get("schema_version") != "solforge_artifact_manifest_v1":
        raise WorkbenchFailure(
            "ARTIFACT_VALIDATION_FAILED", 502, "manifest schema is not supported"
        )
    for key in (
        "publication_authorized",
        "database_write_authorized",
        "physical_execution_authorized",
        "release_authorized",
    ):
        if manifest.get(key) is not False:
            raise WorkbenchFailure(
                "ARTIFACT_VALIDATION_FAILED", 502, "manifest escalates authority"
            )
    modules = tuple(manifest.get("complexity_runtime_modules", ()))
    if modules != _ADMITTED_MODULES:
        raise WorkbenchFailure(
            "RUNTIME_MODULE_SET_CHANGED",
            502,
            "Phase 1 permits only architectural-delta-engine",
        )
    registry_sha256 = manifest.get("complexity_runtime_registry_sha256")
    if not isinstance(registry_sha256, str) or not _SHA256_RE.fullmatch(
        registry_sha256
    ):
        raise WorkbenchFailure(
            "ARTIFACT_VALIDATION_FAILED", 502, "registry hash is invalid"
        )

    raw_entries = manifest.get("records")
    if not isinstance(raw_entries, list) or not raw_entries:
        raise WorkbenchFailure(
            "ARTIFACT_VALIDATION_FAILED", 502, "manifest records are missing"
        )
    summaries: list[ArtifactRecordSummaryV1] = []
    payloads: dict[str, tuple[dict[str, Any], str]] = {}
    for raw_entry in raw_entries:
        if not isinstance(raw_entry, dict) or set(raw_entry) != {
            "filename",
            "record_sha256",
            "file_sha256",
        }:
            raise WorkbenchFailure(
                "ARTIFACT_VALIDATION_FAILED", 502, "manifest record entry is invalid"
            )
        filename = raw_entry["filename"]
        record_sha256 = raw_entry["record_sha256"]
        file_sha256 = raw_entry["file_sha256"]
        if (
            not isinstance(filename, str)
            or not filename
            or Path(filename).name != filename
            or "/" in filename
            or "\\" in filename
            or not isinstance(record_sha256, str)
            or not _SHA256_RE.fullmatch(record_sha256)
            or not isinstance(file_sha256, str)
            or not _SHA256_RE.fullmatch(file_sha256)
        ):
            raise WorkbenchFailure(
                "ARTIFACT_VALIDATION_FAILED", 502, "manifest record path or hash is invalid"
            )
        record_path = (run_dir / filename).resolve()
        if record_path.parent != run_dir:
            raise WorkbenchFailure(
                "ARTIFACT_VALIDATION_FAILED", 502, "record escapes run directory"
            )
        record_exact, payload = _load_json_object(
            record_path, maximum_bytes=config.max_record_bytes
        )
        observed_sha256 = hashlib.sha256(record_exact).hexdigest()
        if observed_sha256 != file_sha256 or observed_sha256 != record_sha256:
            raise WorkbenchFailure(
                "ARTIFACT_VALIDATION_FAILED", 502, "record hash does not match manifest"
            )
        schema_version = payload.get("schema_version")
        if not isinstance(schema_version, str) or not schema_version:
            raise WorkbenchFailure(
                "ARTIFACT_VALIDATION_FAILED", 502, "record schema is missing"
            )
        if "authority_flags" in payload and payload["authority_flags"] != AUTHORITY_FLAGS_FALSE:
            raise WorkbenchFailure(
                "ARTIFACT_VALIDATION_FAILED", 502, "record escalates authority"
            )
        if schema_version in payloads:
            raise WorkbenchFailure(
                "ARTIFACT_VALIDATION_FAILED", 502, "duplicate record schema"
            )
        payloads[schema_version] = (payload, record_sha256)
        summaries.append(_record_summary(raw_entry, payload))

    try:
        compiled, compiled_sha256 = payloads["compiled_experiment_v1"]
        decision, _ = payloads["decision_receipt_v1"]
    except KeyError as exc:
        raise WorkbenchFailure(
            "ARTIFACT_VALIDATION_FAILED",
            502,
            "compiled experiment or decision receipt is missing",
        ) from exc


    arms: list[ArmSummaryV1] = []
    raw_arms = compiled.get("arms", [])
    if not isinstance(raw_arms, list):
        raise WorkbenchFailure(
            "ARTIFACT_VALIDATION_FAILED", 502, "compiled arms are invalid"
        )
    for raw_arm in raw_arms:
        if not isinstance(raw_arm, dict) or raw_arm.get("authority_flags") != AUTHORITY_FLAGS_FALSE:
            raise WorkbenchFailure(
                "ARTIFACT_VALIDATION_FAILED", 502, "compiled arm is invalid"
            )
        formula = raw_arm.get("formula")
        factor_presence = (
            formula.get("factor_presence") if isinstance(formula, dict) else None
        )
        if not isinstance(factor_presence, dict) or any(
            not isinstance(name, str) or not isinstance(present, bool)
            for name, present in factor_presence.items()
        ):
            raise WorkbenchFailure(
                "ARTIFACT_VALIDATION_FAILED", 502, "arm factor presence is invalid"
            )
        try:
            arms.append(
                ArmSummaryV1(
                    arm_id=raw_arm["arm_id"],
                    blind_code=raw_arm["blind_code"],
                    sample_sha256=raw_arm["sample_sha256"],
                    total_active_mass_g=raw_arm["total_active_mass_g"],
                    factor_presence=factor_presence,
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise WorkbenchFailure(
                "ARTIFACT_VALIDATION_FAILED", 502, "compiled arm fields are invalid"
            ) from exc

    raw_statuses = compiled.get("inventory_statuses", [])
    if not isinstance(raw_statuses, list) or any(
        not isinstance(item, list)
        or len(item) != 2
        or not all(isinstance(value, str) and value for value in item)
        for item in raw_statuses
    ):
        raise WorkbenchFailure(
            "ARTIFACT_VALIDATION_FAILED", 502, "inventory statuses are invalid"
        )
    history = manifest.get("history")
    blockers = manifest.get("blockers")
    limitations = decision.get("evidence_limitations")
    if (
        not isinstance(history, list)
        or not all(isinstance(item, str) and item for item in history)
        or not isinstance(blockers, list)
        or not all(isinstance(item, str) and item for item in blockers)
        or not isinstance(limitations, list)
        or not all(isinstance(item, str) and item for item in limitations)
    ):
        raise WorkbenchFailure(
            "ARTIFACT_VALIDATION_FAILED", 502, "history or limitations are invalid"
        )

    try:
        return SolForgeWorkbenchDesignResponseV1(
            schema_version="solforge_workbench_design_response_v1",
            run_id=run_dir.name,
            stage=manifest["stage"],
            history=tuple(history),
            decision=decision["decision"],
            blockers=tuple(blockers),
            evidence_limitations=tuple(limitations),
            next_action=decision.get("next_action"),
            registry_sha256=registry_sha256,
            admitted_module_ids=modules,
            compiled_experiment_sha256=compiled_sha256,
            selected_hypothesis_id=compiled.get("selected_hypothesis_id"),
            delta_kind=compiled.get("delta_kind"),
            arms=tuple(arms),
            inventory_statuses=tuple(tuple(item) for item in raw_statuses),
            manifest_sha256=hashlib.sha256(manifest_exact).hexdigest(),
            records=tuple(summaries),
            artifact_download_available=False,
            authority_flags=dict(AUTHORITY_FLAGS_FALSE),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise WorkbenchFailure(
            "ARTIFACT_VALIDATION_FAILED", 502, "verified artifact summary is invalid"
        ) from exc


class SolForgeWorkbenchService:
    """Run one admitted compiler process at a time and verify its exact output."""

    def __init__(self, config: WorkbenchRuntimeConfig) -> None:
        self.config = config
        self._semaphore = asyncio.Semaphore(config.max_concurrent_runs)

    def _check_quota(self) -> tuple[int, int]:
        completed, total_bytes = inspect_artifact_quota(self.config)
        if (
            completed >= self.config.max_runs
            or total_bytes >= self.config.max_artifact_bytes
        ):
            raise WorkbenchFailure(
                "ARTIFACT_QUOTA_EXCEEDED",
                507,
                "archive exact completed runs before starting another design",
            )
        return completed, total_bytes

    async def status(self) -> SolForgeWorkbenchStatusV1:
        completed, total_bytes = inspect_artifact_quota(self.config)
        blockers: list[str] = []
        if completed >= self.config.max_runs:
            blockers.append("MAX_COMPLETED_RUNS_REACHED")
        if total_bytes >= self.config.max_artifact_bytes:
            blockers.append("MAX_ARTIFACT_BYTES_REACHED")
        return SolForgeWorkbenchStatusV1(
            schema_version="solforge_workbench_status_v1",
            ready=not blockers,
            blockers=tuple(blockers),
            completed_run_count=completed,
            artifact_bytes=total_bytes,
            max_runs=self.config.max_runs,
            max_artifact_bytes=self.config.max_artifact_bytes,
            max_concurrent_runs=self.config.max_concurrent_runs,
            artifact_download_available=False,
            authority_flags=dict(AUTHORITY_FLAGS_FALSE),
        )

    async def _run_cli(
        self,
        case_path: Path,
        hypotheses_path: Path,
        run_dir: Path,
    ) -> None:
        environment = dict(os.environ)
        environment["PYTHONUTF8"] = "1"
        process = await asyncio.create_subprocess_exec(
            str(self.config.engine_python),
            str(self.config.script_path),
            "--solforge-case",
            str(case_path),
            "--solforge-hypotheses",
            str(hypotheses_path),
            "--output-dir",
            str(run_dir),
            cwd=str(self.config.project_root),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=environment,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=self.config.timeout_seconds
            )
        except TimeoutError as exc:
            process.kill()
            await process.wait()
            raise WorkbenchFailure(
                "ENGINE_TIMEOUT", 504, "SolForge CLI exceeded its execution timeout"
            ) from exc
        if process.returncode != 0:
            exact = stderr or stdout or b""
            detail = exact.decode("utf-8", errors="replace")[-16_384:]
            raise WorkbenchFailure(
                "ENGINE_REJECTED_PACKET",
                422,
                detail or "SolForge CLI rejected the closed packet",
            )

    async def run_design(
        self,
        request: SolForgeWorkbenchDesignRequestV1,
    ) -> SolForgeWorkbenchDesignResponseV1:
        case_bytes, hypotheses_bytes = validate_packet_binding(request, self.config)
        async with self._semaphore:
            self._check_quota()
            run_id = f"sf-{uuid.uuid4().hex}"
            run_dir = self.config.artifact_root / run_id
            with tempfile.TemporaryDirectory(
                prefix=".sf-input-", dir=self.config.artifact_root
            ) as temporary:
                input_root = Path(temporary)
                case_path = input_root / "case.json"
                hypotheses_path = input_root / "hypotheses.json"
                case_path.write_bytes(case_bytes)
                hypotheses_path.write_bytes(hypotheses_bytes)
                await self._run_cli(case_path, hypotheses_path, run_dir)
            return verify_artifact_run(run_dir, self.config)


__all__ = [
    "WorkbenchFailure",
    "WorkbenchRuntimeConfig",
    "SolForgeWorkbenchService",
    "canonical_json_bytes",
    "inspect_artifact_quota",
    "resolve_runtime_config",
    "validate_packet_binding",
    "verify_artifact_run",
]
