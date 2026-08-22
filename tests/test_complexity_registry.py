from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from engine.perception.complexity_registry import (
    ModuleState,
    census_complexity_artifacts,
    load_complexity_registry,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = PROJECT_ROOT / "configs/complexity/complexity_module_registry_v1.json"


def _write_registry_fixture(root: Path):
    module = root / "engine/perception/construction_complexity.py"
    module.parent.mkdir(parents=True)
    module.write_text("VALUE = 1\n", encoding="utf-8")
    digest = hashlib.sha256(module.read_bytes()).hexdigest()
    registry_path = root / "registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "schema_version": "complexity_module_registry_v1",
                "discovery": {
                    "roots": ["engine", "future_modules"],
                    "terms": ["complexity", "hedonic", "musk"],
                    "metadata_keys": [],
                },
                "modules": [
                    {
                        "module_id": "construction-profile",
                        "family_id": "construction_profile",
                        "role": "CAPABILITY",
                        "state": "ACTIVE_CANDIDATE",
                        "path": "engine/perception/construction_complexity.py",
                        "import_path": "engine.perception.construction_complexity",
                        "sha256": digest,
                        "evidence_refs": [],
                    }
                ],
                "artifact_rules": [],
                "dismissal_rules": [],
            }
        ),
        encoding="utf-8",
    )
    return load_complexity_registry(root, registry_path)


def test_registry_loads_only_exact_hash_bound_native_candidates(tmp_path: Path) -> None:
    registry = _write_registry_fixture(tmp_path)
    assert registry.modules[0].state is ModuleState.ACTIVE_CANDIDATE
    assert census_complexity_artifacts(tmp_path, registry).state == "PASS"


def test_census_holds_on_hash_drift_or_unclassified_match(tmp_path: Path) -> None:
    registry = _write_registry_fixture(tmp_path)
    (tmp_path / registry.modules[0].path).write_text("VALUE = 2\n", encoding="utf-8")
    candidate = tmp_path / "future_modules/family_hedonic_optimizer.py"
    candidate.parent.mkdir(parents=True)
    candidate.write_text("VALUE = 3\n", encoding="utf-8")
    result = census_complexity_artifacts(tmp_path, registry)
    assert result.state == "HOLD"
    assert result.hash_drift
    assert result.unclassified


def test_unknown_rights_rule_can_never_be_runtime_eligible() -> None:
    registry = load_complexity_registry(PROJECT_ROOT, REGISTRY_PATH)
    external = [
        module
        for module in registry.modules
        if module.state is ModuleState.EVIDENCE_ONLY_NOT_ADMITTED
    ]
    assert external
    assert all(not item.runtime_eligible for item in external)


def test_future_advanced_musk_has_no_runtime_import() -> None:
    registry = load_complexity_registry(PROJECT_ROOT, REGISTRY_PATH)
    advanced = registry.module_by_id("advanced-musk-intelligence")
    assert advanced.state is ModuleState.FUTURE_CANDIDATE_NOT_VALIDATED
    assert advanced.import_path is None
    assert advanced.runtime_eligible is False


def test_repository_census_has_exactly_one_classification_per_finding() -> None:
    registry = load_complexity_registry(PROJECT_ROOT, REGISTRY_PATH)
    result = census_complexity_artifacts(PROJECT_ROOT, registry)
    assert result.multiply_classified == ()
    assert result.unclassified == ()
    assert result.state == "PASS"


def test_registry_rejects_paths_outside_the_project(tmp_path: Path) -> None:
    module = tmp_path / "safe.py"
    module.write_text("VALUE = 1\n", encoding="utf-8")
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "schema_version": "complexity_module_registry_v1",
                "discovery": {"roots": ["."], "terms": ["complexity"], "metadata_keys": []},
                "modules": [
                    {
                        "module_id": "unsafe",
                        "family_id": "unsafe",
                        "role": "CAPABILITY",
                        "state": "ACTIVE_CANDIDATE",
                        "path": "../outside.py",
                        "import_path": "outside",
                        "sha256": "0" * 64,
                        "evidence_refs": [],
                    }
                ],
                "artifact_rules": [],
                "dismissal_rules": [],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="repository-relative"):
        load_complexity_registry(tmp_path, registry_path)
