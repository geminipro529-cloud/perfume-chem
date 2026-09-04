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
    / "chat_a_interaction_atlas_v2_v5_rebase_package_receipt_20260819.json"
)
CAPTURE_DIR = ROOT / "incoming_review" / "chatgpt" / ("20260819T123618Z-chat-a-atlas-v2-6a753afc")
CAPTURE_MANIFEST_PATH = CAPTURE_DIR / "source_manifest.json"
V1_PACKAGE_PATH = ROOT / "incoming_review" / ("Perfumery_Interaction_Layering_Atlas_v1_Package.zip")
PACKAGE_ROOT = "PERFUMERY_INTERACTION_ATLAS_V2_V5_REBASE_20260809"


def _read_json(archive: ZipFile, member: str) -> dict:
    return json.loads(archive.read(f"{PACKAGE_ROOT}/{member}"))


def test_chat_a_atlas_v2_is_exact_v5_rebase_without_scientific_promotion() -> None:
    """Protect exact recovery, V1-row preservation, and the advisory boundary."""

    receipt = load_external_package_receipt(RECEIPT_PATH)
    validate_external_package_receipt(receipt)
    package_path = ROOT / receipt["package"]["locator"]
    verification = verify_external_package_bytes(receipt, package_path=package_path)

    assert verification.integrity_verified is True
    assert verification.status == "VERIFIED_QUARANTINED"
    assert verification.package_sha256 == (
        "e9c4477ea736a5f9f380658ed4dd9e2ab294e01a0e69e565a2a19bb994f50e3e"
    )
    assert verification.archive_entry_count == 14
    assert verification.archive_file_count == 14
    assert verification.promotion_allowed is False
    assert verification.errors == ()
    assert receipt["provenance"]["conversation_id"] == ("6a753afc-c714-83ec-a854-e6fbb3022048")
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
    for parent in receipt["parents"]:
        parent_path = ROOT / parent["artifact_name"]
        assert parent_path.stat().st_size == parent["byte_size"]
        assert hashlib.sha256(parent_path.read_bytes()).hexdigest() == parent["sha256"]

    inventory_snapshot = json.loads(
        (ROOT / "data" / "governance" / "inventory_v5_current_stock_snapshot.json").read_text(
            encoding="utf-8"
        )
    )
    assert inventory_snapshot["source"]["sha256"] == (
        "e36287aca26f34354b3244f07618cb4c12750dfb85db5584dca39d5130025331"
    )

    with ZipFile(package_path) as archive:
        assert archive.testzip() is None
        ledger = _read_json(archive, "SHA256SUMS.json")
        assert len(ledger["entries"]) == 13
        expected_names = {f"{PACKAGE_ROOT}/{relative_path}" for relative_path in ledger["entries"]}
        assert expected_names == set(archive.namelist()) - {f"{PACKAGE_ROOT}/SHA256SUMS.json"}
        for relative_path, expected in ledger["entries"].items():
            payload = archive.read(f"{PACKAGE_ROOT}/{relative_path}")
            assert len(payload) == expected["bytes"]
            assert hashlib.sha256(payload).hexdigest() == expected["sha256"]

        validation = _read_json(archive, "VALIDATION_REPORT.json")
        atlas = _read_json(archive, "Perfumery_Interaction_Layering_Atlas_v2_V5.json")
        source_manifest = _read_json(archive, "SOURCE_MANIFEST.json")
        rebase_rows = list(
            csv.DictReader(
                io.StringIO(
                    archive.read(f"{PACKAGE_ROOT}/GROUP_STOCK_REBASE.csv").decode("utf-8-sig")
                )
            )
        )
        scope_rows = list(
            csv.DictReader(
                io.StringIO(
                    archive.read(f"{PACKAGE_ROOT}/SOURCE_SCOPE_AUDIT.csv").decode("utf-8-sig")
                )
            )
        )

    checks = validation["checks"]
    assert checks["group_count"] == len(atlas["groups"]) == 23
    assert checks["interaction_count"] == len(atlas["interactions"]) == 253
    assert checks["inventory_example_occurrences"] == len(rebase_rows) == 125
    assert checks["v3_to_v5_changed_occurrences"] == 34
    assert checks["physically_ready_occurrences"] == 120
    assert checks["preparation_required_occurrences"] == 4
    assert checks["procurement_pending_occurrences"] == 1
    assert checks["pair_specific_empirical_passes_created"] == 0
    assert checks["exact_stock_refs_fabricated"] == 0

    evidence_classes: dict[str, int] = {}
    for row in atlas["interactions"]:
        evidence_classes[row["evidence_class"]] = evidence_classes.get(row["evidence_class"], 0) + 1
        assert row["pair_specific_empirical_state"] == (
            "NOT_ESTABLISHED_FOR_THIS_FINE_FRAGRANCE_PAIR"
        )
        assert row["formula_authority"] == "ADVISORY_ONLY"
        assert row["inventory_example_authority"] == "V5_REBASED"
    assert evidence_classes == {
        "STRUCTURED HYPOTHESIS": 185,
        "MECHANISTIC PRIMARY + PERFUMERY INFERENCE": 37,
        "DIRECT / DOMAIN PRIMARY": 31,
    }

    physical_states: dict[str, int] = {}
    for row in rebase_rows:
        state = row["physical_compounding_state"]
        physical_states[state] = physical_states.get(state, 0) + 1
    assert physical_states == {
        "PHYSICALLY_READY": 120,
        "PREPARATION_REQUIRED": 4,
        "PROCUREMENT_PENDING": 1,
    }
    held_examples = {
        row["v1_example"]
        for row in rebase_rows
        if row["physical_compounding_state"] != "PHYSICALLY_READY"
    }
    assert held_examples == {
        "Allyl Ionone 10%",
        "Carrot Seed EO 10%",
        "Citronellol 10%",
        "Heliotropal 10%",
        "Ambrettolide 10%",
    }

    new_dois = {row["doi"] for row in source_manifest["web_primary_sources_added"]}
    assert new_dois == {
        "10.1016/j.bbrc.2026.154027",
        "10.1111/ics.13085",
        "10.1016/j.foodchem.2026.150275",
        "10.1016/j.foodchem.2026.147985",
    }
    assert len(scope_rows) == 31
    assert not any(row["pair_upgrade_allowed"] == "YES" for row in scope_rows)

    with ZipFile(V1_PACKAGE_PATH) as v1_archive:
        v1_atlas = json.loads(v1_archive.read("Perfumery_Interaction_Layering_Atlas_v1.json"))
    v2_by_pair = {row["pair_id"]: row for row in atlas["interactions"]}
    assert set(v2_by_pair) == {row["pair_id"] for row in v1_atlas["interactions"]}
    for original in v1_atlas["interactions"]:
        successor = v2_by_pair[original["pair_id"]]
        assert all(successor[key] == value for key, value in original.items())

    graph = scan_archive_graph_quarantine(package_path)
    assert graph.status == "GRAPH_COMPLETE_QUARANTINED"
    assert graph.all_nodes_terminal is True
    assert graph.promotion_allowed is False
    assert "NESTED_ARCHIVE_REQUIRES_CHILD_RECEIPT" in {
        finding.code for node in graph.nodes for finding in node.scan.findings
    }

    summary = receipt["evidence_summary"]
    assert summary["original_chat_a_human_mixture_deliverable_recovered"] is False
    assert summary["atlas_v2_successor_recovered"] is True
    assert summary["v1_interaction_rows_preserved_exactly"] == 253
    assert summary["source_rows_admitted"] == 0
    assert summary["runtime_rows_installed"] == 0
    assert summary["promotion_allowed"] is False
