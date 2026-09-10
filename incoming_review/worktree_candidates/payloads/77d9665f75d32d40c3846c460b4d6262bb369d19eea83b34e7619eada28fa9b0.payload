"""Tests for the V18 authority-false Floral hedonic portfolio capture."""

from __future__ import annotations

import hashlib
import io
import json
from collections import Counter
from copy import deepcopy
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

from openpyxl import load_workbook

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
    / "20260817T045903+0700-v18-floral-hedonic-portfolio-6a79b172-n1654f03a"
)
PACKAGE = CAPTURE / (
    "Floral_Complexity_Expansion_10_Hedonic_Formula_Portfolio_Aug2026_v1_Package.zip"
)
MANIFEST = CAPTURE / "capture_manifest.json"
RECEIPT = (
    ROOT
    / "data"
    / "governance"
    / "complex_perfumery_floral_hedonic_formula_portfolio_package_receipt_20260817.json"
)
DELTA = (
    ROOT
    / "data"
    / "governance"
    / "complex_perfumery_v18_post_v17_floral_hedonic_portfolio_delta_20260817.json"
)
REPORT = ROOT / "output" / "quarantine" / "COMPLEX_PERFUMERY_COLLECTION_DELTA_V18_20260817.md"

PREFIX = "Floral_Complexity_Expansion_10_Hedonic_Formula_Portfolio_Aug2026_v1"
PACKAGE_SHA256 = "1654f03ad0b55fa310a46e6e0ed11a0f9070ab9c94037e726380389f177a35e6"
WORKBOOK_SHA256 = "ac4598ddd9d2130137ec57761d834059405094fb6e4c2ff05093a5dc451c1d64"
LEDGER_SHA256 = "82929e31581f4c90be8ea6082dc807ac17d87ab639a7e4f02856a851bf192e34"
DARK_SHA256 = "eb291f96fdf6e0ec8805d1f7d82f74e92ee5fa3ca6439a00c19f7e4cc15ef769"
RESIDUAL_HOLDS = {
    "8dd04ea6c69e5e3bd72b03e0ae15cb66ad66e9ac5581cf97666249e869c5a998",
    "e9e325bea9117dbe2a97ff67e77d57705a54244591278fac7a34915a7f0ae523",
    "8224f8a1609deb22b43651da825b9bf653a92143f00ee1d5d592130d162f97db",
    "582ae9902e47807f085a61b7add113c9239a2860445e8171fcf569b3ad6d28c5",
}
FORMULA_ERRORS = {"#REF!", "#DIV/0!", "#VALUE!", "#NAME?", "#N/A", "#NUM!", "#NULL!"}


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


def test_v18_exact_transport_capture_adds_dark_and_floral_without_authority() -> None:
    assert PACKAGE.stat().st_size == 361894
    assert stable_file_hash(PACKAGE) == PACKAGE_SHA256
    capture = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert capture["project"]["parent_v17_delta_sha256"] == (
        "7afd3c83cb5d718a6bcaca0f8da00a065888ddc1a017a65d6b4992f2cb174e23"
    )
    assert capture["retrieval"]["exact_source_transport_reassembled"] is True
    assert capture["retrieval"]["archive_regenerated"] is False
    assert capture["retrieval"]["artifact_substituted"] is False
    assert capture["retrieval"]["block_count"] == 118
    assert capture["retrieval"]["full_base64_byte_size"] == 482528
    assert capture["retrieval"]["full_base64_sha256"] == (
        "abb6f264f34aea6737591d08c443186644e3fc2729bf7271acfd0ab35b4d8d93"
    )
    assert capture["collection_delta"]["prior_v17_exact_outer_candidates"] == 51
    assert capture["collection_delta"]["same_turn_post_v17_exact_outer_candidates"] == 2
    assert set(capture["collection_delta"]["same_turn_post_v17_hashes"]) == {
        DARK_SHA256,
        PACKAGE_SHA256,
    }
    assert capture["collection_delta"]["cumulative_exact_outer_candidates"] == 53
    assert capture["collection_delta"]["all_project_packages_collected"] is False
    assert not any(capture["authority"].values())


def test_v18_archive_ledgers_workbook_and_formula_boundary_replay_exactly() -> None:
    with ZipFile(PACKAGE) as archive:
        _safe_archive(archive)
        assert len(archive.infolist()) == 13
        assert sum(not item.is_dir() for item in archive.infolist()) == 13

        ledger_name = f"{PREFIX}_SHA256SUMS.txt"
        ledger_payload = archive.read(ledger_name)
        assert hashlib.sha256(ledger_payload).hexdigest() == LEDGER_SHA256
        records = []
        for line in ledger_payload.decode("utf-8-sig").splitlines():
            digest, name = line.split("  ", 1)
            records.append((digest, name))
        assert len(records) == 6
        for digest, name in records:
            assert hashlib.sha256(archive.read(name)).hexdigest() == digest

        workbook_payload = archive.read(f"{PREFIX}.xlsx")
        assert hashlib.sha256(workbook_payload).hexdigest() == WORKBOOK_SHA256
        workbook = load_workbook(io.BytesIO(workbook_payload), read_only=True, data_only=False)
        assert workbook.sheetnames == [
            "START HERE",
            "PORTFOLIO",
            "MACG GATE",
            "ANTI-COLLAPSE",
            "MISSING IMPACT",
            "PREP QUEUE",
            "TEST PLAN",
            "01 Magnolia",
            "02 Tuberose",
            "03 Rose-Osmanthus",
            "04 Violet-Mimosa",
            "05 Lilac-Hyacinth",
            "06 Frangipani",
            "07 Peony-Leaf",
            "08 Salt-Air Lily",
            "09 Narcissus",
            "10 Neroli-Jasmine",
        ]
        formula_cells = 0
        stored_errors = []
        for worksheet in workbook.worksheets:
            for row in worksheet.iter_rows():
                for cell in row:
                    if isinstance(cell.value, str) and cell.value.startswith("="):
                        formula_cells += 1
                    if cell.value in FORMULA_ERRORS:
                        stored_errors.append((worksheet.title, cell.coordinate, cell.value))
        assert formula_cells == 2760
        assert stored_errors == []

        source = json.loads(archive.read(f"{PREFIX}.json"))
        assert source["inventory_authority"]["sha256"] == (
            "e36287aca26f34354b3244f07618cb4c12750dfb85db5584dca39d5130025331"
        )
        assert len(source["formulas"]) == 10
        current_rows = [row for formula in source["formulas"] for row in formula["current_build"]]
        target_rows = [row for formula in source["formulas"] for row in formula["target_ideal"]]
        assert len(current_rows) == 670
        assert len(target_rows) == 680
        assert Counter(row["inventory_status"] for row in current_rows) == {
            "OWNED": 639,
            "OWNED_PREPARABLE": 30,
            "PREPARABLE": 1,
        }
        assert Counter(row["inventory_status"] for row in target_rows) == {
            "OWNED": 639,
            "OWNED_PREPARABLE": 30,
            "MISSING": 10,
            "PREPARABLE": 1,
        }
        assert sum(formula["metrics"]["preparation_rows"] for formula in source["formulas"]) == 31
        assert {formula["metrics"]["current_total_parts"] for formula in source["formulas"]} == {
            1000.0
        }
        assert {formula["metrics"]["target_total_parts"] for formula in source["formulas"]} == {
            1000.0
        }
        assert Counter(
            gate["state"]
            for formula in source["formulas"]
            for gate in formula["meaningful_complexity_gates"]
        ) == {"PASS": 90, "CONDITIONAL": 10, "NOT_RUN": 30, "HOLD": 20}
        assert Counter(
            gate["state"] for formula in source["formulas"] for gate in formula["macg"]
        ) == {"PASS": 90, "CONDITIONAL": 10, "HOLD": 10}
        assert source["truth_boundary"] == {
            "hedonic_claim": "DESIGN HYPOTHESIS ONLY",
            "physical_compounding": "NOT PERFORMED",
            "sensory_liking": "NOT TESTED",
            "stability": "NOT TESTED",
            "safety": "NOT TESTED",
            "measured_headspace": "NOT TESTED",
            "strict_oav": "NOT TESTED",
            "release": "HOLD",
            "repository_state": "BRIDGE_BLOCKED",
        }


def test_v18_native_graph_and_strict_receipt_remain_quarantined() -> None:
    graph = scan_archive_graph_quarantine(PACKAGE)
    assert graph.status == "GRAPH_COMPLETE_QUARANTINED"
    assert len(graph.nodes) == 2
    assert len(graph.edges) == 1
    assert graph.resource_usage.max_depth == 1
    assert graph.all_nodes_terminal is True
    assert graph.findings == ()
    assert graph.promotion_allowed is False

    nodes = {node.archive_sha256: node for node in graph.nodes}
    root = nodes[PACKAGE_SHA256]
    child = nodes[WORKBOOK_SHA256]
    assert root.scan.status == "QUARANTINE_HOLD"
    assert [(finding.code, finding.member) for finding in root.scan.findings] == [
        ("NESTED_ARCHIVE_REQUIRES_CHILD_RECEIPT", f"{PREFIX}.xlsx"),
        ("PARTIAL_MEMBER_SCAN", f"{PREFIX}.json"),
    ]
    assert child.scan.status == "CLEAR_FOR_RECEIPT_REVIEW"
    assert child.scan.findings == ()

    receipt = validate_external_package_receipt(json.loads(RECEIPT.read_text(encoding="utf-8")))
    verification = verify_external_package_bytes(receipt, package_path=PACKAGE)
    assert verification.status == "VERIFIED_QUARANTINED"
    assert verification.integrity_verified is True
    assert verification.archive_entry_count == 13
    assert verification.archive_file_count == 13
    assert verification.verified_embedded_records == (f"{PREFIX}_SHA256SUMS.txt",)
    assert verification.errors == ()
    assert verification.promotion_allowed is False
    assert len(receipt["parents"]) == 1
    assert receipt["parents"][0]["sha256"] == (
        "e36287aca26f34354b3244f07618cb4c12750dfb85db5584dca39d5130025331"
    )
    assert all(
        pointer["exact_hash_bound"] is False and pointer["parent_edge_created"] is False
        for pointer in receipt["evidence_summary"]["unresolved_source_pointers"]
    )
    assert not any(receipt["authority"].values())


def test_v18_delta_is_semantically_sealed_and_all_pins_replay() -> None:
    delta = json.loads(DELTA.read_text(encoding="utf-8"))
    unhashed = deepcopy(delta)
    declared = unhashed.pop("semantic_receipt_sha256")
    assert stable_json_hash(unhashed) == declared
    assert delta["collection"]["prior_exact_outer_candidates"] == 51
    assert delta["collection"]["new_exact_outer_candidates"] == 2
    assert delta["collection"]["cumulative_exact_outer_candidates"] == 53
    assert {item["sha256"] for item in delta["new_packages"]} == {
        DARK_SHA256,
        PACKAGE_SHA256,
    }
    assert delta["decision"]["collection_complete"] is False
    assert delta["decision"]["implementation_complete"] is False
    assert delta["decision"]["package_installation_complete"] is False
    assert delta["decision"]["new_schema_created"] is False
    assert delta["decision"]["new_truth_store_created"] is False
    assert delta["decision"]["new_pipeline_script_created"] is False
    assert {item["sha256"] for item in delta["residual_exact_byte_holds"]} == RESIDUAL_HOLDS
    assert not any(delta["authority"].values())
    assert REPORT.is_file()
    for artifact in delta["applied_artifacts"]:
        path = ROOT / artifact["path"]
        assert path.stat().st_size == artifact["byte_size"]
        assert stable_file_hash(path) == artifact["sha256"]
