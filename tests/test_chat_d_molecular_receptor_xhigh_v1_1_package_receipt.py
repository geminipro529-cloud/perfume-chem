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
    / "chat_d_molecular_receptor_xhigh_v1_1_package_receipt_20260819.json"
)
CAPTURE_DIR = (
    ROOT / "incoming_review" / "chatgpt" / "20260819T125952Z-chat-d-molecular-receptor-6a753b22"
)
CAPTURE_MANIFEST_PATH = CAPTURE_DIR / "source_manifest.json"
PACKAGE_ROOT = "CHAT_D_XHIGH_MOLECULAR_RECEPTOR_v1_1"
LOCAL_KELLER_WORKBOOK = (
    ROOT / "data" / "external" / "keller_vosshall_2016" / "12868_2016_287_MOESM1_ESM.xlsx"
)


def _read_json(archive: ZipFile, member: str) -> dict:
    return json.loads(archive.read(f"{PACKAGE_ROOT}/{member}"))


def test_chat_d_package_is_exact_quarantined_receptor_evidence_without_runtime_authority() -> None:
    """Protect exact recovery while preventing receptor metadata from becoming perfume truth."""

    receipt = load_external_package_receipt(RECEIPT_PATH)
    validate_external_package_receipt(receipt)
    package_path = ROOT / receipt["package"]["locator"]
    verification = verify_external_package_bytes(receipt, package_path=package_path)

    assert verification.integrity_verified is True
    assert verification.status == "VERIFIED_QUARANTINED"
    assert verification.package_sha256 == (
        "8f283781742e6ed51950b4397b486a2b4ec9745835cc20bd278a013f2a3a5743"
    )
    assert verification.archive_entry_count == 22
    assert verification.archive_file_count == 22
    assert verification.promotion_allowed is False
    assert verification.errors == ()
    assert receipt["provenance"]["conversation_id"] == ("6a753b22-3490-83ec-bc7b-a0e46c4655c0")
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

    capture_manifest = json.loads(CAPTURE_MANIFEST_PATH.read_text(encoding="utf-8"))
    unhashed = deepcopy(capture_manifest)
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
        ledger = _read_json(archive, "SHA256SUMS.json")
        assert len(ledger["files"]) == 21
        expected_names = {f"{PACKAGE_ROOT}/{name}" for name in ledger["files"]}
        assert expected_names == set(archive.namelist()) - {f"{PACKAGE_ROOT}/SHA256SUMS.json"}
        for relative_path, expected in ledger["files"].items():
            payload = archive.read(f"{PACKAGE_ROOT}/{relative_path}")
            assert len(payload) == expected["bytes"]
            assert hashlib.sha256(payload).hexdigest() == expected["sha256"]

        validation = _read_json(archive, "VALIDATION_REPORT.json")
        worker = _read_json(archive, "WORKER_MANIFEST.json")
        receptor_registry = _read_json(archive, "RECEPTOR_DATASET_REGISTRY.json")
        live_snapshot = _read_json(archive, "LIVE_RECEPTOR_SOURCE_SNAPSHOT_2026-08-07.json")
        crosswalk = list(
            csv.DictReader(
                io.StringIO(
                    archive.read(f"{PACKAGE_ROOT}/MOLECULE_IDENTITY_CROSSWALK.csv").decode(
                        "utf-8-sig"
                    )
                )
            )
        )
        bundled_keller = archive.read(
            f"{PACKAGE_ROOT}/sources/Keller_Vosshall_2016_Additional_file_1.xlsx"
        )

    assert validation["state"] == "PASS_WITH_DECLARED_HOLDS"
    assert validation["tests"]["total"] == {"failed": 0, "passed": 36, "run": 36}
    assert validation["authority_mutations"] == {
        "database_schema": 0,
        "formula": 0,
        "inventory": 0,
        "physical_truth": 0,
        "release_state": 0,
    }
    assert set(validation["holds"]) == {
        "HOLD_SOURCE_BYTES_LIVE_M2OR",
        "HOLD_SOURCE_BYTES_OLFACTIONBASE",
        "HOLD_SOURCE_BYTES_DOOR_LOCAL_COPY",
        "HOLD_IDENTITY_SOURCE_CONFLICT",
        "HOLD_ROW_LEVEL_RECEPTOR_INGESTION",
        "HOLD_MODEL_EXECUTION",
    }
    assert len(crosswalk) == 480
    assert sum(row["mapping_state"] == "EXACT_SOURCE_NATIVE_IDENTITY" for row in crosswalk) == 478
    assert sum(row["mapping_state"] == "EXTERNAL_CAS_PUBCHEM_VERIFIED" for row in crosswalk) == 1
    assert sum(row["mapping_state"] == "HOLD_IDENTITY" for row in crosswalk) == 1
    held = next(row for row in crosswalk if row["mapping_state"] == "HOLD_IDENTITY")
    assert held["source_name"] == "isobutyl acetate"
    assert held["cas"] == "109-19-0"
    assert held["candidate_pubchem_cid"] == "8038"
    assert held["pubchem_cid"] == ""

    assert len(bundled_keller) == LOCAL_KELLER_WORKBOOK.stat().st_size == 9_461_137
    assert hashlib.sha256(bundled_keller).hexdigest() == (
        "efcb1b07558431c869c5578abcd3fa1e4405a38cc68a8b1c1621594c673d9f62"
    )
    assert hashlib.sha256(LOCAL_KELLER_WORKBOOK.read_bytes()).hexdigest() == (
        "efcb1b07558431c869c5578abcd3fa1e4405a38cc68a8b1c1621594c673d9f62"
    )

    live_records = {record["source_id"]: record for record in live_snapshot["records"]}
    assert live_records["M2OR_LIVE_1_2_0_2024"]["observed_counts"] == {
        "experiments": 77_611,
        "molecules": 771,
        "pairs": 53_444,
        "references": 45,
        "sequences": 1_402,
        "species": 16,
    }
    assert live_records["OLFACTIONBASE_LIVE_2026_08"]["observed_counts"] == {
        "human_associations": 409,
        "human_odorants": 197,
        "human_receptors": 69,
        "mouse_associations": 466,
        "mouse_ligands": 133,
        "mouse_receptors": 81,
        "or_odorant_pairs_total": 875,
    }
    assert any(
        record["dataset_id"] == "M2OR_LIVE_1_2_0_2024" for record in receptor_registry["records"]
    )
    assert any(
        record["dataset_id"] == "OLFACTIONBASE_LIVE_2026_08"
        for record in receptor_registry["records"]
    )
    assert worker["formula_mutations"] == 0
    assert worker["inventory_mutations"] == 0
    assert worker["physical_truth_mutations"] == 0
    assert worker["release_state_mutations"] == 0

    graph = scan_archive_graph_quarantine(package_path)
    assert graph.status == "GRAPH_COMPLETE_QUARANTINED"
    assert graph.all_nodes_terminal is True
    assert graph.promotion_allowed is False
    assert len(graph.nodes) == 2
    assert {node.archive_sha256 for node in graph.nodes} == {
        "8f283781742e6ed51950b4397b486a2b4ec9745835cc20bd278a013f2a3a5743",
        "efcb1b07558431c869c5578abcd3fa1e4405a38cc68a8b1c1621594c673d9f62",
    }

    summary = receipt["evidence_summary"]
    assert summary["package_recovered"] is True
    assert summary["internal_checksum_entries_verified"] == 21
    assert summary["keller_workbook_is_existing_governed_duplicate"] is True
    assert summary["live_m2or_counts_reverified"] is True
    assert summary["live_olfactionbase_counts_reverified"] is True
    assert summary["live_olfactionbase_page_pairs_claim_reverified"] == 875
    assert summary["live_olfactionbase_export_data_rows_reverified"] == 874
    assert summary["live_olfactionbase_page_export_consistent"] is False
    assert summary["source_rows_admitted"] == 0
    assert summary["receptor_rows_installed"] == 0
    assert summary["bundled_code_executed"] is False
    assert summary["promotion_allowed"] is False
