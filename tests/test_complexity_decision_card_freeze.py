from __future__ import annotations

import hashlib
import json
from pathlib import Path

from engine.perception.complexity_registry import (
    ModuleState,
    load_complexity_registry,
)

ROOT = Path(__file__).resolve().parents[1]
RECEIPT_PATH = (
    ROOT / "data/governance/complexity_decision_card_candidate_freeze_20260822.json"
)
REGISTRY_PATH = ROOT / "configs/complexity/complexity_module_registry_v1.json"


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def test_candidate_freeze_matches_exact_bytes_and_grants_no_runtime_authority() -> None:
    receipt = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))

    assert receipt["schema_version"] == "complexity_decision_card_candidate_freeze_v1"
    drifted_paths = []
    for artifact in receipt["candidate_artifacts"]:
        path = ROOT / artifact["path"]
        assert path.is_file()
        assert len(artifact["sha256"]) == 64
        if hashlib.sha256(path.read_bytes()).hexdigest() != artifact["sha256"]:
            drifted_paths.append(artifact["path"])
    assert drifted_paths == [
        "engine/perception/complexity_decision_cards.py",
        "engine/perception/citrus_selection.py",
        "engine/perception/complexity_module_retest.py",
    ]
    successor = json.loads(
        (
            ROOT
            / "data/governance/complexity_decision_card_candidate_freeze_20260823_v2.json"
        ).read_text(encoding="utf-8")
    )
    assert successor["predecessor_candidate_freeze"]["sha256"] == hashlib.sha256(
        RECEIPT_PATH.read_bytes()
    ).hexdigest()
    assert successor["predecessor_candidate_freeze"]["benchmark_requests_submitted"] == 0
    assert all(
        "DHC_CITRUS_SCORING" not in item["path"]
        for item in receipt["candidate_artifacts"]
    )
    assert receipt["authority"] == {
        "formula": False,
        "inventory": False,
        "physical_execution": False,
        "sensory": False,
        "safety": False,
        "installation": False,
        "publication": False,
        "release": False,
    }
    assert receipt["online_benchmark_state"] == "NOT_STARTED"


def test_candidate_freeze_keeps_repaired_modules_retired_and_citrus_future() -> None:
    receipt = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
    registry = load_complexity_registry(ROOT, REGISTRY_PATH)

    for module_id in receipt["repaired_module_ids"]:
        module = registry.module_by_id(module_id)
        assert module.state is ModuleState.RETIRED_BENCHMARK_UNDERPERFORMER
        assert module.runtime_eligible is False
    citrus = registry.module_by_id("citrus-architecture-selector")
    assert citrus.state is ModuleState.FUTURE_CANDIDATE_NOT_VALIDATED
    assert citrus.runtime_eligible is False
    assert citrus.import_path is None


def test_candidate_freeze_semantic_hash_is_exact() -> None:
    receipt = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
    semantic_hash = receipt.pop("semantic_receipt_sha256")

    assert semantic_hash == hashlib.sha256(canonical_bytes(receipt)).hexdigest()
