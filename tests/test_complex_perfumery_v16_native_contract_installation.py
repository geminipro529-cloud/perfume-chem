from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tests.historical_snapshots import assert_historical_artifact

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = (
    ROOT
    / "data"
    / "governance"
    / "complex_perfumery_v16_native_contract_installation_20260817.json"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_historical_native_contract_receipt_retains_exact_original_source_pins() -> None:
    payload = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert payload["state"] == (
        "NATIVE_CLEAN_ROOM_DIAGNOSTICS_INSTALLED_PACKAGE_CONTENT_HELD"
    )
    assert len(payload["native_modules"]) == 6
    for item in payload["native_modules"]:
        path = ROOT / item["path"]
        assert_historical_artifact(path, item["sha256"], item["byte_size"])


def test_oav_and_authority_boundaries_remain_fail_closed() -> None:
    payload = json.loads(RECEIPT.read_text(encoding="utf-8"))
    oav = payload["oav_gate"]
    assert oav["formula_hash_recomputed_from_exact_name_doses_and_dilutions"] is True
    assert oav["natural_composite_oav_coverage_required"] is True
    assert oav["pre_mix_gate_required"] is True
    assert oav["strict_empirical_oav_authority"] is False
    assert all(value is False for value in payload["authority"].values())
    assert payload["source_package"]["package_code_installed"] is False
    assert payload["source_package"]["package_registries_imported"] is False


def test_provider_accounting_records_zero_paid_execution() -> None:
    payload = json.loads(RECEIPT.read_text(encoding="utf-8"))
    chat = payload["deepluna_chat"]
    assert chat["job_state"] == "TERMINAL_CONTRACT_ERROR"
    assert chat["accepted_evidence"] is False
    assert chat["retry_submitted"] is False
    assert chat["provider_runs"] == 0
    assert chat["provider_api_calls"] == 0
    assert chat["provider_tokens"] == 0
    assert chat["open_reserved_nano_usd"] == 0
    assert chat["unknown_reservations"] == 0
    assert chat["fast_used"] is False
    assert chat["luna_used"] is False
    assert chat["fallback_used"] is False
