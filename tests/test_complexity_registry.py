from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from engine.perception.complexity_registry import (
    CURRENT_REGISTRY_PATH,
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


def test_failed_benchmark_families_are_recoverably_retired() -> None:
    registry = load_complexity_registry(PROJECT_ROOT, REGISTRY_PATH)
    retired_ids = {
        "construction-profile",
        "complexity-expansion-frontier",
        "musk-design-restraint",
        "complexity-model-admission",
        "complexity-model-lifecycle",
        "within-sniff-observation-contract",
        "temporal-observation-contract",
        "order-balance-contract",
        "sensory-panel-contract",
    }

    for module_id in retired_ids:
        module = registry.module_by_id(module_id)
        assert module.state is ModuleState.RETIRED_BENCHMARK_UNDERPERFORMER
        assert module.runtime_eligible is False

    experimental = registry.module_by_id("complexity-experimental-design")
    assert experimental.state is ModuleState.ACTIVE_CANDIDATE
    assert experimental.runtime_eligible is True


def test_repository_census_has_exactly_one_classification_per_finding() -> None:
    registry = load_complexity_registry(PROJECT_ROOT, PROJECT_ROOT / CURRENT_REGISTRY_PATH)
    result = census_complexity_artifacts(PROJECT_ROOT, registry)
    assert result.multiply_classified == ()
    assert result.unclassified == ()
    assert result.state == "PASS", result.as_dict()


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


def _write_overlay_fixture(root: Path):
    _write_registry_fixture(root)
    base = root / "registry.json"
    module = root / "future_modules/new_complexity.py"
    module.parent.mkdir(parents=True)
    module.write_text("raise AssertionError('census must not import candidates')\n", encoding="utf-8")
    payload = {
        "schema_version": "complexity_module_registry_overlay_v1",
        "base_registry": "registry.json",
        "base_registry_sha256": hashlib.sha256(base.read_bytes()).hexdigest(),
        "module_additions": [{
            "module_id": "new-complexity", "family_id": "new-complexity",
            "role": "CAPABILITY", "state": "FUTURE_CANDIDATE_NOT_VALIDATED",
            "path": "future_modules/new_complexity.py", "import_path": None,
            "sha256": hashlib.sha256(module.read_bytes()).hexdigest(), "evidence_refs": [],
        }],
    }
    return base, root / "overlay.json", payload


def test_overlay_classifies_without_mutating_or_promoting_base(tmp_path):
    base, overlay, payload = _write_overlay_fixture(tmp_path)
    original = base.read_bytes()
    overlay.write_text(json.dumps(payload), encoding="utf-8")
    registry = load_complexity_registry(tmp_path, overlay)
    assert registry.schema_version == "complexity_module_registry_overlay_v1"
    assert census_complexity_artifacts(tmp_path, registry).state == "PASS"
    assert base.read_bytes() == original
    candidate = registry.module_by_id("new-complexity")
    assert candidate.import_path is None
    assert candidate.runtime_eligible is False
    (tmp_path / candidate.path).write_text("CHANGED = True\n", encoding="utf-8")
    census = census_complexity_artifacts(tmp_path, registry)
    assert census.state == "HOLD"
    assert census.hash_drift == (candidate.path,)


@pytest.mark.parametrize("mutation", [
    "base_hash", "base_path", "runtime_state", "import", "duplicate_id", "duplicate_path",
    "addition_path", "override", "empty", "unknown_field",
])
def test_overlay_rejects_drift_activation_and_overrides(tmp_path, mutation):
    _, overlay, payload = _write_overlay_fixture(tmp_path)
    row = payload["module_additions"][0]
    if mutation == "base_hash":
        payload["base_registry_sha256"] = "0" * 64
    elif mutation == "base_path":
        payload["base_registry"] = "../outside.json"
    elif mutation == "runtime_state":
        row["state"] = "ACTIVE_CANDIDATE"
    elif mutation == "import":
        row["import_path"] = "future_modules.new_complexity"
    elif mutation == "duplicate_id":
        row["module_id"] = "construction-profile"
    elif mutation == "duplicate_path":
        row["path"] = "engine/perception/construction_complexity.py"
    elif mutation == "addition_path":
        row["path"] = "../outside.py"
    elif mutation == "empty":
        payload["module_additions"] = []
    elif mutation == "override":
        payload["module_overrides"] = []
    else:
        row["release_authority"] = True
    overlay.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError):
        load_complexity_registry(tmp_path, overlay)


def test_current_overlay_preserves_exact_frozen_registry():
    frozen = REGISTRY_PATH.read_bytes()
    assert hashlib.sha256(frozen).hexdigest() == (
        "7567f3ca00ccbf3e1b2b41f50645ed21f4d163612872b8449db6cc022818c639"
    )
    base = load_complexity_registry(PROJECT_ROOT, REGISTRY_PATH)
    current = load_complexity_registry(PROJECT_ROOT, PROJECT_ROOT / CURRENT_REGISTRY_PATH)
    assert current.modules[:len(base.modules)] == base.modules
    assert all(not module.runtime_eligible for module in current.modules[len(base.modules):])
    assert current.artifact_rules == base.artifact_rules
    assert current.dismissal_rules == base.dismissal_rules
    assert REGISTRY_PATH.read_bytes() == frozen
