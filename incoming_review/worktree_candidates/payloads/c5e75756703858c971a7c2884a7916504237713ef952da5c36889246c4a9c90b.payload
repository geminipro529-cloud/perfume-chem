"""Tests for the append-only authority-false V14 Complex Perfumery capture."""

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
    / "20260816T144500+0700-v14-post-v13-30ml-formula-scaling-6a79b172-nc01c9bfd"
)
PACKAGE = CAPTURE / "Nine_Perfume_All_30mL_Concentrate_Formulas_2026-08-16_v1.zip"
MANIFEST = CAPTURE / "capture_manifest.json"
RECEIPT = (
    ROOT
    / "data"
    / "governance"
    / "complex_perfumery_nine_perfume_30ml_concentrate_formula_package_receipt_20260816.json"
)
DELTA = (
    ROOT / "data" / "governance" / "complex_perfumery_v14_post_v13_collection_delta_20260816.json"
)
REPORT = ROOT / "output" / "quarantine" / "COMPLEX_PERFUMERY_COLLECTION_DELTA_V14_20260816.md"
ROOT_NAME = "Nine_Perfume_All_30mL_Concentrate_Formulas_2026-08-16_v1/"


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


def test_v14_exact_capture_and_source_lineage() -> None:
    assert PACKAGE.stat().st_size == 289626
    assert stable_file_hash(PACKAGE) == (
        "c01c9bfd6e18b17968fd2530c7a548f2c3a41c6d4f74e9e64973aef4c950618e"
    )
    assert MANIFEST.stat().st_size == 5277
    assert stable_file_hash(MANIFEST) == (
        "6b1fa4540b080470299757e967c4f91398af6107dc21fc1ce6384349e531d834"
    )
    capture = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert capture["project"]["parent_v13_delta_sha256"] == (
        "044bb689366e4eaf8b23be956756f2866526d65039da2123cedad9f673faee13"
    )
    assert capture["retrieval"]["source_and_capture_sha256_match"] is True
    assert capture["retrieval"]["regeneration"] is False
    assert capture["collection_delta"]["cumulative_exact_outer_candidates"] == 48
    assert not any(capture["authority"].values())


def test_v14_archive_ledger_manifest_and_formula_index_are_exact() -> None:
    with ZipFile(PACKAGE) as archive:
        _assert_safe_archive(archive)
        assert len(archive.namelist()) == 126

        lines = archive.read(ROOT_NAME + "SHA256SUMS.txt").decode("utf-8-sig").splitlines()
        assert len(lines) == 125
        ledger_names = set()
        for line in lines:
            digest, relative = line.split(None, 1)
            relative = relative.strip().lstrip("*")
            ledger_names.add(relative)
            assert hashlib.sha256(archive.read(ROOT_NAME + relative)).hexdigest() == digest
        assert ledger_names == {
            name.removeprefix(ROOT_NAME)
            for name in archive.namelist()
            if name != ROOT_NAME + "SHA256SUMS.txt"
        }

        embedded_manifest = json.loads(archive.read(ROOT_NAME + "MANIFEST.json"))
        assert len(embedded_manifest["files"]) == 124
        for record in embedded_manifest["files"]:
            payload = archive.read(ROOT_NAME + record["path"])
            assert len(payload) == record["bytes"]
            assert hashlib.sha256(payload).hexdigest() == record["sha256"]

        formula_index = json.loads(archive.read(ROOT_NAME + "FORMULA_INDEX.json"))
        assert formula_index["source_package_sha256"] == (
            "8040367862a0a15cf5852dac395a2f630c80898f3ab734755c00299611f9dd17"
        )
        assert len(formula_index["arms"]) == 110
        assert len(formula_index["perfume_books"]) == 9
        assert formula_index["finished_volume_ul"] == 30000
        assert formula_index["canonical_formula_selected"] is False
        assert "formula_authority" in formula_index["authority_false"]


def test_v14_native_graph_and_strict_receipt_remain_nonpromoting() -> None:
    graph = scan_archive_graph_quarantine(PACKAGE)
    assert graph.status == "CLEAR_FOR_RECEIPT_REVIEW"
    assert len(graph.nodes) == 1
    assert len(graph.edges) == 0
    assert graph.all_nodes_terminal is True
    assert graph.findings == ()
    assert graph.promotion_allowed is False

    receipt = validate_external_package_receipt(json.loads(RECEIPT.read_text(encoding="utf-8")))
    assert receipt["receipt_sha256"] == (
        "77129021cc681a4ccfbba373995890bbd4c83360ea25fe405d282267511537e1"
    )
    verification = verify_external_package_bytes(receipt, package_path=PACKAGE)
    assert verification.status == "VERIFIED_QUARANTINED"
    assert verification.integrity_verified is True
    assert verification.archive_entry_count == verification.archive_file_count == 126
    assert verification.errors == ()
    assert verification.promotion_allowed is False
    assert not any(receipt["authority"].values())


def test_v14_pending_complexity_model_card_is_not_counted_or_admitted() -> None:
    capture = json.loads(MANIFEST.read_text(encoding="utf-8"))
    pending = capture["pending_source_cards"]
    assert len(pending) == 1
    assert pending[0]["sha256"] == (
        "f4be1041bb8e2e8b5665962e580aa740996bd2f77b61299cca1d3cdf55014a5d"
    )
    assert pending[0]["file_object_id"] == "file_000000002ff081faa6a1a57e3fc62d3e"
    assert pending[0]["state"] == (
        "LIVE_ORIGINAL_CARD_LOCAL_DOWNLOAD_PENDING_NO_RECONSTRUCTION_OR_SUBSTITUTION"
    )
    assert capture["collection_delta"]["new_unique_exact_outer_candidates"] == 1
    assert capture["collection_delta"]["all_project_packages_collected"] is False


def test_v14_delta_is_semantically_sealed_and_all_authorities_remain_false() -> None:
    delta = json.loads(DELTA.read_text(encoding="utf-8"))
    unhashed = deepcopy(delta)
    declared = unhashed.pop("semantic_receipt_sha256")
    assert stable_json_hash(unhashed) == declared
    assert delta["state"] == ("V14_EXACT_30ML_FORMULA_SCALING_CAPTURED_QUARANTINED_NOT_ADMITTED")
    assert delta["collection"]["prior_exact_outer_candidates"] == 47
    assert delta["collection"]["new_exact_outer_candidates"] == 1
    assert delta["collection"]["cumulative_exact_outer_candidates"] == 48
    assert delta["decision"]["collection_complete"] is False
    assert delta["decision"]["implementation_complete"] is False
    assert delta["decision"]["package_installation_complete"] is False
    assert delta["decision"]["new_schema_created"] is False
    assert delta["decision"]["new_truth_store_created"] is False
    assert delta["decision"]["new_pipeline_script_created"] is False
    assert not any(delta["authority"].values())

    pending_hashes = {item["sha256"] for item in delta["pending_source_cards"]}
    assert pending_hashes == {"f4be1041bb8e2e8b5665962e580aa740996bd2f77b61299cca1d3cdf55014a5d"}
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
