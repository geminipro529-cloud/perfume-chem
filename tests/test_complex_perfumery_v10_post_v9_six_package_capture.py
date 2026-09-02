"""Tests for the append-only Complex Perfumery V10 six-package capture."""

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
CAPTURE_DIR = (
    ROOT
    / "incoming_review"
    / "chatgpt"
    / "20260815T233019+0700-post-v9-six-package-recovery-6a7992db-n417f58e1"
)

PACKAGES = {
    "compilation": {
        "name": "Perfume_Chem_Latest_State_Compilation_2026-08-12_v1.zip",
        "bytes": 41882040,
        "sha256": "417f58e1e471b62dc7d04b7dc817a64b8b4b1d1fb343bb243f02e95fb7ae3418",
        "receipt": "complex_perfumery_latest_state_compilation_package_receipt_20260815.json",
        "semantic": "911fe82822628e631c0680f37b95637697b0ec70e8cae5752797d472b12606fe",
        "entries": 112,
        "graph": ("INTEGRITY_HOLD", 20, 69, 2, False, 24),
    },
    "bridge": {
        "name": "Perfume_Chem_Cloud_Work_Chat_Latest_State_PC-LATEST-STATE-SYNC-20260812T103344Z-6153a337.zip",
        "bytes": 41858464,
        "sha256": "27584a816df351d01bc040e616fef77c1aa3a7e9ac91910a6c04e0220c514aeb",
        "receipt": "complex_perfumery_latest_state_bridge_package_receipt_20260815.json",
        "semantic": "7f3fd9fbccb8501e4fda38eacd8c01adb5d7653be98ce5c92e908693aebabaa8",
        "entries": 10,
        "graph": ("INTEGRITY_HOLD", 1, 0, 0, False, 1),
    },
    "opus": {
        "name": "Amouage_Opus_V_Hedonic_Regeneration_2026-08-12_v1.zip",
        "bytes": 549190,
        "sha256": "123575c756a878950d49f71f9bd9dcd420a837b886833b1de57139c8cdc6d81b",
        "receipt": "complex_perfumery_opus_v_hedonic_regeneration_package_receipt_20260815.json",
        "semantic": "ac21c236aa5e2b1fc5170e546853c02cb084035ff799ea6a4128dd3941883b29",
        "entries": 21,
        "graph": ("GRAPH_COMPLETE_QUARANTINED", 2, 1, 1, True, 0),
    },
    "architecture": {
        "name": "Nine_Perfume_Complexity_Module_Architecture_2026-08-15_v1.zip",
        "bytes": 443317,
        "sha256": "09318ed20c9c29c6d0f171a4333f74fde4d9c3f213ac64eca53997d4e5c20f3b",
        "receipt": "complex_perfumery_nine_perfume_architecture_package_receipt_20260815.json",
        "semantic": "21b3836348f85bd6bd60a3e59888736daa2115784fd309085c53da3dadb62d0f",
        "entries": 22,
        "graph": ("GRAPH_COMPLETE_QUARANTINED", 2, 1, 1, True, 0),
    },
    "completion": {
        "name": "Nine_Perfume_Module_Isolate_Completion_Suite_2026-08-15_v1.zip",
        "bytes": 1892230,
        "sha256": "d3ce4e261539ff5a598eca1d40836a093f0e7b356db6971cd7025b8437173c3c",
        "receipt": "complex_perfumery_nine_perfume_completion_suite_package_receipt_20260815.json",
        "semantic": "c1de019eea72d0607c47b4d1fb8da29ba704596a92e0767bb9742f25c29e21a7",
        "entries": 98,
        "graph": ("GRAPH_COMPLETE_QUARANTINED", 7, 7, 2, True, 0),
    },
    "phase2": {
        "name": "Nine_Perfume_Complexity_Phase2_Execution_2026-08-15_v1.zip",
        "bytes": 520843,
        "sha256": "ec5789c0e996f99ddc8538fbfc2fa28224e5ca6041de6ee615ebd58a22a0aceb",
        "receipt": "complex_perfumery_nine_perfume_phase2_execution_package_receipt_20260815.json",
        "semantic": "f1f4d88edd80d9701ac90e33fadefbbc758389d7c024765a418529d34d1163f1",
        "entries": 21,
        "graph": ("GRAPH_COMPLETE_QUARANTINED", 2, 1, 1, True, 0),
    },
}


def _receipt(spec: dict[str, object]) -> dict[str, object]:
    path = ROOT / "data" / "governance" / str(spec["receipt"])
    return json.loads(path.read_text(encoding="utf-8"))


def test_v10_capture_manifest_and_outer_receipts_replay_exactly() -> None:
    manifest_path = CAPTURE_DIR / "capture_manifest.json"
    assert manifest_path.stat().st_size == 13908
    assert stable_file_hash(manifest_path) == (
        "75e9c7283658fce987cef67b3b3dcdfa5da2b3b16d164355d7b7c0563551d39f"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert len(manifest["captured_artifacts"]) == 6
    assert manifest["cross_artifact_lineage"][0]["relation"] == (
        "CHILD_BRIDGE_EMBEDS_EXACT_PARENT_COMPILATION_BYTES"
    )
    assert not any(manifest["authority"].values())

    for spec in PACKAGES.values():
        package_path = CAPTURE_DIR / str(spec["name"])
        assert package_path.stat().st_size == spec["bytes"]
        assert stable_file_hash(package_path) == spec["sha256"]
        receipt = _receipt(spec)
        assert validate_external_package_receipt(receipt)["receipt_sha256"] == spec["semantic"]
        result = verify_external_package_bytes(receipt, package_path=package_path)
        assert result.integrity_verified is True
        assert result.status == "VERIFIED_QUARANTINED"
        assert result.archive_entry_count == result.archive_file_count == spec["entries"]
        assert result.errors == ()
        assert result.promotion_allowed is False
        assert not any(receipt["authority"].values())


def test_v10_archives_are_safe_and_embedded_ledgers_replay() -> None:
    roots = {
        "bridge": "PC-LATEST-STATE-SYNC-20260812T103344Z-6153a337/",
        "opus": "Amouage_Opus_V_Hedonic_Regeneration_2026-08-12_v1/",
        "architecture": "Nine_Perfume_Complexity_Module_Architecture_2026-08-15_v1/",
        "completion": "Nine_Perfume_Module_Isolate_Completion_Suite_2026-08-15_v1/",
        "phase2": "Nine_Perfume_Complexity_Phase2_Execution_2026-08-15_v1/",
    }
    for key, spec in PACKAGES.items():
        with ZipFile(CAPTURE_DIR / str(spec["name"])) as archive:
            names = [info.filename for info in archive.infolist()]
            assert archive.testzip() is None
            assert len(names) == len({name.casefold() for name in names}) == spec["entries"]
            assert all(
                not PurePosixPath(name).is_absolute()
                and ".." not in PurePosixPath(name).parts
                and "\\" not in name
                for name in names
            )
            if key == "compilation":
                root = "Perfume_Chem_Latest_State_Compilation_2026-08-12_v1/"
                ledger = json.loads(archive.read(root + "metadata/SHA256SUMS.json"))
                assert len(ledger["files"]) == 109
                for record in ledger["files"]:
                    payload = archive.read(root + record["path"])
                    assert len(payload) == record["bytes"]
                    assert hashlib.sha256(payload).hexdigest() == record["sha256"]
                continue
            root = roots[key]
            lines = archive.read(root + "SHA256SUMS.txt").decode("utf-8-sig").splitlines()
            assert len(lines) == spec["entries"] - 1
            for line in lines:
                digest, relative = line.split(None, 1)
                relative = relative.strip().lstrip("*")
                assert hashlib.sha256(archive.read(root + relative)).hexdigest() == digest


def test_v10_cross_artifact_lineage_is_byte_exact() -> None:
    compilation = CAPTURE_DIR / str(PACKAGES["compilation"]["name"])
    architecture = CAPTURE_DIR / str(PACKAGES["architecture"]["name"])
    with ZipFile(CAPTURE_DIR / str(PACKAGES["bridge"]["name"])) as bridge:
        embedded = bridge.read(
            "PC-LATEST-STATE-SYNC-20260812T103344Z-6153a337/artifacts/"
            "Perfume_Chem_Latest_State_Compilation_2026-08-12_v1.zip"
        )
    assert len(embedded) == compilation.stat().st_size
    assert hashlib.sha256(embedded).hexdigest() == stable_file_hash(compilation)

    with ZipFile(CAPTURE_DIR / str(PACKAGES["completion"]["name"])) as completion:
        embedded = completion.read(
            "Nine_Perfume_Module_Isolate_Completion_Suite_2026-08-15_v1/ancestry/"
            "Nine_Perfume_Complexity_Module_Architecture_2026-08-15_v1.zip"
        )
    assert len(embedded) == architecture.stat().st_size
    assert hashlib.sha256(embedded).hexdigest() == stable_file_hash(architecture)

    with (
        ZipFile(architecture) as parent,
        ZipFile(CAPTURE_DIR / str(PACKAGES["phase2"]["name"])) as phase2,
    ):
        for filename in (
            "NINE_PERFUME_COMPLEXITY_ARCHITECTURE.json",
            "NINE_PERFUME_COMPLEXITY_MODULE_REPORT.md",
            "VALIDATION_REPORT.md",
        ):
            parent_bytes = parent.read(
                "Nine_Perfume_Complexity_Module_Architecture_2026-08-15_v1/" + filename
            )
            child_bytes = phase2.read(
                "Nine_Perfume_Complexity_Phase2_Execution_2026-08-15_v1/parent/" + filename
            )
            assert child_bytes == parent_bytes


def test_v10_native_graph_states_remain_fail_closed() -> None:
    for spec in PACKAGES.values():
        graph = scan_archive_graph_quarantine(CAPTURE_DIR / str(spec["name"]))
        status, nodes, edges, depth, terminal, findings = spec["graph"]
        assert graph.status == status
        assert len(graph.nodes) == nodes
        assert len(graph.edges) == edges
        assert graph.resource_usage.max_depth == depth
        assert graph.all_nodes_terminal is terminal
        assert len(graph.findings) == findings
        assert graph.promotion_allowed is False


def test_v10_successor_preserves_parent_and_all_holds() -> None:
    path = (
        ROOT / "output" / "quarantine" / "COMPLEX_PERFUMERY_COLLECTION_SUCCESSOR_V10_20260815.json"
    )
    successor = json.loads(path.read_text(encoding="utf-8"))
    assert successor["parent"] == {
        "path": "output/quarantine/COMPLEX_PERFUMERY_COLLECTION_SUCCESSOR_V9_20260815.json",
        "bytes": 7362,
        "sha256": "b9e573e94d787cfd5f80cb914ad37bfd8ce3581ac18c443635abd9d7cb16794b",
        "relationship": "SUPERSEDES_WITHOUT_MUTATING_PARENT",
    }
    parent_path = ROOT / successor["parent"]["path"]
    assert parent_path.stat().st_size == successor["parent"]["bytes"]
    assert stable_file_hash(parent_path) == successor["parent"]["sha256"]
    assert successor["cumulative_exact_outer_candidates"] == 41
    assert successor["new_exact_outer_candidates"] == 6
    assert successor["post_v9_source_card_identities_captured"] == 6
    assert successor["optional_identities_remaining"] == 1
    assert successor["installation_critical_exact_byte_blocker"]["state"] == (
        "EXPLICIT_UNAVAILABLE_PARENT_BYTES"
    )
    assert successor["native_fit"]["migration_required"] is False
    assert successor["native_fit"]["migration_head_remains"] == "20260810_0016"
    assert successor["native_fit"]["new_truth_store_allowed"] is False
    assert successor["native_fit"]["new_pipeline_script_allowed"] is False
    assert successor["collection_complete"] is False
    assert successor["implementation_complete"] is False
    assert successor["installation_authorized"] is False
    assert not any(successor["authority"].values())


def test_v10_ledger_and_acceptance_replay_exactly() -> None:
    ledger_path = (
        ROOT / "output" / "quarantine" / "COMPLEX_PERFUMERY_HANDOFF_SHA256SUMS_V10_20260815.txt"
    )
    entries = []
    for line in ledger_path.read_text(encoding="utf-8").splitlines():
        digest, byte_size, relative_path = line.split("  ", 2)
        entries.append((digest, int(byte_size), relative_path))
    assert len(entries) == 19
    assert len({relative_path for _, _, relative_path in entries}) == 19
    for digest, byte_size, relative_path in entries:
        artifact_path = ROOT / relative_path
        assert artifact_path.stat().st_size == byte_size
        assert stable_file_hash(artifact_path) == digest

    acceptance_path = (
        ROOT
        / "data"
        / "governance"
        / "complex_perfumery_v10_post_v9_six_package_collection_acceptance_20260815.json"
    )
    acceptance = json.loads(acceptance_path.read_text(encoding="utf-8"))
    unhashed = deepcopy(acceptance)
    declared_hash = unhashed.pop("receipt_sha256")
    assert stable_json_hash(unhashed) == declared_hash
    assert acceptance["state"] == "SIX_POST_V9_EXACT_PACKAGES_CAPTURED_AUTHORITY_FALSE"
    assert acceptance["repository_fence"]["staged_paths"] == 0
    assert acceptance["verification"]["receipt_tests_failed"] == 0
    assert acceptance["decision"]["v9_parent_mutated"] is False
    assert acceptance["decision"]["optional_identities_remaining"] == 1
    assert acceptance["decision"]["collection_complete"] is False
    assert acceptance["decision"]["installation_authorized"] is False
    assert not any(acceptance["authority"].values())
    for artifact in acceptance["applied_artifacts"]:
        artifact_path = ROOT / artifact["path"]
        assert artifact_path.stat().st_size == artifact["byte_size"]
        assert stable_file_hash(artifact_path) == artifact["sha256"]
