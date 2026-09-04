from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

from engine.calibration.hashing import stable_json_hash

ROOT = Path(__file__).resolve().parents[1]
CAPTURE_MANIFEST_PATH = (
    ROOT
    / "incoming_review"
    / "chatgpt"
    / "20260819T173000Z-perfume-chem-task-update-6a7765a9"
    / "source_manifest.json"
)
RECEIPT_PATH = (
    ROOT / "data" / "governance" / "perfume_chem_task_update_g15_provenance_receipt_20260819.json"
)


def _load_hashed_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    unhashed = deepcopy(payload)
    declared_hash = unhashed.pop("receipt_sha256")
    assert stable_json_hash(unhashed) == declared_hash
    return payload


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_task_update_capture_binds_all_rendered_messages_and_local_report() -> None:
    """Bind the complete three-message status chat without importing new authority."""

    manifest = _load_hashed_json(CAPTURE_MANIFEST_PATH)
    assert manifest["conversation"]["conversation_id"] == ("6a7765a9-a50c-83ec-a73e-0dce89b28c55")
    assert manifest["retrieval"]["rendered_message_count"] == 3
    assert manifest["retrieval"]["assistant_message_count"] == 1
    assert manifest["retrieval"]["user_message_count"] == 2
    assert [message["sha256"] for message in manifest["source_messages"]] == [
        "85528041425e2093562bbbfe72acb1f72f01505bd9fe3e50f5f18be2dc10ae91",
        "6f677193fe4003c85e80e2351f19c5f5240eb2cc3775510138d6a8ba125dc1af",
        "9e5f599629bdc5c2c606a71eeeb15124adcc18911307b7f73e8c9725a6928d74",
    ]
    report = ROOT / manifest["local_report"]["path"]
    assert report.stat().st_size == manifest["local_report"]["byte_size"] == 14_102
    assert (
        _sha256(report)
        == manifest["local_report"]["sha256"]
        == ("1104cd55352ad8f49a843905d9b284da7afb10abd0917cef75daff0a1c14eae6")
    )
    assert not any(manifest["authority"].values())


def test_g15_receipt_separates_historical_hashes_from_current_verified_behavior() -> None:
    """Keep the old report as provenance while binding current files and tests separately."""

    receipt = _load_hashed_json(RECEIPT_PATH)
    assert receipt["decision"] == "G15_IMPLEMENTATION_PRESENT_CURRENT_BEHAVIOR_VERIFIED"
    assert receipt["admission"]["duplicate_implementation_allowed"] is False
    assert receipt["admission"]["existing_code_mutated_by_intake"] is False
    assert receipt["verification"]["focused_test_result"] == "15_PASSED"
    assert receipt["verification"]["focused_test_path"] == "tests/test_pre_mix_guard.py"
    assert not any(receipt["authority"].values())

    historical = {row["path"]: row["sha256"] for row in receipt["historical_report_bindings"]}
    current = {row["path"]: row["sha256"] for row in receipt["current_live_bindings"]}
    assert set(historical) == set(current)
    assert all(historical[path] != current[path] for path in current)
    for path, expected_hash in current.items():
        assert _sha256(ROOT / path) == expected_hash

    boundary = receipt["scientific_boundary"]
    assert boundary["modeled_oav_use"] == "ANOMALY_SCREENING_ONLY"
    assert boundary["linear_perceived_contribution_inference_allowed"] is False
    assert boundary["standalone_perfume_verdict_allowed"] is False
    assert boundary["measured_headspace_claim_allowed"] is False
    assert boundary["literature_identifiers"] == [
        "10.1093/chemse/bjg075",
        "10.1038/sj.emboj.7600032",
        "10.1016/j.cub.2020.04.086",
        "10.1016/j.mcn.2020.103469",
    ]
