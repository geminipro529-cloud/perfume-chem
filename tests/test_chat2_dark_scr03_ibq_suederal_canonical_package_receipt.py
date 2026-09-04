from __future__ import annotations

import csv
import hashlib
import io
import json
from pathlib import Path
from zipfile import ZipFile

from engine.ingestion.archive_quarantine import (
    scan_archive_graph_quarantine,
    scan_archive_quarantine,
)
from engine.ingestion.package_receipts import (
    load_external_package_receipt,
    stable_file_hash,
    verify_external_package_bytes,
)

ROOT = Path(__file__).resolve().parents[1]
RECEIPT_PATH = (
    ROOT
    / "data"
    / "governance"
    / "chat2_dark_scr03_ibq_suederal_canonical_package_receipt_20260817.json"
)


def test_dark_scr03_receipt_replays_exact_bytes_and_capture() -> None:
    receipt = load_external_package_receipt(RECEIPT_PATH)
    package_path = ROOT / receipt["package"]["locator"]

    verification = verify_external_package_bytes(receipt, package_path=package_path)

    assert verification.integrity_verified is True
    assert verification.status == "VERIFIED_QUARANTINED"
    assert verification.package_sha256 == (
        "eb291f96fdf6e0ec8805d1f7d82f74e92ee5fa3ca6439a00c19f7e4cc15ef769"
    )
    assert verification.verified_embedded_records == (
        "SHA256SUMS.json",
        "PACKAGE_MANIFEST.json",
        "VALIDATION_REPORT.json",
    )
    assert verification.errors == ()
    assert verification.promotion_allowed is False

    summary = receipt["evidence_summary"]
    capture = summary["capture_manifest"]
    capture_path = ROOT / capture["path"]
    assert capture_path.stat().st_size == capture["byte_size"]
    assert stable_file_hash(capture_path) == capture["sha256"]
    capture_manifest = json.loads(capture_path.read_text(encoding="utf-8"))
    assert capture_manifest["captured_artifact"]["copy_matches_source"] is True
    assert capture_manifest["integrity"]["embedded_ledger_mismatches"] == 0
    assert capture_manifest["native_quarantine"]["promotion_allowed"] is False
    assert not any(capture_manifest["authority"].values())

    assert receipt["provenance"]["rights"]["reuse_status"] == "UNKNOWN"
    assert receipt["admission"]["state"] == (
        "EXTERNAL_BYTES_VERIFIED_GRAPH_QUARANTINED_NOT_ADMITTED"
    )
    assert not any(
        receipt["admission"][field]
        for field in (
            "b1_promotion_allowed",
            "canonical_import_allowed",
            "repository_content_import_allowed",
            "row_projection_allowed",
        )
    )
    assert not any(receipt["authority"].values())
    assert summary["deepluna"]["accepted_evidence"] is False
    assert summary["deepluna"]["retry_performed"] is False
    assert summary["deepluna"]["fallback_used"] is False


def test_dark_scr03_package_is_design_only_with_blank_observations() -> None:
    receipt = load_external_package_receipt(RECEIPT_PATH)
    package_path = ROOT / receipt["package"]["locator"]

    with ZipFile(package_path) as archive:
        assert archive.testzip() is None
        ledger = json.loads(archive.read("SHA256SUMS.json"))
        assert ledger["entry_count"] == 10
        assert len(ledger["entries"]) == 10
        assert {entry["path"] for entry in ledger["entries"]} == (
            set(archive.namelist()) - {"SHA256SUMS.json"}
        )
        for entry in ledger["entries"]:
            payload = archive.read(entry["path"])
            assert len(payload) == entry["byte_length"]
            assert hashlib.sha256(payload).hexdigest() == entry["sha256"]

        manifest = json.loads(archive.read("PACKAGE_MANIFEST.json"))
        validation = json.loads(archive.read("VALIDATION_REPORT.json"))
        preregistration = json.loads(archive.read("DARK-SCR-03_PREREGISTRATION.json"))
        linear = json.loads(archive.read("DARK-SCR-03_LINEAR_CHALLENGE.json"))
        conditions = list(
            csv.DictReader(
                io.StringIO(archive.read("DARK-SCR-03_CONDITION_MATRIX.csv").decode("utf-8"))
            )
        )
        observations = list(
            csv.DictReader(
                io.StringIO(archive.read("DARK-SCR-03_OBSERVATION_TEMPLATE.csv").decode("utf-8"))
            )
        )

    assert {row["path"] for row in manifest["members"]} == set(
        receipt["package"]["embedded_integrity_records"][index]["path"] for index in range(3)
    ) | {
        "README.md",
        "DARK-SCR-03_CANONICAL_EXPERIMENT.md",
        "DARK-SCR-03_CONDITION_MATRIX.csv",
        "DARK-SCR-03_PREREGISTRATION.json",
        "DARK-SCR-03_LINEAR_CHALLENGE.json",
        "DARK-SCR-03_LITERATURE_LEDGER.json",
        "DARK-SCR-03_MISSING_CHEMICAL_IMPACT.json",
        "DARK-SCR-03_OBSERVATION_TEMPLATE.csv",
    }
    assert manifest["physical_evidence_state"] == "NOT_TESTED"
    assert manifest["declared_counts"]["condition_rows"] == 18
    assert manifest["declared_counts"]["observation_template_rows"] == 2520
    assert manifest["declared_counts"]["collected_observations"] == 0
    assert validation["verdict"] == "PASS_WITH_EXECUTION_HOLD"
    assert validation["checks_passed"] == 30
    assert validation["checks_failed"] == 0
    assert preregistration["screen_id"] == "DARK-SCR-03"
    assert preregistration["experiment_id"] == "EXP-DARK-003"
    assert preregistration["physical_evidence_state"] == "NOT_TESTED"
    assert preregistration["material_roles"]["A"]["molecular_identity_state"].startswith(
        "UNRESOLVED"
    )
    assert not any(preregistration["authority"].values())
    assert linear["relationship_to_practical_endpoint"] == (
        "SECONDARY_DESCRIPTIVE_CHALLENGE_ONLY; PRACTICAL MIXED_VERSUS_B_ALONE "
        "DECISION REMAINS SEPARATE"
    )
    assert linear["confirmed_nonlinearity_state"] == "NOT_ESTIMABLE"

    assert len(conditions) == 18
    assert {row["physical_state"] for row in conditions} == {"NOT_PREPARED"}
    assert {row["evidence_state"] for row in conditions} == {"PROPOSED_NOT_TESTED"}
    assert len(observations) == 2520
    assert {row["experiment_id"] for row in observations} == {"EXP-DARK-003"}
    assert {row["missing_status"] for row in observations} == {"NOT_COLLECTED"}
    assert {row["evidence_state"] for row in observations} == {"TEMPLATE_ONLY_NO_OBSERVATION"}
    assert {row["physical_state"] for row in observations} == {"NOT_PREPARED"}
    assert all(
        not row[field]
        for row in observations
        for field in (
            "coded_sample_id",
            "condition_id",
            "session_id",
            "numeric_value",
            "text_value",
        )
    )


def test_dark_scr03_native_quarantine_and_parent_edges_remain_fail_closed() -> None:
    receipt = load_external_package_receipt(RECEIPT_PATH)
    package_path = ROOT / receipt["package"]["locator"]

    single = scan_archive_quarantine(package_path)
    assert single.status == "QUARANTINE_HOLD"
    assert [(finding.code, finding.member) for finding in single.findings] == [
        ("PARTIAL_MEMBER_SCAN", "DARK-SCR-03_OBSERVATION_TEMPLATE.csv")
    ]
    assert single.promotion_allowed is False

    graph = scan_archive_graph_quarantine(package_path)
    assert graph.status == "GRAPH_COMPLETE_QUARANTINED"
    assert len(graph.nodes) == 1
    assert graph.edges == ()
    assert graph.resource_usage.max_depth == 0
    assert graph.all_nodes_terminal is True
    assert graph.findings == ()
    assert graph.promotion_allowed is False

    parents = receipt["parents"]
    assert len(parents) == 4
    assert len({parent["sha256"] for parent in parents}) == 4
    assert {parent["authority_state"] for parent in parents} == {"POINTER_ONLY"}
    assert {parent["relation"] for parent in parents} == {
        "CANONICAL_EXPERIMENT_IDENTITY_PARENT_EXACT_HASH",
        "PACKAGE_DECLARED_V5_INVENTORY_PARENT_EXACT_HASH",
        "NAMESPACE_REPAIR_PARENT_EXACT_HASH",
        "INTERPRETATION_METHOD_PARENT_EXACT_HASH",
    }
    assert receipt["evidence_summary"]["implementation_fit"] == (
        "APPEND_ONLY_CAPTURE_AND_STRICT_EXTERNAL_PACKAGE_RECEIPT_ONLY_NO_SCHEMA_"
        "MIGRATION_TRUTH_STORE_FORMULA_STOCK_OR_EXPERIMENT_IMPORT"
    )
