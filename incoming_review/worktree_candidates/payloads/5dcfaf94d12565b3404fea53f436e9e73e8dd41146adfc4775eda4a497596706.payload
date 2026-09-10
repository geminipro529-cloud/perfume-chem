from __future__ import annotations

import hashlib
import json
from pathlib import Path

from engine.perception.complexity_registry import (
    ModuleState,
    census_complexity_artifacts,
    load_current_complexity_registry,
)

ROOT = Path(__file__).resolve().parents[1]
V6 = ROOT / "configs/complexity/complexity_module_registry_v6.json"
V7 = ROOT / "configs/complexity/complexity_module_registry_v7.json"
V8 = ROOT / "configs/complexity/complexity_module_registry_v8.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_current_registry_retains_v7_retest_failures_with_no_new_admission() -> None:
    payload = json.loads(V7.read_text(encoding="utf-8"))
    registry = load_current_complexity_registry(ROOT)

    assert payload["change_class"] == "BENCHMARK_RETEST_TOMBSTONES_NO_NEW_ADMISSION"
    assert registry.schema_version == "complexity_module_registry_v8"
    assert {module.module_id for module in registry.modules if module.runtime_eligible} == {
        "architectural-delta-engine"
    }
    assert registry.module_by_id(
        "architectural-delta-engine"
    ).state is ModuleState.ADMITTED_RUNTIME
    for module_id in ("temporal-sensory-ledger", "hedonic-preference-learner"):
        module = registry.module_by_id(module_id)
        assert module.state is ModuleState.RETIRED_BENCHMARK_UNDERPERFORMER
        assert module.import_path is None
        assert module.runtime_eligible is False
    shadow = registry.module_by_id("solforge-shadow-orchestrator")
    assert shadow.state is ModuleState.PROVENANCE_TOMBSTONE
    assert shadow.import_path is None
    assert all(value is False for value in payload["authority_flags"].values())
    census = census_complexity_artifacts(ROOT, registry)
    assert census.state == "PASS"
    assert census.hash_drift == ()


def test_v8_preserves_the_frozen_v7_predecessor_and_binds_current_bytes() -> None:
    payload = json.loads(V7.read_text(encoding="utf-8"))
    current = json.loads(V8.read_text(encoding="utf-8"))
    for item in payload["predecessor_registry_chain"]:
        assert _sha256(V7.parent / item["path"]) == item["sha256"]

    assert _sha256(V7) == current["base_registry"]["sha256"]
    runtime_paths = {item["path"] for item in current["runtime_bindings"]}
    provenance_paths = {item["path"] for item in current["provenance_bindings"]}
    assert runtime_paths.isdisjoint(provenance_paths)
    for group in ("runtime_bindings", "provenance_bindings", "benchmark_evidence"):
        for item in current[group]:
            assert _sha256(ROOT / item["path"]) == item["sha256"]


def test_v7_retest_evidence_retires_only_failed_replacements() -> None:
    payload = json.loads(V7.read_text(encoding="utf-8"))
    status_path = ROOT / payload["benchmark_evidence"][0]["path"]
    status = json.loads(status_path.read_text(encoding="utf-8"))

    assert status["decision"] == "ARCHITECTURAL_ONLY_TEMPORAL_AND_HEDONIC_RETIRED"
    assert status["module_dispositions"] == {
        "architectural-delta-engine": {
            "state": "ADMITTED_RUNTIME",
            "runtime_reachable": True,
            "basis": "PRIOR_EXACT_SCOPE_ADMISSION_RETAINED_NO_SCOPE_EXPANSION",
        },
        "temporal-sensory-ledger": {
            "state": "RETIRED_BENCHMARK_UNDERPERFORMER",
            "runtime_reachable": False,
            "basis": "FAILED_REPAIRED_SCREEN_STRICT_WIN_THRESHOLD",
        },
        "hedonic-preference-learner": {
            "state": "RETIRED_BENCHMARK_UNDERPERFORMER",
            "runtime_reachable": False,
            "basis": "FAILED_COMBINED_CONFIRMATION_WIN_AND_MEDIAN_GAIN_THRESHOLDS",
        },
    }
    assert all(value is False for value in status["authority"].values())
