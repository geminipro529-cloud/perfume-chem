from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from engine.perception.complexity_registry import load_complexity_registry

ROOT = Path(__file__).resolve().parents[1]
V1 = ROOT / "configs/complexity/complexity_module_registry_v1.json"
V2 = ROOT / "configs/complexity/complexity_module_registry_v2.json"
V3 = ROOT / "configs/complexity/complexity_module_registry_v3.json"
V4 = ROOT / "configs/complexity/complexity_module_registry_v4.json"
FROZEN = {
    V1.name: "7567f3ca00ccbf3e1b2b41f50645ed21f4d163612872b8449db6cc022818c639",
    V2.name: "d17a3747432f7a002cb6b42aa25cb67b8b215cfe7f2b9a3adf92498c87504500",
    V3.name: "44ecf5268e494121d132dcf99586e099cc4b8819b2367ce08ef7da9c1af37476",
}


def _copy_registry_project(tmp_path: Path) -> tuple[Path, Path]:
    project = tmp_path / "project"
    payload = json.loads(V4.read_text(encoding="utf-8"))
    registry_paths = (V1, V2, V3, V4)
    module_paths = {
        item["path"]
        for path in registry_paths[:3]
        for item in json.loads(path.read_text(encoding="utf-8")).get(
            "module_additions", []
        )
    }
    module_paths.update(
        item["path"]
        for item in json.loads(V1.read_text(encoding="utf-8"))["modules"]
    )
    module_paths.update(
        item["path"]
        for item in json.loads(V3.read_text(encoding="utf-8"))["required_evidence"]
    )
    module_paths.update(item["path"] for item in payload["source_bindings"])
    for source in registry_paths:
        target = project / source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    for relative in module_paths:
        source = ROOT / relative
        target = project / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    return project, project / V4.relative_to(ROOT)


def test_v4_preserves_every_frozen_predecessor_byte() -> None:
    for path in (V1, V2, V3):
        assert hashlib.sha256(path.read_bytes()).hexdigest() == FROZEN[path.name]


def test_v4_frozen_overlay_records_unadmitted_nonruntime_metadata() -> None:
    payload = json.loads(V4.read_text(encoding="utf-8"))
    overrides = {item["module_id"]: item for item in payload["module_overrides"]}
    for module_id in (
        "architectural-delta-engine",
        "temporal-sensory-ledger",
        "hedonic-preference-learner",
    ):
        assert overrides[module_id]["state"] == "FUTURE_CANDIDATE_NOT_VALIDATED"
        assert overrides[module_id]["import_path"] is None
    assert overrides["temporal-sensory-ledger"]["sha256"] == (
        "03b5742e8e66dcf1cc27a94b3e5c4484899ee08893b1b34e006d8890805d0f9f"
    )
    assert payload["module_additions"] == []


def test_v4_strict_load_fails_closed_after_declared_ledger_successor() -> None:
    with pytest.raises(
        ValueError,
        match="source binding hash mismatch: engine/sensory/ledger.py",
    ):
        load_complexity_registry(ROOT, V4)


def test_v4_parent_and_source_hashes_fail_closed(tmp_path: Path) -> None:
    project, path = _copy_registry_project(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["base_registry_chain"][2]["sha256"] = "0" * 64
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="base registry hash mismatch"):
        load_complexity_registry(project, path)

    project, path = _copy_registry_project(tmp_path / "source")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["source_bindings"][0]["sha256"] = "0" * 64
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="source binding hash mismatch"):
        load_complexity_registry(project, path)


def test_v4_authority_is_closed_and_all_false(tmp_path: Path) -> None:
    project, path = _copy_registry_project(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["authority_flags"]["hedonic"] = True
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="authority flags"):
        load_complexity_registry(project, path)
