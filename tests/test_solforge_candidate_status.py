from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATUS = ROOT / "data/governance/solforge_candidate_status_20260825.json"
SCREEN_ROOT = ROOT / "data/benchmarks/solforge/replacement_screen_r1"

EXPECTED_SOURCE_HASHES = {
    "engine/sensory/ledger.py": "f1d9078b7907a75b4aca0242da7228508952fb0b4cae17cd93977961f0b5da3c",
    "engine/perception/complexity_replacement_benchmark.py": "4d72341aa04eac4b8c8677fe0a01dc51fd2f293880ca68da9b6d27dcb6c8763f",
    "configs/complexity/complexity_module_registry_v2.json": "d17a3747432f7a002cb6b42aa25cb67b8b215cfe7f2b9a3adf92498c87504500",
    "tests/fixtures/complexity_replacement_retest_cases_v3.json": "16fb9fa5694ea545b36fff0460631becc4e6bef4b2e5f3bd8b1f8dd9babdaed3",
    "configs/complexity/complexity_replacement_benchmark_rubric_v1.json": "2a91fe926f7316d1f5ec2d07b41e0a4829932a343fc978d5de3da88c39905bc9",
    "docs/SOLFORGE_ABCD_PROGRAM.md": "557f385be2663d2a1547e182394cf3572443c0639775c50b182328fc09f010de",
}


def test_solforge_status_preserves_old_run_and_withholds_new_admission() -> None:
    payload = json.loads(STATUS.read_text(encoding="utf-8"))

    assert payload["program_id"] == "SOLFORGE-ABCD-20260825"
    assert payload["runtime_state"] == "FUTURE_CANDIDATE_NOT_VALIDATED"
    assert payload["runtime_reachable"] is False
    assert payload["prior_run_tombstone"] == {
        "status_path": "data/governance/complexity_replacement_candidate_status_20260824.json",
        "status_sha256": "66ac0c4dd83485de2e00a06fe508f6f53f43ab8e8ee5e062e5668ca879d51aee",
        "run_id": "RPL-XHIGH-20260824-v3-formal-01",
        "completed_outputs": 3,
        "state": "SUPERSEDED_PARTIAL_UNSCORED",
    }
    assert payload["next_benchmark"] == {
        "schema": "complexity_replacement_benchmark_manifest_v5_blinded",
        "phase": "SCREEN",
        "planned_outputs": 27,
        "completed_outputs": 8,
        "status_path": "data/benchmarks/solforge/replacement_screen_r1/status.json",
        "status_sha256": "d6c92058edb5097f00e631cbc3feae99f852fdc540057e4f3e9df65086d8216a",
        "admission_decision": "WITHHELD",
        "old_frozen_requests_resumed": False,
    }
    assert payload["source_hashes"] == EXPECTED_SOURCE_HASHES
    assert all(value is False for value in payload["authority"].values())

    for relative, expected in EXPECTED_SOURCE_HASHES.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected


def test_partial_screen_freezes_only_exact_completed_outputs() -> None:
    manifest = json.loads((SCREEN_ROOT / "manifest.json").read_text(encoding="utf-8"))
    status = json.loads((SCREEN_ROOT / "status.json").read_text(encoding="utf-8"))
    raw_paths = sorted((SCREEN_ROOT / "raw").glob("*.json"))

    assert status["manifest_sha256"] == manifest["manifest_sha256"]
    assert status["state"] == "INCOMPLETE_NOT_SCORED"
    assert status["completed_output_count"] == len(raw_paths) == 8
    assert status["required_output_count"] == manifest["request_count"] == 27
    assert status["confirmation_authorized"] is False
    assert status["runtime_reachable"] is False
    assert all(value is False for value in status["authority"].values())

    request_by_id = {row["request_id"]: row for row in manifest["requests"]}
    observed_ids = set()
    for path in raw_paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        request = request_by_id[payload["request_id"]]
        observed_ids.add(payload["request_id"])
        assert payload["dispatch_sha256"] == request["dispatch_sha256"]
        assert payload["case_id"] == request["case_id"]
        assert payload["module_id"] == request["module_id"]
        assert payload["arm"] == request["arm"]
        assert payload["model_identity"] == "GPT-5.6 Sol"
        assert payload["reasoning_setting"] == "xhigh"
        assert hashlib.sha256(payload["output_text"].encode()).hexdigest() == (
            payload["output_sha256"]
        )
        assert all(value is False for value in payload["authority"].values())

    assert observed_ids == set(status["completed_request_ids"])
    assert observed_ids.isdisjoint(status["missing_request_ids"])
    assert observed_ids | set(status["missing_request_ids"]) == set(request_by_id)
