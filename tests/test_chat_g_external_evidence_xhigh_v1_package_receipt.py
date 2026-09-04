from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path
from zipfile import ZipFile

from engine.calibration.hashing import stable_json_hash
from engine.ingestion.archive_quarantine import scan_archive_graph_quarantine
from engine.ingestion.package_receipts import (
    load_external_package_receipt,
    validate_external_package_receipt,
    verify_external_package_bytes,
)

ROOT = Path(__file__).resolve().parents[1]
RECEIPT_PATH = (
    ROOT / "data" / "governance" / "chat_g_external_evidence_xhigh_v1_package_receipt_20260819.json"
)
CAPTURE_DIR = (
    ROOT / "incoming_review" / "chatgpt" / ("20260819T122123Z-chat-g-external-schema-6a753b49")
)
CAPTURE_MANIFEST_PATH = CAPTURE_DIR / "source_manifest.json"


def test_chat_g_original_archive_is_exact_but_parallel_schema_is_not_installed() -> None:
    """Catch package replacement, parallel-store installation, or authority leakage."""

    receipt = load_external_package_receipt(RECEIPT_PATH)
    validate_external_package_receipt(receipt)
    package_path = ROOT / receipt["package"]["locator"]
    verification = verify_external_package_bytes(receipt, package_path=package_path)

    assert verification.integrity_verified is True
    assert verification.status == "VERIFIED_QUARANTINED"
    assert verification.package_sha256 == (
        "feb747fa9589dfeb621e9c6312bfce291f1aa9fe306ad988aa841cf90eb6c278"
    )
    assert verification.archive_entry_count == 31
    assert verification.archive_file_count == 31
    assert verification.promotion_allowed is False
    assert verification.errors == ()
    assert receipt["provenance"]["conversation_id"] == ("6a753b49-e6dc-83ec-9224-48e24f28e73d")
    assert receipt["provenance"]["rights"]["reuse_status"] == "UNKNOWN"
    assert receipt["provenance"]["rights"]["redistribution_allowed"] is False
    assert not any(receipt["authority"].values())
    assert not any(
        receipt["admission"][field]
        for field in (
            "b1_promotion_allowed",
            "canonical_import_allowed",
            "repository_content_import_allowed",
            "row_projection_allowed",
        )
    )

    manifest = json.loads(CAPTURE_MANIFEST_PATH.read_text(encoding="utf-8"))
    unhashed = deepcopy(manifest)
    declared_manifest_hash = unhashed.pop("receipt_sha256")
    assert stable_json_hash(unhashed) == declared_manifest_hash
    manifest_parent = next(
        parent
        for parent in receipt["parents"]
        if parent["relation"] == "BINDS_BROWSER_CAPTURE_MANIFEST"
    )
    assert manifest_parent["byte_size"] == CAPTURE_MANIFEST_PATH.stat().st_size
    assert (
        manifest_parent["sha256"] == hashlib.sha256(CAPTURE_MANIFEST_PATH.read_bytes()).hexdigest()
    )

    with ZipFile(package_path) as archive:
        assert archive.testzip() is None
        root = "CHAT_G_EXTERNAL_EVIDENCE_CORE_v1/"
        names = set(archive.namelist())
        ledger = json.loads(archive.read(root + "SHA256SUMS.json"))
        assert len(ledger["files"]) == 30
        for relative_path, record in ledger["files"].items():
            payload = archive.read(root + relative_path)
            assert len(payload) == record["bytes"]
            assert hashlib.sha256(payload).hexdigest() == record["sha256"]

        baseline = json.loads(archive.read(root + "baseline/PDS_XHIGH_BASELINE_REFERENCE.json"))
        worker = json.loads(archive.read(root + "WORKER_MANIFEST.json"))
        sql = archive.read(root + "DATABASE_SCHEMA_FINAL.sql").decode("utf-8")

    tables = re.findall(r"CREATE TABLE IF NOT EXISTS\s+([A-Za-z0-9_]+)", sql, re.I)
    assert len(tables) == 34
    assert all(table.startswith("ee_") for table in tables)
    assert baseline["local_byte_state"] == (
        "REFERENCE_ONLY__EXACT_PARENT_SQLITE_AND_SCHEMA_BYTES_NOT_MOUNTED_IN_CHAT_G_RUNTIME"
    )
    assert worker["new_holds"] == [
        "HOLD_BASELINE_BYTES",
        "HOLD_PARALLEL_A_F_PACKAGE_BINDING",
    ]
    assert worker["database_schema_changes"]["parent_database_mutated"] is False
    assert worker["formula_mutations"] == 0
    assert worker["physical_truth_mutations"] == 0
    assert worker["inventory_mutations"] == 0
    assert worker["release_state_mutations"] == 0
    assert not any(name.lower().endswith((".db", ".sqlite", ".sqlite3")) for name in names)

    graph = scan_archive_graph_quarantine(package_path)
    assert graph.status == "CLEAR_FOR_RECEIPT_REVIEW"
    assert graph.all_nodes_terminal is True
    assert graph.findings == ()
    assert graph.promotion_allowed is False
