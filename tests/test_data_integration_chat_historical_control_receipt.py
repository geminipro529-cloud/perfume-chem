from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

from engine.calibration.hashing import stable_json_hash

ROOT = Path(__file__).resolve().parents[1]
CAPTURE_DIR = ROOT / "incoming_review" / "chatgpt" / "20260819T160000Z-data-integration-6a77b1b5"
MANIFEST_PATH = CAPTURE_DIR / "source_manifest.json"
RECEIPT_PATH = (
    ROOT / "data" / "governance" / "data_integration_chat_historical_control_receipt_20260819.json"
)


def _load(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    unhashed = deepcopy(payload)
    declared_hash = unhashed.pop("receipt_sha256")
    assert stable_json_hash(unhashed) == declared_hash
    return payload


def test_complete_chat_census_and_exact_historical_attachments_are_bound() -> None:
    manifest = _load(MANIFEST_PATH)
    assert manifest["conversation"]["conversation_id"] == ("6a77b1b5-fabc-83ec-896b-9b7c5c5a2ebf")

    messages = manifest["source_messages"]
    assert len(messages) == 63
    assert len({row["message_id"] for row in messages}) == 63
    assert sum(row["role"] == "user" for row in messages) == 45
    assert sum(row["role"] == "assistant" for row in messages) == 18
    assert {row["message_id"]: row for row in messages}["317b1fea-e361-5f00-b2ef-a8abf4d7cef5"][
        "sha256"
    ] == "65ae783700bc93851d33ba78001ab3f389f18d3c94891dad0163890a57ddb1f0"

    attachments = manifest["recovered_attachments"]
    assert len(attachments) == 4
    for row in attachments:
        path = CAPTURE_DIR / row["file_name"]
        payload = path.read_bytes()
        assert len(payload) == row["byte_size"]
        assert hashlib.sha256(payload).hexdigest() == row["sha256"]


def test_historical_control_state_cannot_replace_current_project_state() -> None:
    receipt = _load(RECEIPT_PATH)
    assert receipt["historical_control_diff"] == {
        "source_claimed_provisional_destination_count": 75,
        "current_local_registry_visible_count": 38,
        "historical_count_may_replace_current_registry": False,
        "historical_bridge_or_github_status_may_replace_current_state": False,
    }
    assert receipt["ma_2021_diff"]["state"] == "ALREADY_IMPLEMENTED_SOURCE_INTERNAL_BASELINE"
    assert receipt["ma_2021_diff"]["benchmark_decision"] == (
        "DATA_AMBER_MA2021_SOURCE_INTERNAL_BASELINES_QUANTIFIED_NONLINEAR_ESCALATION_NOT_AUTHORIZED"
    )
    assert receipt["ma_2021_diff"]["new_runtime_implementation_required"] is False

    assert receipt["task_output_diff"]["classification"] == (
        "HISTORICAL_OR_SUCCESSOR_PRESENT_NOT_RUNTIME_INPUT"
    )
    assert receipt["task_output_diff"]["exact_unrecovered_task_output_count"] == 16
    assert receipt["task_output_diff"]["absence_inferred"] is False
    assert receipt["task_output_diff"]["c0_successor_present"] is True


def test_disposition_is_preservation_only_and_all_authorities_are_false() -> None:
    receipt = _load(RECEIPT_PATH)
    assert receipt["disposition"]["classification"] == (
        "DATA_INTEGRATION_CONTROL_ARTIFACTS_RECOVERED_MA_AND_C0_SUCCESSORS_"
        "ALREADY_LOCAL_HISTORICAL_TASK_OUTPUTS_NONPROMOTING"
    )
    assert receipt["disposition"]["native_runtime_change_required"] is False
    assert receipt["disposition"]["formula_or_inventory_mutated"] is False
    assert receipt["disposition"]["control_artifacts_preserved"] is True
    assert not any(receipt["authority"].values())
