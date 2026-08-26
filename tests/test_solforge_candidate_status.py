from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATUS = ROOT / "data/governance/solforge_candidate_status_20260825.json"
SCREEN_ROOT = ROOT / "data/benchmarks/solforge/replacement_screen_r1"
JUDGE_ROOT = SCREEN_ROOT / "judge_round1"

EXPECTED_SOURCE_HASHES = {
    "engine/sensory/ledger.py": "f1d9078b7907a75b4aca0242da7228508952fb0b4cae17cd93977961f0b5da3c",
    "engine/perception/complexity_replacement_benchmark.py": "0723489dcfdd1edb33683e875b87477072c2f169b278d8ddd858102fcb9d88e5",
    "engine/perception/complexity_module_retest.py": "a0a300bd81797f0c77db12f91735ad4a7dbf5e032505fa0b9d210203ecab6cb5",
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
        "completed_outputs": 27,
        "status_path": "data/benchmarks/solforge/replacement_screen_r1/status.json",
        "status_sha256": "ead8f30fc9e057313cfc2f0a946372312c89cabb8111bf751fc28d9cb8273671",
        "admission_decision": "WITHHELD",
        "old_frozen_requests_resumed": False,
    }
    assert payload["source_hashes"] == EXPECTED_SOURCE_HASHES
    assert all(value is False for value in payload["authority"].values())

    for relative, expected in EXPECTED_SOURCE_HASHES.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected


def test_complete_screen_freezes_all_exact_outputs_pending_score() -> None:
    manifest = json.loads((SCREEN_ROOT / "manifest.json").read_text(encoding="utf-8"))
    status = json.loads((SCREEN_ROOT / "status.json").read_text(encoding="utf-8"))
    raw_paths = sorted((SCREEN_ROOT / "raw").glob("*.json"))

    assert status["manifest_sha256"] == manifest["manifest_sha256"]
    assert status["state"] == "COMPLETE_PENDING_SCORE"
    assert status["completed_output_count"] == len(raw_paths) == 27
    assert status["required_output_count"] == manifest["request_count"] == 27
    assert status["confirmation_authorized"] is False
    assert status["runtime_reachable"] is False
    assert status["missing_request_ids"] == []
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


def test_blind_judge_manifest_is_hash_bound_and_hides_arm_identity() -> None:
    manifest = json.loads((JUDGE_ROOT / "manifest.json").read_text(encoding="utf-8"))
    unhashed = dict(manifest)
    observed_manifest_hash = unhashed.pop("manifest_sha256")
    canonical = json.dumps(
        unhashed,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()

    assert manifest["state"] == "COMPLETE_PENDING_JUDGE_OUTPUTS"
    assert manifest["request_count"] == len(manifest["requests"]) == 9
    assert hashlib.sha256(canonical).hexdigest() == observed_manifest_hash
    assert all(value is False for value in manifest["authority"].values())

    raw_by_id = {
        payload["request_id"]: payload
        for path in (SCREEN_ROOT / "raw").glob("*.json")
        for payload in [json.loads(path.read_text(encoding="utf-8"))]
    }
    observed_cases = set()
    for request in manifest["requests"]:
        observed_cases.add(request["case_id"])
        assert hashlib.sha256(request["dispatch_text"].encode()).hexdigest() == (
            request["dispatch_sha256"]
        )
        assert len(request["candidates"]) == 3
        assert {row["arm"] for row in request["candidates"]} == {
            "CONTROL",
            "TREATMENT",
            "PLACEBO",
        }
        assert '"arm":' not in request["dispatch_text"]
        for candidate in request["candidates"]:
            assert candidate["source_request_id"] not in request["dispatch_text"]
            assert (
                raw_by_id[candidate["source_request_id"]]["output_sha256"]
                == candidate["output_sha256"]
            )

    assert len(observed_cases) == 9
