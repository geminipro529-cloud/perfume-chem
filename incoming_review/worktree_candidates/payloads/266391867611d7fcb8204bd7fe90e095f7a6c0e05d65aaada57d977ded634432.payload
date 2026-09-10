"""Tests for the append-only Complex Perfumery V9 Perfume Box capture."""

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
PACKAGE_SHA256 = "db0579760159e7438b83e92de399aa0a9f5862f0f547fa030a682c339bd54e84"
WORKBOOK_SHA256 = "90191bed8d702c023cbbae883a2320b656c6ba47355fe5cee3ecf6a63a619ba0"
RECEIPT_SEMANTIC_SHA256 = "2b8d82b02412af1ada25e3934c0f0fda4add4df80feac23e45594db3b55e5c72"


def _receipt() -> dict[str, object]:
    path = (
        ROOT
        / "data"
        / "governance"
        / "complex_perfumery_perfume_box_workflow_formula_book_v2_package_receipt_20260815.json"
    )
    return json.loads(path.read_text(encoding="utf-8"))


def test_perfume_box_receipt_and_exact_package_verify_fail_closed() -> None:
    receipt = _receipt()
    assert validate_external_package_receipt(receipt)["receipt_sha256"] == (RECEIPT_SEMANTIC_SHA256)
    package_path = ROOT / receipt["package"]["locator"]
    assert package_path.stat().st_size == 208163
    assert stable_file_hash(package_path) == PACKAGE_SHA256

    result = verify_external_package_bytes(receipt, package_path=package_path)
    assert result.integrity_verified is True
    assert result.status == "VERIFIED_QUARANTINED"
    assert result.archive_entry_count == result.archive_file_count == 8
    assert result.verified_embedded_records == (
        "Perfume_Box_Workflow_Formula_Book_Aug2026_v2_release.json",
        "Perfume_Box_Workflow_Formula_Book_Aug2026_v2.xlsx.sha256",
        "Perfume_Box_Workflow_Formula_Book_Aug2026_v2.md.sha256",
        "Perfume_Box_Workflow_Formula_Book_Aug2026_v2.json.sha256",
        "Perfume_Box_Workflow_Formula_Book_Aug2026_v2_release.json.sha256",
    )
    assert result.errors == ()
    assert result.promotion_allowed is False
    assert not any(receipt["authority"].values())


def test_perfume_box_members_sidecars_and_content_boundary_are_exact() -> None:
    receipt = _receipt()
    package_path = ROOT / receipt["package"]["locator"]
    with ZipFile(package_path) as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        assert archive.testzip() is None
        assert len(names) == len({name.casefold() for name in names}) == 8
        assert all(
            not PurePosixPath(name).is_absolute()
            and ".." not in PurePosixPath(name).parts
            and "\\" not in name
            for name in names
        )

        payload_names = [name for name in names if not name.endswith(".sha256")]
        assert len(payload_names) == 4
        for payload_name in payload_names:
            sidecar_name = f"{payload_name}.sha256"
            sidecar = archive.read(sidecar_name).decode("utf-8").strip()
            expected = f"{hashlib.sha256(archive.read(payload_name)).hexdigest()}  {payload_name}"
            assert sidecar == expected

        workbook = archive.read("Perfume_Box_Workflow_Formula_Book_Aug2026_v2.xlsx")
        assert len(workbook) == 159218
        assert hashlib.sha256(workbook).hexdigest() == WORKBOOK_SHA256

        package_json = json.loads(archive.read("Perfume_Box_Workflow_Formula_Book_Aug2026_v2.json"))
        release = json.loads(
            archive.read("Perfume_Box_Workflow_Formula_Book_Aug2026_v2_release.json")
        )

    assert len(package_json["formulas"]) == 9
    assert sum(len(formula["rows"]) for formula in package_json["formulas"].values()) == 625
    assert len(package_json["prep_queue"]) == 25
    assert all(record["pass"] is True for record in release["formula_validation"].values())
    assert release["formula_error_scan"] == "PASS"
    assert release["physical_state"] == "HOLD / NOT PHYSICALLY VALIDATED"
    assert release["similarity"] == "NOT TESTED"
    assert release["liking"] == "NOT TESTED"
    assert release["stability"] == "NOT TESTED"
    assert release["safety_release"] == "NOT TESTED"
    assert release["workbook_sha256"] == WORKBOOK_SHA256

    beta_rows = [
        row
        for formula in package_json["formulas"].values()
        for row in formula["rows"]
        if row["material"] == "Beta Ionone 1%"
    ]
    assert len(beta_rows) == 7
    assert {row["active_fraction"] for row in beta_rows} == {0.001}
    assert {row["stock"] for row in beta_rows} == {
        "Beta Ionone 0.1% working dilution (current V5 stock)"
    }


def test_perfume_box_native_graph_retains_bounded_quarantine() -> None:
    receipt = _receipt()
    package_path = ROOT / receipt["package"]["locator"]
    graph = scan_archive_graph_quarantine(package_path)
    assert graph.status == "GRAPH_COMPLETE_QUARANTINED"
    assert graph.root_archive_sha256 == PACKAGE_SHA256
    assert len(graph.nodes) == 2
    assert len(graph.edges) == 1
    assert graph.resource_usage.max_depth == 1
    assert graph.all_nodes_terminal is True
    assert graph.findings == ()
    assert graph.promotion_allowed is False

    root = next(node for node in graph.nodes if node.depth == 0)
    child = next(node for node in graph.nodes if node.depth == 1)
    assert [finding.code for finding in root.scan.findings] == [
        "NESTED_ARCHIVE_REQUIRES_CHILD_RECEIPT",
        "PARTIAL_MEMBER_SCAN",
    ]
    assert root.scan.findings[1].member == ("Perfume_Box_Workflow_Formula_Book_Aug2026_v2.json")
    assert child.archive_sha256 == WORKBOOK_SHA256
    assert child.scan.status == "CLEAR_FOR_RECEIPT_REVIEW"
    assert child.scan.findings == ()


def test_v9_successor_closes_only_perfume_box_and_preserves_holds() -> None:
    successor_path = (
        ROOT / "output" / "quarantine" / "COMPLEX_PERFUMERY_COLLECTION_SUCCESSOR_V9_20260815.json"
    )
    successor = json.loads(successor_path.read_text(encoding="utf-8"))
    assert successor["parent"] == {
        "path": "output/quarantine/COMPLEX_PERFUMERY_COLLECTION_SUCCESSOR_V8_20260815.json",
        "bytes": 6888,
        "sha256": "f48bb0461207f2551e62aa2e5dd0e35a90b86e2957549142988bc318342e1f3c",
        "relationship": "SUPERSEDES_WITHOUT_MUTATING_PARENT",
    }
    parent_path = ROOT / successor["parent"]["path"]
    assert parent_path.stat().st_size == successor["parent"]["bytes"]
    assert stable_file_hash(parent_path) == successor["parent"]["sha256"]
    assert successor["cumulative_exact_outer_candidates"] == 35
    assert successor["new_exact_outer_candidates"] == 1
    assert successor["optional_identities_closed_by_new_capture"] == 1
    assert successor["optional_identities_remaining"] == 1
    assert successor["new_exact_outer_candidate"]["sha256"] == PACKAGE_SHA256
    assert successor["new_exact_outer_candidate"]["promotion_allowed"] is False
    assert successor["native_fit"]["migration_required"] is False
    assert successor["native_fit"]["migration_head_remains"] == "20260810_0016"
    assert successor["native_fit"]["new_truth_store_allowed"] is False
    assert successor["collection_complete"] is False
    assert successor["implementation_complete"] is False
    assert successor["installation_authorized"] is False
    assert not any(successor["authority"].values())


def test_v9_ledger_and_acceptance_replay_exactly() -> None:
    ledger_path = (
        ROOT / "output" / "quarantine" / "COMPLEX_PERFUMERY_HANDOFF_SHA256SUMS_V9_20260815.txt"
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
        / "complex_perfumery_v9_perfume_box_collection_acceptance_20260815.json"
    )
    acceptance = json.loads(acceptance_path.read_text(encoding="utf-8"))
    unhashed = deepcopy(acceptance)
    declared_hash = unhashed.pop("receipt_sha256")
    assert stable_json_hash(unhashed) == declared_hash
    assert acceptance["state"] == "PERFUME_BOX_V2_EXACT_PACKAGE_CAPTURED_AUTHORITY_FALSE"
    assert acceptance["repository_fence"]["staged_paths"] == 0
    assert acceptance["verification"]["receipt_tests_failed"] == 0
    assert acceptance["decision"]["v8_parent_mutated"] is False
    assert acceptance["decision"]["optional_identities_remaining"] == 1
    assert acceptance["decision"]["collection_complete"] is False
    assert acceptance["decision"]["installation_authorized"] is False
    assert not any(acceptance["authority"].values())
    for artifact in acceptance["applied_artifacts"]:
        artifact_path = ROOT / artifact["path"]
        assert artifact_path.stat().st_size == artifact["byte_size"]
        assert stable_file_hash(artifact_path) == artifact["sha256"]
