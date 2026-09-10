"""Tests for the append-only authority-false V16 complexity-engine capture."""

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
    / "20260816T154423+0700-v16-complexity-expansion-engine-6a79b172-nf4be1041"
)
PACKAGE = CAPTURE / "Perfume_Complexity_Expansion_and_Calibration_Engine_Aug2026_v2_0.zip"
MANIFEST = CAPTURE / "capture_manifest.json"
RECEIPT = (
    ROOT
    / "data"
    / "governance"
    / "complex_perfumery_complexity_expansion_calibration_engine_v2_package_receipt_20260816.json"
)
DELTA = (
    ROOT
    / "data"
    / "governance"
    / "complex_perfumery_v16_post_v15_complexity_engine_delta_20260816.json"
)
REPORT = ROOT / "output" / "quarantine" / "COMPLEX_PERFUMERY_COLLECTION_DELTA_V16_20260816.md"

PACKAGE_ROOT = "Perfume_Complexity_Expansion_and_Calibration_Engine_Aug2026_v2_0"
PACKAGE_SHA256 = "f4be1041bb8e2e8b5665962e580aa740996bd2f77b61299cca1d3cdf55014a5d"
MANIFEST_SHA256 = "93bb96b64c3259058a73f73adb2d8815b49c05133da812364429e76ea557b575"
LEDGER_SHA256 = "c202b05d42194af612ed2f2647537b01b6cb56ed8a136ce27b947653d6bc050a"
PARENT_HASHES = {
    "108624938e183af41da63f5ef77e31c875b196389f3467d7acd896ccf7b274df",
    "3bcaec98bb637cb8070a11582044e3ce1b9cb2b317cd40761ae7ba529feeb745",
    "e36287aca26f34354b3244f07618cb4c12750dfb85db5584dca39d5130025331",
}
RESIDUAL_HOLDS = {
    "8dd04ea6c69e5e3bd72b03e0ae15cb66ad66e9ac5581cf97666249e869c5a998",
    "e9e325bea9117dbe2a97ff67e77d57705a54244591278fac7a34915a7f0ae523",
    "8224f8a1609deb22b43651da825b9bf653a92143f00ee1d5d592130d162f97db",
    "582ae9902e47807f085a61b7add113c9239a2860445e8171fcf569b3ad6d28c5",
}


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


def _record_path(record: dict[str, object]) -> str:
    return str(
        record.get("path")
        or record.get("name")
        or record.get("file")
        or record.get("relative_path")
    )


def _record_bytes(record: dict[str, object]) -> int:
    value = record.get("bytes", record.get("byte_length", record.get("size")))
    assert isinstance(value, int)
    return value


def test_v16_exact_capture_closes_pending_card_without_promotion() -> None:
    assert PACKAGE.stat().st_size == 172172
    assert stable_file_hash(PACKAGE) == PACKAGE_SHA256
    capture = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert capture["project"]["parent_v15_delta_sha256"] == (
        "33fe02721f8c4ca1a7e709203c2cce8b1b1eb5c446692d49c2b8ccd7288c69c3"
    )
    assert capture["retrieval"]["source_and_capture_sha256_match"] is True
    assert capture["retrieval"]["regeneration"] is False
    assert capture["retrieval"]["substitution"] is False
    assert capture["retrieval"]["reconstruction"] is False
    assert capture["collection_delta"]["prior_exact_outer_candidates"] == 49
    assert capture["collection_delta"]["cumulative_exact_outer_candidates"] == 50
    assert capture["collection_delta"]["pending_source_cards"] == 0
    assert not any(capture["authority"].values())


def test_v16_archive_ledgers_and_claim_boundary_replay_exactly() -> None:
    with ZipFile(PACKAGE) as archive:
        _assert_safe_archive(archive)
        assert len(archive.infolist()) == 75
        assert sum(not item.is_dir() for item in archive.infolist()) == 75

        manifest_path = f"{PACKAGE_ROOT}/MANIFEST.json"
        ledger_path = f"{PACKAGE_ROOT}/SHA256SUMS.json"
        manifest_payload = archive.read(manifest_path)
        ledger_payload = archive.read(ledger_path)
        assert hashlib.sha256(manifest_payload).hexdigest() == MANIFEST_SHA256
        assert hashlib.sha256(ledger_payload).hexdigest() == LEDGER_SHA256

        embedded_manifest = json.loads(manifest_payload)
        embedded_ledger = json.loads(ledger_payload)
        manifest_records = embedded_manifest["files"]
        ledger_records = embedded_ledger["entries"]
        assert len(manifest_records) == 73
        assert len(ledger_records) == 74

        manifest_names = set()
        for record in manifest_records:
            member = _record_path(record)
            if member not in archive.namelist():
                member = f"{PACKAGE_ROOT}/{member}"
            payload = archive.read(member)
            manifest_names.add(member)
            assert len(payload) == _record_bytes(record)
            assert hashlib.sha256(payload).hexdigest() == record["sha256"]
        assert manifest_names == {
            item.filename
            for item in archive.infolist()
            if not item.is_dir() and item.filename not in {manifest_path, ledger_path}
        }

        ledger_names = set()
        for record in ledger_records:
            member = _record_path(record)
            if member not in archive.namelist():
                member = f"{PACKAGE_ROOT}/{member}"
            payload = archive.read(member)
            ledger_names.add(member)
            assert len(payload) == _record_bytes(record)
            assert hashlib.sha256(payload).hexdigest() == record["sha256"]
        assert ledger_names == {
            item.filename
            for item in archive.infolist()
            if not item.is_dir() and item.filename != ledger_path
        }

        release = json.loads(archive.read(f"{PACKAGE_ROOT}/RELEASE.json"))
        boundary = json.loads(archive.read(f"{PACKAGE_ROOT}/receipts/CLAIM_BOUNDARY.json"))
        assert release["repository_state"] == "BRIDGE_BLOCKED"
        assert release["repository_installation"] == "NOT_PERFORMED"
        assert release["formula_mutations"] == 0
        assert release["inventory_mutations"] == 0
        assert release["physical_results_created"] == 0
        assert release["sensory_results_created"] == 0
        assert release["analytical_results_created"] == 0
        assert boundary["measured_headspace"] == "NOT_TESTED"
        assert boundary["strict_empirical_oav"] == "NOT_TESTED"
        assert boundary["safety"] == "NOT_CLEARED"
        assert boundary["release"] == "WITHHELD"


def test_v16_native_graph_and_strict_receipt_remain_nonpromoting() -> None:
    graph = scan_archive_graph_quarantine(PACKAGE)
    assert graph.status == "CLEAR_FOR_RECEIPT_REVIEW"
    assert len(graph.nodes) == 1
    assert len(graph.edges) == 0
    assert graph.all_nodes_terminal is True
    assert graph.findings == ()
    assert graph.promotion_allowed is False
    root = graph.nodes[0]
    assert root.archive_sha256 == PACKAGE_SHA256
    assert root.scan.status == "CLEAR_FOR_RECEIPT_REVIEW"
    assert root.scan.findings == ()
    assert root.scan.promotion_allowed is False

    receipt = validate_external_package_receipt(json.loads(RECEIPT.read_text(encoding="utf-8")))
    verification = verify_external_package_bytes(receipt, package_path=PACKAGE)
    assert verification.status == "VERIFIED_QUARANTINED"
    assert verification.integrity_verified is True
    assert verification.archive_entry_count == 75
    assert verification.archive_file_count == 75
    assert verification.errors == ()
    assert verification.promotion_allowed is False
    assert {parent["sha256"] for parent in receipt["parents"]} == PARENT_HASHES
    assert not any(receipt["authority"].values())


def test_v16_native_fit_and_residual_holds_remain_fail_closed() -> None:
    capture = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert capture["native_fit"]["migration_required"] is False
    assert capture["native_fit"]["new_schema_required"] is False
    assert capture["native_fit"]["new_truth_store_required"] is False
    assert capture["native_fit"]["new_pipeline_script_required"] is False
    assert capture["native_fit"]["package_code_install_allowed"] is False
    assert capture["native_fit"]["package_schema_install_allowed"] is False
    assert {item["sha256"] for item in capture["residual_exact_byte_holds"]} == RESIDUAL_HOLDS

    delta = json.loads(DELTA.read_text(encoding="utf-8"))
    assert delta["pending_source_cards"] == []
    assert {item["sha256"] for item in delta["residual_exact_byte_holds"]} == RESIDUAL_HOLDS
    assert delta["decision"]["package_code_installed"] is False
    assert delta["decision"]["package_schemas_installed"] is False
    assert delta["decision"]["new_pipeline_script_created"] is False
    assert delta["decision"]["physical_or_sensory_execution_performed"] is False
    assert not any(delta["authority"].values())


def test_v16_delta_is_semantically_sealed_and_artifact_pins_are_exact() -> None:
    delta = json.loads(DELTA.read_text(encoding="utf-8"))
    unhashed = deepcopy(delta)
    declared = unhashed.pop("semantic_receipt_sha256")
    assert stable_json_hash(unhashed) == declared
    assert delta["collection"]["prior_exact_outer_candidates"] == 49
    assert delta["collection"]["new_exact_outer_candidates"] == 1
    assert delta["collection"]["cumulative_exact_outer_candidates"] == 50
    assert delta["collection"]["all_project_packages_collected"] is False
    assert delta["decision"]["collection_complete"] is False
    assert delta["decision"]["implementation_complete"] is False
    assert delta["decision"]["package_installation_complete"] is False
    assert delta["decision"]["installation_authorized"] is False
    assert REPORT.is_file()
    for artifact in delta["applied_artifacts"]:
        path = ROOT / artifact["path"]
        assert path.stat().st_size == artifact["byte_size"]
        assert stable_file_hash(path) == artifact["sha256"]
