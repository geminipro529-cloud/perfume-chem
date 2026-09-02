"""Tests for authority-false external package receipts."""

from __future__ import annotations

import hashlib
import json
import stat
from copy import deepcopy
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import pytest

from engine.calibration.hashing import stable_file_hash, stable_json_hash
from engine.ingestion.archive_quarantine import scan_archive_graph_quarantine
from engine.ingestion import package_receipts as package_receipts_module
from engine.ingestion.package_receipts import (
    EXTERNAL_PACKAGE_RECEIPT_SCHEMA_VERSION,
    ExternalPackageReceiptError,
    load_external_package_receipt,
    validate_external_package_receipt,
    verify_external_package_bytes,
)

ROOT = Path(__file__).resolve().parents[1]

STATIC_RECEIPT_PATHS = (
    ROOT / "data" / "governance" / "interaction_atlas_package_receipt_20260810.json",
    ROOT / "data" / "governance" / "six_recipe_package_receipt_20260810.json",
    ROOT
    / "data"
    / "governance"
    / "complex_perfumery_v5_full_chain_package_receipt_20260812.json",
    ROOT
    / "data"
    / "governance"
    / "complex_perfumery_dhp25_exact_v5_package_receipt_20260812.json",
    ROOT
    / "data"
    / "governance"
    / "complex_perfumery_dhp25_initial_package_receipt_20260812.json",
    ROOT
    / "data"
    / "governance"
    / "chat2_dark_scr02_package_receipt_20260812.json",
    ROOT
    / "data"
    / "governance"
    / "chat2_dark_scr02_interpretation_v2_package_receipt_20260812.json",
    ROOT
    / "data"
    / "governance"
    / "chat2_dark_scr20b_namespace_repair_package_receipt_20260812.json",
)

V4_RECEIPT_PATHS = STATIC_RECEIPT_PATHS[2:5]
SCR02_RECEIPT_PATH = STATIC_RECEIPT_PATHS[5]
SCR02_V2_RECEIPT_PATH = STATIC_RECEIPT_PATHS[6]
SCR20B_RECEIPT_PATH = STATIC_RECEIPT_PATHS[7]


def _rehash(receipt: dict) -> dict:
    updated = deepcopy(receipt)
    updated.pop("receipt_sha256", None)
    updated["receipt_sha256"] = stable_json_hash(updated)
    return updated


def _fixture_receipt(
    package_path: Path,
    *,
    manifest_path: str = "manifest.json",
    package_root: str | None = None,
) -> dict:
    with ZipFile(package_path) as archive:
        manifest = archive.read(manifest_path)
        entry_count = len(archive.infolist())
        file_count = sum(not info.is_dir() for info in archive.infolist())
    receipt = {
        "schema_version": EXTERNAL_PACKAGE_RECEIPT_SCHEMA_VERSION,
        "receipt_id": "test-package-receipt",
        "recorded_at": "2026-08-10T12:00:00+07:00",
        "package": {
            "file_name": package_path.name,
            "locator": str(package_path),
            "locator_scope": "EXTERNAL_LOCAL_PATH",
            "byte_size": package_path.stat().st_size,
            "sha256": stable_file_hash(package_path),
            "media_type": "application/zip",
            "archive_entry_count": entry_count,
            "archive_file_count": file_count,
            "declared_payload_count": 1,
            "package_root": package_root,
            "embedded_integrity_records": [
                {
                    "path": manifest_path,
                    "byte_size": len(manifest),
                    "sha256": hashlib.sha256(manifest).hexdigest(),
                    "role": "MANIFEST",
                }
            ],
        },
        "provenance": {
            "source_type": "SECONDARY_RECONSTRUCTION",
            "independence_group": "test:one-package",
            "conversation_id": "00000000-0000-0000-0000-000000000001",
            "turn_id": None,
            "message_id": None,
            "lineage_resolution": "CONVERSATION_ONLY_MESSAGE_UNRESOLVED",
            "rights": {
                "reuse_status": "UNKNOWN",
                "license_or_reuse_restriction": "Test rights are unresolved.",
                "license_url": None,
                "redistribution_allowed": False,
                "spdx_identifier": None,
                "notes": "No permission inference from possession.",
            },
        },
        "admission": {
            "state": "EXTERNAL_BYTES_VERIFIED_NOT_ADMITTED",
            "b1_promotion_allowed": False,
            "canonical_import_allowed": False,
            "repository_content_import_allowed": False,
            "row_projection_allowed": False,
            "blockers": ["RIGHTS_UNKNOWN"],
        },
        "authority": {
            "source_authority": False,
            "formula_authority": False,
            "inventory_authority": False,
            "oav_authority": False,
            "headspace_authority": False,
            "sensory_authority": False,
            "safety_authority": False,
            "procurement_authority": False,
            "compounding_authority": False,
            "release_authority": False,
        },
        "parents": [],
        "evidence_summary": {"purpose": "contract fixture"},
    }
    return _rehash(receipt)


def _set_encryption_flags(package_path: Path) -> None:
    payload = bytearray(package_path.read_bytes())
    patched = 0
    for signature, flag_offset in ((b"PK\x03\x04", 6), (b"PK\x01\x02", 8)):
        offset = 0
        while True:
            offset = payload.find(signature, offset)
            if offset < 0:
                break
            position = offset + flag_offset
            flags = int.from_bytes(payload[position : position + 2], "little") | 0x1
            payload[position : position + 2] = flags.to_bytes(2, "little")
            patched += 1
            offset = position + 2
    assert patched >= 2
    package_path.write_bytes(payload)


@pytest.fixture
def package_path(tmp_path: Path) -> Path:
    path = tmp_path / "package.zip"
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", '{"payload_count":1}\n')
        archive.writestr("payload.csv", "id,value\n1,test\n")
    return path


def test_valid_receipt_verifies_zip_without_promotion(package_path: Path) -> None:
    receipt = _fixture_receipt(package_path)

    normalized = validate_external_package_receipt(receipt)
    result = verify_external_package_bytes(receipt, package_path=package_path)

    assert normalized == receipt
    assert result.integrity_verified is True
    assert result.status == "VERIFIED_QUARANTINED"
    assert result.promotion_allowed is False
    assert result.verified_embedded_records == ("manifest.json",)
    assert result.errors == ()


def test_receipt_self_hash_detects_tamper(package_path: Path) -> None:
    receipt = _fixture_receipt(package_path)
    receipt["evidence_summary"]["purpose"] = "tampered"

    with pytest.raises(ExternalPackageReceiptError, match="receipt_sha256"):
        validate_external_package_receipt(receipt)


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (
            lambda item: item["admission"].__setitem__(
                "b1_promotion_allowed", True
            ),
            "b1_promotion_allowed",
        ),
        (
            lambda item: item["authority"].__setitem__(
                "formula_authority", True
            ),
            "formula_authority",
        ),
        (
            lambda item: item["provenance"]["rights"].__setitem__(
                "redistribution_allowed", True
            ),
            "UNKNOWN rights",
        ),
        (
            lambda item: item["package"]["embedded_integrity_records"][
                0
            ].__setitem__("path", "../manifest.json"),
            "safe archive path",
        ),
    ],
)
def test_authority_and_path_mutations_fail_closed(
    package_path: Path,
    mutator,
    message: str,
) -> None:
    receipt = _fixture_receipt(package_path)
    mutator(receipt)
    receipt = _rehash(receipt)

    with pytest.raises(ExternalPackageReceiptError, match=message):
        validate_external_package_receipt(receipt)


def test_package_byte_drift_is_integrity_hold(package_path: Path) -> None:
    receipt = _fixture_receipt(package_path)
    package_path.write_bytes(package_path.read_bytes() + b"drift")

    result = verify_external_package_bytes(receipt, package_path=package_path)

    assert result.integrity_verified is False
    assert result.status == "INTEGRITY_HOLD"
    assert result.promotion_allowed is False
    assert "byte size" in result.errors[0]


@pytest.mark.parametrize(
    ("member", "message"),
    [
        ("../escape.txt", "safe archive path"),
        ("C:/escape.txt", "safe archive path"),
    ],
)
def test_unsafe_archive_member_is_integrity_hold(
    tmp_path: Path, member: str, message: str
) -> None:
    path = tmp_path / "unsafe.zip"
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", "{}")
        archive.writestr(member, "blocked")
    receipt = _fixture_receipt(path)

    result = verify_external_package_bytes(receipt, package_path=path)

    assert result.status == "INTEGRITY_HOLD"
    assert result.integrity_verified is False
    assert result.promotion_allowed is False
    assert message in result.errors[0]


def test_declared_package_root_escape_is_integrity_hold(tmp_path: Path) -> None:
    path = tmp_path / "root-escape.zip"
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("root/manifest.json", "{}")
        archive.writestr("outside.txt", "blocked")
    receipt = _fixture_receipt(
        path, manifest_path="root/manifest.json", package_root="root"
    )

    result = verify_external_package_bytes(receipt, package_path=path)

    assert result.status == "INTEGRITY_HOLD"
    assert "escapes declared package root" in result.errors[0]
    assert result.promotion_allowed is False


def test_normalized_duplicate_archive_member_is_integrity_hold(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.zip"
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", "{}")
        archive.writestr("PAYLOAD.csv", "first")
        archive.writestr("payload.csv", "second")
    receipt = _fixture_receipt(path)

    result = verify_external_package_bytes(receipt, package_path=path)

    assert result.status == "INTEGRITY_HOLD"
    assert "duplicate normalized archive member" in result.errors[0]
    assert result.promotion_allowed is False


def test_symlink_archive_member_is_integrity_hold(tmp_path: Path) -> None:
    path = tmp_path / "symlink.zip"
    link = ZipInfo("link")
    link.create_system = 3
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", "{}")
        archive.writestr(link, "manifest.json")
    receipt = _fixture_receipt(path)

    result = verify_external_package_bytes(receipt, package_path=path)

    assert result.status == "INTEGRITY_HOLD"
    assert "symlink is forbidden" in result.errors[0]
    assert result.promotion_allowed is False


def test_encrypted_archive_member_is_integrity_hold(tmp_path: Path) -> None:
    path = tmp_path / "encrypted.zip"
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", "{}")
        archive.writestr("payload.csv", "id,value\n1,test\n")
    receipt = _fixture_receipt(path)
    _set_encryption_flags(path)
    receipt["package"]["byte_size"] = path.stat().st_size
    receipt["package"]["sha256"] = stable_file_hash(path)
    receipt = _rehash(receipt)

    result = verify_external_package_bytes(receipt, package_path=path)

    assert result.status == "INTEGRITY_HOLD"
    assert "encrypted archive member" in result.errors[0]
    assert result.promotion_allowed is False


def test_compression_ratio_limit_is_integrity_hold(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "ratio.zip"
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", "{}")
        archive.writestr("payload.txt", "A" * 100_000)
    receipt = _fixture_receipt(path)
    monkeypatch.setattr(package_receipts_module, "_MAX_COMPRESSION_RATIO", 2)

    result = verify_external_package_bytes(receipt, package_path=path)

    assert result.status == "INTEGRITY_HOLD"
    assert "compression-ratio limit" in result.errors[0]
    assert result.promotion_allowed is False


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("missing", "embedded integrity record is missing"),
        ("size", "embedded record size differs"),
        ("hash", "embedded record SHA-256 differs"),
    ],
)
def test_embedded_record_failures_are_individually_held(
    package_path: Path, mutation: str, message: str
) -> None:
    receipt = _fixture_receipt(package_path)
    record = receipt["package"]["embedded_integrity_records"][0]
    if mutation == "missing":
        record["path"] = "missing-manifest.json"
    elif mutation == "size":
        record["byte_size"] += 1
    else:
        record["sha256"] = "0" * 64
    receipt = _rehash(receipt)

    result = verify_external_package_bytes(receipt, package_path=package_path)

    assert result.status == "INTEGRITY_HOLD"
    assert message in result.errors[0]
    assert result.promotion_allowed is False


def test_static_governance_receipts_are_self_hashed_and_quarantined() -> None:
    receipts = [load_external_package_receipt(path) for path in STATIC_RECEIPT_PATHS]
    atlas, recipes = receipts[:2]

    for receipt in receipts:
        validate_external_package_receipt(receipt)
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
        assert receipt["provenance"]["rights"]["reuse_status"] == "UNKNOWN"
        assert receipt["provenance"]["rights"]["redistribution_allowed"] is False

    package_hashes = [receipt["package"]["sha256"] for receipt in receipts]
    assert len(package_hashes) == len(set(package_hashes)) == len(
        STATIC_RECEIPT_PATHS
    )

    source_ids = atlas["evidence_summary"]["candidate_source_ids"]
    assert len(source_ids) == len(set(source_ids)) == 27
    assert atlas["evidence_summary"]["pair_count"] == 253
    assert atlas["evidence_summary"]["empirical_boundary"] == {
        "measured_headspace": 0,
        "strict_oav": 0,
        "physical_pair_passes": 0,
        "perfumer_style_case_studies_completed": 0,
    }

    assert recipes["evidence_summary"]["target_row_count"] == 361
    assert recipes["evidence_summary"]["build_row_count"] == 362
    assert recipes["evidence_summary"]["nonexact_target_rows"] == 48
    conflict = recipes["evidence_summary"]["manifest_hash_discrepancy"]
    assert conflict["resolution"] == "HANDOFF_TRANSCRIPTION_ERROR_ARCHIVE_BYTES_CONTROL"
    assert conflict["archive_declared_and_recomputed_sha256"].endswith(
        "ee2df0d818a0e30fbcb42"
    )


def test_v4_governance_receipts_verify_exact_quarantined_packages() -> None:
    for receipt_path in V4_RECEIPT_PATHS:
        receipt = load_external_package_receipt(receipt_path)
        package_path = ROOT / receipt["package"]["locator"]

        result = verify_external_package_bytes(receipt, package_path=package_path)

        assert result.integrity_verified is True
        assert result.status == "VERIFIED_QUARANTINED"
        assert result.package_sha256 == receipt["package"]["sha256"]
        assert result.archive_entry_count == receipt["package"]["archive_entry_count"]
        assert result.archive_file_count == receipt["package"]["archive_file_count"]
        assert result.verified_embedded_records == tuple(
            record["path"] for record in receipt["package"]["embedded_integrity_records"]
        )
        assert result.promotion_allowed is False
        assert result.errors == ()


def test_complex_perfumery_v4_receipts_bind_exact_quarantined_bytes() -> None:
    expected = {
        "complex_perfumery_v5_full_chain_package_receipt_20260812.json": (
            "16eb6805414c1a96f30609e7dc9eed5377f522f9872e2017222b23635a73f530"
        ),
        "complex_perfumery_dhp25_exact_v5_package_receipt_20260812.json": (
            "7e38c19a83b25de1edbc190f568b5725655d5e60dca63dec951e8f7c01a98efc"
        ),
        "complex_perfumery_dhp25_initial_package_receipt_20260812.json": (
            "ec27bcd4dd1b9a3e54d4de49ace3293d91af868ba6c6005a581b1646d3905dcd"
        ),
    }
    receipts: dict[str, dict] = {}

    for file_name, package_sha256 in expected.items():
        receipt = load_external_package_receipt(
            ROOT / "data" / "governance" / file_name
        )
        validate_external_package_receipt(receipt)
        verification = verify_external_package_bytes(
            receipt,
            package_path=ROOT / receipt["package"]["locator"],
        )

        assert receipt["package"]["sha256"] == package_sha256
        assert verification.integrity_verified is True
        assert verification.status == "VERIFIED_QUARANTINED"
        assert verification.package_sha256 == package_sha256
        assert verification.promotion_allowed is False
        assert verification.errors == ()
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
        assert receipt["provenance"]["rights"]["reuse_status"] == "UNKNOWN"
        assert receipt["provenance"]["rights"]["redistribution_allowed"] is False
        receipts[file_name] = receipt

    exact = receipts[
        "complex_perfumery_dhp25_exact_v5_package_receipt_20260812.json"
    ]
    embedded_parent = next(
        parent
        for parent in exact["parents"]
        if parent["relation"] == "EMBEDS_SOURCE_PACKAGE"
    )
    assert embedded_parent["sha256"] == expected[
        "complex_perfumery_dhp25_initial_package_receipt_20260812.json"
    ]
    assert embedded_parent["authority_state"] == "POINTER_ONLY"
    assert exact["evidence_summary"]["formula_gate"] == (
        "HOLD_BEFORE_MODELED_STATE_CONSTRUCTION"
    )


def test_complex_perfumery_v4_native_fit_delta_reuses_sealed_p2_2() -> None:
    delta_path = (
        ROOT
        / "data"
        / "governance"
        / "complex_perfumery_v4_p2_2_native_fit_delta_20260812.json"
    )
    delta = json.loads(delta_path.read_text(encoding="utf-8"))
    unhashed = deepcopy(delta)
    declared_hash = unhashed.pop("receipt_sha256")

    assert stable_json_hash(unhashed) == declared_hash
    assert delta["state"] == (
        "SELECTIVE_FIELD_GROUP_MAPPING_COMPLETE_PACKAGE_ADMISSION_WITHHELD"
    )
    assert {source["source_id"] for source in delta["sources"]} == {
        "FULL_CHAIN_V1",
        "DHP25_EXACT_V5",
        "DHP25_INITIAL",
    }

    registry = json.loads(
        (ROOT / "output" / "P2_2_MAPPING_POLICY_REGISTRY_2026-08-11.json")
        .read_text(encoding="utf-8")
    )
    policy_ids = set(registry["mapping_policies"])
    profile_ids = set(registry["dependency_profiles"])
    group_ids = [group["field_group_id"] for group in delta["field_groups"]]

    assert len(group_ids) == len(set(group_ids)) == 9
    assert sum(len(group["fields"]) for group in delta["field_groups"]) == 163
    assert all(
        group["policy_id"] in policy_ids
        and group["dependency_profile_id"] in profile_ids
        and group["authority_promoted"] is False
        for group in delta["field_groups"]
    )
    assert delta["coverage"] == {
        "source_count": 3,
        "selected_field_group_count": 9,
        "selected_field_count": 163,
        "full_package_field_census_claimed": False,
        "duplicate_field_group_ids": [],
        "unmapped_selected_field_groups": [],
    }

    for parent in delta["sealed_parents"]:
        parent_path = ROOT / parent["path"]
        assert parent_path.stat().st_size == parent["byte_size"]
        assert stable_file_hash(parent_path) == parent["sha256"]

    assert not any(delta["authority"].values())
    assert delta["decision"] == {
        "sealed_p2_2_parents_mutated": False,
        "migration_required": False,
        "migration_head_remains": "20260810_0016",
        "new_truth_store_allowed": False,
        "new_pipeline_script_allowed": False,
        "package_code_install_allowed": False,
        "canonical_import_authorized": False,
        "installation_authorized": False,
        "projection_state": "SOURCE_AND_DESIGN_ANCESTRY_ONLY",
    }


def test_chat2_scr02_exact_bytes_ledger_and_native_quarantine_boundary() -> None:
    receipt = load_external_package_receipt(SCR02_RECEIPT_PATH)
    package_path = ROOT / receipt["package"]["locator"]

    verification = verify_external_package_bytes(receipt, package_path=package_path)

    assert verification.integrity_verified is True
    assert verification.status == "VERIFIED_QUARANTINED"
    assert verification.package_sha256 == (
        "dd9fb19c03da6c401aa1bdb718446b830148cc2856be6c525abf836788ce90fb"
    )
    assert verification.verified_embedded_records == (
        "SHA256SUMS.json",
        "VALIDATION_REPORT.json",
    )
    assert verification.promotion_allowed is False
    assert verification.errors == ()

    with ZipFile(package_path) as archive:
        assert archive.testzip() is None
        ledger = json.loads(archive.read("SHA256SUMS.json"))
        assert len(ledger["entries"]) == 14
        assert {entry["file_name"] for entry in ledger["entries"]} == (
            set(archive.namelist()) - {"SHA256SUMS.json"}
        )
        for entry in ledger["entries"]:
            payload = archive.read(entry["file_name"])
            assert len(payload) == entry["size_bytes"]
            assert hashlib.sha256(payload).hexdigest() == entry["sha256"]

    graph = scan_archive_graph_quarantine(package_path)
    assert graph.status == "GRAPH_COMPLETE_QUARANTINED"
    assert len(graph.nodes) == 1
    assert graph.edges == ()
    assert graph.all_nodes_terminal is True
    assert graph.findings == ()
    assert graph.promotion_allowed is False
    assert [finding.code for finding in graph.nodes[0].scan.findings] == [
        "PARTIAL_MEMBER_SCAN"
    ]
    assert graph.nodes[0].scan.findings[0].member == (
        "DARK_SCREEN02_SENSORY_OBSERVATION_TEMPLATE_v1.csv"
    )

    summary = receipt["evidence_summary"]
    capture = summary["capture_manifest"]
    capture_path = ROOT / capture["path"]
    assert capture_path.stat().st_size == capture["byte_size"]
    assert stable_file_hash(capture_path) == capture["sha256"]
    assert capture["superseded_corrupt_chunk_evidence_preserved"] is True
    assert capture["current_zip_exact_target_hash_verified"] is True
    assert summary["validation_state"] == "PASS_WITH_EXECUTION_HOLD"
    assert summary["observations"] == 0
    assert summary["physical_batches"] == 0
    assert summary["decisions"] == 0
    assert summary["analytical_measurements"] == 0
    assert summary["native_graph"]["status"] == "GRAPH_COMPLETE_QUARANTINED"
    assert summary["native_graph"]["promotion_allowed"] is False
    assert not any(receipt["authority"].values())


def test_chat2_scr02_interpretation_v2_is_exact_append_only_candidate() -> None:
    receipt = load_external_package_receipt(SCR02_V2_RECEIPT_PATH)
    package_path = ROOT / receipt["package"]["locator"]

    verification = verify_external_package_bytes(receipt, package_path=package_path)

    assert verification.integrity_verified is True
    assert verification.status == "VERIFIED_QUARANTINED"
    assert verification.package_sha256 == (
        "741a357d8099b30081e1f44d4aace97d18b8bdc7f0d6a4e30a6c6aad81cb67ad"
    )
    assert verification.verified_embedded_records == (
        "SHA256SUMS.json",
        "PACKAGE_MANIFEST.json",
        "VALIDATION_REPORT.json",
    )
    assert verification.promotion_allowed is False
    assert verification.errors == ()

    with ZipFile(package_path) as archive:
        assert archive.testzip() is None
        ledger = json.loads(archive.read("SHA256SUMS.json"))
        assert len(ledger["entries"]) == 6
        assert {entry["file_name"] for entry in ledger["entries"]} == (
            set(archive.namelist()) - {"SHA256SUMS.json"}
        )
        for entry in ledger["entries"]:
            payload = archive.read(entry["file_name"])
            assert len(payload) == entry["byte_length"]
            assert hashlib.sha256(payload).hexdigest() == entry["sha256"]

        challenge = json.loads(archive.read("DARK-SCR-02_LINEAR_CHALLENGE_v2.json"))
        literature = json.loads(
            archive.read("DARK-SCR-02_LITERATURE_LEDGER_DELTA_v2.json")
        )
        validation = json.loads(archive.read("VALIDATION_REPORT.json"))

    assert challenge["parent_package"]["sha256"] == (
        "dd9fb19c03da6c401aa1bdb718446b830148cc2856be6c525abf836788ce90fb"
    )
    assert challenge["parent_package"]["state"] == (
        "EXACT_RECOVERED_ANCESTRY_NOT_MUTATED"
    )
    assert challenge["physical_evidence_state"] == "NOT_TESTED"
    assert challenge["practical_endpoint"]["inference_limit"] == (
        "PRACTICAL_SCREEN_OUTCOME_NOT_NONLINEAR_INTERACTION_PROOF"
    )
    assert challenge["analysis_prerequisite"]["candidate_state"] == (
        "CANDIDATE_DEVIATION_ONLY"
    )
    assert challenge["analysis_prerequisite"]["confirmed_nonlinearity_state"] == (
        "NOT_ESTIMABLE_FROM_V1_TWO_DAY_SINGLE_OBSERVATION_GEOMETRY"
    )
    assert not any(challenge["authority"].values())

    source = literature["sources"][0]
    assert source["doi"] == "10.64898/2026.07.03.736426"
    assert source["peer_review_state"] == "NOT_PEER_REVIEWED"
    assert source["authority_rank"] == "PRIMARY_PREPRINT_QUALIFIED"
    assert validation["status"] == "PASS_WITH_EXECUTION_AND_INTERPRETATION_HOLDS"
    assert validation["checks_passed"] == 25
    assert validation["checks_failed"] == 0

    graph = scan_archive_graph_quarantine(package_path)
    assert graph.status == "CLEAR_FOR_RECEIPT_REVIEW"
    assert len(graph.nodes) == 1
    assert graph.edges == ()
    assert graph.all_nodes_terminal is True
    assert graph.findings == ()
    assert graph.nodes[0].scan.findings == ()
    assert graph.promotion_allowed is False

    summary = receipt["evidence_summary"]
    assert summary["parent_v1_mutated"] is False
    assert summary["physical_evidence_state"] == "NOT_TESTED"
    assert summary["native_graph"]["status"] == "CLEAR_FOR_RECEIPT_REVIEW"
    assert summary["native_graph"]["promotion_allowed"] is False
    assert not any(receipt["authority"].values())


def test_chat2_scr20b_namespace_repair_is_exact_append_only_candidate() -> None:
    receipt = load_external_package_receipt(SCR20B_RECEIPT_PATH)
    package_path = ROOT / receipt["package"]["locator"]

    verification = verify_external_package_bytes(receipt, package_path=package_path)

    assert verification.integrity_verified is True
    assert verification.status == "VERIFIED_QUARANTINED"
    assert verification.package_sha256 == (
        "1ccd3cedd289bd13ab639e586de8ae32fbff8319c1d8f42ff08203c3c52901e9"
    )
    assert verification.verified_embedded_records == (
        "SHA256SUMS.json",
        "PACKAGE_MANIFEST.json",
        "VALIDATION_REPORT.json",
    )
    assert verification.promotion_allowed is False
    assert verification.errors == ()

    with ZipFile(package_path) as archive:
        assert archive.testzip() is None
        ledger = json.loads(archive.read("SHA256SUMS.json"))
        assert len(ledger["entries"]) == 5
        assert {entry["file_name"] for entry in ledger["entries"]} == (
            set(archive.namelist()) - {"SHA256SUMS.json"}
        )
        for entry in ledger["entries"]:
            payload = archive.read(entry["file_name"])
            assert len(payload) == entry["byte_length"]
            assert hashlib.sha256(payload).hexdigest() == entry["sha256"]

        namespace = json.loads(
            archive.read("DARK-SCR-03_TO_DARK-SCR-20B_NAMESPACE_REPAIR.json")
        )
        validation = json.loads(archive.read("VALIDATION_REPORT.json"))

    assert namespace["collision"]["earlier_canonical_assignment"]["disposition"] == (
        "RETAIN_DARK-SCR-03"
    )
    assert namespace["successor"]["experiment_id"] == "DARK-SCR-20B"
    assert namespace["successor"]["legacy_alias_execution_allowed"] is False
    assert namespace["hold_resolution"]["resolved"] == [
        "HOLD_PARENT_BYTES_UNAVAILABLE"
    ]
    assert namespace["physical_state"]["evidence_state"] == "NOT_TESTED"
    assert not any(namespace["authority"].values())
    assert validation["status"] == "PASS_WITH_EXECUTION_AND_NAMESPACE_HOLDS"
    assert validation["checks_passed"] == 32
    assert validation["checks_failed"] == 0

    parent_paths = {
        "20ac62a0a5e639f8a5225937690b582c6c6837b74c6c1311786071bc50ba40ba": (
            ROOT
            / "incoming_review"
            / "chatgpt"
            / "20260811T115527Z-dark-chat2-base64-recovery-6a74ba3d-n7f3c2d1"
            / "ACCORD_INTEL_CHAT2_DARK_MATERIALS_v2.zip"
        ),
        "90f610273aa3c8fab21895a5ca11dd67051e4631509376f03bf5a38337181d2e": (
            ROOT
            / "incoming_review"
            / "chatgpt"
            / "20260811T090138Z-dark-chat2-6a74ba3d-99e3d1c0"
            / "ACCORD_INTEL_DARK_DARK-SCR-03_GUAIACWOOD_GUAIACOL_v1_20260810.zip"
        ),
    }
    for expected_hash, parent_path in parent_paths.items():
        assert stable_file_hash(parent_path) == expected_hash

    graph = scan_archive_graph_quarantine(package_path)
    assert graph.status == "CLEAR_FOR_RECEIPT_REVIEW"
    assert len(graph.nodes) == 1
    assert graph.edges == ()
    assert graph.all_nodes_terminal is True
    assert graph.findings == ()
    assert graph.nodes[0].scan.findings == ()
    assert graph.promotion_allowed is False

    summary = receipt["evidence_summary"]
    capture = summary["capture_manifest"]
    capture_path = ROOT / capture["path"]
    assert capture_path.stat().st_size == capture["byte_size"]
    assert stable_file_hash(capture_path) == capture["sha256"]
    assert summary["parent_archives_mutated"] is False
    assert summary["physical_evidence_state"] == "NOT_TESTED"
    assert summary["native_graph"]["promotion_allowed"] is False
    assert not any(receipt["authority"].values())


def test_complex_perfumery_v5_successor_and_ledger_are_append_only() -> None:
    successor_path = (
        ROOT
        / "output"
        / "quarantine"
        / "COMPLEX_PERFUMERY_COLLECTION_SUCCESSOR_V5_20260812.json"
    )
    plan_path = (
        ROOT
        / "output"
        / "quarantine"
        / "COMPLEX_PERFUMERY_NATIVE_FIT_AND_INSTALL_PLAN_V5_20260812.md"
    )
    ledger_path = (
        ROOT
        / "output"
        / "quarantine"
        / "COMPLEX_PERFUMERY_HANDOFF_SHA256SUMS_V5_20260812.txt"
    )
    successor = json.loads(successor_path.read_text(encoding="utf-8"))

    assert successor["parent"] == {
        "path": "output/quarantine/COMPLEX_PERFUMERY_COLLECTION_SUCCESSOR_V4_20260811.json",
        "bytes": 8550,
        "sha256": "ff781236849094addc2d72ea930f5d02d145e28cd89759e6a8797d098cc9057f",
        "relationship": "SUPERSEDES_WITHOUT_MUTATING_PARENT",
    }
    parent_path = ROOT / successor["parent"]["path"]
    assert parent_path.stat().st_size == successor["parent"]["bytes"]
    assert stable_file_hash(parent_path) == successor["parent"]["sha256"]
    assert successor["cumulative_exact_outer_candidates"] == 33
    assert successor["new_exact_outer_candidates"] == 2
    assert successor["optional_identities_closed_by_new_capture"] == 0
    assert successor["optional_identities_remaining"] == 5
    assert {item["sha256"] for item in successor["new_exact_outer_candidates_detail"]} == {
        "741a357d8099b30081e1f44d4aace97d18b8bdc7f0d6a4e30a6c6aad81cb67ad",
        "1ccd3cedd289bd13ab639e586de8ae32fbff8319c1d8f42ff08203c3c52901e9",
    }
    assert successor["dark_namespace_resolution"]["DARK-SCR-03"].startswith(
        "IBQ_10_PERCENT"
    )
    assert successor["dark_namespace_resolution"]["DARK-SCR-20B"].endswith(
        "DESIGN_POINTER_ONLY"
    )
    assert successor["installation_critical_exact_byte_blocker"][
        "reconstruction_allowed"
    ] is False
    assert successor["installation_critical_exact_byte_blocker"][
        "substitution_allowed"
    ] is False
    assert successor["collection_complete"] is False
    assert successor["implementation_complete"] is False
    assert successor["installation_authorized"] is False
    assert not any(successor["authority"].values())
    assert plan_path.is_file()

    ledger_entries = []
    for line in ledger_path.read_text(encoding="utf-8").splitlines():
        digest, byte_size, relative_path = line.split("  ", 2)
        ledger_entries.append((digest, int(byte_size), relative_path))
    assert len(ledger_entries) == 11
    assert len({relative_path for _, _, relative_path in ledger_entries}) == 11
    for digest, byte_size, relative_path in ledger_entries:
        artifact_path = ROOT / relative_path
        assert artifact_path.stat().st_size == byte_size
        assert stable_file_hash(artifact_path) == digest


def test_complex_perfumery_v5_append_acceptance_hash_and_pins_replay() -> None:
    acceptance_path = (
        ROOT
        / "data"
        / "governance"
        / "complex_perfumery_v5_collection_append_acceptance_20260812.json"
    )
    acceptance = json.loads(acceptance_path.read_text(encoding="utf-8"))
    unhashed = deepcopy(acceptance)
    declared_hash = unhashed.pop("receipt_sha256")

    assert stable_json_hash(unhashed) == declared_hash
    assert acceptance["state"] == (
        "DARK_APPEND_ONLY_RECEIPTS_AND_V5_SUCCESSOR_APPLIED_AUTHORITY_FALSE"
    )
    assert acceptance["repository_fence"]["staged_paths"] == 0
    assert acceptance["verification"]["receipt_tests_failed"] == 0
    assert acceptance["verification"]["quarantine_tests_failed"] == 0
    assert acceptance["decision"]["v4_parent_mutated"] is False
    assert acceptance["decision"]["collection_complete"] is False
    assert acceptance["decision"]["package_installation_complete"] is False
    assert acceptance["decision"]["installation_authorized"] is False
    assert not any(acceptance["authority"].values())

    for artifact in acceptance["applied_artifacts"]:
        artifact_path = ROOT / artifact["path"]
        assert artifact_path.stat().st_size == artifact["byte_size"]
        assert stable_file_hash(artifact_path) == artifact["sha256"]
