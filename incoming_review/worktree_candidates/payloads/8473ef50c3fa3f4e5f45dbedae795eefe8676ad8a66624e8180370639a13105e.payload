"""Tests for the append-only Complex Perfumery V6 AM-E01 capture."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from engine.calibration.hashing import stable_file_hash, stable_json_hash

ROOT = Path(__file__).resolve().parents[1]


def test_am_e01_file_library_formula_is_exact_quarantined_candidate() -> None:
    receipt_path = (
        ROOT
        / "data"
        / "governance"
        / "complex_perfumery_am_e01_file_library_artifact_receipt_20260812.json"
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    unhashed = deepcopy(receipt)
    declared_hash = unhashed.pop("receipt_sha256")

    assert stable_json_hash(unhashed) == declared_hash
    artifact = receipt["artifact"]
    artifact_path = ROOT / artifact["locator"]
    assert artifact_path.stat().st_size == 40713 == artifact["byte_size"]
    assert (
        stable_file_hash(artifact_path)
        == artifact["sha256"]
        == ("965b02beba5faec32dcbe8d5d97aa3df8cb47fe43fc3c1cf040e4fd3b03ff5e2")
    )
    text = artifact_path.read_text(encoding="utf-8")
    assert text.startswith("# Amouage Opus V Woods Symphony")
    assert "COMPUTATIONAL RESEARCH FORMULA" in text
    assert "PHYSICAL RELEASE HOLD" in text

    provenance = receipt["provenance"]
    assert provenance["conversation_id"] == "6a7992db-96b8-83ec-aab0-6a7447b97da1"
    assert provenance["turn_id"] == "e0c8046a-b8b8-4180-8b2f-a84c1363d0f4"
    assert provenance["file_library_reference"] == "filenavlist 124:0"
    assert receipt["admission"]["state"] == (
        "EXTERNAL_FILE_BYTES_VERIFIED_QUARANTINED_NOT_ADMITTED"
    )
    assert receipt["admission"]["canonical_import_allowed"] is False
    assert receipt["evidence_summary"]["formula_candidate_only"] is True
    assert receipt["evidence_summary"]["physical_evidence_state"] == "NOT_TESTED"
    assert not any(receipt["authority"].values())

    capture = receipt["evidence_summary"]["capture_manifest"]
    capture_path = ROOT / capture["path"]
    assert capture_path.stat().st_size == capture["byte_size"]
    assert stable_file_hash(capture_path) == capture["sha256"]


def test_complex_perfumery_v6_successor_and_ledger_close_only_am_e01() -> None:
    successor_path = (
        ROOT / "output" / "quarantine" / "COMPLEX_PERFUMERY_COLLECTION_SUCCESSOR_V6_20260812.json"
    )
    plan_path = (
        ROOT
        / "output"
        / "quarantine"
        / "COMPLEX_PERFUMERY_NATIVE_FIT_AND_INSTALL_PLAN_V6_20260812.md"
    )
    ledger_path = (
        ROOT / "output" / "quarantine" / "COMPLEX_PERFUMERY_HANDOFF_SHA256SUMS_V6_20260812.txt"
    )
    successor = json.loads(successor_path.read_text(encoding="utf-8"))

    assert successor["parent"] == {
        "path": "output/quarantine/COMPLEX_PERFUMERY_COLLECTION_SUCCESSOR_V5_20260812.json",
        "bytes": 6694,
        "sha256": "99a705720fe915cafc1864902e234a3bc62b3c590eb70a327355451e5180caef",
        "relationship": "SUPERSEDES_WITHOUT_MUTATING_PARENT",
    }
    parent_path = ROOT / successor["parent"]["path"]
    assert parent_path.stat().st_size == successor["parent"]["bytes"]
    assert stable_file_hash(parent_path) == successor["parent"]["sha256"]
    assert successor["cumulative_exact_outer_candidates"] == 33
    assert successor["cumulative_exact_nonarchive_candidates"] == 1
    assert successor["new_exact_nonarchive_candidates"] == 1
    assert successor["optional_identities_closed_by_new_capture"] == 1
    assert successor["optional_identities_remaining"] == 4
    assert successor["new_exact_nonarchive_candidate"]["sha256"] == (
        "965b02beba5faec32dcbe8d5d97aa3df8cb47fe43fc3c1cf040e4fd3b03ff5e2"
    )
    assert successor["new_exact_nonarchive_candidate"]["formula_authority"] is False
    assert successor["collection_complete"] is False
    assert successor["implementation_complete"] is False
    assert successor["installation_authorized"] is False
    assert successor["installation_critical_exact_byte_blocker"]["reconstruction_allowed"] is False
    assert successor["installation_critical_exact_byte_blocker"]["substitution_allowed"] is False
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


def test_complex_perfumery_v6_acceptance_hash_and_pins_replay() -> None:
    acceptance_path = (
        ROOT
        / "data"
        / "governance"
        / "complex_perfumery_v6_am_e01_collection_acceptance_20260812.json"
    )
    acceptance = json.loads(acceptance_path.read_text(encoding="utf-8"))
    unhashed = deepcopy(acceptance)
    declared_hash = unhashed.pop("receipt_sha256")

    assert stable_json_hash(unhashed) == declared_hash
    assert acceptance["state"] == ("AM_E01_EXACT_FILE_LIBRARY_BYTES_CAPTURED_AUTHORITY_FALSE")
    assert acceptance["repository_fence"]["staged_paths"] == 0
    assert acceptance["verification"]["receipt_tests_failed"] == 0
    assert acceptance["decision"]["v5_parent_mutated"] is False
    assert acceptance["decision"]["optional_identities_remaining"] == 4
    assert acceptance["decision"]["collection_complete"] is False
    assert acceptance["decision"]["package_installation_complete"] is False
    assert acceptance["decision"]["installation_authorized"] is False
    assert not any(acceptance["authority"].values())

    for artifact in acceptance["applied_artifacts"]:
        artifact_path = ROOT / artifact["path"]
        assert artifact_path.stat().st_size == artifact["byte_size"]
        assert stable_file_hash(artifact_path) == artifact["sha256"]
