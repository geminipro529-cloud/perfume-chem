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
CAPTURE_DIR = (
    ROOT / "incoming_review" / "chatgpt" / "20260819T131508Z-chat-e-physical-analytical-6a753b36"
)
CAPTURE_MANIFEST_PATH = CAPTURE_DIR / "source_manifest.json"
V1_RECEIPT_PATH = (
    ROOT
    / "data"
    / "governance"
    / "chat_e_physical_analytical_lane_v1_package_receipt_20260819.json"
)
HARDENING_RECEIPT_PATH = (
    ROOT / "data" / "governance" / "chat_e_postfreeze_hardening_v1_package_receipt_20260819.json"
)
HARDENING_ROOT = "CHAT_E_XHIGH_POSTFREEZE_HARDENING_v1"


def _read_json(archive: ZipFile, member: str) -> dict:
    return json.loads(archive.read(member))


def _assert_capture_manifest() -> dict:
    manifest = json.loads(CAPTURE_MANIFEST_PATH.read_text(encoding="utf-8"))
    unhashed = deepcopy(manifest)
    declared_hash = unhashed.pop("receipt_sha256")
    assert stable_json_hash(unhashed) == declared_hash
    assert manifest["source"]["conversation_id"] == "6a753b36-a0b8-83ec-a7cc-bc79f1d37b47"
    assert len(manifest["packages"]) == 2
    assert not any(
        manifest["disposition"][field]
        for field in manifest["disposition"]
        if field.endswith("_allowed")
    )
    return manifest


def _assert_receipt_common(path: Path) -> tuple[dict, Path]:
    receipt = load_external_package_receipt(path)
    validate_external_package_receipt(receipt)
    package_path = ROOT / receipt["package"]["locator"]
    verification = verify_external_package_bytes(receipt, package_path=package_path)
    assert verification.integrity_verified is True
    assert verification.status == "VERIFIED_QUARANTINED"
    assert verification.promotion_allowed is False
    assert verification.errors == ()
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
    manifest_parent = next(
        parent
        for parent in receipt["parents"]
        if parent["relation"] == "BINDS_BROWSER_CAPTURE_MANIFEST"
    )
    assert manifest_parent["byte_size"] == CAPTURE_MANIFEST_PATH.stat().st_size
    assert (
        manifest_parent["sha256"] == hashlib.sha256(CAPTURE_MANIFEST_PATH.read_bytes()).hexdigest()
    )
    return receipt, package_path


def test_chat_e_v1_is_exact_source_registry_evidence_with_executable_contract_held() -> None:
    """Recover v1 exactly without installing its known-incoherent executable guard."""

    _assert_capture_manifest()
    receipt, package_path = _assert_receipt_common(V1_RECEIPT_PATH)
    assert receipt["package"] == {
        **receipt["package"],
        "byte_size": 33_356,
        "sha256": "685098081c631a0c39e3113d1d3ef3ba08662537bcee3dbcee722b321aa338cf",
        "archive_entry_count": 25,
        "archive_file_count": 25,
        "declared_payload_count": 24,
        "package_root": None,
    }

    with ZipFile(package_path) as archive:
        assert archive.testzip() is None
        checksum_ledger = _read_json(archive, "SHA256SUMS.json")
        assert len(checksum_ledger["files"]) == 24
        assert set(checksum_ledger["files"]) == set(archive.namelist()) - {"SHA256SUMS.json"}
        for member, expected_hash in checksum_ledger["files"].items():
            assert hashlib.sha256(archive.read(member)).hexdigest() == expected_hash

        validation = _read_json(archive, "VALIDATION_REPORT.json")
        worker = _read_json(archive, "WORKER_MANIFEST.json")
        physical = _read_json(archive, "PHYSICAL_PROPERTY_SOURCE_REGISTRY.json")
        release = _read_json(archive, "RELEASE_MODEL_REGISTRY.json")

    assert validation["state"] == "PASS_WITH_DECLARED_EXTERNAL_ACCESS_HOLDS"
    assert validation["tests"]["tests_run"] == 23
    assert validation["tests"]["tests_passed"] == 23
    assert validation["tests"]["tests_failed"] == 0
    assert set(validation["declared_holds"]) == {
        "HOLD_BASELINE_PACKAGE_BYTES",
        "HOLD_SOURCE_BYTES",
        "HOLD_NUMERIC_TABLE",
        "HOLD_MATRIX_TRANSFER",
    }
    assert physical["source_count"] == 12
    assert len(release["models"]) == 6
    assert len(worker["source_records_used"]) == 12
    assert worker["formula_mutations"] == 0
    assert worker["inventory_mutations"] == 0
    assert worker["physical_truth_mutations"] == 0
    assert worker["release_state_mutations"] == 0

    graph = scan_archive_graph_quarantine(package_path)
    assert graph.status == "CLEAR_FOR_RECEIPT_REVIEW"
    assert graph.all_nodes_terminal is True
    assert graph.promotion_allowed is False
    assert len(graph.nodes) == 1

    summary = receipt["evidence_summary"]
    assert summary["classification"] == (
        "EXACT_CHAT_E_V1_PHYSICAL_ANALYTICAL_PACKAGE_QUARANTINED_EXECUTABLE_CONTRACT_RED"
    )
    assert summary["physical_source_registry_records"] == 12
    assert summary["release_model_registry_records"] == 6
    assert summary["source_rows_admitted"] == 0
    assert summary["bundled_code_executed"] is False
    assert summary["bundled_code_installed"] is False
    assert summary["native_runtime_replaced"] is False
    assert summary["promotion_allowed"] is False


def test_chat_e_hardening_preserves_defects_but_native_c3_c8_b5_remain_controlling() -> None:
    """Freeze the useful defect ledger without replacing native C3/C8 or B5 code."""

    _assert_capture_manifest()
    receipt, package_path = _assert_receipt_common(HARDENING_RECEIPT_PATH)
    assert receipt["package"] == {
        **receipt["package"],
        "byte_size": 86_646,
        "sha256": "0d989b72a2678359b797c5e936c4aebc818e8fca700dcc2f557ae86321a71212",
        "archive_entry_count": 52,
        "archive_file_count": 52,
        "declared_payload_count": 51,
        "package_root": HARDENING_ROOT,
    }

    with ZipFile(package_path) as archive:
        assert archive.testzip() is None
        checksum_ledger = _read_json(archive, f"{HARDENING_ROOT}/SHA256SUMS.json")
        assert checksum_ledger["file_count"] == 51
        expected_members = {f"{HARDENING_ROOT}/{member}" for member in checksum_ledger["files"]}
        assert expected_members == set(archive.namelist()) - {f"{HARDENING_ROOT}/SHA256SUMS.json"}
        for member, expected in checksum_ledger["files"].items():
            payload = archive.read(f"{HARDENING_ROOT}/{member}")
            assert len(payload) == expected["bytes"]
            assert hashlib.sha256(payload).hexdigest() == expected["sha256"]

        defect_ledger = _read_json(archive, f"{HARDENING_ROOT}/DEFECT_LEDGER.json")
        validation = _read_json(archive, f"{HARDENING_ROOT}/VALIDATION_REPORT.json")
        worker = _read_json(archive, f"{HARDENING_ROOT}/WORKER_ADDENDUM_MANIFEST.json")
        embedded_v1 = archive.read(
            f"{HARDENING_ROOT}/baseline/CHAT_E_XHIGH_PHYSICAL_ANALYTICAL_LANE_v1.zip"
        )

    assert [item["id"] for item in defect_ledger["defects"]] == [
        "E-HARD-001",
        "E-HARD-002",
        "E-HARD-003",
        "E-HARD-004",
        "E-HARD-005",
        "E-HARD-006",
    ]
    assert validation["state"] == "PASS_WITH_DECLARED_ADOPTION_HOLDS"
    assert validation["total_pytest"] == {"failed": 0, "passed": 88, "run": 88}
    assert validation["hardening"]["strict_oav_calculation_performed"] is False
    assert validation["authority_mutations"] == {
        "analytical_truth": 0,
        "bottle": 0,
        "formula": 0,
        "inventory": 0,
        "physical_truth": 0,
        "release": 0,
        "repository": 0,
        "scientific_xhigh_release": 0,
        "sensory_observation": 0,
    }
    assert worker["repository_mutations"] == 0
    assert len(embedded_v1) == 33_356
    assert hashlib.sha256(embedded_v1).hexdigest() == (
        "685098081c631a0c39e3113d1d3ef3ba08662537bcee3dbcee722b321aa338cf"
    )
    assert (
        embedded_v1 == (CAPTURE_DIR / "CHAT_E_XHIGH_PHYSICAL_ANALYTICAL_LANE_v1.zip").read_bytes()
    )

    graph = scan_archive_graph_quarantine(package_path)
    assert graph.status == "GRAPH_COMPLETE_QUARANTINED"
    assert graph.all_nodes_terminal is True
    assert graph.promotion_allowed is False
    assert len(graph.nodes) == 2

    summary = receipt["evidence_summary"]
    assert summary["classification"] == (
        "EXACT_CHAT_E_POSTFREEZE_HARDENING_PACKAGE_QUARANTINED_NATIVE_C3_C8_B5_SUPERSEDE"
    )
    assert summary["defect_ids_preserved"] == [
        "E-HARD-001",
        "E-HARD-002",
        "E-HARD-003",
        "E-HARD-004",
        "E-HARD-005",
        "E-HARD-006",
    ]
    assert summary["native_c8_focused_tests_passed"] == 90
    assert summary["native_b5_focused_tests_passed"] == 84
    assert summary["native_c3_c8_exact_model_binding_controls"] is True
    assert summary["native_b5_identity_quantitation_controls"] is True
    assert summary["package_code_imported"] is False
    assert summary["package_code_executed"] is False
    assert summary["native_runtime_replaced"] is False
    assert summary["source_rows_admitted"] == 0
    assert summary["promotion_allowed"] is False
