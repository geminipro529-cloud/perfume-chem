"""Tests for the append-only Complex Perfumery V8 PCV3 package capture."""

from __future__ import annotations

import json
from copy import deepcopy
from hashlib import sha256
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

from engine.calibration.hashing import stable_file_hash, stable_json_hash
from engine.ingestion.archive_quarantine import scan_archive_graph_quarantine
from engine.ingestion.package_receipts import (
    validate_external_package_receipt,
    verify_external_package_bytes,
)

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_SHA256 = "db638ab82c7e1a798297a9f4376014b9f51965511ae1d65132e57b4d12c9c9eb"
RECEIPT_SEMANTIC_SHA256 = "13f7edf5f1ae240d0a8eba2ee8f652f71436e7e5346d97a6334216535b051c72"


def _receipt() -> dict[str, object]:
    path = (
        ROOT
        / "data"
        / "governance"
        / "complex_perfumery_pcv3_chat2_experimental_data_model_package_receipt_20260815.json"
    )
    return json.loads(path.read_text(encoding="utf-8"))


def test_pcv3_receipt_and_exact_package_verify_fail_closed() -> None:
    receipt = _receipt()
    assert validate_external_package_receipt(receipt)["receipt_sha256"] == (RECEIPT_SEMANTIC_SHA256)
    package_path = ROOT / receipt["package"]["locator"]
    assert package_path.stat().st_size == 32196
    assert stable_file_hash(package_path) == PACKAGE_SHA256

    result = verify_external_package_bytes(receipt, package_path=package_path)
    assert result.integrity_verified is True
    assert result.status == "VERIFIED_QUARANTINED"
    assert result.archive_entry_count == result.archive_file_count == 12
    assert result.verified_embedded_records == (
        "SHA256SUMS.json",
        "PCV3_EXPERIMENT_DATA_WORKER_MANIFEST.json",
    )
    assert result.errors == ()
    assert result.promotion_allowed is False
    assert not any(receipt["authority"].values())


def test_pcv3_embedded_ledger_templates_and_native_graph_are_exact() -> None:
    receipt = _receipt()
    package_path = ROOT / receipt["package"]["locator"]
    with ZipFile(package_path) as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        assert archive.testzip() is None
        assert len(names) == len({name.casefold() for name in names}) == 12
        assert all(
            not PurePosixPath(name).is_absolute()
            and ".." not in PurePosixPath(name).parts
            and "\\" not in name
            for name in names
        )

        ledger = json.loads(archive.read("SHA256SUMS.json"))
        assert len(ledger) == 11
        assert set(ledger) == set(names) - {"SHA256SUMS.json"}
        for member, record in ledger.items():
            payload = archive.read(member)
            assert len(payload) == record["bytes"]
            assert sha256(payload).hexdigest() == record["sha256"]

        validation = json.loads(archive.read("VALIDATION_REPORT.json"))
        assert validation["final_state"] == "PASS"
        assert validation["csv_files"]["SENSORY_OBSERVATION_TEMPLATE.csv"]["data_rows"] == 0
        assert validation["csv_files"]["PHYSICAL_BATCH_LEDGER_TEMPLATE.csv"]["data_rows"] == 0
        assert validation["csv_files"]["CODED_SAMPLE_REGISTER_TEMPLATE.csv"]["data_rows"] == 0
        assert validation["csv_files"]["EXISTING_SCHEMA_MIGRATION_MAP.csv"]["data_rows"] == 30

        worker = json.loads(archive.read("PCV3_EXPERIMENT_DATA_WORKER_MANIFEST.json"))
        assert worker["worker_state"] == "COMPLETE_WITH_HOLDS"
        assert (
            "no database, physical test, or engine execution is claimed"
            in worker["assumptions"][-1]
        )

    graph = scan_archive_graph_quarantine(package_path)
    assert graph.status == "CLEAR_FOR_RECEIPT_REVIEW"
    assert graph.root_archive_sha256 == PACKAGE_SHA256
    assert len(graph.nodes) == 1
    assert len(graph.edges) == 0
    assert graph.resource_usage.max_depth == 0
    assert graph.all_nodes_terminal is True
    assert graph.findings == ()
    assert graph.promotion_allowed is False


def test_v8_successor_closes_only_pcv3_and_preserves_holds() -> None:
    successor_path = (
        ROOT / "output" / "quarantine" / "COMPLEX_PERFUMERY_COLLECTION_SUCCESSOR_V8_20260815.json"
    )
    successor = json.loads(successor_path.read_text(encoding="utf-8"))
    assert successor["parent"] == {
        "path": "output/quarantine/COMPLEX_PERFUMERY_COLLECTION_SUCCESSOR_V7_20260812.json",
        "bytes": 5446,
        "sha256": "9d37e67ee8fc62398d33d9d52799d797d6ff8e08266b4394788c3f4e9e38004e",
        "relationship": "SUPERSEDES_WITHOUT_MUTATING_PARENT",
    }
    parent_path = ROOT / successor["parent"]["path"]
    assert parent_path.stat().st_size == successor["parent"]["bytes"]
    assert stable_file_hash(parent_path) == successor["parent"]["sha256"]
    assert successor["cumulative_exact_outer_candidates"] == 34
    assert successor["new_exact_outer_candidates"] == 1
    assert successor["optional_identities_closed_by_new_capture"] == 1
    assert successor["optional_identities_remaining"] == 2
    assert successor["new_exact_outer_candidate"]["sha256"] == PACKAGE_SHA256
    assert successor["new_exact_outer_candidate"]["promotion_allowed"] is False
    assert successor["native_fit"]["migration_required"] is False
    assert successor["native_fit"]["migration_head_remains"] == "20260810_0016"
    assert successor["native_fit"]["new_truth_store_allowed"] is False
    assert successor["collection_complete"] is False
    assert successor["implementation_complete"] is False
    assert successor["installation_authorized"] is False
    assert not any(successor["authority"].values())


def test_v8_ledger_and_acceptance_replay_exactly() -> None:
    ledger_path = (
        ROOT / "output" / "quarantine" / "COMPLEX_PERFUMERY_HANDOFF_SHA256SUMS_V8_20260815.txt"
    )
    entries = []
    for line in ledger_path.read_text(encoding="utf-8").splitlines():
        digest, byte_size, relative_path = line.split("  ", 2)
        entries.append((digest, int(byte_size), relative_path))
    assert len(entries) == 9
    assert len({relative_path for _, _, relative_path in entries}) == 9
    for digest, byte_size, relative_path in entries:
        artifact_path = ROOT / relative_path
        assert artifact_path.stat().st_size == byte_size
        assert stable_file_hash(artifact_path) == digest

    acceptance_path = (
        ROOT
        / "data"
        / "governance"
        / "complex_perfumery_v8_pcv3_collection_acceptance_20260815.json"
    )
    acceptance = json.loads(acceptance_path.read_text(encoding="utf-8"))
    unhashed = deepcopy(acceptance)
    declared_hash = unhashed.pop("receipt_sha256")
    assert stable_json_hash(unhashed) == declared_hash
    assert acceptance["state"] == "PCV3_EXACT_PACKAGE_CAPTURED_AUTHORITY_FALSE"
    assert acceptance["repository_fence"]["staged_paths"] == 0
    assert acceptance["verification"]["receipt_tests_failed"] == 0
    assert acceptance["decision"]["v7_parent_mutated"] is False
    assert acceptance["decision"]["optional_identities_remaining"] == 2
    assert acceptance["decision"]["collection_complete"] is False
    assert acceptance["decision"]["installation_authorized"] is False
    assert not any(acceptance["authority"].values())
    for artifact in acceptance["applied_artifacts"]:
        artifact_path = ROOT / artifact["path"]
        assert artifact_path.stat().st_size == artifact["byte_size"]
        assert stable_file_hash(artifact_path) == artifact["sha256"]
