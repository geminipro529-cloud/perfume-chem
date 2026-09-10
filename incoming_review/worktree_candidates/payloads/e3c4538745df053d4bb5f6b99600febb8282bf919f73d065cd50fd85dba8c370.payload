"""Replay the V19 exact-byte parent recovery without promoting package content."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

from openpyxl import load_workbook

from engine.calibration.hashing import stable_file_hash, stable_json_hash
from engine.ingestion.package_receipts import (
    validate_external_package_receipt,
    verify_external_package_bytes,
)

ROOT = Path(__file__).resolve().parents[1]
CAPTURE = (
    ROOT
    / "incoming_review"
    / "chatgpt"
    / "20260817T061500+0700-v19-floral-atlas-discovery-engine-parent-recovery"
)
ATLAS = CAPTURE / "Floral_Heart_Complexity_Discovery_Atlas_Aug2026_v1.xlsx"
PACKAGE = CAPTURE / ("Perfume_Complexity_Model_Discovery_Admission_Engine_Aug2026_v1_2.zip")
PACKAGE_RECEIPT = (
    ROOT
    / "data"
    / "governance"
    / ("complex_perfumery_model_discovery_admission_v1_2_parent_receipt_20260817.json")
)
ATLAS_RECEIPT = (
    ROOT
    / "data"
    / "governance"
    / ("complex_perfumery_floral_heart_discovery_atlas_receipt_20260817.json")
)
DELTA = ROOT / "data" / "governance" / ("complex_perfumery_v19_parent_recovery_delta_20260817.json")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _semantic_hash(payload: dict, field: str) -> str:
    body = deepcopy(payload)
    body.pop(field)
    return stable_json_hash(body)


def test_exact_artifact_bytes_and_package_receipt_replay() -> None:
    assert ATLAS.stat().st_size == 141770
    assert stable_file_hash(ATLAS) == (
        "91d9cd54605663c9221210fc4e811e91e776530fd9c3aabd13ca450a1373aa7b"
    )
    assert PACKAGE.stat().st_size == 826528
    assert stable_file_hash(PACKAGE) == (
        "108624938e183af41da63f5ef77e31c875b196389f3467d7acd896ccf7b274df"
    )

    receipt = validate_external_package_receipt(_load(PACKAGE_RECEIPT))
    replay = verify_external_package_bytes(receipt, package_path=PACKAGE)
    assert replay.integrity_verified is True
    assert replay.promotion_allowed is False
    assert replay.archive_entry_count == 137
    assert len(replay.verified_embedded_records) == 2


def test_internal_ledgers_and_source_projection_are_exact() -> None:
    root = "Perfume_Complexity_Model_Discovery_Admission_Engine_Aug2026_v1_2/"
    with ZipFile(PACKAGE) as archive:
        assert archive.testzip() is None
        names = archive.namelist()
        assert len(names) == 137
        assert len({PurePosixPath(name).as_posix().casefold() for name in names}) == 137

        manifest = json.loads(archive.read(root + "MANIFEST.json"))
        manifest_rows = manifest.get("artifacts") or manifest.get("files")
        assert len(manifest_rows) == 135
        for row in manifest_rows:
            path = row.get("path") or row.get("file")
            assert hashlib.sha256(archive.read(root + path)).hexdigest() == row["sha256"]

        sums = json.loads(archive.read(root + "SHA256SUMS.json"))
        sum_rows = sums.get("files") or sums.get("artifacts") or sums
        if isinstance(sum_rows, dict):
            sum_rows = [{"path": path, "sha256": digest} for path, digest in sum_rows.items()]
        assert len(sum_rows) == 136
        for row in sum_rows:
            path = row.get("path") or row.get("file")
            assert hashlib.sha256(archive.read(root + path)).hexdigest() == row["sha256"]

    projection = CAPTURE / "source_projection" / "complexity_engine"
    files = sorted(projection.glob("*.py"))
    assert len(files) == 16
    projection_manifest = [{"path": path.name, "sha256": stable_file_hash(path)} for path in files]
    assert stable_json_hash(projection_manifest) == (
        "0a282f86103ac7ccf8b9b82a071d133d104dc550cf9fb979670730183e8b5ef1"
    )


def test_atlas_is_safe_discovery_only_ooxml() -> None:
    with ZipFile(ATLAS) as archive:
        assert archive.testzip() is None
        names = archive.namelist()
        lowered = [name.casefold() for name in names]
        assert len(names) == 45
        assert not any("vbaproject" in name for name in lowered)
        assert not any("externallinks/" in name for name in lowered)
        assert not any("connections.xml" in name for name in lowered)
        assert not any("customxml/" in name for name in lowered)
        assert not any("_xmlsignatures/" in name for name in lowered)

    workbook = load_workbook(ATLAS, data_only=False, read_only=True)
    try:
        assert len(workbook.sheetnames) == 13
        formula_count = 0
        nonempty_count = 0
        for sheet in workbook.worksheets:
            assert sheet.sheet_state == "visible"
            for row in sheet.iter_rows():
                for cell in row:
                    if cell.value is not None:
                        nonempty_count += 1
                    if cell.data_type == "f":
                        formula_count += 1
        assert nonempty_count == 13997
        assert formula_count == 11
    finally:
        workbook.close()

    receipt = _load(ATLAS_RECEIPT)
    assert receipt["semantic_receipt_sha256"] == _semantic_hash(receipt, "semantic_receipt_sha256")
    assert receipt["truth_boundary"]["repository_import_allowed"] is False
    assert set(receipt["authority"].values()) == {False}


def test_delta_preserves_holds_and_rejects_direct_package_installation() -> None:
    delta = _load(DELTA)
    assert delta["semantic_receipt_sha256"] == _semantic_hash(delta, "semantic_receipt_sha256")
    assert delta["collection"]["new_exact_source_objects"] == 2
    assert delta["collection"]["collection_complete"] is False
    assert len(delta["native_fit_census"]) == 15
    assert delta["native_installation"]["previously_installed_clean_room_modules"] == 6
    assert delta["native_installation"]["new_package_source_modules_directly_imported"] == 0
    assert len(delta["residual_exact_byte_holds"]) == 4
    assert set(delta["authority"].values()) == {False}
