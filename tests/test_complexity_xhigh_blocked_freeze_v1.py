from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECEIPT_PATH = (
    ROOT / "data/governance/complexity_xhigh_blocked_freeze_20260823_v1.json"
)


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def test_blocked_freeze_records_exact_execution_boundary() -> None:
    receipt = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))

    assert receipt["schema_version"] == "complexity_xhigh_blocked_freeze_v1"
    assert receipt["benchmark_state"] == "FROZEN_BLOCKED_PENDING_CHAT"
    assert receipt["execution_census"] == {
        "planned_requests": 60,
        "completed_responses": 33,
        "succeeded_responses": 33,
        "pending_requests": 27,
        "response_hash_errors": 0,
        "visible_dom_receipts": 20,
        "prior_copy_receipts_visually_reverified": 13,
    }
    assert len(receipt["pending_request_ids"]) == 27
    assert len(set(receipt["pending_request_ids"])) == 27


def test_completed_screens_claim_no_demonstrated_outperformance_only() -> None:
    receipt = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
    completed = receipt["completed_module_screens"]

    assert set(completed) == {
        "construction_profile",
        "complexity_expansion",
        "musk_design_restraint",
        "citrus_selection",
        "model_admission",
    }
    for result in completed.values():
        assert result["screen_pairs_completed"] == 3
        assert result["material_treatment_wins"] == 0
        assert result["decision"] == "NO_DEMONSTRATED_OUTPERFORMANCE"
        assert result["confirmation_phase_started"] is False


def test_unfinished_modules_remain_inconclusive_and_nonpromoting() -> None:
    receipt = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))

    assert receipt["partial_module_screens"]["model_lifecycle"]["decision"] == (
        "INCONCLUSIVE_PARTIAL_SCREEN"
    )
    assert receipt["untested_module_screens"] == [
        "within_sniff",
        "temporal_observations",
        "order_balance",
        "panel_contract",
    ]
    assert receipt["runtime_disposition"]["modules_promoted"] == []
    assert receipt["runtime_disposition"]["runtime_changes_authorized"] is False
    assert all(value is False for value in receipt["authority"].values())


def test_blocked_freeze_semantic_hash_is_exact() -> None:
    receipt = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
    semantic_hash = receipt.pop("semantic_receipt_sha256")

    assert semantic_hash == hashlib.sha256(canonical_bytes(receipt)).hexdigest()
