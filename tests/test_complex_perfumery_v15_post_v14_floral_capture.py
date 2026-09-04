"""Tests for the append-only authority-false V15 floral package capture."""

from __future__ import annotations

import hashlib
import json
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
    / "20260816T152630+0700-v15-floral-complexity-expansion-6a8054e9-n0eb388b6"
)
PACKAGE = CAPTURE / "Floral_Complexity_Expansion_10_Diverse_Formula_Screens_2026-08-16_v1.zip"
MANIFEST = CAPTURE / "capture_manifest.json"
RECEIPT = (
    ROOT
    / "data"
    / "governance"
    / "complex_perfumery_floral_complexity_expansion_package_receipt_20260816.json"
)
DELTA = (
    ROOT
    / "data"
    / "governance"
    / "complex_perfumery_v15_post_v14_floral_expansion_delta_20260816.json"
)
REPORT = ROOT / "output" / "quarantine" / "COMPLEX_PERFUMERY_COLLECTION_DELTA_V15_20260816.md"

PACKAGE_SHA256 = "0eb388b6ceb420997210e7c6096d4f0e6951e06fc8bd06ab1c45ad0df369780b"
WORKBOOK_SHA256 = "04907dd395430a6381d444952caf08d993f1f97a2babca26646f3bc1e4ae81a1"
PENDING_COMPLEXITY_SHA256 = "f4be1041bb8e2e8b5665962e580aa740996bd2f77b61299cca1d3cdf55014a5d"


def _assert_safe_archive(archive: ZipFile) -> None:
    names = archive.namelist()
    assert archive.testzip() is None
    assert len(names) == len({name.casefold() for name in names})
    assert all(
        not PurePosixPath(name).is_absolute()
        and ".." not in PurePosixPath(name).parts
        and "\\" not in name
        for name in names
    )


def test_v15_exact_capture_and_source_lineage() -> None:
    assert PACKAGE.stat().st_size == 351409
    assert stable_file_hash(PACKAGE) == PACKAGE_SHA256
    capture = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert capture["project"]["parent_v14_delta_sha256"] == (
        "986916e0cbf542a8a01d6507bbb11a8e092e9b26f5cafbbd90aee7de61bfab40"
    )
    assert capture["retrieval"]["source_and_capture_sha256_match"] is True
    assert capture["retrieval"]["regeneration"] is False
    assert capture["retrieval"]["substitution"] is False
    assert capture["collection_delta"]["cumulative_exact_outer_candidates"] == 49
    assert not any(capture["authority"].values())


def test_v15_archive_manifest_and_formula_boundary_are_exact() -> None:
    with ZipFile(PACKAGE) as archive:
        _assert_safe_archive(archive)
        assert len(archive.infolist()) == 21
        assert sum(not item.is_dir() for item in archive.infolist()) == 20

        embedded_manifest = json.loads(archive.read("MANIFEST.json"))
        assert len(embedded_manifest["files"]) == 19
        manifest_names = set()
        for record in embedded_manifest["files"]:
            payload = archive.read(record["path"])
            manifest_names.add(record["path"])
            assert len(payload) == record["bytes"]
            assert hashlib.sha256(payload).hexdigest() == record["sha256"]
        assert manifest_names == {
            item.filename
            for item in archive.infolist()
            if not item.is_dir() and item.filename != "MANIFEST.json"
        }

        assert (
            hashlib.sha256(
                archive.read("Floral_Complexity_Expansion_10_Formula_Master_v1.xlsx")
            ).hexdigest()
            == WORKBOOK_SHA256
        )
        assert embedded_manifest["formulaCount"] == 10
        assert embedded_manifest["totalFormulaRows"] == 860
        assert embedded_manifest["inventoryAuthorityAvailable"] is False
        assert embedded_manifest["authority"]["computationalDesign"] is True
        assert all(
            value is False
            for key, value in embedded_manifest["authority"].items()
            if key != "computationalDesign"
        )


def test_v15_native_graph_and_strict_receipt_remain_nonpromoting() -> None:
    graph = scan_archive_graph_quarantine(PACKAGE)
    assert graph.status == "GRAPH_COMPLETE_QUARANTINED"
    assert len(graph.nodes) == 2
    assert len(graph.edges) == 1
    assert graph.all_nodes_terminal is True
    assert graph.findings == ()
    assert graph.promotion_allowed is False

    nodes = {node.archive_sha256: node for node in graph.nodes}
    root = nodes[PACKAGE_SHA256]
    child = nodes[WORKBOOK_SHA256]
    assert root.scan.status == "QUARANTINE_HOLD"
    assert {finding.code for finding in root.scan.findings} == {
        "NESTED_ARCHIVE_REQUIRES_CHILD_RECEIPT",
        "PARTIAL_MEMBER_SCAN",
    }
    assert child.scan.status == "CLEAR_FOR_RECEIPT_REVIEW"
    assert child.scan.findings == ()
    assert child.scan.promotion_allowed is False

    receipt = validate_external_package_receipt(json.loads(RECEIPT.read_text(encoding="utf-8")))
    verification = verify_external_package_bytes(receipt, package_path=PACKAGE)
    assert verification.status == "VERIFIED_QUARANTINED"
    assert verification.integrity_verified is True
    assert verification.archive_entry_count == 21
    assert verification.archive_file_count == 20
    assert verification.errors == ()
    assert verification.promotion_allowed is False
    assert not any(receipt["authority"].values())


def test_v15_pending_source_card_and_exact_byte_holds_are_retained() -> None:
    capture = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert {item["sha256"] for item in capture["pending_source_cards"]} == {
        PENDING_COMPLEXITY_SHA256
    }
    assert capture["collection_delta"]["all_project_packages_collected"] is False

    delta = json.loads(DELTA.read_text(encoding="utf-8"))
    assert {item["sha256"] for item in delta["pending_source_cards"]} == {PENDING_COMPLEXITY_SHA256}
    assert {item["sha256"] for item in delta["residual_exact_byte_holds"]} == {
        "8dd04ea6c69e5e3bd72b03e0ae15cb66ad66e9ac5581cf97666249e869c5a998",
        "e9e325bea9117dbe2a97ff67e77d57705a54244591278fac7a34915a7f0ae523",
        "8224f8a1609deb22b43651da825b9bf653a92143f00ee1d5d592130d162f97db",
        "582ae9902e47807f085a61b7add113c9239a2860445e8171fcf569b3ad6d28c5",
    }


def test_v15_delta_is_semantically_sealed_and_artifact_pins_are_exact() -> None:
    delta = json.loads(DELTA.read_text(encoding="utf-8"))
    unhashed = deepcopy(delta)
    declared = unhashed.pop("semantic_receipt_sha256")
    assert stable_json_hash(unhashed) == declared
    assert delta["collection"]["prior_exact_outer_candidates"] == 48
    assert delta["collection"]["new_exact_outer_candidates"] == 1
    assert delta["collection"]["cumulative_exact_outer_candidates"] == 49
    assert delta["decision"]["collection_complete"] is False
    assert delta["decision"]["implementation_complete"] is False
    assert delta["decision"]["package_installation_complete"] is False
    assert delta["decision"]["new_schema_created"] is False
    assert delta["decision"]["new_truth_store_created"] is False
    assert delta["decision"]["new_pipeline_script_created"] is False
    assert not any(delta["authority"].values())
    assert REPORT.is_file()
    for artifact in delta["applied_artifacts"]:
        path = ROOT / artifact["path"]
        assert path.stat().st_size == artifact["byte_size"]
        assert stable_file_hash(path) == artifact["sha256"]
