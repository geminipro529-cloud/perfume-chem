from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from engine.perception.complexity_registry import (
    ModuleState,
    census_complexity_artifacts,
    load_complexity_registry,
)
from tests.test_complexity_registry_v4 import _copy_registry_project

ROOT = Path(__file__).resolve().parents[1]
V4 = ROOT / "configs/complexity/complexity_module_registry_v4.json"
V5 = ROOT / "configs/complexity/complexity_module_registry_v5.json"


def test_v5_admits_only_architectural_delta_after_exact_benchmark_gate(
    tmp_path: Path,
) -> None:
    project, path = _copy_v5_project(tmp_path)
    registry = load_complexity_registry(project, path)
    assert registry.schema_version == "complexity_module_registry_v5"

    architectural = registry.module_by_id("architectural-delta-engine")
    assert architectural.state is ModuleState.ADMITTED_RUNTIME
    assert architectural.import_path == "engine.perception.architectural_delta"
    assert architectural.runtime_eligible is True
    assert hashlib.sha256((project / architectural.path).read_bytes()).hexdigest() == (
        architectural.sha256
    )

    for module_id in ("temporal-sensory-ledger", "hedonic-preference-learner"):
        module = registry.module_by_id(module_id)
        assert module.state is ModuleState.RETIRED_BENCHMARK_UNDERPERFORMER
        assert module.import_path is None
        assert module.runtime_eligible is False
    assert {module.module_id for module in registry.modules if module.runtime_eligible} == {
        "architectural-delta-engine"
    }


def test_v5_binds_exact_screen_and_confirmation_evidence() -> None:
    payload = json.loads(V5.read_text(encoding="utf-8"))
    assert hashlib.sha256(V4.read_bytes()).hexdigest() == payload["base_registry"][
        "sha256"
    ]
    assert payload["authority_flags"] == {
        "compounding": False,
        "formula": False,
        "hedonic": False,
        "purchase": False,
        "release": False,
        "safety": False,
        "scientific": False,
        "sensory": False,
    }
    for item in payload["admission_evidence"]:
        path = ROOT / item["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]


def test_frozen_v5_detects_post_benchmark_runtime_drift() -> None:
    payload = json.loads(V5.read_text(encoding="utf-8"))
    bindings = payload["runtime_bindings"]
    assert {item["path"] for item in bindings} == {
        "engine/perception/complexity_registry.py",
        "engine/solforge/runtime.py",
        "scripts/intervention_recommend.py",
    }
    drifted = {
        item["path"]
        for item in bindings
        if hashlib.sha256((ROOT / item["path"]).read_bytes()).hexdigest()
        != item["sha256"]
    }
    assert drifted == {
        "engine/perception/complexity_registry.py",
        "engine/solforge/runtime.py",
    }


def test_v5_reconstructed_census_detects_later_hedonic_model_drift(
    tmp_path: Path,
) -> None:
    project, path = _copy_v5_project(tmp_path)
    registry = load_complexity_registry(project, path)
    result = census_complexity_artifacts(project, registry)
    assert result.state == "HOLD"
    assert result.hash_drift == ("engine/hedonic_model.py",)
    assert result.missing == ()
    assert result.unclassified == ()
    assert result.multiply_classified == ()


def _copy_v5_project(tmp_path: Path) -> tuple[Path, Path]:
    project, target_v4 = _copy_registry_project(tmp_path)
    target_v5 = project / V5.relative_to(ROOT)
    target_v5.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(V5, target_v5)
    payload = json.loads(V5.read_text(encoding="utf-8"))
    for item in (*payload["admission_evidence"], *payload["runtime_bindings"]):
        source = ROOT / item["path"]
        target = project / item["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    payload["base_registry"]["sha256"] = hashlib.sha256(
        target_v4.read_bytes()
    ).hexdigest()
    v4_registry = load_complexity_registry(project, target_v4)
    for item in payload["module_overrides"]:
        module_path = v4_registry.module_by_id(item["module_id"]).path
        item["sha256"] = hashlib.sha256(
            (project / module_path).read_bytes()
        ).hexdigest()
    for item in payload["runtime_bindings"]:
        item["sha256"] = hashlib.sha256(
            (project / item["path"]).read_bytes()
        ).hexdigest()
    target_v5.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return project, target_v5


def test_v5_parent_evidence_and_authority_tampering_fail_closed(
    tmp_path: Path,
) -> None:
    project, path = _copy_v5_project(tmp_path / "parent")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["base_registry"]["sha256"] = "0" * 64
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="base registry hash mismatch"):
        load_complexity_registry(project, path)

    project, path = _copy_v5_project(tmp_path / "evidence")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["admission_evidence"][0]["sha256"] = "0" * 64
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="admission evidence hash mismatch"):
        load_complexity_registry(project, path)

    project, path = _copy_v5_project(tmp_path / "authority")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["authority_flags"]["hedonic"] = True
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="authority flags"):
        load_complexity_registry(project, path)


def test_v5_runtime_wiring_tampering_fails_closed(tmp_path: Path) -> None:
    project, path = _copy_v5_project(tmp_path)
    runtime = project / "engine/solforge/runtime.py"
    runtime.write_bytes(runtime.read_bytes() + b"\n# drift\n")
    with pytest.raises(ValueError, match="runtime binding hash mismatch"):
        load_complexity_registry(project, path)


def test_frozen_v5_fails_closed_against_the_current_repository() -> None:
    with pytest.raises(
        ValueError,
        match="source binding hash mismatch|runtime binding hash mismatch",
    ):
        load_complexity_registry(ROOT, V5)
