from __future__ import annotations

import csv
import hashlib
import io
import json
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
    ROOT
    / "data"
    / "governance"
    / "chat_b_exact_ratio_causal_xhigh_v1_package_receipt_20260819.json"
)
CAPTURE_DIR = ROOT / "incoming_review" / "chatgpt" / "20260819T115321Z-chat-b-exact-ratio-6a753b14"
CAPTURE_MANIFEST_PATH = CAPTURE_DIR / "source_manifest.json"


def test_chat_b_original_archive_is_exact_but_remains_nonpromoting() -> None:
    """Catch package replacement, generated-row admission, or authority leakage."""

    receipt = load_external_package_receipt(RECEIPT_PATH)
    validate_external_package_receipt(receipt)
    package_path = ROOT / receipt["package"]["locator"]
    verification = verify_external_package_bytes(receipt, package_path=package_path)

    assert verification.integrity_verified is True
    assert verification.status == "VERIFIED_QUARANTINED"
    assert verification.package_sha256 == (
        "15ef920283d457ec06e39af6009ae6153e5d835f39d26539d3463806d7c53cd6"
    )
    assert verification.archive_entry_count == 14
    assert verification.archive_file_count == 14
    assert verification.promotion_allowed is False
    assert verification.errors == ()
    assert receipt["provenance"]["conversation_id"] == ("6a753b14-8180-83ec-84f9-38e1e13e01ec")
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
        root = "CHAT_B_EXACT_RATIO_CAUSAL_XHIGH_v1/"
        ledger = json.loads(archive.read(root + "SHA256SUMS.json"))
        assert len(ledger["files"]) == 13
        for relative_path, expected_sha256 in ledger["files"].items():
            payload = archive.read(root + relative_path)
            assert hashlib.sha256(payload).hexdigest() == expected_sha256

        rows = list(
            csv.DictReader(io.StringIO(archive.read(root + "RATIO_GRID_ARMS.csv").decode("utf-8")))
        )

    assert len(rows) == 253
    le_berre = [row for row in rows if row["study_id"] == "LEBERRE_2008_BJN006"]
    assert len(le_berre) == 125
    assert {row["numeric_state"] for row in le_berre} == {"HOLD_PRIMARY_TABLE_VERIFICATION"}
    assert {row["ratio_state"] for row in le_berre} == {"SYMBOLIC_JND_NEIGHBORHOOD"}
    assert all(
        not row["value_a"]
        and not row["value_b"]
        and not row["value_c"]
        and row["formula_mutation_authority"] == "NONE"
        and row["physical_truth_upgrade_authority"] == "NONE"
        for row in le_berre
    )

    graph = scan_archive_graph_quarantine(package_path)
    assert graph.status == "CLEAR_FOR_RECEIPT_REVIEW"
    assert graph.all_nodes_terminal is True
    assert graph.findings == ()
    assert graph.promotion_allowed is False
