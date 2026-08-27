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
V8 = ROOT / "configs/complexity/complexity_module_registry_v8.json"
RECEIPT = ROOT / "data/governance/topology_xhigh_screen_20260827_v1.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_current_registry_tombstones_failed_topology_candidates() -> None:
    registry = load_current_complexity_registry(ROOT)

    assert registry.schema_version == "complexity_module_registry_v8"
    assert {module.module_id for module in registry.modules if module.runtime_eligible} == {
        "architectural-delta-engine"
    }
    for module_id in (
        "universal-perceptual-topology-core",
        "perfumery-art-composition-topology-v1",
        "wood-depth-model-v2",
    ):
        module = registry.module_by_id(module_id)
        assert module.state is ModuleState.PROVENANCE_TOMBSTONE
        assert module.import_path is None
        assert module.runtime_eligible is False


def test_v8_binds_corrected_screen_receipt_and_source_bytes() -> None:
    payload = json.loads(V8.read_text(encoding="utf-8"))
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))

    assert _sha256(V8.parent / payload["base_registry"]["path"]) == payload[
        "base_registry"
    ]["sha256"]
    for item in payload["benchmark_evidence"]:
        assert _sha256(ROOT / item["path"]) == item["sha256"]
    for item in payload["module_overrides"]:
        assert _sha256(ROOT / item["path"]) == item["sha256"]

    rebinding = payload["provenance_rebindings"][0]
    canonical = (ROOT / rebinding["path"]).read_bytes()
    assert b"\r\n" not in canonical
    assert hashlib.sha256(canonical).hexdigest() == rebinding["sha256"]
    attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert "/engine/hedonic_model.py text eol=lf" in attributes

    registry = load_current_complexity_registry(ROOT)
    assert registry.module_by_id("hedonic-model-future").sha256 == rebinding["sha256"]

    assert receipt["decision"] == "TOPOLOGY_CANDIDATES_RETAINED_AS_PROVENANCE_TOMBSTONES"
    assert receipt["confirmation"]["state"] == "NOT_RUN_SCREEN_GATE_FAILED"
    assert receipt["capture_defect_tombstone"]["state"] == "INVALIDATED_PREMATURE_CAPTURE"
    assert receipt["raw_conversations_committed"] is False
    assert all(value is False for value in receipt["authority"].values())
    assert all(value is False for value in payload["authority_flags"].values())


def test_v8_screen_receipt_enforces_declared_strict_win_gate() -> None:
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    dispositions = receipt["module_dispositions"]

    assert dispositions["universal-perceptual-topology-core"] == {
        "screen_state": "FAILED",
        "wins_vs_plain": 2,
        "wins_vs_placebo": 1,
        "wins_vs_both": 1,
        "treatment_critical_errors": 0,
        "median_gain_vs_plain": 8,
        "median_gain_vs_placebo": 0,
        "runtime_state": "PROVENANCE_TOMBSTONE",
        "runtime_reachable": False,
    }
    assert dispositions["perfumery-art-composition-topology-v1"][
        "wins_vs_both"
    ] == 0
    assert dispositions["wood-depth-model-v2"]["wins_vs_both"] == 0
    assert dispositions["wood-depth-model-v2"]["treatment_critical_errors"] == 3
    assert all(
        item["runtime_reachable"] is False for item in dispositions.values()
    )

    registry = load_current_complexity_registry(ROOT)
    census = census_complexity_artifacts(ROOT, registry)
    assert census.state == "PASS"
    assert census.hash_drift == ()
