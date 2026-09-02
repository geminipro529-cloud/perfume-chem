"""Tests for the authority-false V17 nine-perfume computational-formula capture."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from collections import Counter
from copy import deepcopy
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

from engine.calibration.hashing import stable_file_hash, stable_json_hash
from engine.ingestion.archive_quarantine import scan_archive_graph_quarantine
from engine.ingestion.package_receipts import (
    validate_external_package_receipt,
    verify_external_package_bytes,
)

ROOT = Path(__file__).resolve().parents[1]
CAPTURE = (
    ROOT
    / "incoming_review"
    / "chatgpt"
    / "20260816T160448+0700-v17-nine-finished-hedonic-6a7992db-nf1e0f2aa"
)
PACKAGE = CAPTURE / "Nine_Finished_Hedonic_High_Complexity_Perfumes_2026-08-16_v1.zip"
MANIFEST = CAPTURE / "capture_manifest.json"
RECEIPT = (
    ROOT
    / "data"
    / "governance"
    / "complex_perfumery_nine_finished_hedonic_high_complexity_package_receipt_20260816.json"
)
DELTA = (
    ROOT
    / "data"
    / "governance"
    / "complex_perfumery_v17_post_v16_nine_finished_hedonic_delta_20260816.json"
)
REPORT = ROOT / "output" / "quarantine" / "COMPLEX_PERFUMERY_COLLECTION_DELTA_V17_20260816.md"

PACKAGE_ROOT = "Nine_Finished_Hedonic_High_Complexity_Perfumes_2026-08-16_v1"
PACKAGE_SHA256 = "f1e0f2aae2143fe2638c151032f686ee7b36579280445e86e1878c79b54f240b"
WORKBOOK_SHA256 = "afed9ecf7849ec7e017280fdf4b676ce2b212b86e4dfd7f5433cc802521b2b68"
EMBEDDED_MANIFEST_SHA256 = "6ce2ecfceb11b6d7757af3310c493c36212a7c55ad119dbf30b8ad3e459133fb"
EMBEDDED_LEDGER_SHA256 = "4294a1b272c84f8246c0f1b4f79ffbdf767350ed34c67367e0205d2d8707caa3"
PARENT_HASHES = {
    "09318ed20c9c29c6d0f171a4333f74fde4d9c3f213ac64eca53997d4e5c20f3b",
    "1282620cfdb6b48a4f091c12da73414790f1b00461dba5fd4ed63cbacde0cb8f",
    "e36287aca26f34354b3244f07618cb4c12750dfb85db5584dca39d5130025331",
}
RESIDUAL_HOLDS = {
    "8dd04ea6c69e5e3bd72b03e0ae15cb66ad66e9ac5581cf97666249e869c5a998",
    "e9e325bea9117dbe2a97ff67e77d57705a54244591278fac7a34915a7f0ae523",
    "8224f8a1609deb22b43651da825b9bf653a92143f00ee1d5d592130d162f97db",
    "582ae9902e47807f085a61b7add113c9239a2860445e8171fcf569b3ad6d28c5",
}


def _safe_archive(archive: ZipFile) -> None:
    names = archive.namelist()
    assert archive.testzip() is None
    assert len(names) == len({name.casefold() for name in names})
    assert all(
        not PurePosixPath(name).is_absolute()
        and ".." not in PurePosixPath(name).parts
        and "\\" not in name
        for name in names
    )


def _csv_rows(archive: ZipFile, name: str) -> list[dict[str, str]]:
    payload = archive.read(f"{PACKAGE_ROOT}/{name}").decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(payload)))


def test_v17_capture_adds_one_exact_outer_without_authority() -> None:
    assert PACKAGE.stat().st_size == 815495
    assert stable_file_hash(PACKAGE) == PACKAGE_SHA256
    capture = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert capture["project"]["parent_v16_delta_sha256"] == (
        "cdcba4638280580a76b774cd9b4cc4558517bb1b43d2aa31fc1f2a9714f12eab"
    )
    assert capture["retrieval"]["source_and_capture_sha256_match"] is True
    assert capture["retrieval"]["regeneration"] is False
    assert capture["retrieval"]["substitution"] is False
    assert capture["retrieval"]["reconstruction"] is False
    assert capture["collection_delta"]["prior_exact_outer_candidates"] == 50
    assert capture["collection_delta"]["cumulative_exact_outer_candidates"] == 51
    assert capture["collection_delta"]["all_project_packages_collected"] is False
    assert not any(capture["authority"].values())


def test_v17_embedded_ledgers_replay_exactly() -> None:
    with ZipFile(PACKAGE) as archive:
        _safe_archive(archive)
        assert len(archive.infolist()) == 84
        assert sum(not item.is_dir() for item in archive.infolist()) == 84

        manifest_path = f"{PACKAGE_ROOT}/MANIFEST.json"
        ledger_path = f"{PACKAGE_ROOT}/SHA256SUMS.txt"
        manifest_payload = archive.read(manifest_path)
        ledger_payload = archive.read(ledger_path)
        assert hashlib.sha256(manifest_payload).hexdigest() == EMBEDDED_MANIFEST_SHA256
        assert hashlib.sha256(ledger_payload).hexdigest() == EMBEDDED_LEDGER_SHA256

        manifest = json.loads(manifest_payload)
        assert manifest["member_count_excluding_manifest_and_ledger"] == 82
        assert len(manifest["members"]) == 82
        manifest_names = set()
        for record in manifest["members"]:
            member = f"{PACKAGE_ROOT}/{record['path']}"
            payload = archive.read(member)
            manifest_names.add(member)
            assert len(payload) == record["bytes"]
            assert hashlib.sha256(payload).hexdigest() == record["sha256"]
        assert manifest_names == {
            item.filename
            for item in archive.infolist()
            if not item.is_dir() and item.filename not in {manifest_path, ledger_path}
        }

        ledger_records = []
        for line in ledger_payload.decode("utf-8").splitlines():
            digest, name = line.split("  ", 1)
            ledger_records.append((digest, name))
        assert len(ledger_records) == 83
        ledger_names = set()
        for digest, name in ledger_records:
            member = f"{PACKAGE_ROOT}/{name}"
            payload = archive.read(member)
            ledger_names.add(member)
            assert hashlib.sha256(payload).hexdigest() == digest
        assert ledger_names == {
            item.filename
            for item in archive.infolist()
            if not item.is_dir() and item.filename != ledger_path
        }


def test_v17_source_claims_remain_computational_and_not_execution_ready() -> None:
    with ZipFile(PACKAGE) as archive:
        formula_rows = _csv_rows(archive, "FORMULA_REGISTER.csv")
        gate_rows = _csv_rows(archive, "GATE_REGISTER.csv")
        complexity_rows = _csv_rows(archive, "COMPLEXITY_AUDIT.csv")
        build_rows = _csv_rows(archive, "CURRENT_BUILD_ALL_ROWS.csv")
        interaction_rows = _csv_rows(archive, "INTERACTION_MAP_ALL.csv")
        anti_collapse_rows = _csv_rows(archive, "ANTI_COLLAPSE_MATRIX.csv")
        mci_rows = _csv_rows(archive, "MISSING_CHEMICAL_IMPACT.csv")

        assert len(formula_rows) == 9
        assert {row["empirical_state"] for row in formula_rows} == {"NOT TESTED / PHYSICAL HOLD"}
        assert len(gate_rows) == 135
        assert Counter(row["state"] for row in gate_rows) == {
            "PASS": 72,
            "HOLD": 27,
            "CONDITIONAL": 18,
            "NOT_RUN": 18,
        }
        assert len(complexity_rows) == 9
        assert {row["final_state"] for row in complexity_rows} == {
            "CONDITIONAL — ART-DIRECTED FORMULA COMPLETE / PHYSICAL HOLD"
        }
        assert sum(int(row["open_stock_rows"]) for row in complexity_rows) == 51
        assert len(build_rows) == 663
        assert sum(not row["active_fraction"] for row in build_rows) == 17
        assert sum(row["product_basis"] == "True" for row in build_rows) == 17
        assert len(interaction_rows) == 81
        assert Counter(row["evidence_class"] for row in interaction_rows) == {
            "ATLAS-GUIDED STRUCTURED HYPOTHESIS": 80,
            "OFFICIAL-SOURCE CONFLICT / PHYSICAL ADJUDICATION REQUIRED": 1,
        }
        assert len(anti_collapse_rows) == 36
        assert {row["state"] for row in anti_collapse_rows} == {"PASS"}
        assert len(mci_rows) == 23

        source_receipt = json.loads(archive.read(f"{PACKAGE_ROOT}/RECEIPT.json"))
        assert source_receipt["current_build_rows"] == 663
        assert source_receipt["target_rows"] == 740
        assert len(source_receipt["authority_false"]) == 18
        assert source_receipt["workbook"]["sha256"] == WORKBOOK_SHA256


def test_v17_native_graph_and_strict_receipt_remain_quarantined() -> None:
    graph = scan_archive_graph_quarantine(PACKAGE)
    assert graph.status == "GRAPH_COMPLETE_QUARANTINED"
    assert len(graph.nodes) == 2
    assert len(graph.edges) == 1
    assert graph.resource_usage.max_depth == 1
    assert graph.all_nodes_terminal is True
    assert graph.findings == ()
    assert graph.promotion_allowed is False

    root = next(node for node in graph.nodes if node.archive_sha256 == PACKAGE_SHA256)
    child = next(node for node in graph.nodes if node.archive_sha256 == WORKBOOK_SHA256)
    assert root.scan.status == "QUARANTINE_HOLD"
    assert [finding.code for finding in root.scan.findings] == [
        "NESTED_ARCHIVE_REQUIRES_CHILD_RECEIPT",
        "PARTIAL_MEMBER_SCAN",
        "PARTIAL_MEMBER_SCAN",
        "PARTIAL_MEMBER_SCAN",
    ]
    assert child.scan.status == "CLEAR_FOR_RECEIPT_REVIEW"
    assert child.scan.findings == ()

    receipt = validate_external_package_receipt(json.loads(RECEIPT.read_text(encoding="utf-8")))
    verification = verify_external_package_bytes(receipt, package_path=PACKAGE)
    assert verification.status == "VERIFIED_QUARANTINED"
    assert verification.integrity_verified is True
    assert verification.archive_entry_count == 84
    assert verification.archive_file_count == 84
    assert verification.errors == ()
    assert verification.promotion_allowed is False
    assert {parent["sha256"] for parent in receipt["parents"]} == PARENT_HASHES
    assert not any(receipt["authority"].values())


def test_v17_delta_is_sealed_pinned_and_fail_closed() -> None:
    delta = json.loads(DELTA.read_text(encoding="utf-8"))
    unhashed = deepcopy(delta)
    declared = unhashed.pop("semantic_receipt_sha256")
    assert stable_json_hash(unhashed) == declared
    assert delta["collection"]["prior_exact_outer_candidates"] == 50
    assert delta["collection"]["new_exact_outer_candidates"] == 1
    assert delta["collection"]["cumulative_exact_outer_candidates"] == 51
    assert delta["collection"]["all_project_packages_collected"] is False
    assert delta["decision"]["collection_complete"] is False
    assert delta["decision"]["implementation_complete"] is False
    assert delta["decision"]["package_installation_complete"] is False
    assert delta["decision"]["installation_authorized"] is False
    assert delta["decision"]["formula_or_build_mutated"] is False
    assert delta["decision"]["inventory_or_stock_mutated"] is False
    assert delta["decision"]["physical_or_sensory_execution_performed"] is False
    assert {item["sha256"] for item in delta["residual_exact_byte_holds"]} == RESIDUAL_HOLDS
    assert not any(delta["authority"].values())
    assert REPORT.is_file()
    for artifact in delta["applied_artifacts"]:
        path = ROOT / artifact["path"]
        assert path.stat().st_size == artifact["byte_size"]
        assert stable_file_hash(path) == artifact["sha256"]
