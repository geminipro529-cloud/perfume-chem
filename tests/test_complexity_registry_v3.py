from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from engine.perception.complexity_registry import ModuleState, load_complexity_registry

ROOT = Path(__file__).resolve().parents[1]
V1 = ROOT / "configs/complexity/complexity_module_registry_v1.json"
V2 = ROOT / "configs/complexity/complexity_module_registry_v2.json"
V3 = ROOT / "configs/complexity/complexity_module_registry_v3.json"
V1_SHA256 = "7567f3ca00ccbf3e1b2b41f50645ed21f4d163612872b8449db6cc022818c639"
V2_SHA256 = "d17a3747432f7a002cb6b42aa25cb67b8b215cfe7f2b9a3adf92498c87504500"


def _copy_registry_project(tmp_path: Path) -> tuple[Path, Path]:
    project = tmp_path / "project"
    payloads = [json.loads(path.read_text(encoding="utf-8")) for path in (V1, V2, V3)]
    paths = {
        row["path"]
        for row in payloads[0]["modules"] + payloads[1]["module_additions"]
    }
    paths.update(row["path"] for row in payloads[2]["module_additions"])
    paths.update(item["path"] for item in payloads[2]["required_evidence"])
    for source in (V1, V2, V3):
        target = project / source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    for relative in paths:
        source = ROOT / relative
        target = project / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    return project, project / V3.relative_to(ROOT)


def test_v1_and_accepted_v2_bytes_are_frozen() -> None:
    assert hashlib.sha256(V1.read_bytes()).hexdigest() == V1_SHA256
    assert hashlib.sha256(V2.read_bytes()).hexdigest() == V2_SHA256


def test_v3_loads_as_nonruntime_overlay_with_exact_predecessor_chain() -> None:
    registry = load_complexity_registry(ROOT, V3)
    assert registry.schema_version == "complexity_module_registry_v3"
    assert registry.module_by_id("solforge-shadow-orchestrator").state is (
        ModuleState.EXPERIMENT_COMPILER
    )
    assert registry.module_by_id("architectural-delta-engine").state is (
        ModuleState.EXPERIMENT_COMPILER
    )
    assert registry.module_by_id("temporal-sensory-ledger").state is (
        ModuleState.DIAGNOSTIC_ONLY
    )
    assert registry.module_by_id("hedonic-preference-learner").state is (
        ModuleState.DIAGNOSTIC_ONLY
    )
    assert all(
        module.import_path is None
        for module in registry.modules
        if module.state is not ModuleState.ADMITTED_RUNTIME
    )
    assert not any(module.runtime_eligible for module in registry.modules)


def test_v3_preserves_retired_modules_as_provenance_tombstones() -> None:
    registry = load_complexity_registry(ROOT, V3)
    retired = registry.module_by_id("musk-design-restraint")
    assert retired.state is ModuleState.PROVENANCE_TOMBSTONE
    assert retired.sha256
    assert retired.evidence_refs
    assert retired.import_path is None


def test_wrong_base_hash_fails_closed(tmp_path: Path) -> None:
    project, path = _copy_registry_project(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["base_registry_chain"][1]["sha256"] = "0" * 64
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="base registry hash mismatch"):
        load_complexity_registry(project, path)


def test_unknown_v3_state_fails_closed(tmp_path: Path) -> None:
    project, path = _copy_registry_project(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["module_overrides"][0]["state"] = "MAGIC"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="unknown role or state"):
        load_complexity_registry(project, path)


def test_only_admitted_runtime_can_have_v3_import_path(tmp_path: Path) -> None:
    project, path = _copy_registry_project(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["module_overrides"][0]["import_path"] = "engine.fake"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="non-runtime module"):
        load_complexity_registry(project, path)


def test_v3_authority_flags_are_closed_and_all_false(tmp_path: Path) -> None:
    project, path = _copy_registry_project(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["authority_flags"]["release"] = True
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="authority flags"):
        load_complexity_registry(project, path)
