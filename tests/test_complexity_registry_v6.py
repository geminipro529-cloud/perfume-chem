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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_v6_is_an_isolation_repair_with_no_new_admission() -> None:
    payload = json.loads(V6.read_text(encoding="utf-8"))
    registry = load_current_complexity_registry(ROOT)

    assert payload["change_class"] == "RUNTIME_ISOLATION_REPAIR_NO_NEW_ADMISSION"
    assert registry.schema_version == "complexity_module_registry_v6"
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


def test_v6_preserves_every_predecessor_and_binds_current_bytes() -> None:
    payload = json.loads(V6.read_text(encoding="utf-8"))
    for item in payload["predecessor_registry_chain"]:
        assert _sha256(V6.parent / item["path"]) == item["sha256"]

    runtime_paths = {item["path"] for item in payload["runtime_bindings"]}
    provenance_paths = {item["path"] for item in payload["provenance_bindings"]}
    assert runtime_paths.isdisjoint(provenance_paths)
    for group in ("runtime_bindings", "provenance_bindings", "screen_evidence"):
        for item in payload[group]:
            assert _sha256(ROOT / item["path"]) == item["sha256"]


def test_v6_failed_screen_evidence_is_all_stop() -> None:
    payload = json.loads(V6.read_text(encoding="utf-8"))
    decisions_path = next(
        ROOT / item["path"]
        for item in payload["screen_evidence"]
        if item["path"].endswith("screen_decisions.json")
    )
    decisions = json.loads(decisions_path.read_text(encoding="utf-8"))

    assert {row["module_id"] for row in decisions["decisions"]} == {
        "temporal_oav_error_sentinel",
        "temporal_sensory_ledger",
        "hedonic_preference_learner",
    }
    assert {row["state"] for row in decisions["decisions"]} == {"STOP"}
