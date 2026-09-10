"""Tests for the append-only V13 Complex Perfumery chat-estate delta."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from io import BytesIO
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

from openpyxl import load_workbook

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
    / "20260816T141500+0700-v13-post-v12-five-package-recovery-multi-chat"
)
MANIFEST = CAPTURE / "capture_manifest.json"
DELTA = ROOT / "data" / "governance" / "complex_perfumery_v13_chat_estate_delta_20260816.json"
REPORT = ROOT / "output" / "quarantine" / "COMPLEX_PERFUMERY_CHAT_ESTATE_DELTA_V13_20260816.md"

PACKAGES = {
    "Nine_Perfume_All_MD_Formula_Files_2026-08-16_v1.zip": (
        364392,
        "8040367862a0a15cf5852dac395a2f630c80898f3ab734755c00299611f9dd17",
        "complex_perfumery_nine_perfume_markdown_formula_export_package_receipt_20260816.json",
    ),
    "XHIGH_AUDIT_VERIFY_FIX_2026-08-16.zip": (
        35080,
        "1706d4c8ff1eeac22e689627630903ea7fcda5517b24ac79d44da246ed6f0657",
        "complex_perfumery_xhigh_audit_verify_fix_package_receipt_20260816.json",
    ),
    "COMPLEX_PERFUMERY_OPUS_V_HR_A_V1R2_READMISSION_V1_20260815.zip": (
        21809,
        "09f723b79912e88b63308574d83f4ad540e2c0cda7970147b85ed9380768bd53",
        "complex_perfumery_opus_v_hr_a_readmission_package_receipt_20260816.json",
    ),
    "VMC_REC_01_Empirical_Loop_Aug2026_v1_Package.zip": (
        45186,
        "3bcaec98bb637cb8070a11582044e3ce1b9cb2b317cd40761ae7ba529feeb745",
        "complex_perfumery_vmc_rec01_empirical_loop_package_receipt_20260816.json",
    ),
    "ACCORD_INTEL_CHAT0_EXACT_BYTE_RECOVERY_RECHECK_20260816T060719Z.zip": (
        2629,
        "59d253cee98f04e7b2f4269c739d471edb1d98fe564cfa11990169e1941d2b07",
        "complex_perfumery_chat0_exact_byte_recovery_recheck_package_receipt_20260816.json",
    ),
}


def _json_member(archive: ZipFile, leaf: str) -> object:
    member = next(name for name in archive.namelist() if name.endswith(leaf))
    return json.loads(archive.read(member).decode("utf-8-sig"))


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


def test_v13_exact_capture_manifest_receipts_and_native_graphs() -> None:
    capture = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert MANIFEST.stat().st_size == 12948
    assert stable_file_hash(MANIFEST) == (
        "2ea8051ea61e92ce47f71b7ea6abcb42c05e7d0c9557b83cc7ebc70d97793bcc"
    )
    assert capture["project"]["registry_point_in_time_chats"] == 38
    assert capture["project"]["visible_project_chats_not_in_registry"] == 10
    assert capture["project"]["defensible_current_chat_denominator_lower_bound"] == 48
    assert capture["project"]["denominator_complete"] is False
    assert capture["collection_delta"]["cumulative_exact_outer_candidates"] == 47
    assert capture["collection_delta"]["all_project_packages_collected"] is False
    assert not any(capture["authority"].values())

    for file_name, (byte_size, digest, receipt_name) in PACKAGES.items():
        package = CAPTURE / file_name
        assert package.stat().st_size == byte_size
        assert stable_file_hash(package) == digest
        receipt_path = ROOT / "data" / "governance" / receipt_name
        receipt = validate_external_package_receipt(
            json.loads(receipt_path.read_text(encoding="utf-8"))
        )
        result = verify_external_package_bytes(receipt, package_path=package)
        assert result.status == "VERIFIED_QUARANTINED"
        assert result.integrity_verified is True
        assert result.errors == ()
        assert result.promotion_allowed is False
        assert not any(receipt["authority"].values())

        graph = scan_archive_graph_quarantine(package)
        assert graph.all_nodes_terminal is True
        assert graph.findings == ()
        assert graph.promotion_allowed is False


def test_v13_package_ledgers_replay_without_reconstruction() -> None:
    for file_name in (
        "Nine_Perfume_All_MD_Formula_Files_2026-08-16_v1.zip",
        "XHIGH_AUDIT_VERIFY_FIX_2026-08-16.zip",
    ):
        with ZipFile(CAPTURE / file_name) as archive:
            _assert_safe_archive(archive)
            ledger_name = next(
                name for name in archive.namelist() if name.endswith("SHA256SUMS.txt")
            )
            lines = archive.read(ledger_name).decode("utf-8-sig").splitlines()
            expected_count = 175 if file_name.startswith("Nine_Perfume") else 24
            assert len(lines) == expected_count
            root = ledger_name.rsplit("/", 1)[0] if "/" in ledger_name else ""
            for line in lines:
                digest, relative = line.split(None, 1)
                relative = relative.strip().lstrip("*")
                member = f"{root}/{relative}" if root else relative
                assert hashlib.sha256(archive.read(member)).hexdigest() == digest

    with ZipFile(
        CAPTURE / "COMPLEX_PERFUMERY_OPUS_V_HR_A_V1R2_READMISSION_V1_20260815.zip"
    ) as archive:
        _assert_safe_archive(archive)
        ledger = _json_member(archive, "INTEGRITY_RECEIPT.json")
        assert isinstance(ledger, dict)
        assert ledger["members_excluding_receipt"] == len(ledger["members"]) == 13
        root = archive.namelist()[0].split("/", 1)[0]
        for record in ledger["members"]:
            payload = archive.read(f"{root}/{record['path']}")
            assert len(payload) == record["bytes"]
            assert hashlib.sha256(payload).hexdigest() == record["sha256"]

    with ZipFile(CAPTURE / "VMC_REC_01_Empirical_Loop_Aug2026_v1_Package.zip") as archive:
        _assert_safe_archive(archive)
        sidecars = [name for name in archive.namelist() if name.endswith(".sha256")]
        assert len(sidecars) == 5
        for sidecar in sidecars:
            digest, target = archive.read(sidecar).decode("utf-8-sig").split()
            assert hashlib.sha256(archive.read(target)).hexdigest() == digest

    with ZipFile(
        CAPTURE / "ACCORD_INTEL_CHAT0_EXACT_BYTE_RECOVERY_RECHECK_20260816T060719Z.zip"
    ) as archive:
        _assert_safe_archive(archive)
        ledger = _json_member(archive, "REPORT_SHA256SUMS.json")
        assert isinstance(ledger, list) and len(ledger) == 3
        root = archive.namelist()[0].split("/", 1)[0]
        for record in ledger:
            payload = archive.read(f"{root}/{record['path']}")
            assert len(payload) == record["size_bytes"]
            assert hashlib.sha256(payload).hexdigest() == record["sha256"]


def test_v13_formula_xhigh_and_opus_packages_stay_advisory() -> None:
    with ZipFile(CAPTURE / "Nine_Perfume_All_MD_Formula_Files_2026-08-16_v1.zip") as archive:
        manifest = _json_member(archive, "MANIFEST.json")
        assert manifest["state"] == (
            "MARKDOWN_FORMULA_EXPORT__SCREEN_DESIGNS_ONLY__NO_CANONICAL_SELECTION"
        )
        assert manifest["counts"] == {
            "perfumes": 9,
            "arms": 110,
            "parent_masters": 14,
            "factor_or_fixed_modules": 33,
            "preparations": 4,
        }
        assert "formula_authority" in manifest["authority_false"]
        assert "physical_execution" in manifest["authority_false"]

    with ZipFile(CAPTURE / "XHIGH_AUDIT_VERIFY_FIX_2026-08-16.zip") as archive:
        manifest = _json_member(archive, "MANIFEST.json")
        terminal = _json_member(
            archive, "XHIGH_IMPLEMENTATION_CURRENT_TERMINAL_RECEIPT_2026-08-16.json"
        )
        assert manifest["current_terminal_state"] == "SOURCE_BYTES_MISSING"
        assert manifest["freeze_authorized"] is False
        assert manifest["pro_review"] == "NOT_STARTED"
        assert terminal["terminal_state"] == "SOURCE_BYTES_MISSING"
        assert terminal["repository"]["commit_sha"] is None

    with ZipFile(
        CAPTURE / "COMPLEX_PERFUMERY_OPUS_V_HR_A_V1R2_READMISSION_V1_20260815.zip"
    ) as archive:
        source = _json_member(archive, "SOURCE_RECEIPT.json")
        decision = _json_member(archive, "READMISSION_DECISION_RECEIPT.json")
        assert all(
            item["raw_bytes_mounted_in_runtime"] is False for item in source["formula_sources"]
        )
        assert not any(source["mutations"].values())
        assert decision["baseline"]["state"] == "FAIL_V1R2_READMISSION__HOLD"
        assert decision["r1a_design_candidate"]["not_applied"] is True


def test_v13_vmc_templates_are_blank_and_unexecuted() -> None:
    with ZipFile(CAPTURE / "VMC_REC_01_Empirical_Loop_Aug2026_v1_Package.zip") as archive:
        release = _json_member(archive, "VMC_REC_01_Empirical_Loop_release_Aug2026_v1.json")
        assert release["repository_state"] == "BRIDGE_BLOCKED"
        assert not any(release["authorities"].values())
        workbook = load_workbook(
            BytesIO(archive.read("VMC_REC_01_Empirical_Loop_Leaf_Ladder_Aug2026_v1.xlsx")),
            read_only=True,
            data_only=True,
        )

    preflight = list(workbook["PREFLIGHT"].iter_rows(min_row=5, values_only=True))
    arms = [
        row
        for row in workbook["ARM FINISH"].iter_rows(min_row=5, values_only=True)
        if len(row) > 12 and row[12] == "NOT MIXED"
    ]
    physical = [
        row
        for row in workbook["PHYSICAL CHECKS"].iter_rows(min_row=5, values_only=True)
        if len(row) > 10 and row[10] == "NOT RUN"
    ]
    day1 = [
        row
        for row in workbook["SENSORY DAY 1"].iter_rows(min_row=5, values_only=True)
        if row and row[0] in {"B24", "L30", "W49", "Z45"}
    ]
    day2 = [
        row
        for row in workbook["SENSORY DAY 2"].iter_rows(min_row=5, values_only=True)
        if row and row[0] in {"B24", "L30", "W49", "Z45"}
    ]
    decisions = [
        row
        for row in workbook["DECISION VECTOR"].iter_rows(min_row=5, values_only=True)
        if len(row) > 9 and row[8:10] == ("NOT RUN", "HOLD")
    ]

    assert len(preflight) == 11 and {row[9] for row in preflight} == {"NOT STARTED"}
    assert len(arms) == 4 and {row[12] for row in arms} == {"NOT MIXED"}
    assert len(physical) == 12 and {row[10] for row in physical} == {"NOT RUN"}
    assert len(day1) == len(day2) == 20
    assert all(all(value is None for value in row[2:]) for row in day1 + day2)
    assert len(decisions) == 4
    assert {row[8:10] for row in decisions} == {("NOT RUN", "HOLD")}


def test_v13_chat0_negative_search_cannot_override_current_pcv3_state() -> None:
    with ZipFile(
        CAPTURE / "ACCORD_INTEL_CHAT0_EXACT_BYTE_RECOVERY_RECHECK_20260816T060719Z.zip"
    ) as archive:
        report = _json_member(archive, "RECOVERY_REPORT.json")
    assert report["state"] == "NO_EXACT_TARGETS_FOUND"
    assert report["results"] == []
    assert report["packages_rebuilt"] == report["packages_repackaged"] == 0
    targets = {item["target_id"]: item for item in report["targets"]}
    assert targets["PCV3_CHAT2_EXPERIMENTAL_DATA_MODEL_V1"]["exact_candidates_found"] == 0

    capture = json.loads(MANIFEST.read_text(encoding="utf-8"))
    chat0 = next(
        item
        for item in capture["captured_artifacts"]
        if item["file_name"].startswith("ACCORD_INTEL_CHAT0")
    )
    assert chat0["content_boundary"]["current_project_pcv3_state"] == (
        "EXACT_BYTES_RECOVERED_AND_QUARANTINED_NOT_ADMITTED"
    )
    assert chat0["content_boundary"]["current_project_universal_accord_state"] == (
        "EXACT_ORIGINAL_BYTES_UNAVAILABLE"
    )


def test_v13_delta_is_point_in_time_incomplete_and_semantically_sealed() -> None:
    delta = json.loads(DELTA.read_text(encoding="utf-8"))
    unhashed = deepcopy(delta)
    declared = unhashed.pop("semantic_receipt_sha256")
    assert stable_json_hash(unhashed) == declared
    assert delta["state"] == "V13_POINT_IN_TIME_CHAT_ESTATE_DELTA_QUARANTINED_NOT_ADMITTED"
    assert delta["chat_estate"]["registry_point_in_time_chats"] == 38
    assert delta["chat_estate"]["newer_visible_chats_not_in_registry"] == 10
    assert delta["chat_estate"]["defensible_denominator_lower_bound"] == 48
    assert delta["chat_estate"]["denominator_complete"] is False
    assert delta["collection"]["prior_exact_outer_candidates"] == 42
    assert delta["collection"]["new_exact_outer_candidates"] == 5
    assert delta["collection"]["cumulative_exact_outer_candidates"] == 47
    assert delta["decision"]["collection_complete"] is False
    assert delta["decision"]["implementation_complete"] is False
    assert delta["decision"]["package_installation_complete"] is False
    assert delta["decision"]["new_schema_created"] is False
    assert delta["decision"]["new_truth_store_created"] is False
    assert delta["decision"]["new_pipeline_script_created"] is False
    assert not any(delta["authority"].values())

    deepluna = delta["deepluna_chat"]
    assert deepluna["batch_id"] == "DLB-20260816T073419644Z-2c6b5f"
    assert deepluna["logical_lanes"] == 10
    assert deepluna["accepted_positive_lanes"] == 8
    assert deepluna["contract_error_lanes"] == 1
    assert deepluna["blocked_lanes"] == 1
    assert deepluna["missing_lanes"] == 0
    assert len(deepluna["accepted_job_ids"]) == 8
    assert len(deepluna["accepted_findings"]) == 8
    assert deepluna["duplicate_paid_work_submitted"] is False
    assert deepluna["retry_submitted"] is False
    assert deepluna["fast_used"] is False
    assert deepluna["fallback_used"] is False
    assert deepluna["sol_local_acceptance_controls"] is True

    blocker_hashes = {item["sha256"] for item in delta["residual_exact_byte_holds"]}
    assert blocker_hashes == {
        "8dd04ea6c69e5e3bd72b03e0ae15cb66ad66e9ac5581cf97666249e869c5a998",
        "e9e325bea9117dbe2a97ff67e77d57705a54244591278fac7a34915a7f0ae523",
        "8224f8a1609deb22b43651da825b9bf653a92143f00ee1d5d592130d162f97db",
        "582ae9902e47807f085a61b7add113c9239a2860445e8171fcf569b3ad6d28c5",
    }
    assert REPORT.is_file()
    for artifact in delta["applied_artifacts"]:
        path = ROOT / artifact["path"]
        assert path.stat().st_size == artifact["byte_size"]
        assert stable_file_hash(path) == artifact["sha256"]
