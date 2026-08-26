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
    ROOT
    / "data/governance/complexity_decision_card_candidate_freeze_20260823_v2.json"
)
REGISTRY_PATH = ROOT / "configs/complexity/complexity_module_registry_v1.json"


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def test_v2_freeze_is_preserved_as_the_pre_catalog_historical_freeze() -> None:
    receipt = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
    successor_path = (
        ROOT
        / "data/governance/complexity_decision_card_candidate_freeze_20260823_v3.json"
    )
    successor = json.loads(successor_path.read_text(encoding="utf-8"))

    assert receipt["schema_version"] == "complexity_decision_card_candidate_freeze_v2"
    assert receipt["online_benchmark_state"] == "NOT_STARTED"
    assert receipt["predecessor_candidate_freeze"]["path"].endswith(
        "complexity_decision_card_candidate_freeze_20260822.json"
    )
    assert successor["predecessor_candidate_freeze"]["path"] == str(
        RECEIPT_PATH.relative_to(ROOT)
    ).replace("\\", "/")
    assert successor["predecessor_candidate_freeze"]["sha256"] == hashlib.sha256(
        RECEIPT_PATH.read_bytes()
    ).hexdigest()
    assert any(
        item["path"].endswith("complexity_module_retest_cases_v2.json")
        for item in receipt["candidate_artifacts"]
    )


def test_v2_freeze_records_exact_material_authority_without_granting_use() -> None:
    receipt = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))

    assert receipt["material_bindings"] == {
        "Neroli EO 10% in DPG": {
            "state": "OWNED_10_PERCENT_DPG_ONLY",
            "module_use": "SUPPORT_ONLY_FLORAL_TRANSITION_BRIDGE",
        },
        "Ambrettolide 10% in DPG": {
            "state": "PLANNED_ACQUISITION_DESIGN_AVAILABLE",
            "physical_state": "PROCUREMENT_PENDING",
        },
        "Romandolide": {
            "state": "OWNED_NEAT_AS_SUPPLIED",
            "physical_state": "EXACT_LABEL_STOCK_REQUIRED",
        },
        "Habanolide": {
            "state": "OWNED_NEAT_AS_SUPPLIED",
            "physical_state": "EXACT_LABEL_STOCK_REQUIRED",
        },
        "Ethylene Brassylate": {
            "state": "NOT_IN_V5_CURRENT_INVENTORY",
            "module_use": "MISSING_HIGH_VALUE_ARCHITECTURAL_EXPANSION_HYPOTHESIS",
        },
    }
    assert all(value is False for value in receipt["authority"].values())


def test_v2_freeze_keeps_candidates_nonruntime_until_xhigh_passes() -> None:
    receipt = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
    registry = load_complexity_registry(ROOT, REGISTRY_PATH)

    for module_id in receipt["repaired_module_ids"]:
        assert (
            registry.module_by_id(module_id).state
            is ModuleState.RETIRED_BENCHMARK_UNDERPERFORMER
        )
    citrus = registry.module_by_id("citrus-architecture-selector")
    assert citrus.state is ModuleState.FUTURE_CANDIDATE_NOT_VALIDATED
    assert citrus.runtime_eligible is False


def test_v2_freeze_semantic_hash_is_exact() -> None:
    receipt = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
    semantic_hash = receipt.pop("semantic_receipt_sha256")

    assert semantic_hash == hashlib.sha256(canonical_bytes(receipt)).hexdigest()
