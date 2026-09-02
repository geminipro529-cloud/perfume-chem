"""Tests for the authority-false Complex Perfumery V12 package capture."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from collections import defaultdict
from copy import deepcopy
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

from engine.calibration.hashing import stable_file_hash, stable_json_hash
from engine.ingestion.archive_quarantine import (
    scan_archive_graph_quarantine,
    scan_archive_quarantine,
)
from engine.ingestion.package_receipts import (
    validate_external_package_receipt,
    verify_external_package_bytes,
)

ROOT = Path(__file__).resolve().parents[1]
CAPTURE = (
    ROOT
    / "incoming_review"
    / "chatgpt"
    / "20260816T122500+0700-nine-perfume-blockage-clearance-6a7992db-n1282620c"
)
PACKAGE = CAPTURE / "Nine_Perfume_Blockage_Clearance_and_Bench_Activation_2026-08-16_v1.zip"
MANIFEST = CAPTURE / "capture_manifest.json"
RECEIPT = (
    ROOT
    / "data"
    / "governance"
    / "complex_perfumery_nine_perfume_blockage_clearance_package_receipt_20260816.json"
)
SUCCESSOR = (
    ROOT / "output" / "quarantine" / "COMPLEX_PERFUMERY_COLLECTION_SUCCESSOR_V12_20260816.json"
)
PLAN = (
    ROOT / "output" / "quarantine" / "COMPLEX_PERFUMERY_NATIVE_FIT_AND_INSTALL_PLAN_V12_20260816.md"
)
LEDGER = ROOT / "output" / "quarantine" / "COMPLEX_PERFUMERY_HANDOFF_SHA256SUMS_V12_20260816.txt"
ACCEPTANCE = (
    ROOT
    / "data"
    / "governance"
    / "complex_perfumery_v12_nine_perfume_blockage_clearance_acceptance_20260816.json"
)
V10_CAPTURE = (
    ROOT
    / "incoming_review"
    / "chatgpt"
    / "20260815T233019+0700-post-v9-six-package-recovery-6a7992db-n417f58e1"
)
ROOT_NAME = "Nine_Perfume_Blockage_Clearance_and_Bench_Activation_2026-08-16_v1/"


def _csv_rows(archive: ZipFile, leaf: str) -> list[dict[str, str]]:
    raw = archive.read(ROOT_NAME + leaf).decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(raw)))


def test_v12_exact_bytes_manifest_and_receipt_replay() -> None:
    assert PACKAGE.stat().st_size == 619801
    assert stable_file_hash(PACKAGE) == (
        "1282620cfdb6b48a4f091c12da73414790f1b00461dba5fd4ed63cbacde0cb8f"
    )
    assert MANIFEST.stat().st_size == 8226
    assert stable_file_hash(MANIFEST) == (
        "c8f35854d91fee6bfe130779ec67267c720f272cef363f5375e319a2f4b62357"
    )
    capture = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert capture["source_hash_closure"]["exact_hash_matches"] == 8
    assert capture["source_hash_closure"]["rights_or_admission_inferred"] is False
    assert not any(capture["authority"].values())

    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert RECEIPT.stat().st_size == 7313
    assert stable_file_hash(RECEIPT) == (
        "f576554c5f3f3f8c85176755d78306a4a392ee7404a2aa3f3c3a8bc63466e474"
    )
    assert validate_external_package_receipt(receipt)["receipt_sha256"] == (
        "a2839c068f20f0cfb0cb8d80b2bab587e5d6decb24e7b62c25a4c77f858cdb92"
    )
    verification = verify_external_package_bytes(receipt, package_path=PACKAGE)
    assert verification.integrity_verified is True
    assert verification.status == "VERIFIED_QUARANTINED"
    assert verification.archive_entry_count == verification.archive_file_count == 23
    assert verification.errors == ()
    assert verification.promotion_allowed is False
    assert not any(receipt["authority"].values())


def test_v12_zip_ledger_workbook_and_declared_source_hashes_are_exact() -> None:
    with ZipFile(PACKAGE) as archive:
        names = [info.filename for info in archive.infolist()]
        assert archive.testzip() is None
        assert len(names) == len({name.casefold() for name in names}) == 23
        assert all(
            not PurePosixPath(name).is_absolute()
            and ".." not in PurePosixPath(name).parts
            and "\\" not in name
            for name in names
        )
        lines = archive.read(ROOT_NAME + "SHA256SUMS.txt").decode("utf-8-sig").splitlines()
        assert len(lines) == 22
        for line in lines:
            digest, relative = line.split(None, 1)
            relative = relative.strip().lstrip("*")
            assert hashlib.sha256(archive.read(ROOT_NAME + relative)).hexdigest() == digest
        workbook = archive.read(
            ROOT_NAME + "Nine_Perfume_Blockage_Clearance_and_Bench_Activation_v1.xlsx"
        )
        assert len(workbook) == 141277
        assert hashlib.sha256(workbook).hexdigest() == (
            "8e0548549cba430041f562e268804c4333fabcee51178de33f1ae3e977dab1f4"
        )

    capture = json.loads(MANIFEST.read_text(encoding="utf-8"))
    expected = {record["sha256"] for record in capture["source_hash_closure"]["records"]}
    found: set[str] = set()
    for name in (
        "Nine_Perfume_Module_Isolate_Completion_Suite_2026-08-15_v1.zip",
        "Nine_Perfume_Complexity_Phase2_Execution_2026-08-15_v1.zip",
    ):
        with ZipFile(V10_CAPTURE / name) as archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                digest = hashlib.sha256(archive.read(info)).hexdigest()
                if digest in expected:
                    found.add(digest)
    assert found == expected


def test_v12_protocol_geometry_is_not_active_dose_or_execution_truth() -> None:
    with ZipFile(PACKAGE) as archive:
        components = _csv_rows(archive, "EXACT_5ML_ARM_COMPONENTS.csv")
        summaries = _csv_rows(archive, "EXACT_5ML_ARM_SUMMARY.csv")
        factors = _csv_rows(archive, "FACTOR_MODULE_FORMULAS.csv")
        masters = _csv_rows(archive, "PARENT_MASTER_5ML_CARDS.csv")
        preparations = _csv_rows(archive, "PREPARATION_RECEIPT_TEMPLATES.csv")
        verifications = _csv_rows(archive, "VERIFICATION_RECEIPT_TEMPLATES.csv")

    totals: dict[tuple[str, str], float] = defaultdict(float)
    for row in components:
        totals[(row["program_id"], row["condition_id"])] += float(row["component_ul"])
    assert len(components) == 775
    assert len(totals) == len(summaries) == 110
    assert set(totals.values()) == {5000.0}
    assert {row["authority"] for row in summaries} == {"RESEARCH PILOT DESIGN ONLY"}

    assert len(factors) == 77
    assert sum(not row["active_fraction"] for row in factors) == 2
    assert sum(row["product_basis"] == "True" for row in factors) == 2
    assert sum(row["inventory_state"] != "HAVE" for row in factors) == 12
    assert all(row["execution_state"].startswith("PREPARATION DESIGN ONLY") for row in factors)

    assert len(masters) == 174
    assert sum(not row["active_fraction"] for row in masters) == 6
    assert sum(row["product_basis"] == "True" for row in masters) == 6
    assert sum(row["inventory_state"] != "HAVE" for row in masters) == 24
    assert {row["physical_state"] for row in masters} == {
        "NOT PREPARED / EXACTSTOCKREF + SAFETY + OPERATOR RECEIPT REQUIRED"
    }

    assert len(preparations) == 4
    assert all(row["state"] == "DESIGN ONLY / NOT PREPARED" for row in preparations)
    assert all(row["actual_component_amounts"] == "TO_BE_RECORDED" for row in preparations)
    assert len(verifications) == 9
    assert {row["closure_state"] for row in verifications} == {"OPEN"}


def test_v12_native_graph_and_three_parent_receipt_edges_remain_fail_closed() -> None:
    single = scan_archive_quarantine(PACKAGE)
    assert single.status == "QUARANTINE_HOLD"
    assert [finding.code for finding in single.findings] == [
        "NESTED_ARCHIVE_REQUIRES_CHILD_RECEIPT",
        "PARTIAL_MEMBER_SCAN",
        "PARTIAL_MEMBER_SCAN",
    ]
    graph = scan_archive_graph_quarantine(PACKAGE)
    assert graph.status == "GRAPH_COMPLETE_QUARANTINED"
    assert len(graph.nodes) == 2
    assert len(graph.edges) == 1
    assert graph.resource_usage.max_depth == 1
    assert graph.all_nodes_terminal is True
    assert graph.findings == ()
    assert graph.promotion_allowed is False

    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    parents = receipt["parents"]
    assert len(parents) == 3
    assert len({parent["sha256"] for parent in parents}) == 3
    assert {parent["relation"] for parent in parents} == {
        "CHILD_DECLARES_ARCHITECTURE_PARENT_EXACT_HASH",
        "CHILD_DECLARES_COMPLETION_SUITE_PARENT_EXACT_HASH",
        "CHILD_DECLARES_PHASE2_EXECUTION_PARENT_EXACT_HASH",
    }
    assert {parent["authority_state"] for parent in parents} == {"POINTER_ONLY"}


def test_v12_successor_preserves_native_priority_and_all_holds() -> None:
    successor = json.loads(SUCCESSOR.read_text(encoding="utf-8"))
    assert SUCCESSOR.stat().st_size == 9243
    assert stable_file_hash(SUCCESSOR) == (
        "7e67167b180f611774b6a63372c91207fc8bdef1a7d19de993c7029eeccf2bd2"
    )
    assert PLAN.stat().st_size == 4857
    assert stable_file_hash(PLAN) == (
        "660432e77c63447437371f77ce2090b24927c3aaf12fdf8112e10cfdd09db575"
    )
    for parent in successor["parents"]:
        path = ROOT / parent["path"]
        assert path.stat().st_size == parent["bytes"]
        assert stable_file_hash(path) == parent["sha256"]
    priority = successor["native_fit"]["native_experiment_priority"]
    queue = ROOT / priority["controlling_queue_path"]
    assert queue.stat().st_size == priority["controlling_queue_bytes"] == 24578
    assert stable_file_hash(queue) == priority["controlling_queue_sha256"]
    assert priority["first_direct_gates"] == ["CLR-001", "CLR-002"]
    assert priority["physical_execution_authorized"] is False
    assert successor["cumulative_exact_outer_candidates"] == 42
    assert successor["optional_identities_remaining"] == 1
    assert successor["collection_complete"] is False
    assert successor["implementation_complete"] is False
    assert successor["installation_authorized"] is False
    assert not any(successor["authority"].values())


def test_v12_ledger_and_acceptance_replay_exactly() -> None:
    entries = []
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        digest, byte_size, relative_path = line.split("  ", 2)
        entries.append((digest, int(byte_size), relative_path))
    assert len(entries) == 15
    assert len({relative_path for _, _, relative_path in entries}) == 15
    for digest, byte_size, relative_path in entries:
        artifact = ROOT / relative_path
        assert artifact.stat().st_size == byte_size
        assert stable_file_hash(artifact) == digest

    acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
    unhashed = deepcopy(acceptance)
    declared = unhashed.pop("receipt_sha256")
    assert stable_json_hash(unhashed) == declared
    assert acceptance["state"] == (
        "V12_EXACT_BLOCKAGE_CLEARANCE_PACKAGE_CAPTURED_PROTOCOL_GEOMETRY_ONLY"
    )
    assert acceptance["repository_fence"]["staged_paths"] == 0
    assert acceptance["decision"]["v10_v11_parents_mutated"] is False
    assert acceptance["decision"]["collection_complete"] is False
    assert acceptance["decision"]["package_installation_complete"] is False
    assert acceptance["decision"]["installation_authorized"] is False
    assert not any(acceptance["authority"].values())
    for artifact in acceptance["applied_artifacts"]:
        path = ROOT / artifact["path"]
        assert path.stat().st_size == artifact["byte_size"]
        assert stable_file_hash(path) == artifact["sha256"]
