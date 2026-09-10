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
    / "chat_f_external_evidence_f_lane_v1_package_receipt_20260819.json"
)
CAPTURE_DIR = ROOT / "incoming_review" / "chatgpt" / ("20260819T121134Z-chat-f-rights-6a753b43")
CAPTURE_MANIFEST_PATH = CAPTURE_DIR / "source_manifest.json"


def test_chat_f_original_archive_is_exact_but_grants_no_source_rights() -> None:
    """Catch package replacement, blanket-rights import, or authority leakage."""

    receipt = load_external_package_receipt(RECEIPT_PATH)
    validate_external_package_receipt(receipt)
    package_path = ROOT / receipt["package"]["locator"]
    verification = verify_external_package_bytes(receipt, package_path=package_path)

    assert verification.integrity_verified is True
    assert verification.status == "VERIFIED_QUARANTINED"
    assert verification.package_sha256 == (
        "ca290ec0819bc2381beec4a3a53d504517996ac092d050d0bd5d11bf5556b6b0"
    )
    assert verification.archive_entry_count == 20
    assert verification.archive_file_count == 20
    assert verification.promotion_allowed is False
    assert verification.errors == ()
    assert receipt["provenance"]["conversation_id"] == ("6a753b43-9644-83ec-92ad-7d66d62e7ebe")
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
        names = set(archive.namelist())
        ledger = json.loads(archive.read("SHA256SUMS.json"))
        assert len(ledger["files"]) == 19
        for relative_path, expected_sha256 in ledger["files"].items():
            payload = archive.read(relative_path)
            assert hashlib.sha256(payload).hexdigest() == expected_sha256

        rows = list(
            csv.DictReader(
                io.StringIO(archive.read("LICENSE_AND_PERMISSION_LEDGER.csv").decode("utf-8-sig"))
            )
        )

    assert len(rows) == 80
    assert [row["source_id"] for row in rows] == [f"PDS-S{index:03d}" for index in range(1, 81)]
    assert len({row["source_name"] for row in rows}) == 80
    assert {row["rights_artifact_present_in_worker_package"] for row in rows} == {"NO"}
    assert sum(not row["verified_at_utc"] for row in rows) == 65
    assert (
        sum(
            row["legal_review_state"] == "BASELINE_CLASSIFICATION_NOT_LIVE_VERIFIED_IN_F_LANE"
            for row in rows
        )
        == 65
    )
    assert "PDS_XHIGH_MODULE_MANIFEST_v1.json" not in names
    assert "perfume_data_science_source_registry_v1.csv" not in names
    assert "tests/__pycache__/test_f_lane.cpython-313.pyc" in names

    graph = scan_archive_graph_quarantine(package_path)
    assert graph.status == "CLEAR_FOR_RECEIPT_REVIEW"
    assert graph.all_nodes_terminal is True
    assert graph.findings == ()
    assert graph.promotion_allowed is False
