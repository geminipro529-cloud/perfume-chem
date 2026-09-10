from __future__ import annotations

import hashlib
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
CAPTURE_DIR = ROOT / "incoming_review" / "chatgpt" / "20260819T170000Z-xhigh-chat-e-v1-2-6a754c18"
CAPTURE_MANIFEST_PATH = CAPTURE_DIR / "source_manifest.json"
RECEIPT_PATH = (
    ROOT / "data" / "governance" / "chat_e_domain_adjudication_v1_2_package_receipt_20260819.json"
)
PARENT_PACKAGE_PATH = (
    ROOT
    / "incoming_review"
    / "chatgpt"
    / "20260819T131508Z-chat-e-physical-analytical-6a753b36"
    / "CHAT_E_XHIGH_POSTFREEZE_HARDENING_v1.zip"
)
PACKAGE_ROOT = "CHAT_E_XHIGH_DOMAIN_ADJUDICATION_v1_2"


def _read_json(archive: ZipFile, member: str) -> dict:
    return json.loads(archive.read(f"{PACKAGE_ROOT}/{member}"))


def test_xhigh_chat_e_v1_2_capture_binds_complete_rendered_conversation() -> None:
    """Bind the exact five-message XHIGH conversation without promoting its claims."""

    manifest = json.loads(CAPTURE_MANIFEST_PATH.read_text(encoding="utf-8"))
    unhashed = deepcopy(manifest)
    declared_hash = unhashed.pop("receipt_sha256")
    assert stable_json_hash(unhashed) == declared_hash
    assert manifest["conversation"]["conversation_id"] == ("6a754c18-a948-83ec-a456-1923b470d0cc")
    assert manifest["retrieval"]["rendered_message_count"] == 5
    assert manifest["retrieval"]["assistant_message_count"] == 3
    assert manifest["retrieval"]["user_message_count"] == 2
    assert len(manifest["source_messages"]) == 5
    assert manifest["recovered_attachment"]["sha256"] == (
        "8170ac4e7f558698b97a746ac30cd39110b371325b92c542a1ca3b90d2397898"
    )
    assert not any(manifest["authority"].values())


def test_chat_e_v1_2_is_exact_additive_ancestry_with_host_adoption_held() -> None:
    """Preserve the domain adjudication as inert evidence over exact v1.1 ancestry."""

    receipt = load_external_package_receipt(RECEIPT_PATH)
    validate_external_package_receipt(receipt)
    package_path = ROOT / receipt["package"]["locator"]
    verification = verify_external_package_bytes(receipt, package_path=package_path)
    assert verification.integrity_verified is True
    assert verification.status == "VERIFIED_QUARANTINED"
    assert verification.promotion_allowed is False
    assert verification.errors == ()
    assert receipt["package"]["byte_size"] == 120_861
    assert receipt["package"]["sha256"] == (
        "8170ac4e7f558698b97a746ac30cd39110b371325b92c542a1ca3b90d2397898"
    )
    assert receipt["package"]["archive_entry_count"] == 39
    assert receipt["package"]["declared_payload_count"] == 38
    assert not any(receipt["authority"].values())

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
        checksum_ledger = _read_json(archive, "SHA256SUMS.json")
        assert len(checksum_ledger["files"]) == 38
        expected_members = {
            f"{PACKAGE_ROOT}/{record['path']}" for record in checksum_ledger["files"]
        }
        assert expected_members == set(archive.namelist()) - {f"{PACKAGE_ROOT}/SHA256SUMS.json"}
        for record in checksum_ledger["files"]:
            payload = archive.read(f"{PACKAGE_ROOT}/{record['path']}")
            assert len(payload) == record["bytes"]
            assert hashlib.sha256(payload).hexdigest() == record["sha256"]

        embedded_parent = archive.read(
            f"{PACKAGE_ROOT}/baseline/CHAT_E_XHIGH_POSTFREEZE_HARDENING_v1.zip"
        )
        adjudication = _read_json(archive, "DOMAIN_CODE_ADJUDICATION.json")
        closure = _read_json(archive, "MACHINE_DOMAIN_ADJUDICATION_CLOSURE.json")
        literature = _read_json(archive, "LITERATURE_SOURCE_LEDGER.json")
        validation = _read_json(archive, "VALIDATION_REPORT.json")
        migration = _read_json(archive, "MIGRATION_ADVISORY.json")

    assert embedded_parent == PARENT_PACKAGE_PATH.read_bytes()
    assert hashlib.sha256(embedded_parent).hexdigest() == (
        "0d989b72a2678359b797c5e936c4aebc818e8fca700dcc2f557ae86321a71212"
    )
    assert adjudication["decision"] == ("PASS_BOUNDED_LITERATURE_ADJUDICATION__HOST_ADOPTION_HOLD")
    assert len(adjudication["model_decisions"]) == 6
    assert set(adjudication["holds"]) == {
        "HOLD_HOST_ADOPTION",
        "HOLD_FULL_NUMERIC_SOURCE_TABLES",
        "HOLD_RUNTIME_PUBLICATION_AND_CI",
        "HOLD_PHYSICAL_OR_EMPIRICAL_RESULTS",
    }
    assert closure["state"] == ("CLOSED_BY_BOUNDED_LITERATURE_ADJUDICATION_AND_ADVERSARIAL_REPLAY")
    assert closure["frozen_scientific_release_mutated"] is False
    assert len(literature["sources"]) == 7
    assert validation["machine_domain_adjudication"] == "6/6 MODELS ADJUDICATED"
    assert validation["source_scope"] == {
        "full_numeric_tables_ingested": 0,
        "official_model_reporting_guidance": 1,
        "primary_publisher_records": 6,
        "private_reference_database_bytes_ingested": 0,
    }
    assert migration["host_adoption"] == "HOLD"
    assert migration["state"] == "ADVISORY_ONLY__NO_IN_PLACE_REWRITE"

    graph = scan_archive_graph_quarantine(package_path)
    assert graph.status == "GRAPH_COMPLETE_QUARANTINED"
    assert graph.all_nodes_terminal is True
    assert graph.promotion_allowed is False

    summary = receipt["evidence_summary"]
    assert summary["classification"] == (
        "EXACT_CHAT_E_V1_2_DOMAIN_ADJUDICATION_QUARANTINED_HOST_ADOPTION_HELD"
    )
    assert summary["embedded_v1_1_package_byte_exact"] is True
    assert summary["machine_domain_code_adjudication_captured"] is True
    assert summary["native_c3_c8_b5_remain_controlling"] is True
    assert summary["external_numeric_source_tables_present"] is False
    assert summary["package_code_imported"] is False
    assert summary["package_code_executed"] is False
    assert summary["native_runtime_replaced"] is False
    assert summary["promotion_allowed"] is False
