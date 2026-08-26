from __future__ import annotations

import asyncio
import hashlib
import json
import math
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

import pytest

from app.schemas.solforge_workbench import (
    AUTHORITY_FLAGS_FALSE,
    SolForgeWorkbenchDesignRequestV1,
)
from app.services.solforge_workbench import (
    SolForgeWorkbenchService,
    WorkbenchFailure,
    WorkbenchRuntimeConfig,
    canonical_json_bytes,
    inspect_artifact_quota,
    validate_packet_binding,
    verify_artifact_run,
)


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _write_canonical(path: Path, payload: object) -> str:
    exact = canonical_json_bytes(payload)
    path.write_bytes(exact)
    return _sha(exact)


@pytest.fixture
def short_tmp_path() -> Path:
    base = Path(__file__).resolve().parents[2] / "output" / "wb-tests"
    base.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="w-", dir=base) as temporary:
        yield Path(temporary)


@pytest.fixture
def runtime_config(short_tmp_path: Path) -> WorkbenchRuntimeConfig:
    project_root = short_tmp_path / "project"
    project_root.mkdir()
    script_path = project_root / "scripts" / "intervention_recommend.py"
    script_path.parent.mkdir()
    script_path.write_text("raise SystemExit(0)\n", encoding="utf-8")
    inventory_path = project_root / "inventory.xlsx"
    inventory_path.write_bytes(b"authoritative inventory bytes")
    artifact_root = project_root / "output" / "solforge-workbench"
    artifact_root.mkdir(parents=True)
    return WorkbenchRuntimeConfig(
        engine_python=Path(sys.executable).resolve(),
        project_root=project_root.resolve(),
        script_path=script_path.resolve(),
        inventory_path=inventory_path.resolve(),
        artifact_root=artifact_root.resolve(),
        timeout_seconds=90,
        max_runs=50,
        max_artifact_bytes=104_857_600,
        max_record_bytes=4_194_304,
        max_concurrent_runs=1,
    )


def _request(config: WorkbenchRuntimeConfig) -> SolForgeWorkbenchDesignRequestV1:
    case = {
        "schema_version": "solforge_case_v1",
        "state": "READY",
        "case_id": "WB-1",
        "target_identity": "austere sweet orris root",
        "ideal_architecture": {"heart": ["orris root"]},
        "current_inventory_build": {"materials": {"Orris accord": 1.0}},
        "inventory_path": str(config.inventory_path),
        "inventory_sha256": _sha(config.inventory_path.read_bytes()),
        "formula_sha256": "b" * 64,
        "dose_receipt_sha256": "c" * 64,
        "constraints": ["CONSTANT_TOTAL_ACTIVE_MASS"],
        "criterion": "DEPTH",
        "forbidden_claims": ["sensory"],
        "authority_flags": dict(AUTHORITY_FLAGS_FALSE),
    }
    hypotheses = {
        "schema_version": "sol_hypothesis_set_v1",
        "case_sha256": _sha(canonical_json_bytes(case)),
        "model_identity": "gpt-5.6-sol",
        "reasoning_setting": "ultra",
        "prompt_sha256": "e" * 64,
        "input_sha256": "f" * 64,
        "output_sha256": "1" * 64,
        "hypotheses": [],
        "uncertainty": "No nonredundant change justified.",
        "authority_flags": dict(AUTHORITY_FLAGS_FALSE),
    }
    return SolForgeWorkbenchDesignRequestV1(
        schema_version="solforge_workbench_design_request_v1",
        case=case,
        hypotheses=hypotheses,
    )


def _record_payloads() -> list[dict]:
    case = {
        "schema_version": "solforge_case_v1",
        "case_id": "WB-1",
        "authority_flags": dict(AUTHORITY_FLAGS_FALSE),
    }
    hypotheses = {
        "schema_version": "sol_hypothesis_set_v1",
        "case_sha256": "a" * 64,
        "authority_flags": dict(AUTHORITY_FLAGS_FALSE),
    }
    compiled = {
        "schema_version": "compiled_experiment_v1",
        "state": "COMPILED",
        "delta_kind": "ADDITION",
        "selected_hypothesis_id": "ONE-HABANOLIDE",
        "arms": [
            {
                "schema_version": "compiled_arm_v1",
                "arm_id": "CONTROL",
                "formula": {
                    "factor_presence": {"Habanolide": False},
                },
                "total_active_mass_g": 1.0,
                "blind_code": "SF-11111111",
                "sample_sha256": "1" * 64,
                "authority_flags": dict(AUTHORITY_FLAGS_FALSE),
            },
            {
                "schema_version": "compiled_arm_v1",
                "arm_id": "ONE_HABANOLIDE",
                "formula": {
                    "factor_presence": {"Habanolide": True},
                },
                "total_active_mass_g": 1.0,
                "blind_code": "SF-22222222",
                "sample_sha256": "2" * 64,
                "authority_flags": dict(AUTHORITY_FLAGS_FALSE),
            },
        ],
        "inventory_statuses": [["Habanolide", "OWNED"]],
        "authority_flags": dict(AUTHORITY_FLAGS_FALSE),
    }
    decision = {
        "schema_version": "decision_receipt_v1",
        "decision": "EVIDENCE_INSUFFICIENT",
        "evidence_limitations": [
            "No admitted temporal or preference evidence analyzer is available."
        ],
        "next_action": "Compare CONTROL with ONE_HABANOLIDE.",
        "authority_flags": dict(AUTHORITY_FLAGS_FALSE),
    }
    return [case, hypotheses, compiled, decision]


def _populate_valid_run(run_dir: Path) -> Path:
    run_dir.mkdir()
    records = []
    for payload in _record_payloads():
        exact = canonical_json_bytes(payload)
        digest = _sha(exact)
        filename = f"{payload['schema_version']}--{digest}.json"
        (run_dir / filename).write_bytes(exact)
        records.append(
            {
                "filename": filename,
                "record_sha256": digest,
                "file_sha256": digest,
            }
        )
    manifest = {
        "schema_version": "solforge_artifact_manifest_v1",
        "stage": "EXPORTED",
        "history": ["INTAKE", "COMPILED", "EXPORTED"],
        "input_file_sha256": {},
        "records": records,
        "blockers": [],
        "complexity_runtime_registry_sha256": "9" * 64,
        "complexity_runtime_modules": ["architectural-delta-engine"],
        "publication_authorized": False,
        "database_write_authorized": False,
        "physical_execution_authorized": False,
        "release_authorized": False,
    }
    _write_canonical(run_dir / "MANIFEST.json", manifest)
    return run_dir


@pytest.fixture
def valid_run(runtime_config: WorkbenchRuntimeConfig) -> Path:
    return _populate_valid_run(
        runtime_config.artifact_root / ("sf-" + "1" * 32)
    )


class _FakeProcess:
    def __init__(
        self,
        *,
        returncode: int = 0,
        stdout: bytes = b"",
        stderr: bytes = b"",
        block: bool = False,
    ) -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.block = block
        self.killed = False
        self.waited = False
        self.communicate_started = asyncio.Event()

    async def communicate(self) -> tuple[bytes, bytes]:
        self.communicate_started.set()
        if self.block:
            await asyncio.Event().wait()
        return self.stdout, self.stderr

    def kill(self) -> None:
        self.killed = True

    async def wait(self) -> int:
        self.waited = True
        return self.returncode


def test_canonical_json_matches_engine_contract_shape() -> None:
    assert canonical_json_bytes({"b": 2, "a": 1}) == b'{"a":1,"b":2}'
    with pytest.raises(ValueError):
        canonical_json_bytes({"bad": math.nan})


def test_packet_binding_returns_canonical_bytes(runtime_config) -> None:
    request = _request(runtime_config)

    case_bytes, hypotheses_bytes = validate_packet_binding(request, runtime_config)

    assert _sha(case_bytes) == request.hypotheses["case_sha256"]
    assert json.loads(hypotheses_bytes)["reasoning_setting"] == "ultra"


def test_packet_binding_rejects_inventory_path_override(runtime_config) -> None:
    request = _request(runtime_config)
    payload = request.model_dump()
    payload["case"]["inventory_path"] = str(runtime_config.project_root / "other.xlsx")
    changed = SolForgeWorkbenchDesignRequestV1.model_validate(payload)

    with pytest.raises(WorkbenchFailure, match="INVENTORY_BINDING_MISMATCH"):
        validate_packet_binding(changed, runtime_config)


def test_packet_binding_rejects_inventory_hash_mismatch(runtime_config) -> None:
    request = _request(runtime_config)
    payload = request.model_dump()
    payload["case"]["inventory_sha256"] = "0" * 64
    changed = SolForgeWorkbenchDesignRequestV1.model_validate(payload)

    with pytest.raises(WorkbenchFailure, match="INVENTORY_BINDING_MISMATCH"):
        validate_packet_binding(changed, runtime_config)


def test_packet_binding_rejects_case_hash_mismatch(runtime_config) -> None:
    request = _request(runtime_config)
    payload = request.model_dump()
    payload["hypotheses"]["case_sha256"] = "f" * 64
    changed = SolForgeWorkbenchDesignRequestV1.model_validate(payload)

    with pytest.raises(WorkbenchFailure, match="PACKET_INVALID"):
        validate_packet_binding(changed, runtime_config)


def test_quota_counts_only_direct_completed_runs(runtime_config, valid_run) -> None:
    (runtime_config.artifact_root / ".temporary-input").mkdir()
    count, total = inspect_artifact_quota(runtime_config)

    assert count == 1
    assert total == sum(
        path.stat().st_size for path in valid_run.iterdir() if path.is_file()
    )


def test_artifact_verifier_builds_closed_response(runtime_config, valid_run) -> None:
    response = verify_artifact_run(valid_run, runtime_config)

    assert response.run_id == valid_run.name
    assert response.stage == "EXPORTED"
    assert response.decision == "EVIDENCE_INSUFFICIENT"
    assert response.admitted_module_ids == ("architectural-delta-engine",)
    assert [arm.arm_id for arm in response.arms] == ["CONTROL", "ONE_HABANOLIDE"]
    assert response.inventory_statuses == (("Habanolide", "OWNED"),)
    assert not any(response.authority_flags.values())


def test_artifact_verifier_rejects_parent_path(runtime_config, valid_run) -> None:
    manifest_path = valid_run / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["records"][0]["filename"] = "../escape.json"
    _write_canonical(manifest_path, manifest)

    with pytest.raises(WorkbenchFailure, match="ARTIFACT_VALIDATION_FAILED"):
        verify_artifact_run(valid_run, runtime_config)


def test_artifact_verifier_rejects_hash_mismatch(runtime_config, valid_run) -> None:
    record = next(valid_run.glob("decision_receipt_v1--*.json"))
    record.write_bytes(b"{}")

    with pytest.raises(WorkbenchFailure, match="ARTIFACT_VALIDATION_FAILED"):
        verify_artifact_run(valid_run, runtime_config)


def test_artifact_verifier_rejects_authority_escalation(runtime_config, valid_run) -> None:
    record = next(valid_run.glob("decision_receipt_v1--*.json"))
    payload = json.loads(record.read_text(encoding="utf-8"))
    payload["authority_flags"]["release"] = True
    record.write_bytes(canonical_json_bytes(payload))
    manifest_path = valid_run / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entry = next(item for item in manifest["records"] if item["filename"] == record.name)
    entry["file_sha256"] = _sha(record.read_bytes())
    _write_canonical(manifest_path, manifest)

    with pytest.raises(WorkbenchFailure, match="ARTIFACT_VALIDATION_FAILED"):
        verify_artifact_run(valid_run, runtime_config)


def test_artifact_verifier_rejects_runtime_module_set_change(runtime_config, valid_run) -> None:
    manifest_path = valid_run / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["complexity_runtime_modules"].append("temporal-sensory-ledger")
    _write_canonical(manifest_path, manifest)

    with pytest.raises(WorkbenchFailure, match="RUNTIME_MODULE_SET_CHANGED"):
        verify_artifact_run(valid_run, runtime_config)


@pytest.mark.asyncio
async def test_runner_uses_fixed_argv_without_shell(runtime_config, monkeypatch) -> None:
    observed: dict[str, object] = {}

    async def fake_create_subprocess_exec(*argv, **kwargs):
        observed["argv"] = argv
        observed["kwargs"] = kwargs
        output_index = argv.index("--output-dir") + 1
        _populate_valid_run(Path(argv[output_index]))
        return _FakeProcess()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)
    service = SolForgeWorkbenchService(runtime_config)

    response = await service.run_design(_request(runtime_config))

    argv = observed["argv"]
    kwargs = observed["kwargs"]
    assert argv[0] == str(runtime_config.engine_python)
    assert argv[1] == str(runtime_config.script_path)
    assert kwargs["cwd"] == str(runtime_config.project_root)
    assert "shell" not in kwargs
    assert response.admitted_module_ids == ("architectural-delta-engine",)


@pytest.mark.asyncio
async def test_runner_maps_timeout_to_engine_timeout(runtime_config, monkeypatch) -> None:
    process = _FakeProcess(block=True)
    config = replace(runtime_config, timeout_seconds=0.01)

    async def fake_create_subprocess_exec(*_argv, **_kwargs):
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)
    service = SolForgeWorkbenchService(config)

    with pytest.raises(WorkbenchFailure, match="ENGINE_TIMEOUT"):
        await service.run_design(_request(config))
    assert process.killed is True
    assert process.waited is True


@pytest.mark.asyncio
async def test_runner_kills_child_and_releases_slot_when_cancelled(
    runtime_config, monkeypatch
) -> None:
    blocked_process = _FakeProcess(block=True)
    invocation = 0

    async def fake_create_subprocess_exec(*argv, **_kwargs):
        nonlocal invocation
        invocation += 1
        if invocation == 1:
            return blocked_process
        output_index = argv.index("--output-dir") + 1
        _populate_valid_run(Path(argv[output_index]))
        return _FakeProcess()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)
    service = SolForgeWorkbenchService(runtime_config)
    first = asyncio.create_task(service.run_design(_request(runtime_config)))
    await blocked_process.communicate_started.wait()

    first.cancel()
    with pytest.raises(asyncio.CancelledError):
        await first

    assert blocked_process.killed is True
    assert blocked_process.waited is True
    second = await asyncio.wait_for(
        service.run_design(_request(runtime_config)), timeout=1
    )
    assert second.admitted_module_ids == ("architectural-delta-engine",)


@pytest.mark.asyncio
async def test_runner_maps_nonzero_exit_without_publishing(runtime_config, monkeypatch) -> None:
    process = _FakeProcess(returncode=2, stderr=b"closed contract rejected")

    async def fake_create_subprocess_exec(*_argv, **_kwargs):
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)
    service = SolForgeWorkbenchService(runtime_config)

    with pytest.raises(WorkbenchFailure, match="ENGINE_REJECTED_PACKET") as caught:
        await service.run_design(_request(runtime_config))
    assert "closed contract rejected" in caught.value.detail


@pytest.mark.asyncio
async def test_runner_refuses_quota_without_starting_process(runtime_config, monkeypatch) -> None:
    _populate_valid_run(runtime_config.artifact_root / ("sf-" + "2" * 32))
    config = replace(runtime_config, max_runs=1)
    called = False

    async def fake_create_subprocess_exec(*_argv, **_kwargs):
        nonlocal called
        called = True
        return _FakeProcess()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)
    service = SolForgeWorkbenchService(config)

    with pytest.raises(WorkbenchFailure, match="ARTIFACT_QUOTA_EXCEEDED"):
        await service.run_design(_request(config))
    assert called is False


@pytest.mark.asyncio
async def test_status_reports_configuration_and_quota(runtime_config) -> None:
    service = SolForgeWorkbenchService(runtime_config)

    status = await service.status()

    assert status.ready is True
    assert status.completed_run_count == 0
    assert status.artifact_download_available is False
    assert not any(status.authority_flags.values())
