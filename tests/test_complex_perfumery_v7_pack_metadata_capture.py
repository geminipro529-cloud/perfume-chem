"""Tests for the append-only Complex Perfumery V7 PACK_METADATA capture."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from engine.calibration.hashing import stable_file_hash, stable_json_hash

ROOT = Path(__file__).resolve().parents[1]
PACK_SHA256 = "d051505ea9144716fb860c5ff74e92b2bed2b33e419c830460cc60278b94f869"


def test_pack_metadata_file_library_artifact_is_exact_and_authority_false() -> None:
    receipt_path = (
        ROOT
        / "data"
        / "governance"
        / "complex_perfumery_pack_metadata_file_library_artifact_receipt_20260812.json"
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    unhashed = deepcopy(receipt)
    declared_hash = unhashed.pop("receipt_sha256")
    assert stable_json_hash(unhashed) == declared_hash

    artifact = receipt["artifact"]
    artifact_path = ROOT / artifact["locator"]
    assert artifact_path.stat().st_size == 14116 == artifact["byte_size"]
    assert stable_file_hash(artifact_path) == artifact["sha256"] == PACK_SHA256
    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert payload["pack_id"] == "Six_Perfume_Latest_Integrated_Recipe_Pack_Aug2026"
    assert set(payload["targets"]) == {"AM-E01", "C03", "H07", "PR-E01", "PR-E07", "S06"}
    assert payload["global_boundaries"]["formula_mutation_authorized_by_oav"] is False
    assert payload["global_boundaries"]["strict_empirical_oav"] == "NOT TESTED"
    assert payload["global_boundaries"]["safety_release"] == "NOT TESTED"

    provenance = receipt["provenance"]
    assert provenance["conversation_id"] == "6a7992db-96b8-83ec-aab0-6a7447b97da1"
    assert provenance["turn_id"] == "e0c8046a-b8b8-4180-8b2f-a84c1363d0f4"
    assert provenance["file_library_reference"] == "filenavlist 123:0"
    assert receipt["admission"]["canonical_import_allowed"] is False
    assert receipt["evidence_summary"]["metadata_only"] is True
    assert not any(receipt["authority"].values())


def test_complex_perfumery_v7_successor_and_ledger_close_only_pack_metadata() -> None:
    successor_path = (
        ROOT / "output" / "quarantine" / "COMPLEX_PERFUMERY_COLLECTION_SUCCESSOR_V7_20260812.json"
    )
    plan_path = (
        ROOT
        / "output"
        / "quarantine"
        / "COMPLEX_PERFUMERY_NATIVE_FIT_AND_INSTALL_PLAN_V7_20260812.md"
    )
    ledger_path = (
        ROOT / "output" / "quarantine" / "COMPLEX_PERFUMERY_HANDOFF_SHA256SUMS_V7_20260812.txt"
    )
    successor = json.loads(successor_path.read_text(encoding="utf-8"))

    assert successor["parent"] == {
        "path": "output/quarantine/COMPLEX_PERFUMERY_COLLECTION_SUCCESSOR_V6_20260812.json",
        "bytes": 5520,
        "sha256": "5709250a6623f991d3a3de26d9001b015737dff1fd83d6d5f5aef2d3c9f8b80b",
        "relationship": "SUPERSEDES_WITHOUT_MUTATING_PARENT",
    }
    parent_path = ROOT / successor["parent"]["path"]
    assert parent_path.stat().st_size == successor["parent"]["bytes"]
    assert stable_file_hash(parent_path) == successor["parent"]["sha256"]
    assert successor["cumulative_exact_outer_candidates"] == 33
    assert successor["cumulative_exact_nonarchive_candidates"] == 2
    assert successor["new_exact_nonarchive_candidates"] == 1
    assert successor["optional_identities_closed_by_new_capture"] == 1
    assert successor["optional_identities_remaining"] == 3
    assert successor["new_exact_nonarchive_candidate"]["sha256"] == PACK_SHA256
    assert successor["new_exact_nonarchive_candidate"]["metadata_authority"] is False
    assert successor["collection_complete"] is False
    assert successor["implementation_complete"] is False
    assert successor["installation_authorized"] is False
    assert not any(successor["authority"].values())
    assert plan_path.is_file()

    ledger_entries = []
    for line in ledger_path.read_text(encoding="utf-8").splitlines():
        digest, byte_size, relative_path = line.split("  ", 2)
        ledger_entries.append((digest, int(byte_size), relative_path))
    assert len(ledger_entries) == 9
    assert len({relative_path for _, _, relative_path in ledger_entries}) == 9
    for digest, byte_size, relative_path in ledger_entries:
        artifact_path = ROOT / relative_path
        assert artifact_path.stat().st_size == byte_size
        assert stable_file_hash(artifact_path) == digest


def test_complex_perfumery_v7_acceptance_hash_and_pins_replay() -> None:
    acceptance_path = (
        ROOT
        / "data"
        / "governance"
        / "complex_perfumery_v7_pack_metadata_collection_acceptance_20260812.json"
    )
    acceptance = json.loads(acceptance_path.read_text(encoding="utf-8"))
    unhashed = deepcopy(acceptance)
    declared_hash = unhashed.pop("receipt_sha256")
    assert stable_json_hash(unhashed) == declared_hash
    assert acceptance["state"] == "PACK_METADATA_EXACT_FILE_LIBRARY_BYTES_CAPTURED_AUTHORITY_FALSE"
    assert acceptance["repository_fence"]["staged_paths"] == 0
    assert acceptance["verification"]["receipt_tests_failed"] == 0
    assert acceptance["decision"]["v6_parent_mutated"] is False
    assert acceptance["decision"]["optional_identities_remaining"] == 3
    assert acceptance["decision"]["collection_complete"] is False
    assert acceptance["decision"]["installation_authorized"] is False
    assert not any(acceptance["authority"].values())
    for artifact in acceptance["applied_artifacts"]:
        artifact_path = ROOT / artifact["path"]
        assert artifact_path.stat().st_size == artifact["byte_size"]
        assert stable_file_hash(artifact_path) == artifact["sha256"]
