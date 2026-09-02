"""Replay the V20 block diagnosis without lifting scientific or release holds."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from engine.calibration.hashing import stable_json_hash

ROOT = Path(__file__).resolve().parents[1]
DIAGNOSIS = ROOT / "data" / "governance" / "complex_perfumery_v20_block_diagnosis_20260817.json"


def _load() -> dict:
    return json.loads(DIAGNOSIS.read_text(encoding="utf-8"))


def _semantic_hash(payload: dict) -> str:
    body = deepcopy(payload)
    body.pop("semantic_receipt_sha256")
    return stable_json_hash(body)


def test_deepluna_oversize_cause_and_accounting_are_preserved() -> None:
    payload = _load()
    chat = payload["deepluna_chat"]
    assert chat["required_read_cap_bytes"] == 15360
    assert [row["selected_utf8_bytes"] for row in chat["failed_contracts"]] == [
        170292,
        191523,
    ]
    assert all(row["provider_transmissions"] == 0 for row in chat["failed_contracts"])

    replacement = chat["request_level_fix"]
    assert replacement["compact_selected_utf8_bytes"] < chat["required_read_cap_bytes"]
    assert replacement["provider_transmissions"] == 2
    assert replacement["actual_nano_usd"] == 1192248
    assert replacement["accepted_as_authority"] is False
    assert replacement["retry_allowed"] is False
    assert len(replacement["evidence_errors"]) == 2
    assert chat["runtime_hardening"]["active_pinned_runtime_modified"] is False
    assert chat["runtime_hardening"]["candidate_runtime_source_modified"] is True
    assert set(chat["postflight"].values()) >= {False, 0, "READY"}


def test_external_and_cloud_blocks_remain_fail_closed() -> None:
    payload = _load()
    cloud = payload["cloud_attachment_census"]
    assert cloud["chat_state"] == "ACTIVE"
    assert cloud["agent_reply_present"] is False
    assert cloud["duplicate_message_sent"] is False

    holds = payload["residual_exact_byte_holds"]
    assert len(holds) == 4
    assert {row["byte_size"] for row in holds} == {539050, 1228587, 540402, 65724}
    assert all(len(row["sha256"]) == 64 for row in holds)
    assert all("SUPPLY_EXACT_ORIGINAL_BYTES" in row["safe_fix"] for row in holds)


def test_module_and_authority_boundaries_are_unchanged() -> None:
    payload = _load()
    modules = payload["complex_perfumery_module_holds"]
    assert modules["direct_package_imports"] == 0
    assert modules["previous_clean_room_native_modules"] == 6
    assert modules["source_rights_established"] is False
    assert len(modules["candidate_seams"]) == 4
    assert set(payload["authority"].values()) == {False}
    assert payload["semantic_receipt_sha256"] == _semantic_hash(payload)
